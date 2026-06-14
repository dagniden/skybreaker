from django.conf import settings
from django.db import models
from django.urls import reverse


class Timeline(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='timelines',
    )
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('timeline:timeline_detail', kwargs={'name': self.name})


class TimelineEvent(models.Model):
    timeline = models.ForeignKey(
        Timeline,
        on_delete=models.CASCADE,
        related_name='events',
    )
    event_date = models.DateField()
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='timeline/events/%Y/%m/', blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'timeline_event'
        ordering = ['event_date', 'id']
        indexes = [
            models.Index(fields=['timeline', 'event_date']),
            models.Index(fields=['timeline', 'is_published']),
        ]

    def __str__(self):
        return f'{self.event_date:%Y-%m-%d}: {self.title}'

    @property
    def display_date(self):
        return self.event_date.strftime('%b %d').upper()

    @property
    def display_kicker(self):
        return f"TIMELINE: {self.event_date.strftime('%b %Y').upper()}"
