from django import forms

from .models import Plant


class PlantForm(forms.ModelForm):
    class Meta:
        model = Plant
        fields = ('name', 'watering_interval_days')
        labels = {
            'name': 'Название',
            'watering_interval_days': 'Интервал полива, дней',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Монстера'}),
            'watering_interval_days': forms.NumberInput(attrs={'min': 1}),
        }
