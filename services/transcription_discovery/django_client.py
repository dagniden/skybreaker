import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class DjangoClientError(Exception):
    pass


class DjangoTranscriptionClient:
    def __init__(self, api_base, api_token, timeout=30):
        self.api_base = api_base.rstrip('/')
        self.api_token = api_token
        self.timeout = timeout

    def register(self, recording):
        payload = {
            'file_path': recording.file_path,
            'file_name': recording.file_name,
            'file_size': recording.file_size,
            'modified_at': recording.modified_at.isoformat(),
            'fingerprint': recording.fingerprint,
        }

        return self.post_json('/jobs/register/', payload)

    def post_json(self, path, payload):
        request = Request(
            f'{self.api_base}{path}',
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            method='POST',
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except HTTPError as error:
            body = error.read().decode('utf-8', errors='replace')
            raise DjangoClientError(f'Django API returned HTTP {error.code}: {body}') from error
        except URLError as error:
            raise DjangoClientError(f'Django API request failed: {error.reason}') from error
