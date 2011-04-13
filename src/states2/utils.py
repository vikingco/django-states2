from states2.models import _state_models


def get_state_model(model_name):
    if model_name in _state_models:
        return _state_models[model_name]
    else:
        raise Exception('No such state model "%s"' % model_name)
