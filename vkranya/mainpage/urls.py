from django.urls import path
from . import views

urlpatterns = [
    path('', views.mainpage, name='mainpage'),
    path('api/calculate/', calculate_admission, name='calculate'),

]