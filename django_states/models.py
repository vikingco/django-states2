# -*- coding: utf-8 -*-
"""Models"""
from __future__ import absolute_import
import six

# Author: Jonathan Slenders, CityLive

__doc__ = \
"""

Base models for every State.

"""


__all__ = ('StateMachine', 'StateDefinition', 'StateTransition', 'StateModel')

from django.db import models
from django.db.models.base import ModelBase
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from django_states.machine import StateMachine, StateDefinition, StateTransition
from django_states.exceptions import States2Exception
from django_states.fields import StateField


# =======================[ State ]=====================
class StateModelBase(ModelBase):
    """
    Metaclass for State models.

    This metaclass will initiate a logging model as well, if required.
    """
    def __new__(cls, name, bases, attrs):
        """
        Instantiation of the State type.

        When this type is created, also create a logging model if required.
        """
        if name != 'StateModel' and 'Machine' in attrs:
            attrs['state'] = StateField(max_length=100, default='0',
                                        verbose_name=_('state id'),
                                        machine=attrs['Machine'])

        # Wrap __unicode__ for state model
        if '__unicode__' in attrs:
            old_unicode = attrs['__unicode__']

            def new_unicode(self):
                return '%s (%s)' % (old_unicode(self), self.Machine.get_state(self.state).description)
            attrs['__unicode__'] = new_unicode

        # Call class constructor of parent
        return ModelBase.__new__(cls, name, bases, attrs)


@python_2_unicode_compatible
class StateModel(six.with_metaclass(StateModelBase, models.Model)):
    """
    Every model which needs state can inherit this abstract model.

    This will dynamically add a :class:`~django_states.fields.StateField` named
    ``state``.
    """

    class Machine(StateMachine):
        """
        Example machine definition.

        State machines should override this by creating a new machine,
        inherited directly from :class:`~django_states.machine.StateMachine`.
        """
        #: True when we should log all transitions
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
        abstract = True

    def __str__(self):
        return 'State: ' + self.state

    @property
    def state_transitions(self):
        """
        Wraps :meth:`django_states.model_methods.get_STATE_transitions`
        """
        return self.get_state_transitions()

    @property
    def public_transitions(self):
        """
        Wraps :meth:`django_states.model_methods.get_public_STATE_transitions`
        """
        return self.get_public_state_transitions()

    @property
    def state_description(self):
        """
        Gets the full description of the (current) state
        """
        return six.text_type(self.get_state_info().description)

    @property
    def is_initial_state(self):
        """
        Gets whether this is the initial state.

        :returns: ``True`` when the current state is the initial state
        """
        return bool(self.get_state_info().initial)

    @property
    def possible_transitions(self):
        """
        Gets the list of transitions which can be made from the current state.

        :returns: list of transitions which can be made from the current state
        """
        return self.get_state_info().possible_transitions

    @classmethod
    def get_state_model_name(self):
        """
        Gets the state model
        """
        return '%s.%s' % (self._meta.app_label, self._meta.object_name)

    def can_make_transition(self, transition, user=None):
        """
        Gets whether we can make the transition.

        :param str transition: the transition name
        :param user: the user that will execute the transition. Used for
            permission checking
        :type: :class:`django.contrib.auth.models.User` or ``None``

        :returns: ``True`` when we should be able to make this transition
        """
        try:
            return self.test_transition(transition, user)
        except States2Exception:
            return False

    def test_transition(self, transition, user=None):
        """
        Check whether we could execute this transition.

        :param str transition: the transition name
        :param user: the user that will execute the transition. Used for
            permission checking
        :type: :class:`django.contrib.auth.models.User` or ``None``

        :returns:``True`` when we expect this transition to be executed
            succesfully. It will raise an ``Exception`` when this
            transition is impossible or not allowed.
        """
        return self.get_state_info().test_transition(transition, user=user)

    def make_transition(self, transition, user=None, **kwargs):
        """
        Executes state transition.

        :param str transition: the transition name
        :param user: the user that will execute the transition. Used for
            permission checking
        :type: :class:`django.contrib.auth.models.User` or ``None``
        :param dict kwargs: the kwargs that will be passed to
            :meth:`~django_states.machine.StateTransition.handler`
        """
        return self.get_state_info().make_transition(transition, user=user, **kwargs)

    @classmethod
    def get_state_choices(cls):
        return cls.Machine.get_state_choices()
