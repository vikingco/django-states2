from states2.exceptions import *


def get_STATE_transitions(self, field='state'):
    '''
    Return state transitions log model.
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
    '''
    if getattr(self, '_%s_log_model' % field, None):
        transitions = getattr(self, 'get_%s_transitions' % field)
        return filter(lambda t: t.is_public and t.completed, transitions())
    else:
        return []


def get_STATE_machine(self, field='state', machine=None):
    '''
    Get the machine
    '''
    return machine


def get_STATE_info(self, field='state', machine=None):
    '''
    Get the state definition from the machine
    '''
    if machine is None:
        return None

    class state_info(object):
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

        def possible_transitions(si_self):
            '''
            Return list of transitions which can be made from the current
            state.
            '''
            for name in machine.transitions:
                t = machine.transitions[name]
                if isinstance(t.from_state, basestring) and getattr(self, field) == t.from_state:
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
            return True

        def make_transition(si_self, transition, user=None):
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
                transition_log = _state_log_model.objects.create(on=self, from_state=getattr(self, field), to_state=t.to_state, user=user)

            # Transition should start from here
            if getattr(self, field) not in t.from_state:
                if _state_log_model:
                    transition_log.make_transition('fail')
                raise TransitionCannotStart(self, transition)

            # User should have permissions for this transition
            if user and not t.has_permission(self, user):
                if _state_log_model:
                    transition_log.make_transition('fail')
                raise PermissionDenied(self, transition, user)

            # Execute
            if _state_log_model:
                transition_log.make_transition('start')

            try:
                t.handler(self, user)
                setattr(self, field, t.to_state)
                self.save()
            except Exception, e:
                if _state_log_model:
                    transition_log.make_transition('fail')
                raise e
            else:
                if _state_log_model:
                    transition_log.make_transition('complete')

    return state_info()
