from django.urls import path

from . import views

app_name = 'transcription'

urlpatterns = [
    path('jobs/register/', views.RegisterJobView.as_view(), name='job_register'),
    path('jobs/acquire-next/', views.AcquireNextJobView.as_view(), name='job_acquire_next'),
    path('jobs/<int:pk>/complete/', views.CompleteJobView.as_view(), name='job_complete'),
    path('jobs/<int:pk>/fail/', views.FailJobView.as_view(), name='job_fail'),
    path('jobs/recover-stale/', views.RecoverStaleJobsView.as_view(), name='job_recover_stale'),
]
