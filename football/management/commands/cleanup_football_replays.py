from django.core.management.base import BaseCommand
from django.utils import timezone

from football.models import Replay


class Command(BaseCommand):
    help = 'Delete expired football replay rows and their private files.'

    def handle(self, *args, **options):
        # Batches keep transaction/file callback memory bounded.
        count = 0
        while True:
            ids = list(Replay.objects.filter(expires_at__lte=timezone.now()).values_list('pk', flat=True)[:100])
            if not ids:
                break
            Replay.objects.filter(pk__in=ids).delete()
            count += len(ids)
        self.stdout.write(self.style.SUCCESS(f'Deleted {count} expired replays.'))
