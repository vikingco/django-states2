__all__ = ('StateField',)

from django.db import models
from django.utils.functional import curry

from states2.models import _create_state_log_model
from states2.model_methods import *


class StateField(models.CharField):
    def __init__(self, **kwargs):
        if 'machine' in kwargs:
            self._machine = kwargs.pop('machine')
        kwargs.setdefault('max_length', 100)
        kwargs['choices'] = None
        super(StateField, self).__init__(**kwargs)

    def contribute_to_class(self, cls, name):
        super(StateField, self).contribute_to_class(cls, name)
        if not hasattr(self, '_machine'):
            self._machine = cls.Machine

        self._choices = self._machine.get_state_choices()
        self.default = self._machine.initial_state

        # do we need logging?
        if self._machine.log_transitions:
            cls._state_log_model = _create_state_log_model(cls, name)
        else:
            cls._state_log_model = None

        # adding extra methods
        setattr(cls, 'get_%s_transitions' % name,
            curry(get_STATE_transitions, field=name))
        setattr(cls, 'get_public_%s_transitions' % name,
            curry(get_public_STATE_transitions, field=name)
        setattr(cls, 'get_%s_info' % name,
            curry(get_STATE_info, field=name, machine=self._machine)

try:
    from south.modelsinspector import add_introspection_rules
except ImportError:
    pass
else:
    add_introspection_rules([], ["^states2\.fields\.StateField"])
