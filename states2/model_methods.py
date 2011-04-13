def get_STATE_transitions(self, field='state'):
    """
    Return state transitions log model.
    """
    if self._state_log_model:
        # Similar to: self._state_log_model.objects.filter(on=self)
        return self.all_transitions.all()
    else:
        raise Exception('This model does not log state transitions. '
                        'Please enable it by setting log_transitions=True')


def get_public_STATE_transitions(self, field='state'):
    """
    Return the transitions which are meant to be seen by the customer. (The
    admin on the other hand should be able to see everything.)
    """
    if self._state_log_model:
        transitions = getattr(self, 'get_%s_transitions' % attr_name)
        return filter(lambda t: t.is_public and t.completed, transitions())
    else:
        return []

