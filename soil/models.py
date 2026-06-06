from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone


class SoilComponent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='soil_components',
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['user', 'name'], name='unique_soil_component_per_user'),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('soil:component_list')


class PlantSoil(models.Model):
    plant = models.ForeignKey(
        'garden.Plant',
        on_delete=models.CASCADE,
        related_name='soils',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='plant_soils',
    )
    name = models.CharField(max_length=150, blank=True)
    set_at = models.DateTimeField(default=timezone.now)
    is_current = models.BooleanField(default=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-set_at', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['plant'],
                condition=Q(is_current=True),
                name='unique_current_soil_per_plant',
            ),
        ]

    def __str__(self):
        return self.name or f'{self.plant} soil from {self.set_at:%Y-%m-%d}'

    def get_absolute_url(self):
        return reverse('soil:plant_soil_edit', kwargs={'pk': self.pk})

    @property
    def composition_text(self):
        parts = [
            f'{self._format_percentage(part.percentage)}% {part.soil_component.name}'
            for part in self.parts.select_related('soil_component').order_by('soil_component__name')
        ]
        return ', '.join(parts)

    @staticmethod
    def _format_percentage(value):
        normalized = value.normalize()
        if normalized == normalized.to_integral():
            return format(normalized.to_integral(), 'f')
        return format(normalized, 'f').rstrip('0').rstrip('.')


class PlantSoilComponent(models.Model):
    plant_soil = models.ForeignKey(
        PlantSoil,
        on_delete=models.CASCADE,
        related_name='parts',
    )
    soil_component = models.ForeignKey(
        SoilComponent,
        on_delete=models.PROTECT,
        related_name='plant_soil_parts',
    )
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0.01), MaxValueValidator(100)],
    )

    class Meta:
        ordering = ['soil_component__name']
        constraints = [
            models.UniqueConstraint(
                fields=['plant_soil', 'soil_component'],
                name='unique_component_per_plant_soil',
            ),
        ]

    def __str__(self):
        return f'{self.soil_component}: {self.percentage:g}%'
