# Author: Jonathan Slenders, CityLive

__doc__ = \
"""

Base models for every State.

"""


__all__ = ('StateMachine', 'StateDefinition', 'StateTransition', 'StateModel')

from django.contrib.auth.models import User
from django.db import models
from django.db.models.base import ModelBase
from django.utils.translation import ugettext_lazy as _
from functools import wraps

from states2.machine import StateMachine, StateDefinition, StateTransition
from states2.exceptions import *

import copy
import datetime


# Global list of all state models (mapping from name -> model class }
_state_models = {}


# =======================[ State ]=====================
class StateModelBase(ModelBase):
    """
    Metaclass for State models.
    This metaclass will initiate a logging model as well, if required.
    """
    def __new__(cls, name, bases, attrs):
        """
        Instantiation of the State type.
        When this type is created, also create logging model if required.
        """
        # Wrap __unicode__ for state model
        if '__unicode__' in attrs:
            old_unicode = attrs['__unicode__']

            def new_unicode(self):
                return '%s (%s)' % (old_unicode(self), self.Machine.get_state(self.state).description)
            attrs['__unicode__'] = new_unicode

        # Call class constructor of parent
        state_model = ModelBase.__new__(cls, name, bases, attrs)

        # If we need logging, create logging model
        if state_model.Machine.log_transitions:
            state_model._state_log_model = _create_state_log_model(state_model, name)
        else:
            state_model._state_log_model = None

        # Link default value for the State Machine
        for f in state_model._meta.fields:
            if f.name == 'state':
                f.default = state_model.Machine.initial_state
                f._choices = state_model.get_state_choices()

        # Register state model in global register
        _state_models[state_model.get_state_model_name()] = state_model

        return state_model


class StateModel(models.Model):
    """
    Every model which needs state should inherit this abstract model.
    """
    state = models.CharField(max_length=64, default='0', verbose_name=_('state id'))

    __metaclass__ = StateModelBase

    class Machine(StateMachine):
        """
        Example machine definition. State machines should override this by
        creating a new machine, inherited directly from StateMachine.
        """
        # True when we should log all transitions
        log_transitions = False

        # Definition of states (mapping from state_slug to description)
        class initial(StateDefinition):
            initial = True
            description = _('Initial state')

        # Possible transitions, and their names
        class dummy(StateTransition):
            from_state = 'initial'
            to_state = 'initial'
            description = _('Make dummy state transition')

    class Meta:
        verbose_name = _('state')
        verbose_name_plural = _('states')
        abstract = True

    def __unicode__(self):
        return 'State: ' + self.state

    @property
    def state_transitions(self):
        """
        Return state transitions log model.
        """
        if self._state_log_model:
            return self.all_transitions  # Almost similar to: self._state_log_model.objects.filter(on=self)
        else:
            raise Exception('This model does not log state transitions. please enable it by setting log_transitions=True')

    @property
    def public_transitions(self):
        """
        Return the transitions which are meant to be seen by the customer. (The
        admin on the other hand should be able to see everything.)
        """
        if self._state_log_model:
            return filter(lambda t: t.is_public and t.completed, self.state_transitions.all())
        else:
            return []

    @property
    def state_description(self):
        """
        Get the full description of the (current) state
        """
        return unicode(self.Machine.get_state(self.state).description)

    @property
    def is_initial_state(self):
        """
        returns True when the current state is the initial state
        """
        return bool(self.Machine.get_state(self.state).initial)

    @property
    def possible_transitions(self):
        """
        Return list of transitions which can be made from the current state.
        """
        for name in self.Machine.transitions:
            t = self.Machine.transitions[name]
            if isinstance(t.from_state, basestring) and self.state == t.from_state:
                    yield t
            elif self.state in t.from_state:  # from_state is a list/tuple
                    yield t

    @classmethod
    def get_state_model_name(self):
        return '%s.%s' % (self._meta.app_label, self._meta.object_name)

    def can_make_transition(self, transition, user=None):
        """ True when we should be able to make this transition """
        try:
            self.test_transition(transition, user)
            return True
        except Exception, e:
            return False

    def test_transition(self, transition, user=None):
        """
        Return True when we exect this transition to be executed succesfully.
        Raise Exception when this transition is impossible.
        """
        # Transition name should be known
        if not self.Machine.has_transition(transition):
            raise UnknownTransition(self, transition)
        t = self.Machine.get_transitions(transition)

        if self.state not in t.from_state:
            raise TransitionCannotStart(self, transition)

        # User should have permissions for this transition
        if user and not t.has_permission(self, user):
            raise PermissionDenied(self, transition, user)
        return True

    def make_transition(self, transition, user=None):
        """
        Execute state transition
        user: the user executing the transition
        """
        # Transition name should be known
        if not self.Machine.has_transition(transition):
            raise UnknownTransition(self, transition)
        t = self.Machine.get_transitions(transition)

        # Start transition log
        if self._state_log_model:
            transition_log = self._state_log_model.objects.create(on=self, from_state=self.state, to_state=t.to_state, user=user)

        # Transition should start from here
        if self.state not in t.from_state:
            if self._state_log_model:
                transition_log.make_transition('fail')
            raise TransitionCannotStart(self, transition)

        # User should have permissions for this transition
        if user and not t.has_permission(self, user):
            if self._state_log_model:
                transition_log.make_transition('fail')
            raise PermissionDenied(self, transition, user)

        # Execute
        if self._state_log_model:
            transition_log.make_transition('start')

        try:
            t.handler(self, user)
            self.state = t.to_state
            self.save()
            if self._state_log_model:
                transition_log.make_transition('complete')
        except Exception, e:
            if self._state_log_model:
                transition_log.make_transition('fail')
            raise e

    @classmethod
    def get_state_choices(cls):
        return [(k, cls.Machine.states[k].description) for k in cls.Machine.states.keys()]


def _create_state_log_model(state_model, name):
    """
    Create a new model for logging the state transitions.
    """
    class StateTransitionMachine(StateMachine):
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

    class _StateTransitionMeta(StateModelBase):
        """
        Make _StateTransition act like it has another name,
        and was defined in another model.
        """
        def __new__(c, name, bases, attrs):
            attrs['__module__'] = state_model.__module__
            return StateModelBase.__new__(c, '%s_StateTransition' % state_model.__name__, bases, attrs)

    class _StateTransition(StateModel):
        """
        State transitions log entry.
        """
        __metaclass__ = _StateTransitionMeta

        from_state = models.CharField(max_length=32, choices=state_model.get_state_choices())
        to_state = models.CharField(max_length=32, choices=state_model.get_state_choices())
        user = models.ForeignKey(User, blank=True, null=True)

        start_time = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_('transition started at'))
        on = models.ForeignKey(state_model, related_name='all_transitions')

        Machine = StateTransitionMachine

        class Meta:
            verbose_name = _('%s transition') % state_model._meta.verbose_name

        @property
        def completed(self):
            return self.state == 'transition_completed'

        @property
        def state_transition_definition(self):
            return state_model.Machine.get_transition_from_states(self.from_state, self.to_state)

        @property
        def from_state_definition(self):
            return state_model.Machine.get_state(self.from_state)

        @property
        def from_state_description(self):
            return unicode(self.from_state_definition.description)

        @property
        def to_state_definition(self):
            return state_model.Machine.get_state(self.to_state)

        @property
        def to_state_description(self):
            return unicode(self.to_state_definition.description)

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
                        state_model.__name__, self.start_time, self.from_state, self.to_state)

    # This model will be detected by South because of the models.Model.__new__ constructor,
    # which will register it somewhere in a global variable.

    return _StateTransition
