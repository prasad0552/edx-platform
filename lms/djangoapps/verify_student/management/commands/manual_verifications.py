"""
Django admin commands related to verify_student
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from lms.djangoapps.verify_student.models import ManualVerification
from lms.djangoapps.verify_student.utils import earliest_allowed_verification_date


class Command(BaseCommand):
    """
        This method attempts to manually verify users.
        Example usage:
            $ ./manage.py lms manual_verifications --email-id email1 email2 email3 ...
    """
    help = 'Manually verifies one or more users passed as an argument list.'

    def add_arguments(self, parser):
        """
        Add arguments to the command parser.
        """
        parser.add_argument(
            '--email-id', '--email_id',
            dest='email_ids',
            nargs='+',
            required=True,
            help=u'Email id list for verification.'
        )

    def handle(self, *args, **options):

        email_ids = options['email_ids']

        for email in email_ids:
            user = User.objects.get(email=email)

            # Get previous valid, non expired verification attempts for this user
            verifications = ManualVerification.objects.filter(
                user=user,
                status="approved",
                created_at__gte=earliest_allowed_verification_date(),
            )

            # If there is none, create a new approved verification for the user.
            if not verifications:
                ManualVerification.objects.create(
                    user=user,
                    status="approved",
                    name=user.profile.name,
                )
