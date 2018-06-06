""" Course API URLs. """
from django.conf import settings
from django.conf.urls import url

from cms.djangoapps.contentstore.api.views import course_import, course_validation

urlpatterns = [
    url(r'^v0/import/{course_id}/$'.format(course_id=settings.COURSE_ID_PATTERN,),
        course_import.CourseImportView.as_view(), name='course_import'),
]

urlpatterns = [
    url(r'^v1/validation/{course_id}/$'.format(course_id=settings.COURSE_ID_PATTERN,),
        course_validation.CourseValidationView.as_view(), name='course_validation'),
]
