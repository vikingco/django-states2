from states2.exceptions import *
from django.utils import simplejson as json


def get_STATE_transitions(self, field='state'):
    '''
    Return state transitions log model.

    :param str field: the name of the ``StateField``
    '''
    if getattr(self, '_%s_log_model' % field, None):
        # Similar to: _state_log_model.objects.filter(on=self)
        return self.all_transitions.all()
    else:
        raise Exception('This model does not log state transitions. '
                        'Please enable it by setting log_transitions=True')


def get_public_STATE_transitions(self, field='state'):
    '''
    Return the transitions which are meant to be seen by the customer. (The
    admin on the other hand should be able to see everything.)

    :param str field: the name of the ``StateField``
    '''
    if getattr(self, '_%s_log_model' % field, None):
        transitions = getattr(self, 'get_%s_transitions' % field)
        return filter(lambda t: t.is_public and t.completed, transitions())
    else:
        return []


def get_STATE_machine(self, field='state', machine=None):
    '''
    Get the machine

    :param str field: the name of the ``StateField``
    :param states2.machine.StateMachine machine: the state machine, default
        ``None``
    '''
    return machine


def get_STATE_info(self, field='state', machine=None):
    '''
    Get the state definition from the machine

    :param str field: the name of the ``StateField``
    :param states2.machine.StateMachine machine: the state machine, default
        ``None``
    '''
    if machine is None:
        return None

    class state_info(object):
        '''
        An extra object that hijackes the actual state methods.
        '''
        @property
        def name(si_self):
            '''
            The name of the current state
            '''
            return getattr(self, field)

        @property
        def description(si_self):
            '''
            The description of the current state
            '''
            si = machine.get_state(getattr(self, field))
            return si.description

        @property
        def in_group(si_self):
            return machine.get_state_groups(getattr(self, field))

        def possible_transitions(si_self):
            '''
            Return list of transitions which can be made from the current
            state.
            '''
            for name in machine.transitions:
                t = machine.transitions[name]
                if isinstance(t.from_state, basestring):
                    if getattr(self, field) == t.from_state:
                        yield t
                elif getattr(self, field) in t.from_state:  # from_state is a list/tuple
                    yield t

        def test_transition(si_self, transition, user=None):
            '''
            Check whether we could execute this transition.

            Returns ``True`` when we expect this transition to be executed
            succesfully.
            Raises an ``Exception`` when this transition is impossible or not
            allowed.
            '''
            # Transition name should be known
            if not machine.has_transition(transition):
                raise UnknownTransition(self, transition)

            t = machine.get_transitions(transition)

            if getattr(self, field) not in t.from_state:
                raise TransitionCannotStart(self, transition)

            # User should have permissions for this transition
            if user and not t.has_permission(self, user):
                raise PermissionDenied(self, transition, user)

            # Transition should validate
            validation_errors = list(t.validate(self))
            if validation_errors:
                raise TransitionNotValidated(si_self, transition, validation_errors)

            return True

        def make_transition(si_self, transition, user=None, **kwargs):
            '''
            Execute state transition.
            Provide ``user`` to do permission checking
            '''
            # Transition name should be known
            if not machine.has_transition(transition):
                raise UnknownTransition(self, transition)
            t = machine.get_transitions(transition)

            _state_log_model = getattr(self, '_%s_log_model' % field, None)

            # Start transition log
            if _state_log_model:
                transition_log = _state_log_model.objects.create(
                                on=self,
                                from_state=getattr(self, field),
                                to_state=t.to_state,
                                user=user,
                                serialized_kwargs=json.dumps(kwargs)
                                )

            # Test transition (access/execution validation)
            try:
                si_self.test_transition(transition, user)
            except TransitionException, e:
                if _state_log_model:
                    transition_log.make_transition('fail')
                raise e

            # Execute
            if _state_log_model:
                transition_log.make_transition('start')

            try:
                # First call handler (handler should still see the original state.)
                t.handler(self, user, **kwargs)

                # Then set new state and save.
                setattr(self, field, t.to_state)
                self.save()
            except Exception, e:
                if _state_log_model:
                    transition_log.make_transition('fail')

                # Print original traceback for debugging
                import traceback
                traceback.print_exc()
                raise e
            else:
                if _state_log_model:
                    transition_log.make_transition('complete')

                # *After completion*, call the handler of this state
                # definition
                machine.get_state(t.to_state).handler(self)

    return state_info()
