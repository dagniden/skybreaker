import secrets

from django.conf import settings
from django.db import models
from django.urls import reverse

from .storage import replay_storage


def replay_id():
    return secrets.token_urlsafe(18)


class Replay(models.Model):
    id = models.CharField(primary_key=True, max_length=24, default=replay_id, editable=False)
    file = models.FileField(storage=replay_storage, upload_to='', max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    duration_ms = models.PositiveIntegerField()
    format_version = models.PositiveSmallIntegerField(default=1)
    player_goals = models.PositiveIntegerField(default=0)
    bot_goals = models.PositiveIntegerField(default=0)
    size_bytes = models.PositiveIntegerField()
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name='football_replays')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Реплей'
        verbose_name_plural = 'Реплеи'

    def __str__(self):
        return f'{self.id}: {self.player_goals}:{self.bot_goals}'

    def get_absolute_url(self):
        return reverse('football:viewer', args=[self.pk])

    @property
    def duration_display(self):
        seconds = self.duration_ms // 1000
        return f'{seconds // 60}:{seconds % 60:02}'


class UploadBudget(models.Model):
    """Singleton lock shared by all upload workers; created by the migration."""
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    window_started = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
