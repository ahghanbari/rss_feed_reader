
from django.core.management.base import BaseCommand
from feeds.utils import update_feeds


class Command(BaseCommand):
    help = 'Rrefreshes the RSS feeds'

    def handle(self, *args, **options):        
        update_feeds(30)
        self.stdout.write(self.style.SUCCESS('Finished'))