import logging
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from contentstore.course_info_model import get_course_updates
from contentstore.views.certificates import CertificateManager
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

        * is_self_paced - whether the course is self-paced.
        * dates
            * has_start_date - whether the start date is set on the course.
            * has_end_date - whether the end date is set on the course.
        * assignments
            * total_number - total number of assignments in the course.
            * total_visible - number of assignments visible to learners in the course.
            * num_with_dates - number of assignments with due dates.
            * num_with_dates_after_start - number of assignments with due dates after the start date.
            * num_with_dates_before_end - number of assignments with due dates before the end date.
        * grades
            * sum_of_weights - sum of weights for all assignments in the course (valid ones should equal 1).
        * certificates
            * is_activated - whether the certificate is activated for the course.
            * has_certificate - whether the course has a certificate.
        * updates
            * has_update - whether at least one course update exists.

    """
    def get(self, request, course_id):
        """
        Returns validation information for the given course.
        """
        default_request_value = request.query_params.get('all', False)

        course_key = CourseKey.from_string(course_id)
        if not has_course_author_access(request.user, course_key):
            return self.make_error_response(
                status_code=status.HTTP_403_FORBIDDEN,
                developer_message='The user requested does not have the required permissions.',
                error_code='user_mismatch'
            )

        store = modulestore()
        with store.bulk_operations(course_key):
            course = store.get_course(course_key, depth=self._required_course_depth(request, default_request_value))

            response = dict(
                is_self_paced=course.self_paced,
            )
            if request.query_params.get('dates', default_request_value):
                response.update(
                    dates=self._dates_validation(course)
                )
            if request.query_params.get('assignments', default_request_value):
                response.update(
                    assignments=self._assignments_validation(course)
                )
            if request.query_params.get('grades', default_request_value):
                response.update(
                    grades=self._grades_validation(course)
                )
            if request.query_params.get('certificates', default_request_value):
                response.update(
                    certificates=self._certificates_validation(course)
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
            has_start_date=self._has_start_date(course),
            has_end_date=course.end is not None,
        )

    def _assignments_validation(self, course):
        assignments, visible_assignments = self._get_assignments(course)
        assignments_with_dates = filter(lambda a: a.due, visible_assignments)
        num_with_dates = len(assignments_with_dates)
        num_with_dates_after_start = (
            len(filter(lambda a: a.due > course.start, assignments_with_dates))
            if self._has_start_date(course)
            else 0
        )
        num_with_dates_before_end = (
            len(filter(lambda a: a.due < course.end, assignments_with_dates))
            if course.end
            else 0
        )

        return dict(
            total_number=len(assignments),
            total_visible=len(visible_assignments),
            num_with_dates=num_with_dates,
            num_with_dates_after_start=num_with_dates_after_start,
            num_with_dates_before_end=num_with_dates_before_end,
        )

    def _grades_validation(self, course):
        sum_of_weights = course.grader.sum_of_weights
        return dict(
            sum_of_weights=sum_of_weights,
        )

    def _certificates_validation(self, course):
        return dict(
            is_activated=CertificateManager.is_activated(course),
            has_certificate=len(CertificateManager.get_certificates(course)) > 0,
        )

    def _updates_validation(self, course, request):
        updates_usage_key = course.id.make_usage_key('course_info', 'updates')
        updates = get_course_updates(updates_usage_key, provided_id=None, user_id=request.user.id)
        return dict(
            has_update=len(updates) > 0,
        )

    def _get_assignments(self, course):
        store = modulestore()
        sections = [store.get_item(section_usage_key) for section_usage_key in course.children]
        assignments = [
            store.get_item(assignment_usage_key)
            for section in sections
            for assignment_usage_key in section.children
        ]

        visible_sections = filter(
            lambda s: not s.visible_to_staff_only and not s.hide_from_toc,
            sections,
        )
        assignments_in_visible_sections = [
            store.get_item(assignment_usage_key)
            for visible_section in visible_sections
            for assignment_usage_key in visible_section.children
        ]
        visible_assignments = filter(lambda a: not a.visible_to_staff_only, assignments_in_visible_sections)
        return assignments, visible_assignments

    def _has_start_date(self, course):
        return not course.start_date_is_still_default
