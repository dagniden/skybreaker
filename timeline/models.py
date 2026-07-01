from django.conf import settings
from django.db import models
from django.urls import reverse


class Timeline(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='timelines',
        verbose_name='Владелец',
        help_text='Пользователь, который отвечает за этот таймлайн.',
    )
    name = models.CharField(
        'Техническое имя',
        max_length=120,
        unique=True,
        help_text='Используется в адресе страницы, например demo или vpro. Лучше использовать латиницу, цифры и дефисы.',
    )
    description = models.TextField(
        'Описание',
        blank=True,
        help_text='Внутреннее описание таймлайна для администраторов.',
    )
    is_published = models.BooleanField(
        'Опубликован',
        default=False,
        help_text='Если выключено, публичная страница таймлайна будет недоступна.',
    )
    owner_only = models.BooleanField(
        'Просмотр только для владельца',
        default=False,
        help_text='Если включено, публичную страницу сможет открыть только авторизованный владелец таймлайна или администратор.',
    )
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Таймлайн'
        verbose_name_plural = 'Таймлайны'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('timeline:timeline_detail', kwargs={'name': self.name})


class TimelineEvent(models.Model):
    timeline = models.ForeignKey(
        Timeline,
        on_delete=models.CASCADE,
        related_name='events',
        verbose_name='Таймлайн',
        help_text='Таймлайн, к которому относится событие.',
    )
    event_date = models.DateField(
        'Дата события',
        help_text='Используется для сортировки, группировки по годам и автоматических подписей на публичной странице.',
    )
    title = models.CharField(
        'Заголовок',
        max_length=250,
        help_text='Основной заголовок события на публичной странице.',
    )
    description = models.TextField(
        'Описание',
        blank=True,
        help_text='Текст события, который будет показан под заголовком.',
    )
    image = models.ImageField(
        'Изображение',
        upload_to='timeline/events/%Y/%m/',
        blank=True,
        help_text='Фоновое изображение события. Рекомендуется горизонтальное изображение хорошего качества.',
    )
    is_published = models.BooleanField(
        'Опубликовано',
        default=True,
        help_text='Если выключено, событие не будет отображаться на публичной странице.',
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        db_table = 'timeline_event'
        ordering = ['event_date', 'id']
        indexes = [
            models.Index(fields=['timeline', 'event_date']),
            models.Index(fields=['timeline', 'is_published']),
        ]
        verbose_name = 'Событие таймлайна'
        verbose_name_plural = 'События таймлайна'

    def __str__(self):
        return f'{self.event_date:%Y-%m-%d}: {self.title}'

    @property
    def display_date(self):
        return self.event_date.strftime('%b %d').upper()

    @property
    def display_kicker(self):
        return f"TIMELINE: {self.event_date.strftime('%b %Y').upper()}"
