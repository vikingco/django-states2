




def state_transition_handler(instance_method):
    instance_method.is_transition_handler = True
    return instance_method
