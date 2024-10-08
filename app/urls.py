from django.urls import path
from .views import *

urlpatterns = [
    path('', open),
    path('cities/<int:city_id>/', city),
    path('applications/<int:application_id>/', application),
]