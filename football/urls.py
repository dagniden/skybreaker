from django.urls import path, re_path

from . import views

app_name = 'football'

urlpatterns = [
    path('football/', views.catalog, name='catalog'),
    path('football/download/', views.download, name='download'),
    path('api/football/replays/', views.UploadReplayView.as_view(), name='upload'),
    re_path(r'^api/football/replays/(?P<replay_id>[A-Za-z0-9_-]{24})/$', views.replay_data, name='replay_data'),
    re_path(r'^football/replays/(?P<replay_id>[A-Za-z0-9_-]{24})/$', views.viewer, name='viewer'),
]
