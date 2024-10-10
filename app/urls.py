from django.contrib import admin
from django.urls import include, path
from app import views
from rest_framework import routers

router = routers.DefaultRouter()

urlpatterns = [
    # Путь на главную страницу вашего приложения
    path('', views.GetCities, name='home_page'),

    # Ваши кастомные пути
    path('cities/<int:city_id>/', views.city, name='city-detail'),
    path('applications/<int:app_id>/', views.application, name='application-detail'),
    path('add_city_to_draft/', views.add_city_to_draft, name='add_city_to_draft'),
    path('delete_application/', views.delete_application, name='delete_application'),

    # Пути с использованием Class-Based Views
    path('cities/', views.CitiesList.as_view(), name='cities-list'),
    path('cities/<int:city_id>/', views.CitiesDetail.as_view(), name='cities-detail'),
    path('cities/<int:city_id>/put/', views.put, name='cities-put'),

    # Пользователи
    path('users/', views.UsersList.as_view(), name='users-list'),

    # Включение роутера для DRF по адресу /api/
    path('api/', include(router.urls)),

    # DRF аутентификация и админ-панель
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('admin/', admin.site.urls),
]
