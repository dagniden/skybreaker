import asyncio
import os
from pathlib import Path

import httpx
from pyzeebe import ZeebeWorker, create_insecure_channel


ZEEBE_ADDRESS = os.getenv('ZEEBE_ADDRESS', 'localhost:26500')
SPEACHES_BASE_URL = os.getenv('TRANSCRIPTION_SPEACHES_BASE_URL', 'http://localhost:8008').rstrip('/')
SPEACHES_MODEL = os.getenv('TRANSCRIPTION_SPEACHES_MODEL', 'whisper-large-v3')
SPEACHES_LANGUAGE = os.getenv('TRANSCRIPTION_SPEACHES_LANGUAGE', '')
SPEACHES_STUB = os.getenv('TRANSCRIPTION_SPEACHES_STUB', 'false').lower() in {'1', 'true', 'yes', 'on'}
SPEACHES_TIMEOUT_SECONDS = float(os.getenv('TRANSCRIPTION_SPEACHES_TIMEOUT_SECONDS', '3600'))


def write_text_atomic(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f'{path.name}.tmp')
    temp_path.write_text(text, encoding='utf-8')
    temp_path.replace(path)


def transcribe_with_speaches(file_path):
    file_path = Path(file_path)
    endpoint = f'{SPEACHES_BASE_URL}/v1/audio/transcriptions'
    data = {
        'model': SPEACHES_MODEL,
        'response_format': 'json',
    }

    if SPEACHES_LANGUAGE:
        data['language'] = SPEACHES_LANGUAGE

    with file_path.open('rb') as audio_file:
        files = {'file': (file_path.name, audio_file, 'application/octet-stream')}
        response = httpx.post(endpoint, data=data, files=files, timeout=SPEACHES_TIMEOUT_SECONDS)
        response.raise_for_status()

    payload = response.json()
    transcript_text = payload.get('text')

    if not transcript_text:
        raise RuntimeError('Speaches response does not contain text')

    return {
        'text': transcript_text,
        'language': payload.get('language', SPEACHES_LANGUAGE),
        'duration_seconds': payload.get('duration'),
        'metadata': {
            'speaches_response': payload,
        },
    }


def transcribe_stub(file_path):
    return {
        'text': f'Stub transcript for {file_path}\n',
        'language': SPEACHES_LANGUAGE,
        'duration_seconds': None,
        'metadata': {
            'stub': True,
        },
    }


def transcribe_recording(job_id, file_path, file_name, transcript_path):
    source_path = Path(file_path)

    if not source_path.exists():
        raise FileNotFoundError(f'Recording file does not exist: {source_path}')
    if not source_path.is_file():
        raise FileNotFoundError(f'Recording path is not a file: {source_path}')

    result = transcribe_stub(source_path) if SPEACHES_STUB else transcribe_with_speaches(source_path)
    write_text_atomic(transcript_path, result['text'])

    return {
        'job_id': job_id,
        'file_path': str(source_path),
        'file_name': file_name,
        'transcript_path': transcript_path,
        'language': result.get('language') or '',
        'duration_seconds': result.get('duration_seconds'),
        'model': SPEACHES_MODEL,
        'metadata': result.get('metadata') or {},
    }


async def main():
    channel = create_insecure_channel(ZEEBE_ADDRESS)
    worker = ZeebeWorker(channel)

    worker.task(
        task_type='transcribe-recording',
        variables_to_fetch=['job_id', 'file_path', 'file_name', 'transcript_path'],
    )(transcribe_recording)

    print(f'Listening for transcribe-recording jobs on {ZEEBE_ADDRESS}')
    await worker.work()


if __name__ == '__main__':
    asyncio.run(main())
