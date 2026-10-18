from django.conf import settings
from django.core.files.storage import FileSystemStorage


def replay_storage():
    # Deliberately outside MEDIA_ROOT: expired/deleted replays must not remain
    # accessible via an unprotected /media/ URL.
    return FileSystemStorage(location=settings.FOOTBALL_REPLAY_ROOT)
