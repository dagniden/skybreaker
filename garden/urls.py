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
]
