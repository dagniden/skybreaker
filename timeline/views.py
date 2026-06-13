from django.shortcuts import get_object_or_404, render

from .models import TimelinePage


def page_detail(request, slug='demo'):
    page = get_object_or_404(
        TimelinePage.objects.prefetch_related('years__events'),
        slug=slug,
        is_published=True,
    )
    years = []
    for year in page.years.all():
        if not year.is_published:
            continue
        events = [event for event in year.events.all() if event.is_published]
        if events:
            years.append((year, events))

    active_year = years[0][0] if years else None
    active_event = years[0][1][0] if years else None

    return render(
        request,
        'timeline/page_detail.html',
        {
            'page': page,
            'years': years,
            'active_year': active_year,
            'active_event': active_event,
        },
    )
