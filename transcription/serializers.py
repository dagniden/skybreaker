import ntpath

from rest_framework import serializers

from .models import TranscriptionJob


def default_transcript_path(file_path):
    base_path, _extension = ntpath.splitext(file_path)
    return f'{base_path}.txt'


class TranscriptionJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranscriptionJob
        fields = (
            'id',
            'source_type',
            'file_path',
            'file_name',
            'file_size',
            'modified_at',
            'fingerprint',
            'status',
            'locked_by',
            'locked_at',
            'process_instance_key',
            'started_at',
            'finished_at',
            'transcript_path',
            'language',
            'duration_seconds',
            'model',
            'metadata',
            'error_type',
            'error_message',
            'retry_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class RegisterJobSerializer(serializers.Serializer):
    file_path = serializers.CharField(max_length=1024)
    file_name = serializers.CharField(max_length=255)
    file_size = serializers.IntegerField(min_value=0)
    modified_at = serializers.DateTimeField()
    fingerprint = serializers.CharField(max_length=512)
    transcript_path = serializers.CharField(max_length=1024, required=False, allow_blank=True)

    def create(self, validated_data):
        transcript_path = validated_data.pop('transcript_path', '')
        if not transcript_path:
            transcript_path = default_transcript_path(validated_data['file_path'])

        job, created = TranscriptionJob.objects.get_or_create(
            fingerprint=validated_data['fingerprint'],
            defaults={
                **validated_data,
                'transcript_path': transcript_path,
            },
        )
        return job, created


class AcquireNextJobSerializer(serializers.Serializer):
    worker_id = serializers.CharField(max_length=255)
    process_instance_key = serializers.CharField(max_length=64, required=False, allow_blank=True)


class CompleteJobSerializer(serializers.Serializer):
    transcript_path = serializers.CharField(max_length=1024)
    language = serializers.CharField(max_length=32, required=False, allow_blank=True)
    duration_seconds = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    model = serializers.CharField(max_length=255, required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)


class FailJobSerializer(serializers.Serializer):
    error_type = serializers.CharField(max_length=255)
    error_message = serializers.CharField(allow_blank=True)
    retryable = serializers.BooleanField(required=False, default=False)


class RecoverStaleJobsSerializer(serializers.Serializer):
    older_than_minutes = serializers.IntegerField(min_value=1)
