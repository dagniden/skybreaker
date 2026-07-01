import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase


def load_worker_module():
    module_path = Path(__file__).resolve().parent.parent / 'camunda-workers' / 'transcribe-recording.py'
    spec = importlib.util.spec_from_file_location('transcribe_recording_worker', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TranscribeRecordingWorkerTests(TestCase):
    def setUp(self):
        self.worker = load_worker_module()
        self.worker.SPEACHES_STUB = True
        self.worker.SPEACHES_LANGUAGE = 'ru'
        self.worker.SPEACHES_MODEL = 'test-whisper'

    def test_transcribe_recording_stub_writes_transcript(self):
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            source_path = root / 'meeting.mp3'
            transcript_path = root / 'meeting.txt'
            source_path.write_bytes(b'audio')

            result = self.worker.transcribe_recording(
                job_id=42,
                file_path=str(source_path),
                file_name='meeting.mp3',
                transcript_path=str(transcript_path),
            )

            self.assertTrue(transcript_path.exists())
            self.assertEqual(transcript_path.read_text(encoding='utf-8'), f'Stub transcript for {source_path}\n')
            self.assertFalse(transcript_path.with_name('meeting.txt.tmp').exists())
            self.assertEqual(result['job_id'], 42)
            self.assertEqual(result['transcript_path'], str(transcript_path))
            self.assertEqual(result['language'], 'ru')
            self.assertEqual(result['model'], 'test-whisper')
            self.assertEqual(result['metadata'], {'stub': True})

    def test_transcribe_recording_fails_when_source_file_is_missing(self):
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            missing_path = root / 'missing.mp3'
            transcript_path = root / 'missing.txt'

            with self.assertRaises(FileNotFoundError):
                self.worker.transcribe_recording(
                    job_id=42,
                    file_path=str(missing_path),
                    file_name='missing.mp3',
                    transcript_path=str(transcript_path),
                )

            self.assertFalse(transcript_path.exists())
