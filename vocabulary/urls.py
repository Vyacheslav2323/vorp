from django.urls import path
from . import views

app_name = 'vocabulary'

urlpatterns = [
    path('my-vocabulary/', views.my_vocabulary, name='my_vocabulary'),
    path('sets/', views.vocabulary_sets, name='sets'),
    path('create-set/', views.create_vocabulary_set, name='create_set'),
    path('add-to-set/', views.add_word_to_set, name='add_to_set'),
    path('manage-lemma/', views.manage_word_lemma, name='manage_lemma'),
] 