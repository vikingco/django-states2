# -*- coding: utf-8 -*-
"""State Machine"""
from __future__ import absolute_import
import six

__all__ = ('StateMachine', 'StateDefinition', 'StateTransition')

from collections import defaultdict
import logging

from django.contrib import messages
from django_states.exceptions import (TransitionNotFound, TransitionValidationError,
                                UnknownState, TransitionException, MachineDefinitionException)
from django.utils.encoding import python_2_unicode_compatible


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
        for t in list(transitions.values()):
            t.to_state_description = states[t.to_state].description

        return type.__new__(c, name, bases, attrs)

    def has_transition(self, transition_name):
        """
        Gets whether a transition with the given name is defined in the
        machine.

        :param str transition_name: the transition name

        :returns: ``True`` or ``False``
        """
        return transition_name in self.transitions

    def get_transitions(self, transition_name):
        """
        Gets a transition with the given name.

        :param str transition_name: the transition name

        :returns: the :class:`StateTransition` or raises a :class:`KeyError`
        """
        return self.transitions[transition_name]

    def has_state(self, state_name):
        """
        Gets whether a state with given name is defined in the machine.

        :param str state_name: the state name

        :returns: ``True`` or ``False``
        """
        return state_name in self.states

    def get_state(self, state_name):
        """
        Gets the state with given name

        :param str state_name: the state name

        :returns: a :class:`StateDefinition` or raises
            a :class:`~django_states.exceptions.UnknownState`
        """
        try:
            return self.states[state_name]
        except KeyError:
            raise UnknownState(state_name)

    def get_transition_from_states(self, from_state, to_state):
        """
        Gets the transitions between 2 specified states.

        :param str from_state: the from state
        :param str to_state: the to state

        :returns: a :class:`StateTransition` or raises
            a :class:`~django_states.exceptions.TransitionNotFound`
        """
        for t in list(self.transitions.values()):
            if from_state in t.from_states and t.to_state == to_state:
                return t
        raise TransitionNotFound(self, from_state, to_state)

    def get_state_groups(self, state_name):
        """
        Gets a :class:`dict` of state groups, which will be either ``True`` or
        ``False`` if the current state is specified in that group.

        .. note:: That groups that are not defined will still return ``False``
            and not raise a ``KeyError``.

        :param str state_name: the current state
        """
        result = defaultdict(lambda: False)
        for group in self.groups:
            sg = self.groups[group]
            if hasattr(sg, 'states'):
                result[group] = state_name in sg.states
            elif hasattr(sg, 'exclude_states'):
                result[group] = not state_name in sg.exclude_states
        return result


class StateDefinitionMeta(type):
    def __new__(c, name, bases, attrs):
        """
        Validate state definition
        """
        if bases != (object,):
            if name.lower() != name and not attrs.get('abstract', False):
                raise Exception('Please use lowercase names for state definitions (instead of %s)' % name)
            if not 'description' in attrs and not attrs.get('abstract', False):
                raise Exception('Please give a description to this state definition')

        if 'handler' in attrs and len(attrs['handler'].__code__.co_varnames) < 2:
            raise Exception('StateDefinition handler needs at least two arguments')

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
            # check attributes
            if 'states' in attrs and 'exclude_states' in attrs:
                raise Exception('Use either states or exclude_states but not both')
            elif not 'states' in attrs and not 'exclude_states' in attrs:
                raise Exception('Please specify states or exclude_states to this state group')
            # check type of attributes
            if 'exclude_states' in attrs and not isinstance(attrs['exclude_states'], (list, set)):
                raise Exception('Please give a list (or set) of states to this state group')
            elif 'states' in attrs and not isinstance(attrs['states'], (list, set)):
                raise Exception('Please give a list (or set) of states to this state group')

        return type.__new__(c, name, bases, attrs)


@python_2_unicode_compatible
class StateTransitionMeta(type):
    def __new__(c, name, bases, attrs):
        """
        Validate state transition definition
        """
        if bases != (object,):
            if 'from_state' in attrs and 'from_states' in attrs:
                raise Exception('Please use either from_state or from_states')
            if 'from_state' in attrs:
                attrs['from_states'] = (attrs['from_state'],)
                del attrs['from_state']
            if not 'from_states' in attrs:
                raise Exception('Please give a from_state to this state transition')
            if not 'to_state' in attrs:
                raise Exception('Please give a from_state to this state transition')
            if not 'description' in attrs:
                raise Exception('Please give a description to this state transition')

        if 'handler' in attrs and len(attrs['handler'].__code__.co_varnames) < 3:
            raise Exception('StateTransition handler needs at least three arguments')

        # Turn `has_permission` and `handler` into classmethods
        for m in ('has_permission', 'handler', 'validate'):
            if m in attrs:
                attrs[m] = classmethod(attrs[m])

        return type.__new__(c, name, bases, attrs)

    def __str__(self):
        return '%s: (from %s to %s)' % (six.text_type(self.description), ' or '.join(self.from_states), self.to_state)


class StateMachine(six.with_metaclass(StateMachineMeta, object)):
    """
    Base class for a state machine definition
    """

    #: Log transitions? Log by default.
    log_transitions = True

    @classmethod
    def get_admin_actions(cls, field_name='state'):
        """
        Creates a list of actions for use in the Django Admin.
        """
        actions = []

        def create_action(transition_name):
            def action(modeladmin, request, queryset):
                # Dry run first
                for o in queryset:
                    get_STATE_info = getattr(o, 'get_%s_info' % field_name)
                    try:
                        get_STATE_info().test_transition(transition_name,
                                                       request.user)
                    except TransitionException as e:
                        modeladmin.message_user(request, 'ERROR: %s on: %s' % (e.message, six.text_type(o)),
                                                level=messages.ERROR)
                        return

                # Make actual transitions
                for o in queryset:
                    get_STATE_info = getattr(o, 'get_%s_info' % field_name)
                    get_STATE_info().make_transition(transition_name,
                                                   request.user)

                # Feeback
                modeladmin.message_user(request, 'State changed for %s objects.' % len(queryset))

            action.short_description = six.text_type(cls.transitions[transition_name])
            action.__name__ = 'state_transition_%s' % transition_name
            return action

        for t in list(cls.transitions.keys()):
            actions.append(create_action(t))

        return actions

    @classmethod
    def get_state_choices(cls):
        """
        Gets all possible choices for a model.
        """
        return [(k, cls.states[k].description) for k in list(cls.states.keys())]


class StateDefinition(six.with_metaclass(StateDefinitionMeta, object)):
    """
    Base class for a state definition
    """

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


class StateGroup(six.with_metaclass(StateGroupMeta, object)):
    """
    Base class for a state groups
    """

    #: Description for this state group
    description = ''

    @classmethod
    def get_name(cls):
        """
        The name of the state group is given by its classname
        """
        return cls.__name__


class StateTransition(six.with_metaclass(StateTransitionMeta, object)):
    """
    Base class for a state transitions
    """

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
        Validates whether this object is valid to make this state transition.

        Yields a list of
        :class:`~django_states.exceptions.TransitionValidationError`. You can
        override this function for every StateTransition.
        """
        if False:
            yield TransitionValidationError('Example error')  # pragma: no cover
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
        return self.handler.__code__.co_varnames[3:]
