try:
    from celery.task import PeriodicTask
    from celery.registry import tasks
except ImportError:
    PeriodicTask = object
    tasks = None

from datetime import timedelta
import logging
from .models import Answer
from . import settings as local_settings

logger = logging.getLogger('crowdsourcing.tasks')

class SyncFlickr(PeriodicTask):
    run_every = timedelta(minutes=5)

    def run(self, *args, **kwargs):
        logger.debug("Syncing flickr")
        Answer.sync_to_flickr()

if tasks and not local_settings.SYNCHRONOUS_FLICKR_UPLOAD:
    tasks.register(SyncFlickr)
