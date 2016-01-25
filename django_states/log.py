# -*- coding: utf-8 -*-
"""log model"""
from __future__ import absolute_import

import json
import sys

from django.db import models
from django.db.models.base import ModelBase
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from django_states import conf
from django_states.fields import StateField
from django_states.machine import StateMachine, StateDefinition, StateTransition
import six


def _create_state_log_model(state_model, field_name, machine):
    """
    Create a new model for logging the state transitions.

    :param django.db.models.Model state_model: the model that has the
        :class:`~django_states.fields.StateField`
    :param str field_name: the field name of the
        :class:`~django_states.fields.StateField` on the model
    :param django_states.machine.StateMachine machine: the state machine that's used
    """
    class StateTransitionMachine(StateMachine):
        """
        A :class:`~django_states.machine.StateMachine` for log entries (depending on
        what happens).
        """
        # We don't need logging of state transitions in a state transition log
        # entry, as this would cause eternal, recursively nested state
        # transition models.
        log_transitions = False

        class transition_initiated(StateDefinition):
            """Transition has initiated"""
            description = _('State transition initiated')
            initial = True

        class transition_started(StateDefinition):
            """Transition has started"""
            description = _('State transition started')

        class transition_failed(StateDefinition):
            """Transition has failed"""
            description = _('State transition failed')

        class transition_completed(StateDefinition):
            """Transition has completed"""
            description = _('State transition completed')

        class start(StateTransition):
            """Transition Started"""
            from_state = 'transition_initiated'
            to_state = 'transition_started'
            description = _('Start state transition')

        class complete(StateTransition):
            """Transition Complete"""
            from_state = 'transition_started'
            to_state = 'transition_completed'
            description = _('Complete state transition')

        class fail(StateTransition):
            """Transition Failure"""
            from_states = ('transition_initiated', 'transition_started')
            to_state = 'transition_failed'
            description = _('Mark state transition as failed')

    class _StateTransitionMeta(ModelBase):
        """
        Make :class:`_StateTransition` act like it has another name and was
        defined in another model.
        """
        def __new__(c, name, bases, attrs):

            new_unicode = u''
            if '__unicode__' in attrs:
                old_unicode = attrs['__unicode__']

                def new_unicode(self):
                    """New Unicode"""
                    return u'%s (%s)' % (old_unicode(self), self.get_state_info().description)

            attrs['__unicode__'] = new_unicode

            attrs['__module__'] = state_model.__module__
            values = {'model_name': state_model.__name__,
                      'field_name': field_name.capitalize()}
            class_name = conf.LOG_MODEL_NAME % values

            # Make sure that for Python2, class_name is a 'str' object.
            # In Django 1.7, `field_name` returns a unicode object, causing
            # `class_name` to be unicode as well.
            if sys.version_info[0] == 2:
                class_name = str(class_name)

            return ModelBase.__new__(c, class_name, bases, attrs)

    get_state_choices = machine.get_state_choices

    @python_2_unicode_compatible
    class _StateTransition(six.with_metaclass(_StateTransitionMeta, models.Model)):
        """
        The log entries for :class:`~django_states.machine.StateTransition`.
        """

        state = StateField(max_length=100, default='0',
                           verbose_name=_('state id'),
                           machine=StateTransitionMachine)

        from_state = models.CharField(max_length=100,
                                      choices=get_state_choices())
        to_state = models.CharField(max_length=100, choices=get_state_choices())
        user = models.ForeignKey(getattr(settings, 'AUTH_USER_MODEL', 'auth.User'), on_delete=models.CASCADE,
                                 blank=True, null=True)
        serialized_kwargs = models.TextField(blank=True)

        start_time = models.DateTimeField(
            auto_now_add=True, db_index=True,
            verbose_name=_('transition started at')
        )
        on = models.ForeignKey(state_model, on_delete=models.CASCADE, related_name=('%s_history' % field_name))

        class Meta:
            """Non-field Options"""
            verbose_name = '%s transition' % state_model._meta.verbose_name

            # When the state class has been given an app_label, use
            # use this app_label as well for this StateTransition model.
            if hasattr(state_model._meta, 'app_label'):
                app_label = state_model._meta.app_label

        @property
        def kwargs(self):
            """
            The ``kwargs`` that were used when calling the state transition.
            """
            if not self.serialized_kwargs:
                return {}
            return json.loads(self.serialized_kwargs)

        @property
        def completed(self):
            """
            Was the transition completed?
            """
            return self.state == 'transition_completed'

        @property
        def state_transition_definition(self):
            """
            Gets the :class:`django_states.machine.StateTransition` that was used.
            """
            return machine.get_transition_from_states(self.from_state, self.to_state)

        @property
        def from_state_definition(self):
            """
            Gets the :class:`django_states.machine.StateDefinition` from which we
            originated.
            """
            return machine.get_state(self.from_state)

        @property
        def from_state_description(self):
            """
            Gets the description of the
            :class:`django_states.machine.StateDefinition` from which we were
            originated.
            """
            return six.text_type(self.from_state_definition.description)

        @property
        def to_state_definition(self):
            """
            Gets the :class:`django_states.machine.StateDefinition` to which we
            transitioning.
            """
            return machine.get_state(self.to_state)

        @property
        def to_state_description(self):
            """
            Gets the description of the
            :class:`django_states.machine.StateDefinition` to which we were
            transitioning.
            """
            return six.text_type(self.to_state_definition.description)

        def make_transition(self, transition, user=None):
            """
            Execute state transition.
            Provide ``user`` to do permission checking.
            :param transition: Name of the transition
            :param user: User object
            """
            return self.get_state_info().make_transition(transition, user=user)

        @property
        def is_public(self):
            """
            Returns ``True`` when this state transition is defined public in
            the machine.
            """
            return self.state_transition_definition.public

        @property
        def transition_description(self):
            """
            Returns the description for this transition as defined in the
            :class:`django_states.machine.StateTransition` declaration of the
            machine.
            """
            return six.text_type(self.state_transition_definition.description)

        def __str__(self):
            return '<State transition on {0} at {1} from "{2}" to "{3}">'.format(
                state_model.__name__, self.start_time, self.from_state, self.to_state)

    # This model will be detected by South because of the models.Model.__new__
    # constructor, which will register it somewhere in a global variable.
    return _StateTransition
