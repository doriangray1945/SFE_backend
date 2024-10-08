from django.urls import path
from .views import *

urlpatterns = [
    path('', GetCities, name='home_page'),
    path('cities/<int:city_id>/', city),
    path('applications/<int:app_id>/', application),
    path('add_city_to_draft/', add_city_to_draft, name='add_city_to_draft'),
    path('delete_application/', delete_application, name='delete_application'),
]