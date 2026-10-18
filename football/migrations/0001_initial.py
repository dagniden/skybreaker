import django.db.models.deletion
import django.utils.timezone
import football.models
import football.storage
from django.conf import settings
from django.db import migrations, models


def create_budget(apps, schema_editor):
    apps.get_model('football', 'UploadBudget').objects.using(schema_editor.connection.alias).get_or_create(
        pk=1, defaults={'window_started': django.utils.timezone.now(), 'attempts': 0})


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name='UploadBudget',
            fields=[
                ('id', models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ('window_started', models.DateTimeField()),
                ('attempts', models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Replay',
            fields=[
                ('id', models.CharField(default=football.models.replay_id, editable=False, max_length=24, primary_key=True, serialize=False)),
                ('file', models.FileField(storage=football.storage.replay_storage, upload_to='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('duration_ms', models.PositiveIntegerField()),
                ('format_version', models.PositiveSmallIntegerField(default=1)),
                ('player_goals', models.PositiveIntegerField(default=0)),
                ('bot_goals', models.PositiveIntegerField(default=0)),
                ('size_bytes', models.PositiveIntegerField()),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='football_replays', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Реплей', 'verbose_name_plural': 'Реплеи', 'ordering': ['-created_at']},
        ),
        migrations.RunPython(create_budget, migrations.RunPython.noop),
    ]
