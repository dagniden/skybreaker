from django.contrib import admin
from django.utils.html import format_html

from .models import TimelineEvent, TimelinePage, TimelineYear


class TimelineYearInline(admin.TabularInline):
    model = TimelineYear
    extra = 1
    fields = ('year', 'title', 'sort_order', 'is_published')
    ordering = ('sort_order', 'year')


class TimelineEventInline(admin.StackedInline):
    model = TimelineEvent
    extra = 1
    fields = (
        'event_date',
        'date_label',
        'kicker',
        'title',
        'description',
        'image',
        'image_alt',
        'sort_order',
        'is_published',
    )
    ordering = ('sort_order', 'event_date', 'id')


@admin.register(TimelinePage)
class TimelinePageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_published', 'updated_at')
    list_filter = ('is_published', 'created_at', 'updated_at')
    search_fields = ('title', 'subtitle', 'intro_text')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [TimelineYearInline]


@admin.register(TimelineYear)
class TimelineYearAdmin(admin.ModelAdmin):
    list_display = ('year', 'page', 'title', 'sort_order', 'is_published', 'updated_at')
    list_filter = ('page', 'is_published', 'created_at', 'updated_at')
    search_fields = ('title', 'description', 'page__title')
    inlines = [TimelineEventInline]
    ordering = ('page', 'sort_order', 'year')


@admin.register(TimelineEvent)
class TimelineEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'year', 'display_date', 'sort_order', 'is_published', 'image_preview')
    list_filter = ('year__page', 'year', 'is_published', 'event_date', 'created_at')
    search_fields = ('title', 'description', 'kicker', 'year__page__title')
    autocomplete_fields = ('year',)
    readonly_fields = ('image_preview',)
    fieldsets = (
        (None, {'fields': ('year', 'event_date', 'date_label', 'kicker', 'title', 'description')}),
        ('Изображение', {'fields': ('image', 'image_alt', 'image_preview')}),
        ('Публикация', {'fields': ('sort_order', 'is_published')}),
    )
    ordering = ('year__page', 'year__sort_order', 'year__year', 'sort_order', 'event_date')

    @admin.display(description='Изображение')
    def image_preview(self, obj):
        if not obj.image:
            return '-'
        return format_html('<img src="{}" style="max-width: 180px; max-height: 90px; object-fit: cover;" />', obj.image.url)
