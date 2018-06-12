""" Course API """
from openedx.core.djangoapps.waffle_utils import (WaffleSwitch, WaffleSwitchNamespace)

WAFFLE_SWITCH_NAMESPACE = WaffleSwitchNamespace(name='course_list_api_rate_limit')

USE_RATE_LIMIT_10_FOR_COURSE_LIST_API = WaffleSwitch(WAFFLE_SWITCH_NAMESPACE, 'rate_limit_10')
USE_RATE_LIMIT_20_FOR_COURSE_LIST_API = WaffleSwitch(WAFFLE_SWITCH_NAMESPACE, 'rate_limit_20')
