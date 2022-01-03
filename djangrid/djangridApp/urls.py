from django.urls import path
from . import views


urlpatterns = [
    path('subscribe/', views.subscribe, name='subscribe'),
    path('confirm/', views.confirm, name='confirm'),
    path('delete/', views.delete, name='delete'),
]