from django.urls import include, path
from app import views
from rest_framework import routers, permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


router = routers.DefaultRouter()

router.register(r'user', views.UserViewSet, basename='user')

# схема swagger
schema_view = get_schema_view(
   openapi.Info(
      title="Snippets API",
      default_version='v1',
      description="Test description",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@snippets.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('', include(router.urls)),
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
    path('vacancy_applications/<int:app_id>/update_vacancy/', views.UpdateVacancy, name='update_vacancy'),
    path('vacancy_applications/<int:app_id>/update_status_user/', views.UpdateStatusUser, name='update_status_user'),
    path('vacancy_applications/<int:app_id>/update_status_admin/', views.UpdateStatusAdmin, name='update_status_admin'),
    path('vacancy_applications/<int:app_id>/delete_vacancy_application/', views.DeleteVacancyApplication, name='delete_vacancy_application'),

    path('cities_vacancy_applications/<int:mm_id>/delete_city_from_vacancy_application/', views.DeleteCityFromVacancyApplication, name='delete_city_from_vacancy_application'),
    path('cities_vacancy_applications/<int:mm_id>/update_vacancy_application/', views.UpdateVacancyApplication, name='update_vacancy_application'),

    path('user/<int:user_id>/update_user/', views.UpdateUser, name='update_user'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]