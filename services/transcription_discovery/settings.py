from dataclasses import dataclass
from pathlib import Path

from decouple import Csv, config


DEFAULT_EXTENSIONS = '.mp3,.wav,.m4a,.mp4,.webm'


@dataclass(frozen=True)
class DiscoverySettings:
    recordings_dir: Path
    db_path: Path
    django_api_base: str
    api_token: str
    scan_interval_seconds: int
    file_stable_seconds: int
    supported_extensions: tuple[str, ...]


def load_settings():
    extensions = tuple(
        extension.lower().strip()
        for extension in config(
            'TRANSCRIPTION_DISCOVERY_EXTENSIONS',
            default=DEFAULT_EXTENSIONS,
            cast=Csv(),
        )
        if extension.strip()
    )

    return DiscoverySettings(
        recordings_dir=Path(config('TRANSCRIPTION_DISCOVERY_RECORDINGS_DIR')),
        db_path=Path(
            config(
                'TRANSCRIPTION_DISCOVERY_DB',
                default='services/transcription_discovery/var/discovery.sqlite3',
            )
        ),
        django_api_base=config('TRANSCRIPTION_DJANGO_API_BASE', default='http://localhost:8000/api/transcription'),
        api_token=config('TRANSCRIPTION_API_TOKEN'),
        scan_interval_seconds=config('TRANSCRIPTION_DISCOVERY_SCAN_INTERVAL_SECONDS', default=60, cast=int),
        file_stable_seconds=config('TRANSCRIPTION_DISCOVERY_FILE_STABLE_SECONDS', default=300, cast=int),
        supported_extensions=extensions,
    )
