import argparse
import logging
import time

from .cache import DiscoveryCache
from .django_client import DjangoTranscriptionClient
from .scanner import scan_recordings_dir
from .settings import load_settings


logger = logging.getLogger(__name__)


def run_once(settings, cache, client):
    cache.init_schema()
    recordings = scan_recordings_dir(
        settings.recordings_dir,
        settings.supported_extensions,
        settings.file_stable_seconds,
    )

    registered = 0
    failed = 0
    skipped = 0

    for recording in recordings:
        if not cache.should_send(recording.fingerprint):
            skipped += 1
            continue

        cache.mark_pending(recording)

        try:
            response = client.register(recording)
        except Exception as error:  # noqa: BLE001 - service loop must keep running after network errors.
            cache.mark_failed_to_register(recording.fingerprint, error)
            logger.warning('Failed to register %s: %s', recording.file_path, error)
            failed += 1
            continue

        cache.mark_registered(recording.fingerprint, response['id'])
        registered += 1
        logger.info('Registered %s as transcription job %s', recording.file_path, response['id'])

    return {
        'found': len(recordings),
        'registered': registered,
        'failed': failed,
        'skipped': skipped,
    }


def main():
    parser = argparse.ArgumentParser(description='Discover local recording files and register them in Django.')
    parser.add_argument('--once', action='store_true', help='Run one discovery iteration and exit.')
    parser.add_argument('--log-level', default='INFO', help='Python logging level. Default: INFO.')
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
    )
    settings = load_settings()
    cache = DiscoveryCache(settings.db_path)
    client = DjangoTranscriptionClient(settings.django_api_base, settings.api_token)

    logger.info('Starting transcription discovery service for %s', settings.recordings_dir)

    if args.once:
        result = run_once(settings, cache, client)
        logger.info('Discovery iteration finished: %s', result)
        return

    while True:
        result = run_once(settings, cache, client)
        logger.info('Discovery iteration finished: %s', result)
        time.sleep(settings.scan_interval_seconds)


if __name__ == '__main__':
    main()
