from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('process_answers/', views.process_answers, name='process_answers'),
    path('save_photo/', views.save_photo, name='save_photo'),
    path('json/<str:filename>', views.serve_json, name='serve_json'),
    path('get_user_code/', views.get_user_code_endpoint, name='get_user_code'),
]
