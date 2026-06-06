from django.contrib import admin

from .models import PlantSoil, PlantSoilComponent, SoilComponent


class PlantSoilComponentInline(admin.TabularInline):
    model = PlantSoilComponent
    extra = 0


@admin.register(SoilComponent)
class SoilComponentAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'user__username')


@admin.register(PlantSoil)
class PlantSoilAdmin(admin.ModelAdmin):
    list_display = ('plant', 'user', 'name', 'set_at', 'is_current', 'created_at')
    list_filter = ('is_current', 'set_at', 'created_at')
    search_fields = ('plant__name', 'user__username', 'name')
    inlines = [PlantSoilComponentInline]
