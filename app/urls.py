from django.urls import path
from .views import *

urlpatterns = [
    path('', GetCities, name='home_page'),
    path('cities/<int:city_id>/', city),
    path('vacancy_applications/<int:app_id>/', vacancy_application),
    path('add_city_to_draft/', add_city_to_draft, name='add_city_to_draft'),
    path('delete_vacancy_application/', delete_vacancy_application, name='delete_vacancy_application'),
]