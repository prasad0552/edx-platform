"""
Tests for django admin commands in the verify_student module

"""

from django.core.management import call_command
from django.test import TestCase
from nose.tools import assert_equals
from lms.djangoapps.verify_student.models import ManualVerification
from lms.djangoapps.verify_student.utils import earliest_allowed_verification_date
from student.tests.factories import UserFactory


class TestVerifyStudentCommand(TestCase):
    """
    Tests for django admin commands in the verify_student module
    """

    def setUp(self):
        super(TestVerifyStudentCommand, self).setUp()
        self.user1 = UserFactory.create()
        self.user2 = UserFactory.create()

    def test_manual_verifications(self):
        """
        Tests that the manual_verifications management command executes successfully
        """
        assert_equals(len(ManualVerification.objects.filter(status="approved")), 0)

        call_command('manual_verifications', '--email-id', self.user1.email, self.user2.email)

        assert_equals(len(ManualVerification.objects.filter(status="approved")), 2)

    def test_manual_verifications_created_date(self):
        """
        Tests that the manual_verifications management command does not create a new verification
        if a previous non-expired verification exists
        """
        call_command('manual_verifications', '--email-id', self.user1.email)

        verification1 = ManualVerification.objects.filter(
            user=self.user1,
            status="approved",
            created_at__gte=earliest_allowed_verification_date()
        )

        call_command('manual_verifications', '--email-id', self.user1.email)

        verification2 = ManualVerification.objects.filter(
            user=self.user1,
            status="approved",
            created_at__gte=earliest_allowed_verification_date()
        )

        TestCase.assertQuerysetEqual(self, verification1, [repr(r) for r in verification2])
