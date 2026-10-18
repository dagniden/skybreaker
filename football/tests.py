import copy
import json
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Replay, UploadBudget
from .validation import MAX_BYTES


def recording():
    units = [{'team': team, 'keeper': i == 0} for team in (0, 1) for i in range(6)]
    frames = [{'t': t, 'u': [[90 + i * 60, 450, 1, 0] for i in range(12)],
               'b': [800, 450], 'h': -1, 's': [0, 0], 'r': 0} for t in (0, 50, 100)]
    return {'version': 1, 'mode': 'free_play', 'field': [1600, 900], 'units': units,
            'frames': frames, 'duration_ms': 100}


@override_settings(FOOTBALL_REPLAY_UPLOAD_TOKEN='test-football-token',
                   ALLOWED_HOSTS=['testserver', 'football.sky-breaker.ru'],
                   FOOTBALL_SITE_HOSTS=['football.sky-breaker.ru'])
class ReplayTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        # Storage is constructed by the field at app startup; replace the field's
        # storage explicitly so tests can never touch real recording files.
        from django.core.files.storage import FileSystemStorage
        self.field = Replay._meta.get_field('file')
        old_storage = self.field.storage
        self.field.storage = FileSystemStorage(location=self.directory.name)
        self.addCleanup(setattr, self.field, 'storage', old_storage)

    def upload(self, data=None, client=None, **kwargs):
        return (client or self.client).post(reverse('football:upload'),
                                           data=json.dumps(recording() if data is None else data),
                                           content_type='application/json',
                                           HTTP_AUTHORIZATION='Bearer test-football-token', **kwargs)

    def test_upload_and_anonymous_playback(self):
        response = self.upload()
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        replay = Replay.objects.get(pk=payload['id'])
        self.assertEqual(len(replay.pk), 24)
        self.assertTrue(Path(replay.file.path).is_file())
        self.assertEqual(replay.duration_ms, 100)
        self.assertNotIn('test-football-token', response.content.decode())
        public = Client()
        self.assertContains(public.get(replay.get_absolute_url()), 'data-replay-url=')
        data = public.get(reverse('football:replay_data', args=[replay.pk]))
        self.assertEqual(data.status_code, 200)
        self.assertEqual(json.loads(b''.join(data.streaming_content)), recording())
        self.assertEqual(data['Cache-Control'], 'no-store')
        self.assertIn('frame-ancestors', data['Content-Security-Policy'])

    def test_token_is_required_even_with_session_csrf_checks(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('football:upload'), '{}', content_type='application/json').status_code, 401)
        self.assertEqual(self.upload(client=client).status_code, 201)
        with override_settings(FOOTBALL_REPLAY_UPLOAD_TOKEN=''):
            self.assertEqual(self.upload().status_code, 503)

    def test_catalog_and_host_specific_homepage(self):
        payload = self.upload().json()
        replay = Replay.objects.get(pk=payload['id'])
        catalog = self.client.get('/', HTTP_HOST='football.sky-breaker.ru')
        self.assertContains(catalog, 'История матчей')
        self.assertContains(catalog, replay.get_absolute_url())
        self.assertNotContains(catalog, 'test-football-token')
        self.assertContains(self.client.get('/football/'), 'Смотреть матч')
        self.assertNotEqual(self.client.get('/').resolver_match.func, self.client.get('/football/').resolver_match.func)

    def test_expired_replay_is_not_listed_or_readable(self):
        replay = Replay.objects.get(pk=self.upload().json()['id'])
        replay.expires_at = timezone.now() - timedelta(seconds=1)
        replay.save(update_fields=['expires_at'])
        self.assertNotContains(self.client.get('/football/'), replay.get_absolute_url())
        self.assertEqual(self.client.get(replay.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get(reverse('football:replay_data', args=[replay.pk])).status_code, 404)

    def test_invalid_replays_and_type_checks(self):
        changes = [lambda d: d.update(version=True), lambda d: d.update(duration_ms=999),
                   lambda d: d['frames'][1].update(t=0), lambda d: d['frames'][0].update(b=[float('nan'), 0]),
                   lambda d: d.update(units=[]), lambda d: d['frames'][1].update(h=12)]
        for change in changes:
            data = copy.deepcopy(recording())
            change(data)
            self.assertEqual(self.upload(data).status_code, 400)
        self.assertFalse(Replay.objects.exists())

    def test_size_media_type_and_quota(self):
        response = self.client.post(reverse('football:upload'), b' ' * (MAX_BYTES + 1),
                                    content_type='application/json', HTTP_AUTHORIZATION='Bearer test-football-token')
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.client.post(reverse('football:upload'), '{}', content_type='text/plain',
                                         HTTP_AUTHORIZATION='Bearer test-football-token').status_code, 415)
        with override_settings(FOOTBALL_REPLAY_MAX_STORAGE_BYTES=10):
            self.assertEqual(self.upload().status_code, 507)
        self.assertFalse(list(Path(self.directory.name).glob('*')))

    def test_rate_limit_is_persistent_and_invalid_attempts_count(self):
        with override_settings(FOOTBALL_REPLAY_UPLOADS_PER_WINDOW=2):
            self.assertEqual(self.upload({}).status_code, 400)
            self.assertEqual(self.upload({}, client=Client()).status_code, 400)
            response = self.upload(client=Client())
            self.assertEqual(response.status_code, 429)
            UploadBudget.objects.filter(pk=1).update(window_started=timezone.now() - timedelta(minutes=11))
            self.assertEqual(self.upload().status_code, 201)

    def test_cleanup_and_admin_deletion_remove_files(self):
        replay = Replay.objects.get(pk=self.upload().json()['id'])
        path = Path(replay.file.path)
        Replay.objects.filter(pk=replay.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        with self.captureOnCommitCallbacks(execute=True):
            call_command('cleanup_football_replays', verbosity=0)
        self.assertFalse(path.exists())
        self.assertFalse(Replay.objects.exists())
        replay = Replay.objects.get(pk=self.upload().json()['id'])
        path = Path(replay.file.path)
        with self.captureOnCommitCallbacks(execute=True):
            Replay.objects.filter(pk=replay.pk).delete()
        self.assertFalse(path.exists())

    def test_missing_file_is_404(self):
        replay = Replay.objects.get(pk=self.upload().json()['id'])
        Path(replay.file.path).unlink()
        self.assertEqual(self.client.get(reverse('football:replay_data', args=[replay.pk])).status_code, 404)

    def test_does_not_raise_other_apps_request_body_limits(self):
        with override_settings(DATA_UPLOAD_MAX_MEMORY_SIZE=32):
            self.assertEqual(self.upload().status_code, 201)

    def test_failed_database_save_removes_new_file(self):
        from django.db import OperationalError
        with patch('football.views.Replay.save', side_effect=OperationalError('test failure')):
            self.assertEqual(self.upload().status_code, 503)
        self.assertFalse(Replay.objects.exists())
        self.assertFalse(list(Path(self.directory.name).glob('*')))

    def test_deletion_rollback_preserves_file(self):
        from django.db import transaction
        replay = Replay.objects.get(pk=self.upload().json()['id'])
        path = Path(replay.file.path)
        with self.assertRaises(ValueError):
            with transaction.atomic():
                Replay.objects.filter(pk=replay.pk).delete()
                raise ValueError('rollback')
        self.assertTrue(Replay.objects.filter(pk=replay.pk).exists())
        self.assertTrue(path.exists())

    def test_pagination(self):
        with override_settings(FOOTBALL_REPLAY_UPLOADS_PER_WINDOW=30):
            for _ in range(21):
                self.assertEqual(self.upload().status_code, 201)
        page1 = self.client.get('/football/')
        page2 = self.client.get('/football/?page=2')
        self.assertEqual(len(page1.context['page']), 20)
        self.assertEqual(len(page2.context['page']), 1)
