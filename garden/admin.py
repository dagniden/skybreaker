from django.contrib import admin

from .models import Plant, PlantPhoto


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'watering_interval_days', 'last_watered_at', 'created_at')
    list_filter = ('user', 'created_at')
    search_fields = ('name', 'user__username')


@admin.register(PlantPhoto)
class PlantPhotoAdmin(admin.ModelAdmin):
    list_display = ('plant', 'taken_at', 'created_at')
    list_filter = ('taken_at', 'created_at')
    search_fields = ('plant__name', 'plant__user__username')
