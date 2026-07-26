import re

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import PlantEventForm, PlantFertilizingForm, PlantForm, PlantNoteForm, PlantWateringForm
from .models import Plant, PlantEvent


VOLUME_PATTERN = re.compile(r'\d+(?:[,.]\d+)?(?:\s*-\s*\d+(?:[,.]\d+)?)?')


def format_watering_comment(volume, interval_days):
    period = f'на {interval_days} дн.'
    volume = volume.strip()
    if not volume:
        return period
    if VOLUME_PATTERN.fullmatch(volume):
        volume = f'{volume} мл'
    return f'{volume} {period}'


class UserPlantQuerySetMixin(LoginRequiredMixin):
    model = Plant

    def get_queryset(self):
        return Plant.objects.filter(user=self.request.user)


class PlantListView(UserPlantQuerySetMixin, ListView):
    template_name = 'garden/plant_list.html'
    context_object_name = 'plants'

    def get_queryset(self):
        plants = super().get_queryset()
        return sorted(plants, key=lambda plant: (plant.moisture_percent, plant.name.lower()))


class PlantDetailView(UserPlantQuerySetMixin, DetailView):
    template_name = 'garden/plant_detail.html'
    context_object_name = 'plant'

    def get_queryset(self):
        return super().get_queryset().prefetch_related(
            'events',
            'soils__parts__soil_component',
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_soil'] = next(
            (plant_soil for plant_soil in self.object.soils.all() if plant_soil.is_current),
            None,
        )
        context['watering_form'] = PlantWateringForm()
        context['note_form'] = PlantNoteForm()
        context['fertilizing_form'] = PlantFertilizingForm()
        context['recent_events'] = list(
            self.object.events.exclude(event_type=PlantEvent.EventType.NOTE)[:5],
        )
        context['note_events'] = list(self.object.events.filter(event_type=PlantEvent.EventType.NOTE))
        return context


class PlantEventListView(UserPlantQuerySetMixin, ListView):
    template_name = 'garden/plant_event_list.html'
    context_object_name = 'events'

    def dispatch(self, request, *args, **kwargs):
        self.plant = get_object_or_404(Plant, pk=kwargs['pk'], user=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.plant.events.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plant'] = self.plant
        return context


class PlantCreateView(LoginRequiredMixin, CreateView):
    model = Plant
    form_class = PlantForm
    template_name = 'garden/plant_form.html'

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class PlantUpdateView(UserPlantQuerySetMixin, UpdateView):
    form_class = PlantForm
    template_name = 'garden/plant_form.html'


class PlantDeleteView(UserPlantQuerySetMixin, DeleteView):
    template_name = 'garden/plant_confirm_delete.html'
    success_url = reverse_lazy('garden:plant_list')


@login_required
@require_POST
def water_plant(request, pk):
    plant = get_object_or_404(Plant, pk=pk, user=request.user)
    form = PlantWateringForm(request.POST)
    comment = ''
    if form.is_valid():
        comment = format_watering_comment(form.cleaned_data['volume'], plant.watering_interval_days)
    plant.last_watered_at = timezone.now()
    plant.save(update_fields=['last_watered_at'])
    PlantEvent.objects.create(
        user=request.user,
        plant=plant,
        event_type=PlantEvent.EventType.WATERING,
        occurred_at=plant.last_watered_at,
        title='Полив',
        comment=comment,
    )
    if request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return redirect(plant)
    return JsonResponse({'ok': True, 'moisture_percent': plant.moisture_percent})


@login_required
@require_POST
def add_plant_note(request, pk):
    plant = get_object_or_404(Plant, pk=pk, user=request.user)
    form = PlantNoteForm(request.POST)
    if form.is_valid():
        PlantEvent.objects.create(
            user=request.user,
            plant=plant,
            event_type=PlantEvent.EventType.NOTE,
            title='Заметка',
            comment=form.cleaned_data['comment'],
        )
        messages.success(request, 'Заметка добавлена.')
    else:
        messages.error(request, 'Заполни текст заметки.')
    return redirect(plant)


@login_required
@require_POST
def fertilize_plant(request, pk):
    plant = get_object_or_404(Plant, pk=pk, user=request.user)
    form = PlantFertilizingForm(request.POST)
    if form.is_valid():
        PlantEvent.objects.create(
            user=request.user,
            plant=plant,
            event_type=PlantEvent.EventType.FERTILIZING,
            title='Удобрение',
            comment=form.cleaned_data['fertilizer'],
        )
        messages.success(request, 'Событие удобрения добавлено.')
    else:
        messages.error(request, 'Укажи, чем удобрял растение.')
    return redirect(plant)


class PlantEventCreateView(LoginRequiredMixin, CreateView):
    model = PlantEvent
    form_class = PlantEventForm
    template_name = 'garden/plant_event_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.plant = get_object_or_404(Plant, pk=kwargs['pk'], user=request.user)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.plant = self.plant
        messages.success(self.request, 'Событие добавлено.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plant'] = self.plant
        return context

    def get_success_url(self):
        return self.plant.get_absolute_url()
