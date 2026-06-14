from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Timeline, TimelineEvent


@override_settings(ALLOWED_HOSTS=['testserver'])
class TimelinePageViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='owner', password='password')

    def test_published_timeline_shows_published_event(self):
        timeline = Timeline.objects.create(user=self.user, name='demo', is_published=True)
        TimelineEvent.objects.create(
            timeline=timeline,
            title='Launch',
            event_date=date(2001, 2, 28),
            is_published=True,
        )

        response = self.client.get(reverse('timeline:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Launch')
        self.assertContains(response, 'TIMELINE: FEB 2001')
        self.assertContains(response, '2001')

    def test_unpublished_timeline_returns_404(self):
        Timeline.objects.create(user=self.user, name='demo', is_published=False)

        response = self.client.get(reverse('timeline:index'))

        self.assertEqual(response.status_code, 404)

    def test_unpublished_events_are_hidden(self):
        timeline = Timeline.objects.create(user=self.user, name='demo', is_published=True)
        TimelineEvent.objects.create(
            timeline=timeline,
            title='Hidden',
            event_date=date(2001, 2, 28),
            is_published=False,
        )

        response = self.client.get(reverse('timeline:index'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Hidden')
