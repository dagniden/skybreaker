from django.contrib import admin

from .models import TranscriptionJob


@admin.register(TranscriptionJob)
class TranscriptionJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'file_name', 'status', 'file_size', 'locked_at', 'finished_at', 'created_at')
    list_filter = ('status', 'source_type', 'created_at', 'finished_at')
    search_fields = ('file_name', 'file_path', 'fingerprint', 'process_instance_key')
    readonly_fields = ('created_at', 'updated_at')
