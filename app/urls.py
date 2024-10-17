from django.contrib import admin
from django.urls import include, path
from app import views
from rest_framework import routers

router = routers.DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),

    path('cities/', views.CitiesList, name='cities_list'),
    path('cities/<int:city_id>/', views.GetCityById, name='get_city_by_id'),
    path('cities/create_city/', views.CreateCity, name='create_city'),
    path('cities/edit_city/<int:city_id>/', views.EditCity, name='edit_city'),




]

"""path(r'cities/<int:city_id>/', views.CitiesDetail.as_view(), name='stocks-detail'),
    path(r'cities/<int:city_id>/put/', views.put, name='cities-put'),


    path(r'users/', views.UsersList.as_view(), name='users-list'),"""
