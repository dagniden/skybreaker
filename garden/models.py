from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Plant(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='plants',
    )
    name = models.CharField(max_length=100)
    watering_interval_days = models.PositiveIntegerField()
    last_watered_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('garden:plant_detail', kwargs={'pk': self.pk})

    @property
    def moisture_percent(self):
        if self.watering_interval_days <= 0:
            return 0

        elapsed = timezone.now() - self.last_watered_at
        elapsed_days = elapsed.total_seconds() / 86400
        percent = 100 - elapsed_days / self.watering_interval_days * 100
        return max(0, min(100, round(percent)))


class PlantPhoto(models.Model):
    plant = models.ForeignKey(
        Plant,
        on_delete=models.CASCADE,
        related_name='photos',
    )
    image = models.ImageField(upload_to='plant_photos/%Y/%m/')
    taken_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-taken_at', '-created_at']

    def __str__(self):
        return f'{self.plant} photo from {self.taken_at:%Y-%m-%d}'
