from datetime import datetime

from django import forms
from django.utils import timezone

from .models import Plant


class PlantForm(forms.ModelForm):
    last_watered_on = forms.DateField(
        label='Дата последнего полива',
        initial=timezone.localdate,
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
    )

    class Meta:
        model = Plant
        fields = ('name', 'watering_interval_days', 'last_watered_on', 'notes')
        labels = {
            'name': 'Название',
            'watering_interval_days': 'Интервал полива, дней',
            'notes': 'Заметки по уходу',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Монстера'}),
            'watering_interval_days': forms.NumberInput(attrs={'min': 1}),
            'notes': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Например: любит рассеянный свет, не заливать...',
            }),
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
