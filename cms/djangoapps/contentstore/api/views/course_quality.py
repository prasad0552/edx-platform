import logging
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from opaque_keys.edx.keys import CourseKey
from openedx.core.lib.api.view_utils import DeveloperErrorViewMixin, view_auth_classes
from student.auth import has_course_author_access
from xmodule.modulestore.django import modulestore

log = logging.getLogger(__name__)


@view_auth_classes()
class CourseQualityView(DeveloperErrorViewMixin, GenericAPIView):
    """
    **Use Case**

    **Example Requests**

        GET /api/courses/v1/quality/{course_id}/

    **GET Parameters**

        A GET request may include the following parameters.

        * all
        * sections
        * subsections
        * units
        * videos

    **GET Response Values**

        The HTTP 200 response has the following values.

        * is_self_paced

    **Example GET Response**

        {
        }

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
            if request.query_params.get('sections', default_request_value):
                response.update(
                    highlights=self._sections_quality(course)
                )
            if request.query_params.get('subsections', default_request_value):
                response.update(
                    structure=self._subsections_quality(course)
                )
            if request.query_params.get('units', default_request_value):
                response.update(
                    structure=self._units_quality(course)
                )
            if request.query_params.get('videos', default_request_value):
                response.update(
                    videos=self._videos_quality(course)
                )

        return Response(response)

    def _required_course_depth(self, request, default_request_value):
        if request.query_params.get('units', default_request_value):
            return None
        if request.query_params.get('subsections', default_request_value):
            return 2
        elif request.query_params.get('sections', default_request_value):
            return 1
        else:
            return 0

    def _sections_quality(self, course):
        store = modulestore()
        sections = [store.get_item(section_usage_key) for section_usage_key in course.children]
        visible_sections = filter(
            lambda s: not s.visible_to_staff_only and not s.hide_from_toc,
            sections,
        )
        sections_with_highlights = filter(lambda s: s.highlights, visible_sections)
        return dict(
            total_number=len(sections),
            total_visible=len(visible_sections),
            number_with_highlights=len(sections_with_highlights),
            highlights_enabled=course.highlights_enabled_for_messaging,
        )

    def _subsections_quality(self, course):
        return dict()

    def _units_quality(self, course):
        return dict()

    def _videos_quality(self, course):
        return dict()
