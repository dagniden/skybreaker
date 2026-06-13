from django.test import TestCase
from django.urls import reverse

from .models import TimelineEvent, TimelinePage, TimelineYear


class TimelinePageViewTests(TestCase):
    def test_published_page_shows_published_event(self):
        page = TimelinePage.objects.create(title='Demo', slug='demo', is_published=True)
        year = TimelineYear.objects.create(page=page, year=2001)
        TimelineEvent.objects.create(year=year, title='Launch', date_label='FEB 28', is_published=True)

        response = self.client.get(reverse('timeline:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Launch')
        self.assertContains(response, '2001')

    def test_unpublished_page_returns_404(self):
        TimelinePage.objects.create(title='Demo', slug='demo', is_published=False)

        response = self.client.get(reverse('timeline:index'))

        self.assertEqual(response.status_code, 404)
