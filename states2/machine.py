__all__ = ('StateMachine', 'StateDefinition', 'StateTransition')

from states2.exceptions import TransitionNotFound, TransitionValidationError


class StateMachineMeta(type):
    def __new__(c, name, bases, attrs):
        """
        Validate state machine, and make `states`, `transitions` and
        `initial_state` attributes available.
        """
        states = {}
        transitions = {}
        initial_state = None
        for a in attrs:
            # All definitions derived from StateDefinition
            # should be addressable by Machine.states
            if isinstance(attrs[a], StateDefinitionMeta):
                states[a] = attrs[a]
                if states[a].initial:
                    if not initial_state:
                        initial_state = a
                    else:
                        raise Exception('Machine defines multiple initial states')

            # All definitions derived from StateTransitionMeta
            # should be addressable by Machine.transitions
            if isinstance(attrs[a], StateTransitionMeta):
                transitions[a] = attrs[a]

        # At least one initial state required. (But don't throw error for the base defintion.)
        if not initial_state and bases != (object,):
            raise MachineDefinitionException(c, 'Machine does not define initial state')

        attrs['states'] = states
        attrs['transitions'] = transitions
        attrs['initial_state'] = initial_state

        # Give all state transitions a 'to_state_description' attribute.
        # by copying the description from the state definition. (no from_state_description,
        # because multiple from-states are possible.)
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
        return self.states[state_name]

    def get_transition_from_states(self, from_state, to_state):
        for t in self.transitions.values():
            if t.from_state == from_state and t.to_state == to_state:
                return t
        raise TransitionNotFound(self, from_state, to_state)


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


class StateTransitionMeta(type):
    def __new__(c, name, bases, attrs):
        if bases != (object,):
            if not 'from_state' in attrs:
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
        return '%s: (from %s to %s)' % (unicode(self.description), self.from_state, self.to_state)


class StateMachine(object):
    """ Base class for a state machine definition """
    __metaclass__ = StateMachineMeta

    # Log transitions by default
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

    # Not initial by default. The machine should define at least one state
    # where initial=True
    initial = False

    def handler(cls, instance):
        """
        Override this method if some specific actions need
        to be executed *after arriving* in this state.
        """
        pass


class StateTransition(object):
    """ Base class for a state transitions """
    __metaclass__ = StateTransitionMeta

    # When a transition has been defined as public, is meant to be seen
    # by the end-user.
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
