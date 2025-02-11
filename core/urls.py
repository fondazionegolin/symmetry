from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('process_answers/', views.process_answers, name='process_answers'),
    path('save_photo/', views.save_photo, name='save_photo'),
]
