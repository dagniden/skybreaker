from django.urls import path

from . import views

app_name = 'soil'

urlpatterns = [
    path('components/', views.SoilComponentListView.as_view(), name='component_list'),
    path('components/new/', views.SoilComponentCreateView.as_view(), name='component_create'),
    path('components/<int:pk>/edit/', views.SoilComponentUpdateView.as_view(), name='component_update'),
    path('plants/<int:plant_pk>/soil/new/', views.PlantSoilCreateView.as_view(), name='plant_soil_create'),
    path('plants/<int:plant_pk>/soil/history/', views.PlantSoilHistoryView.as_view(), name='plant_soil_history'),
    path('plant-soils/<int:pk>/edit/', views.PlantSoilUpdateView.as_view(), name='plant_soil_edit'),
    path('plant-soils/<int:pk>/replace/', views.PlantSoilReplaceView.as_view(), name='plant_soil_replace'),
]
