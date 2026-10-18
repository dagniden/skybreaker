from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    path('', views.catalog, name='football_home'),
    path('admin/', admin.site.urls),
    path('', include('football.urls')),
]
