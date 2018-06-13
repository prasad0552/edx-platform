""" Tests for journals learner dashboard views. """

import mock

from django.conf import settings
from django.core.urlresolvers import reverse

from lms.djangoapps.courseware.tests.helpers import LoginEnrollmentTestCase
from openedx.features.journals.tests.utils import get_mocked_journal_access


@mock.patch.dict(settings.FEATURES, {"ENABLE_JOURNAL_INTEGRATION": True})
class JournalLearnerDashboardTest(LoginEnrollmentTestCase):
    """ Tests for the student account views that update the user's account information. """

    def setUp(self):
        super(JournalLearnerDashboardTest, self).setUp()
        self.setup_user()
        self.path = reverse('journal_listing_view')

    def test_without_authenticated_user(self):
        self.logout()
        response = self.client.get(path=self.path)
        self.assertEqual(response.status_code, 404)

    @mock.patch('openedx.features.journals.views.learner_dashboard.fetch_journal_access')
    def test_with_empty_journals(self, mocked_journal_access):
        mocked_journal_access.return_value = []
        response = self.client.get(path=self.path)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Journals")
        self.assertContains(response, "You have not purchased access to any journals yet.")

    @mock.patch('openedx.features.journals.views.learner_dashboard.fetch_journal_access')
    def test_with_with_valid_data(self, mocked_journal_access):
        journals = get_mocked_journal_access()
        mocked_journal_access.return_value = journals
        response = self.client.get(path=self.path)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "View Journal")
        for journal in journals:
            self.assertContains(response, journal["journal"]["name"])
            self.assertContains(response, journal["journal"]["organization"])
