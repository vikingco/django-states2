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
        Exception.__init__(self, "Permission for executing the state '%s' has be denied to %s."
                % (transition, user.get_full_name()))


class UnknownTransition(TransitionException):
    def __init__(self, instance, transition):
        Exception.__init__(self, "Unknown transition '%s' on %s" %
                    (transition, instance.__class__.__name__))


class TransitionCannotStart(TransitionException):
    def __init__(self, instance, transition):
        Exception.__init__(self, "Transition '%s' on %s cannot start in the state '%s'" %
                    (transition, instance.__class__.__name__, instance.state))
