from django.apps import AppConfig


class FootballConfig(AppConfig):
    name = 'football'
    verbose_name = 'Футбольные реплеи'

    def ready(self):
        from . import signals  # noqa: F401
