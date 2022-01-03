"""
command to send campaigns
"""
import logging

from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _

from ...models import Campaign


class Command(BaseCommand):
    help = _("Submit pending messages.")

    def handle(self, *args, **options):
        # Setup logging based on verbosity: 1 -> INFO, >1 -> DEBUG
        verbosity = int(options['verbosity'])
        logger = logging.getLogger('campaign')
        if verbosity == 0:
            logger.setLevel(logging.WARN)
        elif verbosity == 1:  # default
            logger.setLevel(logging.INFO)
        elif verbosity > 1:
            logger.setLevel(logging.DEBUG)
        if verbosity > 2:
            logger = logging.getLogger()
            logger.setLevel(logging.DEBUG)

        logger.info(_('Submitting queued campaigns'))

        # Call submission
        Campaign.submit_queue()
