import django.dispatch

#: Signal that is sent before a state transition is executed
before_state_execute = django.dispatch.Signal(providing_args=['from_state',
                                                              'to_state'])
#: Signal that s sent after a state transition is executed
after_state_execute = django.dispatch.Signal(providing_args=['from_state',
                                                             'to_state'])
