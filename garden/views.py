from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import PlantForm
from .models import Plant


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
    plant.last_watered_at = timezone.now()
    plant.save(update_fields=['last_watered_at'])
    if request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return redirect(plant)
    return JsonResponse({'ok': True, 'moisture_percent': plant.moisture_percent})
