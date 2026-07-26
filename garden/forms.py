from datetime import datetime

from django import forms
from django.utils import timezone

from .models import Plant, PlantEvent


class PlantForm(forms.ModelForm):
    last_watered_on = forms.DateField(
        label='Дата последнего полива',
        initial=timezone.localdate,
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
    )

    class Meta:
        model = Plant
        fields = ('name', 'watering_interval_days', 'last_watered_on')
        labels = {
            'name': 'Название',
            'watering_interval_days': 'Интервал полива, дней',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Монстера'}),
            'watering_interval_days': forms.NumberInput(attrs={'min': 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['last_watered_on'].initial = timezone.localtime(
                self.instance.last_watered_at,
            ).date()

    def save(self, commit=True):
        plant = super().save(commit=False)
        last_watered_on = self.cleaned_data['last_watered_on']
        current_time = timezone.localtime().time()
        last_watered_at = datetime.combine(last_watered_on, current_time)
        plant.last_watered_at = timezone.make_aware(last_watered_at, timezone.get_current_timezone())

        if commit:
            plant.save()
            self.save_m2m()

        return plant


class PlantNoteForm(forms.Form):
    comment = forms.CharField(
        label='Заметка',
        widget=forms.TextInput(attrs={'placeholder': 'Например: любит влажный воздух'}),
    )


class PlantWateringForm(forms.Form):
    volume = forms.CharField(
        label='Объем полива',
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Объем, мл', 'inputmode': 'decimal'}),
    )


class PlantFertilizingForm(forms.Form):
    fertilizer = forms.CharField(
        label='Чем удобрял',
        widget=forms.TextInput(attrs={'placeholder': 'Например: Аминоцимус полив'}),
    )


class PlantEventForm(forms.ModelForm):
    occurred_on = forms.DateField(
        label='Дата события',
        initial=timezone.localdate,
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
    )

    class Meta:
        model = PlantEvent
        fields = ('event_type', 'occurred_on', 'title', 'comment')
        labels = {
            'event_type': 'Тип события',
            'title': 'Название',
            'comment': 'Комментарий',
        }
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Короткое описание'}),
            'comment': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Подробности события'}),
        }

    def save(self, commit=True):
        event = super().save(commit=False)
        occurred_on = self.cleaned_data['occurred_on']
        current_time = timezone.localtime().time()
        occurred_at = datetime.combine(occurred_on, current_time)
        event.occurred_at = timezone.make_aware(occurred_at, timezone.get_current_timezone())

        if commit:
            event.save()
            self.save_m2m()

        return event
