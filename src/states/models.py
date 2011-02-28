from django.contrib.auth.models import User
from django.db import models
from django.db.models.base import ModelBase
from django.utils.translation import ugettext_lazy as _
from functools import wraps
from states.fields import StateField

import copy
import datetime


class StateTransition(object):
    def __init__(self, from_state, to_state):
        self.from_state = from_state
        self.to_state = to_state


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
    def transitions(self):
        """
        Return state transitions log model.
        """
        if self._log:
            return self.all_transitions
        else:
            raise Exception('This model does not log state transitions. please enable it by setting log_transitions=True')

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
            transition_log = self.log.objects.create(on=self, from_state=self.value, to_state=t.to, user=user)

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

            @property
            def completed(self):
                return self.value == 'complete'

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
            Log state transitions.
            """
            __metaclass__ = _StateTransitionMeta

            from_state = models.CharField(max_length=32, choices=cls.get_state_choices())
            to_state = models.CharField(max_length=32, choices=cls.get_state_choices())
            user = models.ForeignKey(User, blank=True, null=True)

            state = StateField(machine=state_transition_state_model)
            on    = models.ForeignKey(cls, related_name='all_transitions')

            def __unicode__(self):
                return '<State transition on %s from "%s" to "%s">' % (cls.__name__, self.from_state, self.to_state)

        state_transition_model = _StateTransition

        # These models will be detected by South because of the models.Model.__new__ constructor,
        # which will register it somewhere in a global variable.

        return state_transition_model

