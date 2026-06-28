from datetime import timedelta

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import TranscriptionJob


TOKEN = 'test-token'


@override_settings(TRANSCRIPTION_API_TOKEN=TOKEN)
class TranscriptionJobApiTests(APITestCase):
    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {TOKEN}')

    def register_payload(self, **overrides):
        payload = {
            'file_path': 'D:\\Meetings\\meeting.mp3',
            'file_name': 'meeting.mp3',
            'file_size': 123456789,
            'modified_at': '2026-06-20T12:30:00Z',
            'fingerprint': 'D:\\Meetings\\meeting.mp3:123456789:1781958600',
        }
        payload.update(overrides)
        return payload

    def register_job(self, **overrides):
        response = self.client.post(
            reverse('transcription:job_register'),
            self.register_payload(**overrides),
            format='json',
        )
        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
        return TranscriptionJob.objects.get(pk=response.data['id'])

    def test_requires_bearer_token(self):
        self.client.credentials()

        response = self.client.post(
            reverse('transcription:job_register'),
            self.register_payload(),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(TranscriptionJob.objects.count(), 0)

    def test_register_creates_job_and_is_idempotent(self):
        response = self.client.post(
            reverse('transcription:job_register'),
            self.register_payload(),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['created'])
        self.assertEqual(response.data['status'], TranscriptionJob.STATUS_QUEUED)
        self.assertEqual(TranscriptionJob.objects.count(), 1)

        duplicate_response = self.client.post(
            reverse('transcription:job_register'),
            self.register_payload(),
            format='json',
        )

        self.assertEqual(duplicate_response.status_code, status.HTTP_200_OK)
        self.assertFalse(duplicate_response.data['created'])
        self.assertEqual(duplicate_response.data['id'], response.data['id'])
        self.assertEqual(TranscriptionJob.objects.count(), 1)

    def test_register_derives_default_transcript_path(self):
        job = self.register_job(file_path='D:\\Meetings\\meeting.webm', file_name='meeting.webm')

        self.assertEqual(job.transcript_path, 'D:\\Meetings\\meeting.txt')

    def test_acquire_next_marks_oldest_queued_job_processing(self):
        job = self.register_job()

        response = self.client.post(
            reverse('transcription:job_acquire_next'),
            {
                'worker_id': 'camunda-transcription-supervisor',
                'process_instance_key': '2251799813685249',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['job_found'])
        self.assertEqual(response.data['job']['id'], job.id)

        job.refresh_from_db()
        self.assertEqual(job.status, TranscriptionJob.STATUS_PROCESSING)
        self.assertEqual(job.locked_by, 'camunda-transcription-supervisor')
        self.assertEqual(job.process_instance_key, '2251799813685249')
        self.assertIsNotNone(job.locked_at)
        self.assertIsNotNone(job.started_at)

    def test_acquire_next_returns_empty_response_when_queue_is_empty(self):
        response = self.client.post(
            reverse('transcription:job_acquire_next'),
            {'worker_id': 'camunda-transcription-supervisor'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['job_found'])

    def test_complete_marks_processing_job_completed(self):
        job = self.register_job()
        self.client.post(
            reverse('transcription:job_acquire_next'),
            {'worker_id': 'camunda-transcription-supervisor'},
            format='json',
        )

        response = self.client.post(
            reverse('transcription:job_complete', kwargs={'pk': job.pk}),
            {
                'transcript_path': 'D:\\Meetings\\meeting.txt',
                'language': 'ru',
                'duration_seconds': 3600,
                'model': 'whisper-large-v3',
                'metadata': {'segments_count': 123},
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        job.refresh_from_db()
        self.assertEqual(job.status, TranscriptionJob.STATUS_COMPLETED)
        self.assertEqual(job.language, 'ru')
        self.assertEqual(job.duration_seconds, 3600)
        self.assertEqual(job.model, 'whisper-large-v3')
        self.assertEqual(job.metadata, {'segments_count': 123})
        self.assertEqual(job.locked_by, '')
        self.assertIsNone(job.locked_at)
        self.assertIsNotNone(job.finished_at)

    def test_fail_marks_job_failed_with_error_details(self):
        job = self.register_job()
        self.client.post(
            reverse('transcription:job_acquire_next'),
            {'worker_id': 'camunda-transcription-supervisor'},
            format='json',
        )

        response = self.client.post(
            reverse('transcription:job_fail', kwargs={'pk': job.pk}),
            {
                'error_type': 'speaches_error',
                'error_message': 'Speaches returned HTTP 500',
                'retryable': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        job.refresh_from_db()
        self.assertEqual(job.status, TranscriptionJob.STATUS_FAILED)
        self.assertEqual(job.error_type, 'speaches_error')
        self.assertEqual(job.error_message, 'Speaches returned HTTP 500')
        self.assertEqual(job.retry_count, 1)
        self.assertEqual(job.locked_by, '')
        self.assertIsNone(job.locked_at)

    def test_recover_stale_returns_old_processing_jobs_to_queue(self):
        stale_job = self.register_job()
        fresh_job = self.register_job(
            file_path='D:\\Meetings\\fresh.mp3',
            file_name='fresh.mp3',
            fingerprint='D:\\Meetings\\fresh.mp3:123456789:1781958600',
        )

        stale_job.status = TranscriptionJob.STATUS_PROCESSING
        stale_job.locked_at = timezone.now() - timedelta(hours=4)
        stale_job.locked_by = 'old-worker'
        stale_job.process_instance_key = 'old-process'
        stale_job.save()

        fresh_job.status = TranscriptionJob.STATUS_PROCESSING
        fresh_job.locked_at = timezone.now()
        fresh_job.locked_by = 'fresh-worker'
        fresh_job.save()

        response = self.client.post(
            reverse('transcription:job_recover_stale'),
            {'older_than_minutes': 180},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['recovered'], 1)

        stale_job.refresh_from_db()
        fresh_job.refresh_from_db()
        self.assertEqual(stale_job.status, TranscriptionJob.STATUS_QUEUED)
        self.assertEqual(stale_job.locked_by, '')
        self.assertIsNone(stale_job.locked_at)
        self.assertEqual(stale_job.process_instance_key, '')
        self.assertEqual(fresh_job.status, TranscriptionJob.STATUS_PROCESSING)
