import hmac
import json
from datetime import timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.db import DatabaseError, OperationalError, transaction
from django.db.models import Count, Sum
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Replay, UploadBudget
from .releases import current_release
from .validation import MAX_BYTES, validate_replay


def secure_response(response):
    response['Referrer-Policy'] = 'no-referrer'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    return response


class UploadReplayView(APIView):
    # Only a separate game upload token is accepted, never browser cookies.
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = []

    def post(self, request):
        token = settings.FOOTBALL_REPLAY_UPLOAD_TOKEN
        if not token:
            return Response({'error': 'Replay uploads are not configured'}, status=503)
        expected = ('Bearer ' + token).encode()
        if not hmac.compare_digest(request.headers.get('Authorization', '').encode(), expected):
            return Response({'error': 'Invalid upload token'}, status=401)
        if request.content_type != 'application/json' or request.headers.get('Content-Encoding', 'identity') != 'identity':
            return Response({'error': 'Expected uncompressed application/json'}, status=415)
        try:
            if int(request.META.get('CONTENT_LENGTH') or 0) > MAX_BYTES:
                return Response({'error': 'Replay too large'}, status=413)
        except ValueError:
            return Response({'error': 'Invalid content length'}, status=400)
        try:
            # Reserve attempts in a separate transaction so invalid recordings
            # also count. Row locking works across PostgreSQL/Gunicorn workers.
            with transaction.atomic():
                budget = UploadBudget.objects.select_for_update().get(pk=1)
                now = timezone.now()
                if (now - budget.window_started).total_seconds() >= 600:
                    budget.window_started, budget.attempts = now, 0
                if budget.attempts >= settings.FOOTBALL_REPLAY_UPLOADS_PER_WINDOW:
                    return Response({'error': 'Upload rate limit exceeded'}, status=429, headers={'Retry-After': '600'})
                budget.attempts += 1
                budget.save(update_fields=['window_started', 'attempts'])
            # Stream reads bypass Django's smaller request.body limit without
            # changing upload limits for unrelated applications.
            body = request.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                return Response({'error': 'Replay too large'}, status=413)
            data = validate_replay(json.loads(body))
            encoded = json.dumps(data, separators=(',', ':'), allow_nan=False).encode()
        except (ValueError, UnicodeError, RecursionError):
            return Response({'error': 'Invalid replay'}, status=400)
        except OperationalError:
            return Response({'error': 'Upload busy, retry later'}, status=503, headers={'Retry-After': '5'})
        replay = None
        try:
            with transaction.atomic():
                # Serialize quota check + file/row creation, not just each query.
                UploadBudget.objects.select_for_update().get(pk=1)
                usage = Replay.objects.aggregate(size=Sum('size_bytes'), count=Count('pk'))
                if usage['count'] >= settings.FOOTBALL_REPLAY_MAX_COUNT or (usage['size'] or 0) + len(encoded) > settings.FOOTBALL_REPLAY_MAX_STORAGE_BYTES:
                    return Response({'error': 'Replay storage is full'}, status=507)
                replay = Replay(duration_ms=data['duration_ms'], size_bytes=len(encoded),
                                player_goals=data['frames'][-1]['s'][0], bot_goals=data['frames'][-1]['s'][1],
                                expires_at=timezone.now() + timedelta(days=settings.FOOTBALL_REPLAY_RETENTION_DAYS))
                replay.file.save(replay.pk + '.json', ContentFile(encoded), save=False)
                replay.save(force_insert=True)
        except (OSError, DatabaseError):
            if replay and replay.file.name:
                replay.file.delete(save=False)
            return Response({'error': 'Replay storage unavailable'}, status=503)
        return Response({'id': replay.pk,
                         'viewer_url': request.build_absolute_uri(replay.get_absolute_url()),
                         'data_url': request.build_absolute_uri(reverse('football:replay_data', args=[replay.pk]))}, status=201)


def public_replay(replay_id):
    return get_object_or_404(Replay, pk=replay_id, expires_at__gt=timezone.now())


@require_GET
def replay_data(request, replay_id):
    replay = public_replay(replay_id)
    try:
        file = replay.file.open('rb')
    except FileNotFoundError:
        raise Http404('Replay file not found')
    response = FileResponse(file, content_type='application/json')
    response['Cache-Control'] = 'no-store'
    return secure_response(response)


@require_GET
def viewer(request, replay_id):
    replay = public_replay(replay_id)
    response = render(request, 'football/replay.html', {'replay': replay})
    response['Cache-Control'] = 'no-store'
    return secure_response(response)


@require_GET
def catalog(request):
    available = Replay.objects.filter(expires_at__gt=timezone.now()).defer('file')
    page = Paginator(available, 20).get_page(request.GET.get('page'))
    response = render(request, 'football/catalog.html', {'page': page, 'release': current_release()})
    response['Cache-Control'] = 'no-store'
    return secure_response(response)


@require_GET
def download(request):
    release = current_release()
    if release is None:
        raise Http404('No client release is available yet')
    response = HttpResponseRedirect(release['url'])
    response['Cache-Control'] = 'no-store'
    return secure_response(response)
