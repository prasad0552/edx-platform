import logging
import numpy as np
from scipy import stats
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from edxval.api import get_videos_for_course
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.request_cache.middleware import request_cached
from openedx.core.lib.api.view_utils import DeveloperErrorViewMixin, view_auth_classes
from openedx.core.lib.graph_traversals import traverse_pre_order
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
        * sections
            * total_number
            * total_visible
            * number_with_highlights
            * highlights_enabled
        * subsections
            * total_number
            * num_with_one_block_type
            * num_block_types
                * min
                * max
                * mean
                * median
                * mode
        * units
            * total_number
            * num_blocks
                * min
                * max
                * mean
                * median
                * mode
        * videos

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
                    sections=self._sections_quality(course)
                )
            if request.query_params.get('subsections', default_request_value):
                response.update(
                    subsections=self._subsections_quality(course)
                )
            if request.query_params.get('units', default_request_value):
                response.update(
                    units=self._units_quality(course)
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
            return None
        elif request.query_params.get('sections', default_request_value):
            return 1
        else:
            return 0

    def _sections_quality(self, course):
        sections, visible_sections = self._get_sections(course)
        sections_with_highlights = filter(lambda s: s.highlights, visible_sections)
        return dict(
            total_number=len(sections),
            total_visible=len(visible_sections),
            number_with_highlights=len(sections_with_highlights),
            highlights_enabled=course.highlights_enabled_for_messaging,
        )

    def _subsections_quality(self, course):
        subsection_unit_dict = self._get_subsections_and_units(course)
        subsection_num_block_types_dict = {}
        for subsection_key, unit_dict in subsection_unit_dict.iteritems():
            all_block_types = (
                unit_info['leaf_block_types']
                for unit_info in unit_dict.itervalues()
                if unit_info['num_leaf_blocks'] > 1
            )
            subsection_num_block_types_dict[subsection_key] = len(set().union(*all_block_types))

        return dict(
            total_number=len(subsection_num_block_types_dict),
            num_with_one_block_type=len(filter(lambda s: s == 1, subsection_num_block_types_dict.itervalues())),
            num_block_types=self._stats_dict(list(subsection_num_block_types_dict.itervalues())),
        )

    def _units_quality(self, course):
        subsection_unit_dict = self._get_subsections_and_units(course)
        num_leaf_blocks_list = [
            unit_info['num_leaf_blocks']
            for unit_dict in subsection_unit_dict.itervalues()
            for unit_info in unit_dict.itervalues()
        ]
        return dict(
            total_number=len(num_leaf_blocks_list),
            num_blocks=self._stats_dict(num_leaf_blocks_list),
        )

    def _videos_quality(self, course):
        video_blocks_in_course = modulestore().get_items(course.id, qualifiers={'category': 'video'})
        videos_in_val = list(get_videos_for_course(course.id))
        video_durations = [video['duration'] for video in videos_in_val]

        return dict(
            total_number=len(video_blocks_in_course),
            num_mobile_encoded=len(videos_in_val),
            num_with_val_id=len(filter(lambda v: v.edx_video_id, video_blocks_in_course)),
            durations=self._stats_dict(video_durations),
        )

    @request_cached
    def _get_subsections_and_units(self, course):
        """
        Returns {subsection_key: {unit_key: {num_leaf_blocks: <>, leaf_block_types: set(<>) }}}
        for all visible subsections and units.
        """
        _, visible_sections = self._get_sections(course)
        subsection_dict = {}
        for section in visible_sections:
            visible_subsections = self._get_visible_children(section)
            for subsection in visible_subsections:
                unit_dict = {}
                visible_units = self._get_visible_children(subsection)
                for unit in visible_units:
                    leaf_blocks = self._get_leaf_blocks(unit)
                    unit_dict[unit.location] = dict(
                        num_leaf_blocks=len(leaf_blocks),
                        leaf_block_types=set(block.location.block_type for block in leaf_blocks),
                    )
                subsection_dict[subsection.location] = unit_dict
        return subsection_dict

    @request_cached
    def _get_sections(self, course):
        return self._get_all_children(course)

    def _get_all_children(self, parent):
        store = modulestore()
        children = [store.get_item(child_usage_key) for child_usage_key in self._get_children(parent)]
        visible_children = filter(
            lambda s: not s.visible_to_staff_only and not s.hide_from_toc,
            children,
        )
        return children, visible_children

    def _get_visible_children(self, parent):
        _, visible_chidren = self._get_all_children(parent)
        return visible_chidren

    def _get_children(self, parent):
        if not hasattr(parent, 'children'):
            return []
        else:
            return parent.children

    def _get_leaf_blocks(self, unit):
        return [
            block for block in
            traverse_pre_order(unit, self._get_visible_children, lambda b: len(self._get_children(b)) == 0)
        ]

    def _stats_dict(self, data):
        if not data:
            return dict(
                min=None,
                max=None,
                mean=None,
                median=None,
                mode=None,
            )
        else:
            return dict(
                min=min(data),
                max=max(data),
                mean=np.around(np.mean(data)),
                median=np.around(np.median(data)),
                mode=stats.mode(data, axis=None)[0][0],
            )
