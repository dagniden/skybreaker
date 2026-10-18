from django.contrib import admin
from django.utils.html import format_html

from .models import Replay


@admin.register(Replay)
class ReplayAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'duration_ms', 'player_goals', 'bot_goals', 'size_bytes', 'expires_at')
    search_fields = ('id',)
    list_filter = ('format_version',)
    readonly_fields = ('id', 'viewer_link', 'created_at', 'expires_at', 'duration_ms', 'format_version',
                       'player_goals', 'bot_goals', 'size_bytes', 'owner')
    exclude = ('file',)

    @admin.display(description='Просмотр')
    def viewer_link(self, replay):
        return format_html('<a href="{}">Открыть реплей</a>', replay.get_absolute_url())

    def has_add_permission(self, request):
        return False
