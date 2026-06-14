from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import Timeline, TimelineEvent


MONTH_NAMES = {
    1: 'Январь',
    2: 'Февраль',
    3: 'Март',
    4: 'Апрель',
    5: 'Май',
    6: 'Июнь',
    7: 'Июль',
    8: 'Август',
    9: 'Сентябрь',
    10: 'Октябрь',
    11: 'Ноябрь',
    12: 'Декабрь',
}


class EventYearFilter(admin.SimpleListFilter):
    title = 'Год события'
    parameter_name = 'event_year'

    def lookups(self, request, model_admin):
        years = model_admin.get_queryset(request).dates('event_date', 'year', order='DESC')
        return [(year.year, year.year) for year in years]

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        return queryset.filter(event_date__year=self.value())


class EventMonthFilter(admin.SimpleListFilter):
    title = 'Месяц события'
    parameter_name = 'event_month'

    def lookups(self, request, model_admin):
        months = {
            month.month
            for month in model_admin.get_queryset(request).dates('event_date', 'month', order='ASC')
        }
        return [(month, MONTH_NAMES[month]) for month in sorted(months)]

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        return queryset.filter(event_date__month=self.value())


class EventTimelineFilter(admin.SimpleListFilter):
    title = 'Таймлайн'
    parameter_name = 'timeline'

    def lookups(self, request, model_admin):
        timelines = (
            Timeline.objects.filter(events__in=model_admin.get_queryset(request))
            .distinct()
            .order_by('name')
        )
        return [(timeline.pk, timeline.name) for timeline in timelines]

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        return queryset.filter(timeline_id=self.value())


def user_owns_timeline(user, timeline):
    return user.is_superuser or timeline.user_id == user.id


def user_owns_event(user, event):
    return user.is_superuser or event.timeline.user_id == user.id


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
    list_display = ('name', 'user', 'events_count', 'is_published', 'updated_at')
    list_filter = ('is_published', 'created_at', 'updated_at')
    search_fields = ('name', 'description', 'user__username')
    fields = ('user', 'name', 'description', 'is_published')
    inlines = [TimelineEventInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request).annotate(events_total=Count('events'))
        if request.user.is_superuser:
            return queryset
        return queryset.filter(user=request.user)

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return self.fields
        return ('name', 'description', 'is_published')

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return super().has_add_permission(request)
        return False

    def has_view_permission(self, request, obj=None):
        if not super().has_view_permission(request, obj):
            return False
        if obj is None:
            return True
        return user_owns_timeline(request.user, obj)

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        if obj is None:
            return True
        return user_owns_timeline(request.user, obj)

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return super().has_delete_permission(request, obj)
        return False

    @admin.display(description='Событий', ordering='events_total')
    def events_count(self, obj):
        return obj.events_total

    def save_model(self, request, obj, form, change):
        if not obj.pk and not obj.user_id:
            obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(TimelineEvent)
class TimelineEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'timeline', 'event_date', 'display_kicker', 'display_date', 'is_published', 'image_preview')
    list_filter = (EventTimelineFilter, EventYearFilter, EventMonthFilter, 'is_published')
    search_fields = ('title', 'description', 'timeline__name')
    autocomplete_fields = ('timeline',)
    readonly_fields = ('image_preview',)
    date_hierarchy = 'event_date'
    actions = ('publish_events', 'unpublish_events')
    fields = (
        'timeline',
        'event_date',
        'title',
        'description',
        'image',
        'image_preview',
        'is_published',
    )
    ordering = ('timeline', 'event_date', 'id')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(timeline__user=request.user)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'timeline' and not request.user.is_superuser:
            kwargs['queryset'] = Timeline.objects.filter(user=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_add_permission(self, request):
        if not super().has_add_permission(request):
            return False
        if request.user.is_superuser:
            return True
        return Timeline.objects.filter(user=request.user).exists()

    def has_view_permission(self, request, obj=None):
        if not super().has_view_permission(request, obj):
            return False
        if obj is None:
            return True
        return user_owns_event(request.user, obj)

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        if obj is None:
            return True
        return user_owns_event(request.user, obj)

    def has_delete_permission(self, request, obj=None):
        if not super().has_delete_permission(request, obj):
            return False
        if obj is None:
            return True
        return user_owns_event(request.user, obj)

    @admin.action(description='Опубликовать выбранные события')
    def publish_events(self, request, queryset):
        queryset.update(is_published=True)

    @admin.action(description='Снять выбранные события с публикации')
    def unpublish_events(self, request, queryset):
        queryset.update(is_published=False)

    @admin.display(description='Изображение')
    def image_preview(self, obj):
        if not obj.image:
            return '-'
        return format_html('<img src="{}" style="max-width: 180px; max-height: 90px; object-fit: cover;" />', obj.image.url)
