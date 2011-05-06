class States2Exception(Exception):
    pass


class TransitionException(States2Exception):
    pass


class TransitionOnUnsavedObject(TransitionException):
    def __init__(self, instance):
        Exception.__init__(self, "Cannot run state transition on unsaved object '%s'. "
                "Please call save() on this object first." % instance)


class PermissionDenied(TransitionException):
    def __init__(self, instance, transition, user):
        if user.is_authenticated():
            username = user.get_full_name()
        else:
            username = 'AnonymousUser'
        Exception.__init__(self, "Permission for executing the state '%s' has be denied to %s."
                % (transition, username))


class UnknownTransition(TransitionException):
    def __init__(self, instance, transition):
        Exception.__init__(self, "Unknown transition '%s' on %s" %
                    (transition, instance.__class__.__name__))

class TransitionNotFound(TransitionException):
    def __init__(self, model, from_state, to_state):
        Exception.__init__(self, "Transition from '%s' to '%s' on %s not found" %
                    (from_state, to_state, model.__name__))


class TransitionCannotStart(TransitionException):
    def __init__(self, instance, transition):
        Exception.__init__(self, "Transition '%s' on %s cannot start in the state '%s'" %
                    (transition, instance.__class__.__name__, instance.state))


class MachineDefinitionException(States2Exception):
    def __init__(self, machine, description):
        Exception.__init__(self, 'Error in state machine definition: ' + description)
