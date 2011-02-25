
from django.db import models
from django.contrib.auth.models import User
from functools import wraps
from django.utils.translation import ugettext_lazy as _
from states.fields import StateField

import datetime
import copy


class StateTransition(object):
    def __init__(self, from_state, to_state):
        self.from_state = from_state
        self.to_state = to_state

class StateManager(models.Manager):
    pass

from django.db.models.base import ModelBase

class StateBase(ModelBase):
    def __new__(cls, name, bases, attrs):
        """
        Instantiation of the State type.
        When this type is created, also create logging model if required.
        """
        # Call class constructor of parent
        state= ModelBase.__new__(cls, name, bases, attrs)

        # If we need logging, create logging model
        if state.Machine.log_transitions:
            state.log = state.create_state_log_model(name)
        else:
            state.log = None

        return state


class State(models.Model):
    """
    Every state table should inherit this model.
    """
    updated_on = models.DateTimeField(auto_now=True, default=datetime.datetime.now)
    #value = models.CharField(max_length=64, choices=get_state_choices(), default='0', verbose_name=_('state id'))
    value = models.CharField(max_length=64, default='0', verbose_name=_('state id'))

    objects = StateManager()

    __metaclass__ = StateBase

    class Machine:
        """
        Machine declaration. Needs to be overridden for every machine.
        """
        # Definition of states (mapping from state_slug to description)
        states = {
            'initial': _('Initial state'),
            }

        # The initial state, when an object is created. This should be
        # a key from the dictionary above.
        initial_state = 'initial'

        # Possible transitions, and their names
        transitions = {
            'dummy': StateTransition(from_state='initial', to_state='initial'),
        }

        # True when we should log all transitions (Causes state on state)
        log_transitions = False


    class Meta:
        verbose_name = _('state')
        verbose_name_plural = _('states')
        abstract = True

    def __unicode__(self):
        return 'State: ' + self.value

    @property
    def description(self):
        """
        Get the full description of the (current) state
        """
        return self.value # TODO

    def make_transition(self, transition, user): #, **kwargs):
        """
        Execute state transition
        """
        # Transition should be known
        if not transition in self.transitions:
            raise UnknownTransition(transition)
        t = self.transitions[transition]

        # Start transition log
        if self.log:
            transition_log = self.log.objects.create(state = self, from_state = self.value, to_state = t.to, user = user)

        # Transition should start from here
        if self.value != t.from_state:
            raise CannotExecuteTransitionInThisState(transition)

        # User should have permissions for this transition
        if not t.has_permission(user):
            raise StatePermissionFailed(transition)

        # Execute
        if self.log:
            transition_log.action('start')

        if self.has_state_transition_handler():
            if handler():
                self.value = transition.to

            else:
                if self.log:
                    transition_log.action('failed')

        else:
            self.value = transition.to

        if self.log:
            transition_log.action('complete')


    @classmethod
    def get_state_choices(cls):
        return cls.Machine.states.iteritems()


    @classmethod
    def create_state_log_model(cls, name):
        """
        Create a new model for logging the state transitions.
        """
        print 'creating log models'

        def copy_fields(model):
            fields = { '__module__': cls.__module__ }

            for f in model._meta.fields:
                fields[f.name] = copy.copy(f)

            if hasattr(model, 'Machine'):
                fields['Machine'] = model.Machine

            if hasattr(model, 'Meta'):
                fields['Meta'] = model.Meta

            return fields

        class _StateTransitionState(models.Model):
            class Machine:
                states = {
                    'state_transition_initiated': _('State transition initiated'),
                    'state_transition_started': _('State transition started'),
                    'state_transition_failed': _('State transition failed'),
                    'state_transition_completed': _('State transition completed'),
                }
                initial_state = 'state_started'
                transitions = {
                    'start': StateTransition('state_transition_initiated', 'state_transition_started'),
                    'complete': StateTransition('state_transition_started', 'state_transition_completed'),
                    'fail': StateTransition('state_transition_started', 'state_transition_failed'),
                }
                # We don't need logging of state transitions in a state transition log entry,
                # as this would cause eternal, recursively nested state transition models.
                log_transitions = False

            class Meta:
                abstract = True

        # We need to use 'type', because we want models.Model._new__ constructor to be called with this name.
        state_transition_state_model = type('%s_StateTransitionState' % cls.__name__,
                (State,), copy_fields(_StateTransitionState))

        class _StateTransition(models.Model):
            from_state = models.CharField(max_length=32)
            to_state = models.CharField(max_length=32)
            user = models.ForeignKey(User, blank=True, null=True)

            state = StateField(machine=state_transition_state_model)

            class Meta:
                abstract = True

        state_transition_model = type('%s_StateTransition' % cls.__name__,
            (models.Model, ), copy_fields(_StateTransition))

        # These models will be detected by South because of the models.Model.__new__ constructor,
        # which will register it somewhere in a global variable.

        return state_transition_model
