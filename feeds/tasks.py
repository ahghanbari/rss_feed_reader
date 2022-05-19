
from celery import shared_task
from feeds.utils import update_feeds
from celery.utils.log import get_task_logger


# This is for celery beat
@shared_task
def get_those_feeds():

    logger = get_task_logger(__name__)
    logger.info("\n\nStartign to update the feeds...\n")
    update_feeds(30)