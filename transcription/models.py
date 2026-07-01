from django.db import models


class TranscriptionJob(models.Model):
    SOURCE_ARES_LOCAL = 'ares_local'

    STATUS_QUEUED = 'queued'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'

    SOURCE_CHOICES = [
        (SOURCE_ARES_LOCAL, 'Локальный файл на ares'),
    ]

    STATUS_CHOICES = [
        (STATUS_QUEUED, 'В очереди'),
        (STATUS_PROCESSING, 'В обработке'),
        (STATUS_COMPLETED, 'Завершено'),
        (STATUS_FAILED, 'Ошибка'),
    ]

    source_type = models.CharField(max_length=32, choices=SOURCE_CHOICES, default=SOURCE_ARES_LOCAL)
    file_path = models.CharField(max_length=1024)
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveBigIntegerField()
    modified_at = models.DateTimeField()
    fingerprint = models.CharField(max_length=512, unique=True)

    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True)
    locked_by = models.CharField(max_length=255, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    process_instance_key = models.CharField(max_length=64, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    transcript_path = models.CharField(max_length=1024, blank=True)
    language = models.CharField(max_length=32, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    model = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    error_type = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at', 'id']
        indexes = [
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f'{self.file_name} ({self.status})'
