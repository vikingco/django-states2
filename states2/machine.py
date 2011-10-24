__all__ = ('StateMachine', 'StateDefinition', 'StateTransition')

from collections import defaultdict
import logging

from states2.exceptions import TransitionNotFound, TransitionValidationError, UnknownState


logger = logging.getLogger(__name__)


class StateMachineMeta(type):
    def __new__(c, name, bases, attrs):
        """
        Validate state machine, and make ``states``, ``transitions`` and
        ``initial_state`` attributes available.
        """
        states = {}
        transitions = {}
        groups = {}
        initial_state = None
        for a in attrs:
            # All definitions are derived from StateDefinition and should be
            # addressable by Machine.states
            if isinstance(attrs[a], StateDefinitionMeta):
                states[a] = attrs[a]
                logger.debug('Found state: %s' % states[a].get_name())
                if states[a].initial:
                    logger.debug('Found initial state: %s' % states[a].get_name())
                    if not initial_state:
                        initial_state = a
                    else:
                        raise Exception('Machine defines multiple initial states')

            # All transitions are derived from StateTransition and should be
            # addressable by Machine.transitions
            if isinstance(attrs[a], StateTransitionMeta):
                transitions[a] = attrs[a]
                logger.debug('Found state transition: %s' % transitions[a].get_name())

            # All definitions derived from StateGroup
            # should be addressable by Machine.groups
            if isinstance(attrs[a], StateGroupMeta):
                groups[a] = attrs[a]
                logger.debug('Found state group: %s' % groups[a].get_name())

        # At least one initial state required. (But don't throw error for the
        # base defintion.)
        if not initial_state and bases != (object,):
            raise MachineDefinitionException(c, 'Machine does not define initial state')

        attrs['states'] = states
        attrs['transitions'] = transitions
        attrs['initial_state'] = initial_state
        attrs['groups'] = groups

        # Give all state transitions a 'to_state_description' attribute.
        # by copying the description from the state definition. (no
        # from_state_description, because multiple from-states are possible.)
        for t in transitions.values():
            t.to_state_description = states[t.to_state].description

        return type.__new__(c, name, bases, attrs)

    def has_transition(self, transition_name):
        return transition_name in self.transitions

    def get_transitions(self, transition_name):
        return self.transitions[transition_name]

    def has_state(self, state_name):
        return state_name in self.states

    def get_state(self, state_name):
        try:
            return self.states[state_name]
        except KeyError:
            raise UnknownState(state_name)

    def get_transition_from_states(self, from_state, to_state):
        for t in self.transitions.values():
            if from_state in t.from_states and t.to_state == to_state:
                return t
        raise TransitionNotFound(self, from_state, to_state)

    def get_state_groups(self, state_name):
        '''
        Get a dict of state groups, which will be either ``True`` or ``False``
        if the current state is specified in that group.

        :param str state_name: the current state
        '''
        result = defaultdict(lambda: False)
        for group in self.groups:
            result[group] = state_name in self.groups[group]
        return result


class StateDefinitionMeta(type):
    def __new__(c, name, bases, attrs):
        """
        Validate state definition
        """
        if bases != (object,):
            if name.lower() != name:
                raise Exception('Please use lowercase names for state definitions (instead of %s)' % name)
            if not 'description' in attrs:
                raise Exception('Please give a description to this state definition')

        if 'handler' in attrs and len(attrs['handler'].func_code.co_varnames) < 2:
            raise Exception('StateDefinition handler needs at least twoarguments')

        # Turn `handler` into classmethod
        if 'handler' in attrs:
            attrs['handler'] = classmethod(attrs['handler'])

        return type.__new__(c, name, bases, attrs)


class StateGroupMeta(type):
    def __new__(c, name, bases, attrs):
        """
        Validate state group definition
        """
        if bases != (object,):
            if name.lower() != name:
                raise Exception('Please use lowercase names for state groups (instead of %s)' % name)
            if not 'description' in attrs or not attrs['description']:
                raise Exception('Please give a description to this state group')
            if not 'states' in attrs or not isinstance(attrs['states'], (list, set)):
                raise Exception('Please give a list (or set) of states to this state group')

        return type.__new__(c, name, bases, attrs)


