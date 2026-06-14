from datetime import date

from django.db import migrations, models


def fill_missing_event_dates(apps, schema_editor):
    TimelineEvent = apps.get_model('timeline', 'TimelineEvent')

    for event in TimelineEvent.objects.filter(event_date__isnull=True).select_related('year'):
        event.event_date = date(event.year.year, 1, 1)
        event.save(update_fields=['event_date'])


class Migration(migrations.Migration):

    dependencies = [
        ('timeline', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fill_missing_event_dates, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='timelineevent',
            name='event_date',
            field=models.DateField(),
        ),
    ]
