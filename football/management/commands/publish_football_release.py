import hashlib
import json
import os
import re
import tempfile
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from football.releases import VERSION_PATTERN


def atomic_write(path, content):
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.publishing-')
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(content)
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Command(BaseCommand):
    help = 'Publish a verified Windows ZIP; switch the current release atomically, last.'

    def add_arguments(self, parser):
        parser.add_argument('archive', type=Path)
        parser.add_argument('--release-version', required=True)
        parser.add_argument('--sha256', required=True, help='Expected SHA256 from the build machine')
        parser.add_argument('--note', action='append', default=[])

    def handle(self, *args, **options):
        version = options['release_version']
        if not re.fullmatch(VERSION_PATTERN, version):
            raise CommandError('Invalid version')
        archive = options['archive']
        try:
            content = archive.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            if digest != options['sha256'].lower():
                raise CommandError('Archive SHA256 mismatch')
            with zipfile.ZipFile(archive) as package:
                if package.testzip() is not None:
                    raise CommandError('Corrupt ZIP')
                info = json.loads(package.read('build-info.json').decode('utf-8-sig'))
                if info['version'] != version or info['platform'] != 'windows-x86_64':
                    raise CommandError('Package version/platform mismatch')
                if 'football.exe' not in package.namelist():
                    raise CommandError('Package has no football.exe')
        except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
            raise CommandError(f'Invalid release archive: {error}') from error
        root = Path(settings.FOOTBALL_DOWNLOAD_ROOT)
        root.mkdir(parents=True, exist_ok=True)
        filename = f'football-{version}-windows-x86_64.zip'
        destination = root / filename
        if destination.exists() and hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            raise CommandError('This version already exists with different contents; use a new version')
        if not destination.exists():
            atomic_write(destination, content)
        atomic_write(root / (filename + '.sha256'), f'{digest}  {filename}\n'.encode('ascii'))
        metadata = {'version': version, 'filename': filename, 'sha256': digest,
                    'size_bytes': len(content), 'published_at': timezone.now().isoformat(),
                    'notes': options['note'], 'commit': info.get('commit', '')}
        atomic_write(root / 'current.json', json.dumps(metadata, ensure_ascii=False, indent=2).encode('utf-8'))
        self.stdout.write(self.style.SUCCESS(f'Published Football {version}: /downloads/{filename}'))
