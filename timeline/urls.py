from django.urls import path

from . import views

app_name = 'timeline'

urlpatterns = [
    path('', views.page_detail, name='index'),
    path('<slug:slug>/', views.page_detail, name='page_detail'),
]