class StateTransitionMeta(type):
    def __new__(c, name, bases, attrs):
        if bases != (object,):
            if 'from_state' in attrs and 'from_states' in attrs:
                raise Exception('Please use either from_state or from_states')
            if 'from_state' in attrs:
                attrs['from_states'] = [attrs['from_state']]
            if not 'from_states' in attrs:
                raise Exception('Please give a from_state to this state transition')
            if not 'to_state' in attrs:
                raise Exception('Please give a from_state to this state transition')
            if not 'description' in attrs:
                raise Exception('Please give a description to this state transition')

        if 'handler' in attrs and len(attrs['handler'].func_code.co_varnames) < 3:
            raise Exception('StateTransition handler needs at least three arguments')

        # Turn `has_permission` and `handler` into classmethods
        for m in ('has_permission', 'handler', 'validate'):
            if m in attrs:
                attrs[m] = classmethod(attrs[m])

        return type.__new__(c, name, bases, attrs)

    def __unicode__(self):
        return '%s: (from %s to %s)' % (unicode(self.description), ' or '.join(self.from_states), self.to_state)


class StateMachine(object):
    """ Base class for a state machine definition """
    __metaclass__ = StateMachineMeta

    #: Log transitions? Log by default.
    log_transitions = True

    @classmethod
    def get_admin_actions(cls):
        """
        Create a list of actions for use in the Django Admin.
        """
        actions = []

        def create_action(transition_name):
            def action(modeladmin, request, queryset):
                # Dry run first
                for o in queryset:
                    try:
                        o.test_transition(transition_name, request.user)
                    except TransitionException, e:
                        modeladmin.message_user(request, 'ERROR: %s on: %s' % (e.message, unicode(o)))
                        return

                # Make actual transitions
                for o in queryset:
                    o.make_transition(transition_name, request.user)

                # Feeback
                modeladmin.message_user(request, _('State changed for %s objects.' % len(queryset)))

            action.short_description = unicode(cls.transitions[transition_name])
            action.__name__ = 'state_transition_%s' % transition_name
            return action

        for t in cls.transitions.keys():
            actions.append(create_action(t))

        return actions

    @classmethod
    def get_state_choices(cls):
        'Get all possible states'
        return [(k, cls.states[k].description) for k in cls.states.keys()]


class StateDefinition(object):
    """ Base class for a state definition """
    __metaclass__ = StateDefinitionMeta

    #: Is this the initial state?  Not initial by default. The machine should
    # define at least one state where ``initial=True``
    initial = False

    def handler(cls, instance):
        """
        Override this method if some specific actions need
        to be executed *after arriving* in this state.
        """
        pass

    @classmethod
    def get_name(cls):
        """
        The name of the state is given by its classname
        """
        return cls.__name__


class StateGroup(object):
    "Base class for a state groups"
    __metaclass__ = StateGroupMeta

    #: Description for this state group
    description = None

    @classmethod
    def get_name(cls):
        """
        The name of the state group is given by its classname
        """
        return cls.__name__


class StateTransition(object):
    """ Base class for a state transitions """
    __metaclass__ = StateTransitionMeta

    #: When a transition has been defined as public, is meant to be seen
    #: by the end-user.
    public = False

    def has_permission(cls, instance, user):
        """
        Check whether this user is allowed to execute this state transition on
        this object. You can override this function for every StateTransition.
        """
        return user.is_superuser
        # By default, only superusers are allowed to execute this transition.
        # Note that this is the only permission checking for the POST views.

    def validate(cls, instance):
        """
        Validate whether this object is valid to make this state transition.
        Yields a list of TransitionValidationError. You can override this
        function for every StateTransition.
        """
        if False:
            yield TransitionValidationError('Example error')
        # Don't use the 'raise'-statement in here, just yield all the errors.
        # yield TransitionValidationError("This object needs ....")
        # yield TransitionValidationError("Another error ....")

    def handler(cls, instance, user):
        """
        Override this method if some specific actions need
        to be executed during this state transition.
        """
        pass

    @classmethod
    def get_name(cls):
        """
        The name of the state transition is always given by its classname
        """
        return cls.__name__

    @property
    def handler_kwargs(self):
        return self.handler.func_code.co_varnames[3:]
