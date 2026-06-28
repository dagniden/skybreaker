from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class RecordingFile:
    file_path: str
    file_name: str
    file_size: int
    modified_at: datetime
    fingerprint: str


def build_fingerprint(path, stat_result):
    return f'{path}:{stat_result.st_size}:{int(stat_result.st_mtime)}'


def scan_recordings_dir(recordings_dir, supported_extensions, file_stable_seconds, now=None):
    now = now or datetime.now(timezone.utc)
    recordings_dir = Path(recordings_dir)

    if not recordings_dir.exists():
        return []

    files = []
    supported_extensions = {extension.lower() for extension in supported_extensions}

    for path in recordings_dir.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() not in supported_extensions:
            continue
        if path.name.endswith(('.tmp', '.part', '.crdownload')):
            continue

        stat_result = path.stat()
        modified_at = datetime.fromtimestamp(stat_result.st_mtime, tz=timezone.utc)
        if (now - modified_at).total_seconds() < file_stable_seconds:
            continue

        files.append(
            RecordingFile(
                file_path=str(path),
                file_name=path.name,
                file_size=stat_result.st_size,
                modified_at=modified_at,
                fingerprint=build_fingerprint(path, stat_result),
            )
        )

    return sorted(files, key=lambda item: (item.modified_at, item.file_name))
