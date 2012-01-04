import django.dispatch

before_state_execute = django.dispatch.Signal(providing_args=['from_state',
                                                                'to_state'])
after_state_execute = django.dispatch.Signal(providing_args=['from_state',
                                                       'to_state'])
