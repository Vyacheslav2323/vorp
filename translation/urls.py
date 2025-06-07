from django.urls import path
from . import views

app_name = 'translation'
 
urlpatterns = [
    path('translate-word/', views.translate_word_ajax, name='translate_word'),
    path('translate-phrase/', views.translate_phrase, name='translate_phrase'),
    path('preferences/', views.translation_preferences, name='preferences'),
] 