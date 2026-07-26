from django.urls import path

from . import views

app_name = 'garden'

urlpatterns = [
    path('', views.PlantListView.as_view(), name='plant_list'),
    path('plants/new/', views.PlantCreateView.as_view(), name='plant_create'),
    path('plants/<int:pk>/', views.PlantDetailView.as_view(), name='plant_detail'),
    path('plants/<int:pk>/edit/', views.PlantUpdateView.as_view(), name='plant_update'),
    path('plants/<int:pk>/delete/', views.PlantDeleteView.as_view(), name='plant_delete'),
    path('plants/<int:pk>/water/', views.water_plant, name='plant_water'),
    path('plants/<int:pk>/fertilize/', views.fertilize_plant, name='plant_fertilize'),
    path('plants/<int:pk>/notes/new/', views.add_plant_note, name='plant_note_create'),
    path('plants/<int:pk>/events/', views.PlantEventListView.as_view(), name='plant_event_list'),
    path('plants/<int:pk>/events/new/', views.PlantEventCreateView.as_view(), name='plant_event_create'),
]
