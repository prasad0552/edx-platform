""" API v0 views. """
import logging
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from contentstore.course_info_model import get_course_updates
from opaque_keys.edx.keys import CourseKey
from openedx.core.lib.api.view_utils import DeveloperErrorViewMixin, view_auth_classes
from student.auth import has_course_author_access
from xmodule.modulestore.django import modulestore

log = logging.getLogger(__name__)


@view_auth_classes()
class CourseValidationView(DeveloperErrorViewMixin, GenericAPIView):
    """
    **Use Case**

    **Example Requests**

        GET /api/courses/v1/validation/{course_id}/

    **GET Parameters**

        A GET request may include the following parameters.

        * all
        * dates
        * assignments
        * grades
        * certificates
        * updates

    **GET Response Values**

        The HTTP 200 response has the following values.

        * dates
            * has_start_date
            * has_end_date
        * assignments
            * dates_within_range
        * grades
            * sum_of_weights
        * certificates
        * updates
            * has_update: True

    **Example GET Response**

        {
            dates: {
                has_start_date: True,
                has_end_date: True,
            }
        }

    """
    def get(self, request, course_id):
        """
        Returns validation information for the given course.
        """
        log.info("In the GET method")
        default_request_value = request.query_params.get('all', False)

        course_key = CourseKey.from_string(course_id)
        if not has_course_author_access(request.user, course_key):
            return self.make_error_response(
                status_code=status.HTTP_403_FORBIDDEN,
                developer_message='The user requested does not have the required permissions.',
                error_code='user_mismatch'
            )
        course = modulestore().get_course(course_key, depth=self._required_course_depth(request, default_request_value))

        response = {}
        if request.query_params.get('dates', default_request_value):
            response.update(
                dates=self._dates_validation(course)
            )
        if request.query_params.get('assignments', default_request_value):
            response.update(
                assignment_dates=self._assignments_validation(course)
            )
        if request.query_params.get('grades', default_request_value):
            response.update(
                self._grades_validation(course)
            )
        if request.query_params.get('certificates', default_request_value):
            response.update(
                self._certificates_validation(course)
            )
        if request.query_params.get('updates', default_request_value):
            response.update(
                updates=self._updates_validation(course, request)
            )

        return Response(response)

    def _required_course_depth(self, request, default_request_value):
        if request.query_params.get('assignments', default_request_value):
            return 2
        else:
            return 0

    def _dates_validation(self, course):
        return dict(
            has_start_date=not course.start_date_is_still_default,
            has_end_date=course.end is not None
        )

    def _assignments_validation(self, course):
        assignments = self._get_assignments(course)
        return dict(
        )

    def _grades_validation(self, course):
        sum_of_weights = course.grader.sum_of_weights
        return dict(
            sum_of_weights=sum_of_weights,
        )

    def _certificates_validation(self, course):
        return dict(
        )

    def _updates_validation(self, course, request):
        updates_usage_key = course.id.make_usage_key('course_info', 'updates')
        updates = get_course_updates(updates_usage_key, provided_id=None, user_id=request.user.id)
        return dict(
            has_update=len(updates) > 0,
        )

    def _get_assignments(self, course):
        return modulestore().get_items(course.id, qualifiers={'category': 'sequential'})
