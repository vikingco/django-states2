# Author: Jonathan Slenders, CityLive

__doc__ = \
"""

Base models for every State.

"""


__all__ = ('StateMachine', 'StateDefinition', 'StateTransition', 'State')

from django.contrib.auth.models import User
from django.db import models
from django.db.models.base import ModelBase
from django.utils.translation import ugettext_lazy as _
from functools import wraps
from states2.fields import StateField
from states2.exceptions import *

import copy
import datetime


# =======================[ Helper classes ]=====================

class MachineDefinitionException(Exception):
    def __init__(self, machine, description):
        Exception.__init__(self, 'Error in state machine definition: ' + description)


class StateMachineMeta(type):
    def __new__(c, name, bases, attrs):
        """
        Validate state machine, and make `states`, `transitions` and
        `initial_state` attributes available.
        """
        states = { }
        transitions = { }
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
                        raise Exception('Machine defined multiple initial states')

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
        raise Exception("Transition not found")


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

        # Turn `has_permission` and `handler` into classmethods
        for m in ('has_permission', 'handler'):
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


class StateDefinition(object):
    """ Base class for a state definition """
    __metaclass__ = StateDefinitionMeta

    # Not initial by default. The machine should define at least one state
    # where initial=True
    initial = False


class StateTransition(object):
    """ Base class for a state transitions """
    __metaclass__ = StateTransitionMeta

    # When a transition has been defined as public, is meant to be seen
    # by the end-user.
    public = False

    def has_permission(cls, instance, user):
        """ Override this method for special checking.  """
        return True

    def handler(cls, instance, user):
        """
        Override this method if some specific actions need
        to be executed during this state transition.
        """
        pass


# =======================[ State ]=====================

class StateBase(ModelBase):
    """
    Metaclass for State models.
    This metaclass will initiate a logging model as well, if required.
    """
    def __new__(cls, name, bases, attrs):
        """
        Instantiation of the State type.
        When this type is created, also create logging model if required.
        """
        # Call class constructor of parent
        state_model = ModelBase.__new__(cls, name, bases, attrs)

        # If we need logging, create logging model
        if state_model.Machine.log_transitions:
            state_model._log = state_model._create_state_log_model(name)
        else:
            state_model._log = None

        # Link default value for the State Machine
        for f in state_model._meta.fields:
            if f.name == 'value':
                f.default = state_model.Machine.initial_state

        return state_model


class StateManager(models.Manager):
    pass


