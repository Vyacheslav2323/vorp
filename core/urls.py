from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('vocabulary-test/', views.vocabulary_test, name='vocabulary_test'),
    path('subscription/', views.subscription_page, name='subscription_page'),
    path('subscription/create/', views.create_subscription, name='create_subscription'),
    path('subscription/execute/', views.execute_subscription, name='execute_subscription'),
    path('subscription/cancel/', views.cancel_subscription, name='cancel_subscription'),
] 