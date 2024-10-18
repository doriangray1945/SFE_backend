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
    path('cities/<int:city_id>/edit_city/', views.EditCity, name='edit_city'),
    path('cities/<int:city_id>/delete_city/', views.DeleteCity, name='delete_city'),
    path('cities/<int:city_id>/add_to_vacancy_application/', views.AddCityToDraft, name='add_city_to_vacancy_application'),
    path('cities/<int:city_id>/update_image/', views.UpdateCityImage, name='update_city_image'),

    path('vacancy_applications/', views.VacancyApplicationsList, name='vacancy_applications_list'),
    path('vacancy_applications/<int:app_id>/', views.GetVacancyApplicationById, name='get_vacancy_application_by_id'),
    path('vacancy_applications/<int:app_id>/update_vacancy_application/', views.UpdateVacancyApplication, name='update_vacancy_application'),
    path('vacancy_applications/<int:app_id>/update_status_user/', views.UpdateStatusUser, name='update_status_user'),
    path('vacancy_applications/<int:app_id>/update_status_admin/', views.UpdateStatusAdmin, name='update_status_admin'),
    path('vacancy_applications/<int:app_id>/delete_vacancy_application/', views.DeleteVacancyApplication, name='delete_vacancy_application'),





]

"""path(r'cities/<int:city_id>/', views.CitiesDetail.as_view(), name='stocks-detail'),
    path(r'cities/<int:city_id>/put/', views.put, name='cities-put'),


    path(r'users/', views.UsersList.as_view(), name='users-list'),"""