class State(models.Model):
    """
    Every state table should inherit this model.
    """
    updated_on = models.DateTimeField(auto_now=True, default=datetime.datetime.now)
    #value = models.CharField(max_length=64, choices=get_state_choices(), default='0', verbose_name=_('state id'))
    value = models.CharField(max_length=64, default='0', verbose_name=_('state id'))

    objects = StateManager()

    __metaclass__ = StateBase

    class Machine(StateMachine):
        """
        Example machine definition. State machines should not override this,
        but create a new machine by inheriting directly from StateMachine.
        """
        # True when we should log all transitions
        log_transitions = False

        # Definition of states (mapping from state_slug to description)
        class initial(StateDefinition):
            initial=True
            description = _('Initial state')

        # Possible transitions, and their names
        class dummy(StateTransition):
            from_state='initial'
            to_state='initial'
            description = _('Make dummy state transition')

    class Meta:
        verbose_name = _('state')
        verbose_name_plural = _('states')
        abstract = True

    def __unicode__(self):
        return 'State: ' + self.value

    @property
    def transitions(self):
        """
        Return state transitions log model.
        """
        if self._log:
            return self.all_transitions # Almost similar to: self._log.objects.filter(on=self)
        else:
            raise Exception('This model does not log state transitions. please enable it by setting log_transitions=True')

    @property
    def public_transitions(self):
        """
        Return the transitions which are meant to be seen by the customer. (The
        admin on the other hand should be able to see everything.)
        """
        if self._log:
            return filter(lambda t: t.is_public and t.state.completed, self.transitions.all())
        else:
            return []

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

            action.short_description = unicode(cls.Machine.transitions[transition_name])
            action.__name__ = 'state_transition_%s' % transition_name
            return action

        for t in cls.Machine.transitions.keys():
            actions.append(create_action(t))

        return actions

    @property
    def description(self):
        """
        Get the full description of the (current) state
        """
        return self.Machine.states[self.value].description

    def _test_transition(self, transition, instance, user=None):
        """
        Return True when we exect this transition to be executed succesfully.
        Raise Exception when this transition is impossible.
        """
        # Transition name should be known
        if not self.Machine.has_transition(transition):
            raise UnknownTransition(instance, transition)
        t = self.Machine.get_transitions(transition)

        if self.value not in t.from_state:
            raise TransitionCannotStart(instance, transition)

        # User should have permissions for this transition
        if not t.has_permission(instance, user):
            raise PermissionDenied(instance, transition, user)
        return True

    def _make_transition(self, transition, instance, user=None):
        """
        Execute state transition
        user: the user executing the transition
        instance: the object which will undergo the state transition.
        """
        # Transition name should be known
        if not self.Machine.has_transition(transition):
            raise UnknownTransition(instance, transition)
        t = self.Machine.get_transitions(transition)

        # Start transition log
        if self._log:
            transition_log = self._log.objects.create(on=self, from_state=self.value, to_state=t.to_state, user=user)

        # Transition should start from here
        if self.value not in t.from_state:
            if self._log: transition_log.make_transition('fail')
            raise TransitionCannotStart(instance, transition)

        # User should have permissions for this transition
        if not t.has_permission(instance, user):
            if self._log: transition_log.make_transition('fail')
            raise PermissionDenied(instance, transition, user)

        # Execute
        if self._log: transition_log.make_transition('start')

        try:
            t.handler(instance, user)
            self.value = t.to_state
            self.save()
            if self._log: transition_log.make_transition('complete')
        except Exception, e:
            if self._log: transition_log.make_transition('fail')
            raise e

    @classmethod
    def get_state_choices(cls):
        return cls.Machine.states.items()


    @classmethod
    def _create_state_log_model(cls, name):
        """
        Create a new model for logging the state transitions.
        """
        class _StateTransitionStateMeta(StateBase):
            """
            Make _StateTransitionState act like it has another name,
            and was defined in another model.
            """
            def __new__(c, name, bases, attrs):
                attrs[ '__module__'] = cls.__module__
                return StateBase.__new__(c, '%s_StateTransitionState' % cls.__name__, bases, attrs)

        class _StateTransitionState(State):
            """
            Log the progress of every individual state transition.
            """
            __metaclass__ = _StateTransitionStateMeta
            class Machine(StateMachine):
                # We don't need logging of state transitions in a state transition log entry,
                # as this would cause eternal, recursively nested state transition models.
                log_transitions = False

                class transition_initiated(StateDefinition):
                    description = _('State transition initiated')
                    initial = True
                class transition_started(StateDefinition):
                    description = _('State transition initiated')
                class transition_failed(StateDefinition):
                    description = _('State transition failed')
                class transition_completed(StateDefinition):
                    description = _('State transition completed')

                class start(StateTransition):
                    from_state = 'transition_initiated'
                    to_state = 'transition_started'
                    description = _('Start state transition')

                class complete(StateTransition):
                    from_state = 'transition_started'
                    to_state = 'transition_completed'
                    description = _('Complete state transition')

                class fail(StateTransition):
                    from_state = ('transition_initiated', 'transition_started')
                    to_state = 'transition_failed'
                    description = _('Mark state transition as failed')

            @property
            def completed(self):
                return self.value == 'transition_completed'

            def __unicode__(self):
                return '<State transition state on %s : "%s">' % (cls.__name__, self.value)

        state_transition_state_model = _StateTransitionState

        class _StateTransitionMeta(ModelBase):
            """
            Make _StateTransition act like it has another name,
            and was defined in another model.
            """
            def __new__(c, name, bases, attrs):
                attrs[ '__module__'] = cls.__module__
                return ModelBase.__new__(c, '%s_StateTransition' % cls.__name__, bases, attrs)

        class _StateTransition(models.Model):
            """
            State transitions log entry.
            """
            __metaclass__ = _StateTransitionMeta
                # TODO: add some description for this state transition

            from_state = models.CharField(max_length=32, choices=cls.get_state_choices())
            to_state = models.CharField(max_length=32, choices=cls.get_state_choices())
            user = models.ForeignKey(User, blank=True, null=True)

            start_time = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_('transition started at'))
            state = StateField(machine=state_transition_state_model)
            on    = models.ForeignKey(cls, related_name='all_transitions')

            @property
            def state_transition_definition(self):
                return cls.Machine.get_transition_from_states(self.from_state, self.to_state)

            @property
            def state_definiton(self):
                return cls.Machine.get_state(self.to_state)

            @property
            def state_description(self):
                return unicode(self.state_definiton.description)

            @property
            def is_public(self):
                """
                Return True when this state transition is defined public in the machine.
                """
                return self.state_transition_definition.public

            @property
            def transition_description(self):
                """
                Return the description for this transition as defined in the
                StateTransition declaration of the machine.
                """
                return unicode(self.state_transition_definition.description)

            def __unicode__(self):
                return '<State transition on %s at %s from "%s" to "%s">' % (
                            cls.__name__, self.start_time, self.from_state, self.to_state)

        state_transition_model = _StateTransition

        # These models will be detected by South because of the models.Model.__new__ constructor,
        # which will register it somewhere in a global variable.

        return state_transition_model

