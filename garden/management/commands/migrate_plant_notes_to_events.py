from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from garden.models import Plant, PlantEvent


class Command(BaseCommand):
    help = 'Migrates non-empty Plant.notes lines to PlantEvent note events.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show how many events would be created without writing to the database.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        occurred_at = timezone.now()
        created_count = 0
        skipped_count = 0

        plants = Plant.objects.exclude(notes='').select_related('user')

        with transaction.atomic():
            for plant in plants.iterator():
                for line in plant.notes.splitlines():
                    comment = line.strip()
                    if not comment:
                        continue

                    exists = PlantEvent.objects.filter(
                        user=plant.user,
                        plant=plant,
                        event_type=PlantEvent.EventType.NOTE,
                        title='Заметка',
                        comment=comment,
                    ).exists()
                    if exists:
                        skipped_count += 1
                        continue

                    created_count += 1
                    if dry_run:
                        continue

                    PlantEvent.objects.create(
                        user=plant.user,
                        plant=plant,
                        event_type=PlantEvent.EventType.NOTE,
                        occurred_at=occurred_at,
                        title='Заметка',
                        comment=comment,
                    )

            if dry_run:
                transaction.set_rollback(True)

        action = 'Would create' if dry_run else 'Created'
        self.stdout.write(self.style.SUCCESS(f'{action} {created_count} note events.'))
        if skipped_count:
            self.stdout.write(f'Skipped {skipped_count} existing note events.')
