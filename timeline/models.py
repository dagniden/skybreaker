from django.db import models
from django.urls import reverse


class TimelinePage(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    intro_text = models.TextField(blank=True)
    slug = models.SlugField(max_length=120, unique=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('timeline:page_detail', kwargs={'slug': self.slug})


class TimelineYear(models.Model):
    page = models.ForeignKey(
        TimelinePage,
        on_delete=models.CASCADE,
        related_name='years',
    )
    year = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'year']
        constraints = [
            models.UniqueConstraint(fields=['page', 'year'], name='unique_timeline_year_per_page'),
        ]

    def __str__(self):
        return f'{self.page}: {self.year}'


class TimelineEvent(models.Model):
    year = models.ForeignKey(
        TimelineYear,
        on_delete=models.CASCADE,
        related_name='events',
    )
    event_date = models.DateField(blank=True, null=True)
    date_label = models.CharField(
        max_length=50,
        blank=True,
        help_text='Например: FEB 28. Если оставить пустым, подпись будет собрана из даты.',
    )
    kicker = models.CharField(max_length=100, blank=True, help_text='Короткая строка над заголовком.')
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='timeline/events/%Y/%m/', blank=True)
    image_alt = models.CharField(max_length=250, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'event_date', 'id']
        indexes = [
            models.Index(fields=['year', 'event_date']),
            models.Index(fields=['year', 'sort_order']),
        ]

    def __str__(self):
        return f'{self.year.year}: {self.title}'

    @property
    def display_date(self):
        if self.date_label:
            return self.date_label
        if self.event_date:
            return self.event_date.strftime('%b %d').upper()
        return ''
