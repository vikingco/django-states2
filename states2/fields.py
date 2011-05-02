__all__ = ('StateField',)

from django.db import models
from django.utils.functional import curry
from states2.machine import StateMachine

from states2.model_methods import *


class StateField(models.CharField):
    def __init__(self, **kwargs):
        self._machine = kwargs.pop('machine')

        # Use a dummy machine when this field is initiated by a south migration
        if self._machine == 'south_machine':
            self._machine = StateMachine

        kwargs.setdefault('max_length', 100)
        kwargs['choices'] = None
        super(StateField, self).__init__(**kwargs)

    def contribute_to_class(self, cls, name):
        super(StateField, self).contribute_to_class(cls, name)

        # Set choice options (for combo box)
        self._choices = self._machine.get_state_choices()
        self.default = self._machine.initial_state

        # do we need logging?
        if self._machine.log_transitions:
            from states2.log import _create_state_log_model
            log_model = _create_state_log_model(cls, name, self._machine)
        else:
            log_model = None

        setattr(cls, '_%s_log_model' % name, log_model)

        # adding extra methods
        setattr(cls, 'get_%s_transitions' % name,
            curry(get_STATE_transitions, field=name))
        setattr(cls, 'get_public_%s_transitions' % name,
            curry(get_public_STATE_transitions, field=name))
        setattr(cls, 'get_%s_info' % name,
            curry(get_STATE_info, field=name, machine=self._machine))
        setattr(cls, 'get_%s_machine' % name,
            curry(get_STATE_machine, field=name, machine=self._machine))


# South introspection
try:
    from south.modelsinspector import add_introspection_rules
except ImportError:
    pass
else:
    add_introspection_rules([
        (
            (StateField,),
            [],
            {
                'machine': ['south_machine', { "is_value": True }],
                'max_length': [100, { "is_value": True }],
            },
        ),

        ], ["^states2\.fields\.StateField"])
