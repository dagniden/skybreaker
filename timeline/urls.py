from django.urls import path

from . import views

app_name = 'timeline'

urlpatterns = [
    path('', views.timeline_detail, name='index'),
    path('<slug:name>/', views.timeline_detail, name='timeline_detail'),
]
