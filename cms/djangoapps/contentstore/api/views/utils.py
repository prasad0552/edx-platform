"""
Common utilities for Contentstore APIs.
"""
from openedx.core.djangoapps.util.forms import to_bool


def get_bool_param(request, param_name, default):
    param_value = request.query_params.get(param_name, None)
    bool_value = to_bool(param_value)
    if bool_value is None:
        return default
    else:
        return bool_value
