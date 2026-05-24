# Deploy

Production target:

- Debian VDI
- Caddy for HTTPS and reverse proxy
- Gunicorn for Django
- Poetry for dependency management
- SQLite for the first deployment stage
- GitHub Actions deploys `main` over SSH

Runtime paths:

```text
/opt/skybreaker
/opt/skybreaker/.env
/opt/skybreaker/staticfiles
/opt/skybreaker/media
```

Required GitHub secrets:

```text
VDI_HOST
VDI_USER
VDI_PORT
VDI_SSH_KEY
```

Production environment file on VDI:

```env
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=sky-breaker.ru,www.sky-breaker.ru
DJANGO_CSRF_TRUSTED_ORIGINS=https://sky-breaker.ru,https://www.sky-breaker.ru
```

Caddyfile snippet:

```caddyfile
www.sky-breaker.ru {
    redir https://sky-breaker.ru{uri}
}

sky-breaker.ru {
    encode gzip zstd

    handle_path /static/* {
        root * /opt/skybreaker/staticfiles
        file_server
    }

    handle_path /media/* {
        root * /opt/skybreaker/media
        file_server
    }

    reverse_proxy 127.0.0.1:8001
}
```

Systemd service template:

```ini
[Unit]
Description=Skybreaker Django app
After=network.target

[Service]
User=deploy
Group=deploy
WorkingDirectory=/opt/skybreaker
EnvironmentFile=/opt/skybreaker/.env
ExecStart=/home/deploy/.local/bin/poetry run gunicorn config.wsgi:application --bind 127.0.0.1:8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
