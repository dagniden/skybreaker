from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from garden.models import Plant

from .forms import PlantSoilForm, SoilComponentForm, plant_soil_component_formset_factory
from .models import PlantSoil, SoilComponent


class SoilComponentQuerySetMixin(LoginRequiredMixin):
    model = SoilComponent

    def get_queryset(self):
        return SoilComponent.objects.filter(user=self.request.user)


class SoilComponentListView(SoilComponentQuerySetMixin, ListView):
    template_name = 'soil/component_list.html'
    context_object_name = 'components'


class SoilComponentCreateView(LoginRequiredMixin, CreateView):
    model = SoilComponent
    form_class = SoilComponentForm
    template_name = 'soil/component_form.html'
    success_url = reverse_lazy('soil:component_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class SoilComponentUpdateView(SoilComponentQuerySetMixin, UpdateView):
    form_class = SoilComponentForm
    template_name = 'soil/component_form.html'
    success_url = reverse_lazy('soil:component_list')


class PlantSoilEditorMixin(LoginRequiredMixin):
    template_name = 'soil/plant_soil_form.html'
    form_class = PlantSoilForm

    def get_formset(self, instance, extra=0):
        formset_class = plant_soil_component_formset_factory(extra=extra)
        return formset_class(
            self.request.POST or None,
            instance=instance,
            user=self.request.user,
        )

    def render_soil_form(self, form, formset, plant, plant_soil=None, mode='edit'):
        return self.render_to_response({
            'form': form,
            'formset': formset,
            'plant': plant,
            'plant_soil': plant_soil,
            'mode': mode,
        })

    def save_plant_soil(self, form, formset, plant, is_new_current):
        with transaction.atomic():
            if is_new_current:
                PlantSoil.objects.filter(plant=plant, is_current=True).update(is_current=False)

            plant_soil = form.save(commit=False)
            plant_soil.plant = plant
            plant_soil.user = self.request.user
            if is_new_current:
                plant_soil.is_current = True
            plant_soil.save()
            formset.instance = plant_soil
            formset.save()

        return plant_soil


class PlantSoilCreateView(PlantSoilEditorMixin, TemplateView):
    def dispatch(self, request, *args, **kwargs):
        self.plant = get_object_or_404(Plant, pk=kwargs['plant_pk'], user=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        plant_soil = PlantSoil(plant=self.plant, user=request.user)
        form = PlantSoilForm(instance=plant_soil)
        formset = self.get_formset(plant_soil, extra=1)
        return self.render_soil_form(form, formset, self.plant, mode='create')

    def post(self, request, *args, **kwargs):
        plant_soil = PlantSoil(plant=self.plant, user=request.user)
        form = PlantSoilForm(request.POST, instance=plant_soil)
        formset = self.get_formset(plant_soil)

        if form.is_valid() and formset.is_valid():
            plant_soil = self.save_plant_soil(form, formset, self.plant, is_new_current=True)
            messages.success(request, 'Состав почвы сохранен.')
            return redirect('garden:plant_detail', pk=plant_soil.plant_id)

        return self.render_soil_form(form, formset, self.plant, mode='create')


class PlantSoilUpdateView(PlantSoilEditorMixin, TemplateView):
    def dispatch(self, request, *args, **kwargs):
        self.plant_soil = get_object_or_404(
            PlantSoil.objects.select_related('plant').prefetch_related('parts__soil_component'),
            pk=kwargs['pk'],
            user=request.user,
        )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = PlantSoilForm(instance=self.plant_soil)
        formset = self.get_formset(self.plant_soil)
        return self.render_soil_form(form, formset, self.plant_soil.plant, self.plant_soil, mode='edit')

    def post(self, request, *args, **kwargs):
        form = PlantSoilForm(request.POST, instance=self.plant_soil)
        formset = self.get_formset(self.plant_soil)

        if form.is_valid() and formset.is_valid():
            self.save_plant_soil(form, formset, self.plant_soil.plant, is_new_current=False)
            messages.success(request, 'Текущий состав почвы исправлен.')
            return redirect('garden:plant_detail', pk=self.plant_soil.plant_id)

        return self.render_soil_form(form, formset, self.plant_soil.plant, self.plant_soil, mode='edit')


class PlantSoilReplaceView(PlantSoilCreateView):
    def dispatch(self, request, *args, **kwargs):
        old_soil = get_object_or_404(
            PlantSoil.objects.select_related('plant'),
            pk=kwargs['pk'],
            user=request.user,
        )
        self.previous_soil = old_soil
        self.plant = old_soil.plant
        return super(PlantSoilCreateView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        plant_soil = PlantSoil(plant=self.plant, user=request.user)
        form = PlantSoilForm(instance=plant_soil)
        formset = self.get_formset(plant_soil, extra=1)
        return self.render_soil_form(form, formset, self.plant, self.previous_soil, mode='replace')

    def post(self, request, *args, **kwargs):
        plant_soil = PlantSoil(plant=self.plant, user=request.user)
        form = PlantSoilForm(request.POST, instance=plant_soil)
        formset = self.get_formset(plant_soil)

        if form.is_valid() and formset.is_valid():
            plant_soil = self.save_plant_soil(form, formset, self.plant, is_new_current=True)
            messages.success(request, 'Создан новый текущий состав почвы.')
            return redirect('garden:plant_detail', pk=plant_soil.plant_id)

        return self.render_soil_form(form, formset, self.plant, self.previous_soil, mode='replace')


class PlantSoilHistoryView(LoginRequiredMixin, ListView):
    template_name = 'soil/plant_soil_history.html'
    context_object_name = 'plant_soils'

    def dispatch(self, request, *args, **kwargs):
        self.plant = get_object_or_404(Plant, pk=kwargs['plant_pk'], user=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.plant.soils.prefetch_related('parts__soil_component')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plant'] = self.plant
        return context
