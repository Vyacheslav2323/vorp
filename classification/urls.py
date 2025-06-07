from django.urls import path
from . import views

app_name = 'classification'

urlpatterns = [
    path('mark-as-learned/', views.mark_as_learned, name='mark_as_learned'),
    path('mark-as-unknown/', views.mark_as_unknown, name='mark_as_unknown'),
    path('remove-known-word/', views.remove_known_word, name='remove_known_word'),
    path('update-word-status/', views.update_word_status, name='update_word_status'),
    path('api/vocabulary-analysis/', views.api_vocabulary_analysis, name='api_vocabulary_analysis'),
] 