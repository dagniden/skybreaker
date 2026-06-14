from django.contrib import admin
from django.utils.html import format_html

from .models import Timeline, TimelineEvent


class TimelineEventInline(admin.StackedInline):
    model = TimelineEvent
    extra = 1
    fields = ('event_date', 'title', 'description', 'image', 'image_preview', 'is_published')
    readonly_fields = ('image_preview',)
    ordering = ('event_date', 'id')

    @admin.display(description='Изображение')
    def image_preview(self, obj):
        if not obj.image:
            return '-'
        return format_html('<img src="{}" style="max-width: 180px; max-height: 90px; object-fit: cover;" />', obj.image.url)


@admin.register(Timeline)
class TimelineAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'is_published', 'updated_at')
    list_filter = ('is_published', 'created_at', 'updated_at')
    search_fields = ('name', 'description', 'user__username')
    fields = ('user', 'name', 'description', 'is_published')
    inlines = [TimelineEventInline]

    def save_model(self, request, obj, form, change):
        if not obj.pk and not obj.user_id:
            obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(TimelineEvent)
class TimelineEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'timeline', 'event_date', 'display_kicker', 'display_date', 'is_published', 'image_preview')
    list_filter = ('timeline', 'is_published', 'event_date', 'created_at')
    search_fields = ('title', 'description', 'timeline__name')
    autocomplete_fields = ('timeline',)
    readonly_fields = ('image_preview',)
    fieldsets = (
        (None, {'fields': ('timeline', 'event_date', 'title', 'description')}),
        ('Изображение', {'fields': ('image', 'image_preview')}),
        ('Публикация', {'fields': ('is_published',)}),
    )
    ordering = ('timeline', 'event_date', 'id')

    @admin.display(description='Изображение')
    def image_preview(self, obj):
        if not obj.image:
            return '-'
        return format_html('<img src="{}" style="max-width: 180px; max-height: 90px; object-fit: cover;" />', obj.image.url)
