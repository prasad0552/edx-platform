import json
import logging
import math
from functools import partial
import re

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest, HttpResponseNotFound
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST, require_http_methods
from opaque_keys.edx.keys import AssetKey, CourseKey
from pymongo import ASCENDING, DESCENDING
from six import text_type
from xmodule.contentstore.content import StaticContent
from xmodule.contentstore.django import contentstore
from xmodule.exceptions import NotFoundError
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.exceptions import ItemNotFoundError

from contentstore.utils import reverse_course_url
from contentstore.views.exception import AssetNotFoundException, AssetSizeTooLargeException
from edxmako.shortcuts import render_to_response
from openedx.core.djangoapps.contentserver.caching import del_cached_content
from student.auth import has_course_author_access
from util.date_utils import get_default_time_display
from util.json_request import JsonResponse

__all__ = ['course_health_handler']


@login_required
@ensure_csrf_cookie
def course_health_handler(request, course_key_string=None):
    '''
    The restful handler for assets.
    It allows retrieval of all the assets (as an HTML page), as well as uploading new assets,
    deleting assets, and changing the 'locked' state of an asset.

    GET
        html: return an html page which will show all course assets. Note that only the asset container
            is returned and that the actual assets are filled in with a client-side request.
        json: returns a page of assets. The following parameters are supported:
            page: the desired page of results (defaults to 0)
            page_size: the number of items per page (defaults to 50)
            sort: the asset field to sort by (defaults to 'date_added')
            direction: the sort direction (defaults to 'descending')
            asset_type: the file type to filter items to (defaults to All)
            text_search: string to filter results by file name (defaults to '')
    POST
        json: create (or update?) an asset. The only updating that can be done is changing the lock state.
    PUT
        json: update the locked state of an asset
    DELETE
        json: delete an asset
    '''
    course_key = CourseKey.from_string(course_key_string)
    if not has_course_author_access(request.user, course_key):
        raise PermissionDenied()

    course_module = modulestore().get_course(course_key)
    return render_to_response('course_health.html', {
        'language_code': request.LANGUAGE_CODE,
        'context_course': course_module,
    })
