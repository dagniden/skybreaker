from django.shortcuts import get_object_or_404, render

from .models import Timeline


def timeline_detail(request, name='demo'):
    timeline = get_object_or_404(
        Timeline.objects.prefetch_related('events'),
        name=name,
        is_published=True,
    )
    events = timeline.events.filter(is_published=True).order_by('event_date', 'id')
    years_by_value = {}

    for event in events:
        years_by_value.setdefault(event.event_date.year, []).append(event)

    years = list(years_by_value.items())

    active_year = years[0][0] if years else None
    active_event = years[0][1][0] if years else None

    return render(
        request,
        'timeline/page_detail.html',
        {
            'timeline': timeline,
            'years': years,
            'active_year': active_year,
            'active_event': active_event,
        },
    )
