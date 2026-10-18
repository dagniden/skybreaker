"""Release metadata lives beside the archives, outside Git and replay storage."""
import json
import re
from pathlib import Path

from django.conf import settings
from django.utils.dateparse import parse_datetime

VERSION_PATTERN = r'[0-9]+\.[0-9]+\.[0-9]+[A-Za-z0-9._-]*'


def current_release():
    root = Path(settings.FOOTBALL_DOWNLOAD_ROOT)
    try:
        data = json.loads((root / 'current.json').read_text(encoding='utf-8'))
        version = data['version']
        if not re.fullmatch(VERSION_PATTERN, version):
            return None
        filename = f'football-{version}-windows-x86_64.zip'
        if data['filename'] != filename or not re.fullmatch(r'[0-9a-f]{64}', data['sha256']):
            return None
        if type(data['size_bytes']) is not int or data['size_bytes'] <= 0:
            return None
        if not isinstance(data['notes'], list) or not all(isinstance(note, str) for note in data['notes']):
            return None
        published = parse_datetime(data['published_at'])
        if published is None or published.tzinfo is None:
            return None
        if (root / filename).stat().st_size != data['size_bytes'] or not (root / (filename + '.sha256')).is_file():
            return None
        return {**data, 'published_at': published, 'url': '/downloads/' + filename,
                'checksum_url': '/downloads/' + filename + '.sha256'}
    except (OSError, ValueError, KeyError, TypeError):
        return None
