from decimal import Decimal

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.utils import timezone

from .models import PlantSoil, PlantSoilComponent, SoilComponent


class SoilComponentForm(forms.ModelForm):
    class Meta:
        model = SoilComponent
        fields = ('name', 'description', 'is_active')
        labels = {
            'name': 'Название',
            'description': 'Описание',
            'is_active': 'Активен',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Перлит'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Необязательное описание'}),
        }


class PlantSoilForm(forms.ModelForm):
    set_on = forms.DateField(
        label='Дата установки состава',
        initial=timezone.localdate,
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
    )

    class Meta:
        model = PlantSoil
        fields = ('name', 'set_on', 'comment')
        labels = {
            'name': 'Название состава',
            'comment': 'Комментарий',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Например: после пересадки'}),
            'comment': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Что изменилось или почему такой состав'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['set_on'].initial = timezone.localtime(self.instance.set_at).date()

    def save(self, commit=True):
        plant_soil = super().save(commit=False)
        set_on = self.cleaned_data['set_on']
        current_time = timezone.localtime().time()
        plant_soil.set_at = timezone.make_aware(
            timezone.datetime.combine(set_on, current_time),
            timezone.get_current_timezone(),
        )
        if commit:
            plant_soil.save()
            self.save_m2m()
        return plant_soil


class PlantSoilComponentForm(forms.ModelForm):
    class Meta:
        model = PlantSoilComponent
        fields = ('soil_component', 'percentage')
        labels = {
            'soil_component': 'Компонент',
            'percentage': 'Процент',
        }
        widgets = {
            'percentage': forms.NumberInput(attrs={'min': '0.01', 'max': '100', 'step': '0.01'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['soil_component'].queryset = SoilComponent.objects.filter(user=user, is_active=True)

    def validate_unique(self):
        pass


class BasePlantSoilComponentFormSet(BaseInlineFormSet):
    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['user'] = self.user
        return kwargs

    def active_components(self):
        components = []
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get('DELETE'):
                continue

            component = form.cleaned_data.get('soil_component')
            percentage = form.cleaned_data.get('percentage')
            if not component and not percentage:
                continue

            components.append((component, percentage))
        return components

    def clean(self):
        super().clean()

        total = Decimal('0')
        selected_components = set()
        has_component = False

        for component, percentage in self.active_components():
            if not component or percentage is None:
                raise forms.ValidationError('У каждой строки состава должны быть компонент и процент.')
            if component.pk in selected_components:
                raise forms.ValidationError('Один компонент нельзя добавить в состав дважды.')

            selected_components.add(component.pk)
            total += percentage
            has_component = True

        if not has_component:
            raise forms.ValidationError('Добавь хотя бы один компонент почвы.')
        if total != Decimal('100'):
            raise forms.ValidationError('Сумма процентов должна быть ровно 100%.')

    def save(self, commit=True):
        total = sum((percentage for _, percentage in self.active_components()), Decimal('0'))
        if total != Decimal('100'):
            raise forms.ValidationError('Сумма процентов должна быть ровно 100%.')
        return super().save(commit=commit)


def plant_soil_component_formset_factory(extra=0):
    return inlineformset_factory(
        PlantSoil,
        PlantSoilComponent,
        form=PlantSoilComponentForm,
        formset=BasePlantSoilComponentFormSet,
        extra=extra,
        can_delete=True,
    )
