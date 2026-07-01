from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TranscriptionJob
from .serializers import (
    AcquireNextJobSerializer,
    CompleteJobSerializer,
    FailJobSerializer,
    RecoverStaleJobsSerializer,
    RegisterJobSerializer,
)


class TranscriptionTokenMixin:
    authentication_classes = []
    permission_classes = []

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        expected_token = settings.TRANSCRIPTION_API_TOKEN
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.removeprefix('Bearer ').strip()

        if not expected_token or token != expected_token:
            self.permission_denied(request, message='Invalid transcription API token')


def job_payload(job):
    return {
        'id': job.id,
        'file_path': job.file_path,
        'file_name': job.file_name,
        'file_size': job.file_size,
        'transcript_path': job.transcript_path,
    }


class RegisterJobView(TranscriptionTokenMixin, APIView):
    def post(self, request):
        serializer = RegisterJobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job, created = serializer.save()
        return Response(
            {
                'id': job.id,
                'status': job.status,
                'created': created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class AcquireNextJobView(TranscriptionTokenMixin, APIView):
    def post(self, request):
        serializer = AcquireNextJobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        now = timezone.now()
        with transaction.atomic():
            job = (
                TranscriptionJob.objects.select_for_update(skip_locked=True)
                .filter(status=TranscriptionJob.STATUS_QUEUED)
                .order_by('created_at', 'id')
                .first()
            )

            if job is None:
                return Response({'job_found': False})

            job.status = TranscriptionJob.STATUS_PROCESSING
            job.locked_by = serializer.validated_data['worker_id']
            job.locked_at = now
            job.started_at = job.started_at or now
            job.process_instance_key = serializer.validated_data.get('process_instance_key', '')
            job.error_type = ''
            job.error_message = ''
            job.save(
                update_fields=[
                    'status',
                    'locked_by',
                    'locked_at',
                    'started_at',
                    'process_instance_key',
                    'error_type',
                    'error_message',
                    'updated_at',
                ]
            )

        return Response({'job_found': True, 'job': job_payload(job)})


class CompleteJobView(TranscriptionTokenMixin, APIView):
    def post(self, request, pk):
        serializer = CompleteJobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job = get_object_or_404(TranscriptionJob, pk=pk)
        job.status = TranscriptionJob.STATUS_COMPLETED
        job.finished_at = timezone.now()
        job.locked_by = ''
        job.locked_at = None
        job.transcript_path = serializer.validated_data['transcript_path']
        job.language = serializer.validated_data.get('language', '')
        job.duration_seconds = serializer.validated_data.get('duration_seconds')
        job.model = serializer.validated_data.get('model', '')
        job.metadata = serializer.validated_data.get('metadata', {})
        job.error_type = ''
        job.error_message = ''
        job.save()

        return Response({'id': job.id, 'status': job.status})


class FailJobView(TranscriptionTokenMixin, APIView):
    def post(self, request, pk):
        serializer = FailJobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job = get_object_or_404(TranscriptionJob, pk=pk)
        job.status = TranscriptionJob.STATUS_FAILED
        job.finished_at = timezone.now()
        job.locked_by = ''
        job.locked_at = None
        job.error_type = serializer.validated_data['error_type']
        job.error_message = serializer.validated_data['error_message']
        job.retry_count += 1
        job.save()

        return Response({'id': job.id, 'status': job.status, 'retry_count': job.retry_count})


class RecoverStaleJobsView(TranscriptionTokenMixin, APIView):
    def post(self, request):
        serializer = RecoverStaleJobsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cutoff = timezone.now() - timedelta(minutes=serializer.validated_data['older_than_minutes'])
        recovered = TranscriptionJob.objects.filter(
            status=TranscriptionJob.STATUS_PROCESSING,
            locked_at__lt=cutoff,
        ).update(
            status=TranscriptionJob.STATUS_QUEUED,
            locked_by='',
            locked_at=None,
            process_instance_key='',
        )

        return Response({'recovered': recovered})
