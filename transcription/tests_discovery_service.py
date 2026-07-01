from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from services.transcription_discovery.cache import (
    STATUS_FAILED_TO_REGISTER,
    STATUS_REGISTERED,
    DiscoveryCache,
)
from services.transcription_discovery.scanner import scan_recordings_dir
from services.transcription_discovery.service import run_once


@dataclass(frozen=True)
class TestSettings:
    recordings_dir: Path
    supported_extensions: tuple[str, ...]
    file_stable_seconds: int


class FakeClient:
    def __init__(self, fail=False):
        self.fail = fail
        self.recordings = []

    def register(self, recording):
        self.recordings.append(recording)
        if self.fail:
            raise RuntimeError('Django is unavailable')
        return {'id': len(self.recordings), 'status': 'queued', 'created': True}


class DiscoveryScannerTests(TestCase):
    def test_scan_recordings_dir_returns_only_stable_supported_files(self):
        with TemporaryDirectory() as tmp_dir:
            recordings_dir = Path(tmp_dir)
            old_file = recordings_dir / 'meeting.mp3'
            fresh_file = recordings_dir / 'fresh.mp3'
            unsupported_file = recordings_dir / 'notes.txt'

            old_file.write_bytes(b'audio')
            fresh_file.write_bytes(b'audio')
            unsupported_file.write_text('not audio')

            now_timestamp = datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc).timestamp()
            old_timestamp = now_timestamp - 600
            fresh_timestamp = now_timestamp - 10

            set_mtime(old_file, old_timestamp)
            set_mtime(fresh_file, fresh_timestamp)
            set_mtime(unsupported_file, old_timestamp)

            recordings = scan_recordings_dir(
                recordings_dir,
                supported_extensions=('.mp3', '.wav'),
                file_stable_seconds=300,
                now=datetime.fromtimestamp(now_timestamp, tz=timezone.utc),
            )

        self.assertEqual(len(recordings), 1)
        self.assertEqual(recordings[0].file_name, 'meeting.mp3')


class DiscoveryServiceTests(TestCase):
    def test_run_once_registers_new_file_and_skips_it_next_time(self):
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            recordings_dir = root / 'recordings'
            recordings_dir.mkdir()
            recording_path = recordings_dir / 'meeting.mp3'
            recording_path.write_bytes(b'audio')
            set_mtime(recording_path, datetime.now(timezone.utc).timestamp() - 600)

            settings = TestSettings(
                recordings_dir=recordings_dir,
                supported_extensions=('.mp3',),
                file_stable_seconds=300,
            )
            cache = DiscoveryCache(root / 'discovery.sqlite3')
            client = FakeClient()

            first_result = run_once(settings, cache, client)
            second_result = run_once(settings, cache, client)

            self.assertEqual(first_result['registered'], 1)
            self.assertEqual(first_result['failed'], 0)
            self.assertEqual(second_result['registered'], 0)
            self.assertEqual(second_result['skipped'], 1)
            self.assertEqual(len(client.recordings), 1)
            self.assertEqual(cache.get_status(client.recordings[0].fingerprint), STATUS_REGISTERED)

    def test_run_once_marks_failed_registration_for_retry(self):
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            recordings_dir = root / 'recordings'
            recordings_dir.mkdir()
            recording_path = recordings_dir / 'meeting.mp3'
            recording_path.write_bytes(b'audio')
            set_mtime(recording_path, datetime.now(timezone.utc).timestamp() - 600)

            settings = TestSettings(
                recordings_dir=recordings_dir,
                supported_extensions=('.mp3',),
                file_stable_seconds=300,
            )
            cache = DiscoveryCache(root / 'discovery.sqlite3')
            failing_client = FakeClient(fail=True)
            working_client = FakeClient()

            with self.assertLogs('services.transcription_discovery.service', level='WARNING'):
                failed_result = run_once(settings, cache, failing_client)
            self.assertEqual(failed_result['failed'], 1)
            self.assertEqual(cache.get_status(failing_client.recordings[0].fingerprint), STATUS_FAILED_TO_REGISTER)

            retry_result = run_once(settings, cache, working_client)
            self.assertEqual(retry_result['registered'], 1)
            self.assertEqual(cache.get_status(working_client.recordings[0].fingerprint), STATUS_REGISTERED)


def set_mtime(path, timestamp):
    path.touch()
    import os

    os.utime(path, (timestamp, timestamp))
