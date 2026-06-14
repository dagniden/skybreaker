import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('timeline', '0002_require_event_date'),
    ]

    operations = [
        migrations.DeleteModel(
            name='TimelineEvent',
        ),
        migrations.DeleteModel(
            name='TimelineYear',
        ),
        migrations.DeleteModel(
            name='TimelinePage',
        ),
        migrations.CreateModel(
            name='Timeline',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, unique=True)),
                ('description', models.TextField(blank=True)),
                ('is_published', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='timelines', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='TimelineEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_date', models.DateField()),
                ('title', models.CharField(max_length=250)),
                ('description', models.TextField(blank=True)),
                ('image', models.ImageField(blank=True, upload_to='timeline/events/%Y/%m/')),
                ('is_published', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('timeline', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='timeline.timeline')),
            ],
            options={
                'db_table': 'timeline_event',
                'ordering': ['event_date', 'id'],
            },
        ),
        migrations.AddIndex(
            model_name='timelineevent',
            index=models.Index(fields=['timeline', 'event_date'], name='timeline_ev_timelin_fa189a_idx'),
        ),
        migrations.AddIndex(
            model_name='timelineevent',
            index=models.Index(fields=['timeline', 'is_published'], name='timeline_ev_timelin_fcaac9_idx'),
        ),
    ]
