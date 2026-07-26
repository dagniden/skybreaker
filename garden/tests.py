from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Plant, PlantEvent


class PlantEventViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='garden-user', password='password')
        self.plant = Plant.objects.create(
            user=self.user,
            name='Монстера',
            watering_interval_days=7,
            last_watered_at=timezone.now(),
        )
        self.client.force_login(self.user)

    def test_water_plant_creates_watering_event(self):
        response = self.client.post(reverse('garden:plant_water', kwargs={'pk': self.plant.pk}), {'volume': '50-70'})

        self.assertRedirects(response, reverse('garden:plant_detail', kwargs={'pk': self.plant.pk}))
        event = PlantEvent.objects.get(plant=self.plant)
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.event_type, PlantEvent.EventType.WATERING)
        self.assertEqual(event.title, 'Полив')
        self.assertEqual(event.comment, '50-70 мл на 7 дн.')

    def test_water_plant_without_volume_stores_watering_interval(self):
        response = self.client.post(reverse('garden:plant_water', kwargs={'pk': self.plant.pk}))

        self.assertRedirects(response, reverse('garden:plant_detail', kwargs={'pk': self.plant.pk}))
        event = PlantEvent.objects.get(plant=self.plant)
        self.assertEqual(event.comment, 'на 7 дн.')

    def test_ajax_water_plant_still_returns_json(self):
        response = self.client.post(
            reverse('garden:plant_water', kwargs={'pk': self.plant.pk}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['ok'], True)
        self.assertEqual(PlantEvent.objects.filter(event_type=PlantEvent.EventType.WATERING).count(), 1)

    def test_add_note_creates_note_event(self):
        response = self.client.post(
            reverse('garden:plant_note_create', kwargs={'pk': self.plant.pk}),
            {'comment': 'Любит влажный воздух'},
        )

        self.assertRedirects(response, reverse('garden:plant_detail', kwargs={'pk': self.plant.pk}))
        event = PlantEvent.objects.get(plant=self.plant)
        self.assertEqual(event.event_type, PlantEvent.EventType.NOTE)
        self.assertEqual(event.title, 'Заметка')
        self.assertEqual(event.comment, 'Любит влажный воздух')

    def test_fertilize_creates_fertilizing_event(self):
        response = self.client.post(
            reverse('garden:plant_fertilize', kwargs={'pk': self.plant.pk}),
            {'fertilizer': 'Опрыск. Аминоцимус'},
        )

        self.assertRedirects(response, reverse('garden:plant_detail', kwargs={'pk': self.plant.pk}))
        event = PlantEvent.objects.get(plant=self.plant)
        self.assertEqual(event.event_type, PlantEvent.EventType.FERTILIZING)
        self.assertEqual(event.title, 'Удобрение')
        self.assertEqual(event.comment, 'Опрыск. Аминоцимус')

    def test_user_cannot_create_event_for_other_user_plant(self):
        other_user = get_user_model().objects.create_user(username='other-user', password='password')
        other_plant = Plant.objects.create(
            user=other_user,
            name='Фикус',
            watering_interval_days=7,
            last_watered_at=timezone.now(),
        )

        response = self.client.post(
            reverse('garden:plant_note_create', kwargs={'pk': other_plant.pk}),
            {'comment': 'Чужая заметка'},
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(PlantEvent.objects.exists())

    def test_detail_page_shows_note_and_event_history(self):
        PlantEvent.objects.create(
            user=self.user,
            plant=self.plant,
            event_type=PlantEvent.EventType.NOTE,
            title='Заметка',
            comment='Любит влажный воздух',
        )
        PlantEvent.objects.create(
            user=self.user,
            plant=self.plant,
            event_type=PlantEvent.EventType.WATERING,
            title='Полив',
            comment='50 мл на 7 дн.',
        )

        response = self.client.get(reverse('garden:plant_detail', kwargs={'pk': self.plant.pk}))

        self.assertContains(response, 'Любит влажный воздух')
        self.assertContains(response, 'Последние события')
        self.assertContains(response, '50 мл на 7 дн.')

    def test_event_cards_hide_watering_and_fertilizing_titles(self):
        PlantEvent.objects.create(
            user=self.user,
            plant=self.plant,
            event_type=PlantEvent.EventType.WATERING,
            title='Полив',
            comment='50 мл на 7 дн.',
        )
        PlantEvent.objects.create(
            user=self.user,
            plant=self.plant,
            event_type=PlantEvent.EventType.FERTILIZING,
            title='Удобрение',
            comment='Аминоцимус полив',
        )

        response = self.client.get(reverse('garden:plant_detail', kwargs={'pk': self.plant.pk}))

        self.assertContains(response, '50 мл на 7 дн.')
        self.assertContains(response, 'Аминоцимус полив')
        self.assertNotContains(response, '<strong>Полив</strong>', html=True)
        self.assertNotContains(response, '<strong>Удобрение</strong>', html=True)

    def test_detail_page_recent_events_excludes_notes_and_limits_to_five(self):
        for index in range(6):
            PlantEvent.objects.create(
                user=self.user,
                plant=self.plant,
                event_type=PlantEvent.EventType.WATERING,
                title=f'Полив {index}',
            )
        PlantEvent.objects.create(
            user=self.user,
            plant=self.plant,
            event_type=PlantEvent.EventType.NOTE,
            title='Заметка',
            comment='Только в заметках',
        )

        response = self.client.get(reverse('garden:plant_detail', kwargs={'pk': self.plant.pk}))

        self.assertEqual(len(response.context['recent_events']), 5)
        self.assertTrue(all(event.event_type != PlantEvent.EventType.NOTE for event in response.context['recent_events']))

    def test_event_list_page_shows_all_events_including_notes(self):
        PlantEvent.objects.create(
            user=self.user,
            plant=self.plant,
            event_type=PlantEvent.EventType.NOTE,
            title='Заметка',
            comment='Любит влажный воздух',
        )

        response = self.client.get(reverse('garden:plant_event_list', kwargs={'pk': self.plant.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'История {self.plant.name}')
        self.assertContains(response, 'Любит влажный воздух')


class MigratePlantNotesToEventsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='notes-user', password='password')
        self.plant = Plant.objects.create(
            user=self.user,
            name='Монстера',
            watering_interval_days=7,
            last_watered_at=timezone.now(),
            notes='Любит пересыхать\n\nАминоцимус 30.06 полив',
        )

    def test_command_splits_multiline_notes_into_events(self):
        call_command('migrate_plant_notes_to_events', stdout=StringIO())

        comments = list(PlantEvent.objects.order_by('comment').values_list('comment', flat=True))
        self.assertEqual(comments, ['Аминоцимус 30.06 полив', 'Любит пересыхать'])

    def test_command_dry_run_does_not_create_events(self):
        call_command('migrate_plant_notes_to_events', '--dry-run', stdout=StringIO())

        self.assertFalse(PlantEvent.objects.exists())

    def test_command_does_not_duplicate_existing_events(self):
        call_command('migrate_plant_notes_to_events', stdout=StringIO())
        call_command('migrate_plant_notes_to_events', stdout=StringIO())

        self.assertEqual(PlantEvent.objects.count(), 2)
