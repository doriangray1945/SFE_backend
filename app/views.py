from urllib import request

from rest_framework.response import Response
from rest_framework import status
from app.serializers import *
from rest_framework.decorators import api_view, permission_classes,authentication_classes
from .minio import add_pic
from app.models import *
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from drf_yasg.utils import swagger_auto_schema
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse

from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework import viewsets
import redis
from django.conf import settings
import uuid
from django.views.decorators.csrf import csrf_exempt
from app.permissions import IsAdmin, IsManager
from rest_framework.authentication import SessionAuthentication


# класс аутентификации, который исключает CSRF для сессий
class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # Отключаем CSRF-проверку


def GetDraftVacancyApplication(request):
    current_user = request.user
    return VacancyApplications.objects.filter(creator=current_user.id, status=1).first()  # так как у пользователя только один черновик, то берем первый элемент, иначе None


#ДОМЕН УСЛУГИ
# GET список с фильтрацией. В списке услуг возвращается id заявки-черновика этого пользователя для страницы заявки и количество услуг в этой заявке
@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def CitiesList(request):
    city_name = request.GET.get("city_name", '')
    cities = Cities.objects.filter(status=1, name__istartswith=city_name)
    serializer = CitiesSerializer(cities, many=True)

    if GetDraftVacancyApplication(request):
        app_id = GetDraftVacancyApplication(request).app_id
        count = CitiesVacancyApplications.objects.filter(app_id=app_id).count()
    else:
        app_id = None
        count = 0

    response = {
        "cities": serializer.data,
        "draft_vacancy_application": app_id,
        "count": count,
    }
    return Response(response, status=status.HTTP_200_OK)


# GET одна запись
@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def GetCityById(request, city_id):
    try:
        city = Cities.objects.get(city_id=city_id, status=1)
    except Cities.DoesNotExist:
        return Response({"Ошибка": "Город не найден"}, status=status.HTTP_404_NOT_FOUND)

    serializer = CitiesSerializer(city, many=False)

    return Response(serializer.data, status=status.HTTP_200_OK)


# POST добавление
@swagger_auto_schema(method='post', request_body=CitiesSerializer)
@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAdmin])
def CreateCity(request):
    city_data = request.data.copy()
    city_data.pop('image', None)

    serializer = CitiesSerializer(data=city_data)
    serializer.is_valid(raise_exception=True)
    new_city = serializer.save()

    return Response(CitiesSerializer(new_city).data, status=status.HTTP_201_CREATED)


# PUT изменение
@swagger_auto_schema(method='put', request_body=CitiesSerializer)
@api_view(["PUT"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAdmin])
def EditCity(request, city_id):
    try:
        city = Cities.objects.get(city_id=city_id)
    except Cities.DoesNotExist:
        return Response({"Ошибка": "Город не найден"}, status=status.HTTP_404_NOT_FOUND)

    city_data = request.data.copy()
    city_data.pop('image', None)

    serializer = CitiesSerializer(city, data=city_data, partial=True)
    serializer.is_valid(raise_exception=True)
    edited_city = serializer.save()

    # Обработка изменения изображения, если оно предоставлено
    pic = request.FILES.get("image")
    if pic:
        pic_result = add_pic(edited_city, pic)
        if 'error' in pic_result.data:
            return pic_result  # Возвращаем ошибку, если загрузка изображения не удалась

    # Возвращаем обновлённые данные
    return Response(CitiesSerializer(edited_city).data, status=status.HTTP_200_OK)


# DELETE удаление. Удаление изображения встроено в метод удаления услуги
@api_view(["DELETE"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAdmin])
def DeleteCity(request, city_id):
    try:
        city = Cities.objects.get(city_id=city_id)
    except Cities.DoesNotExist:
        return Response({"Ошибка": "Город не найден"}, status=status.HTTP_404_NOT_FOUND)

    city.status = 2
    city.save()

    cities = Cities.objects.filter(status=1)
    serializer = CitiesSerializer(cities, many=True)
    return Response(serializer.data)


# POST добавления в заявку-черновик. Заявка создается пустой, указывается автоматически создатель, дата создания и статус, остальные поля указываются через PUT или смену статуса
@swagger_auto_schema(method='post', request_body=VacancyApplicationsSerializer)
@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def AddCityToDraft(request, city_id):
    try:
        city = Cities.objects.get(city_id=city_id)
    except Cities.DoesNotExist:
        return Response({"error": "Город не найден"}, status=status.HTTP_404_NOT_FOUND)

    draft_vacancy_application = GetDraftVacancyApplication(request)

    # если черновика нет, создаем новый
    if draft_vacancy_application is None:
        draft_vacancy_application = VacancyApplications.objects.create(
            date_created=timezone.now(),  # Время создания
            creator=request.user,  # Создатель заявки
            status=1,  # Статус "Действует"
        )

    # есть ли уже этот город в черновике
    existing_entry = CitiesVacancyApplications.objects.filter(app_id=draft_vacancy_application, city_id=city_id).first()

    if existing_entry:
        # увеличиваем, если город уже есть в заявке
        existing_entry.count += 1
        existing_entry.save()
    else:
        # если города нет в заявке, создаем новую запись
        try:
            CitiesVacancyApplications.objects.create(
                app_id=draft_vacancy_application,
                city_id=Cities.objects.get(city_id=city_id),
                count=1  # Начинаем с 1
            )
        except Exception as e:
            return Response({"error": f"Ошибка при создании связки: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    serializer = VacancyApplicationsSerializer(draft_vacancy_application)

    return Response(serializer.data, status=status.HTTP_200_OK)


# POST добавление изображения. Добавление изображения по id услуги, старое изображение заменяется/удаляется. minio только в этом методе и удалении!
@swagger_auto_schema(method='post', request_body=CitiesSerializer)
@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAdmin])
def UpdateCityImage(request, city_id):
    try:
        city = Cities.objects.get(city_id=city_id)
    except Cities.DoesNotExist:
        return Response({"Ошибка": "Город не найден"}, status=status.HTTP_404_NOT_FOUND)

    image = request.FILES.get("image")

    if image is not None:
        # Заменяем старое изображение
        pic_result = add_pic(city, image)  # Используем функцию add_pic для загрузки нового изображения
        if 'error' in pic_result.data:
            return pic_result  # Если произошла ошибка, возвращаем её

        serializer = CitiesSerializer(city)  # Обновляем сериализатор
        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response({"Ошибка": "Изображение не предоставлено"}, status=status.HTTP_400_BAD_REQUEST)



#ДОМЕН ЗАЯВКИ
#GET список (кроме удаленных и черновика, поля модератора и создателя через логины) с фильтрацией по диапазону даты формирования и статусу
@api_view(["GET"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def VacancyApplicationsList(request):
    status = int(request.GET.get("status", 0))
    date_submitted_start = request.GET.get("date_submitted_start")
    date_submitted_end = request.GET.get("date_submitted_end")

    if request.user.is_staff or request.user.is_superuser:
        vacancy_applications = VacancyApplications.objects.all()
    else:
        vacancy_applications = VacancyApplications.objects.exclude(status__in=[1, 2])
        vacancy_applications = vacancy_applications.filter(creator=request.user)

    if status:
        vacancy_applications = vacancy_applications.filter(status=status)

    if date_submitted_start and parse_datetime(date_submitted_start):
        vacancy_applications = vacancy_applications.filter(submitted__gte=parse_datetime(date_submitted_start))

    if date_submitted_end and parse_datetime(date_submitted_end):
        vacancy_applications = vacancy_applications.filter(submitted__lt=parse_datetime(date_submitted_end))

    serializer = VacancyApplicationsSerializer(vacancy_applications, many=True)

    return Response(serializer.data)


# GET одна запись (поля заявки + ее услуги). При получении заявки возвращется список ее услуг с картинками
@api_view(["GET"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def GetVacancyApplicationById(request, app_id):
    try:
        if request.user.is_staff or request.user.is_superuser:
            vacancy_application = VacancyApplications.objects.get(app_id=app_id)
        else:
            vacancy_application = VacancyApplications.objects.get(app_id=app_id, creator=request.user)
    except VacancyApplications.DoesNotExist:
        return Response({"Ошибка": "Заявка на создание вакансии не найдена"}, status=status.HTTP_404_NOT_FOUND)

    vacancy_application_serializer = VacancyApplicationsSerializer(vacancy_application, many=False)

    cities_vacancy_applications = CitiesVacancyApplications.objects.filter(app_id=app_id)
    cities_serializer = CitiesVacancyApplicationsSerializer(cities_vacancy_applications, many=True)

    response_data = {
        'vacancy_application': vacancy_application_serializer.data,
        'cities': cities_serializer.data
    }

    return Response(response_data, status=status.HTTP_200_OK)


# PUT изменения полей заявки по теме
@swagger_auto_schema(method='put', request_body=VacancyApplicationsSerializer)
@api_view(["PUT"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def UpdateVacancy(request, app_id):
    try:
        if request.user.is_staff or request.user.is_superuser:
            vacancy_application = VacancyApplications.objects.get(app_id=app_id)
        else:
            vacancy_application = VacancyApplications.objects.get(app_id=app_id, creator=request.user, status=1)
    except VacancyApplications.DoesNotExist:
        return Response({"Ошибка": "Заявка на создание вакансии не найдена"}, status=status.HTTP_404_NOT_FOUND)

    allowed_fields = ['vacancy_name', 'vacancy_responsibilities', 'vacancy_requirements']

    data = {key: value for key, value in request.data.items() if key in allowed_fields}

    if not data:
        return Response({"Ошибка": "Нет данных для обновления или поля не разрешены"}, status=status.HTTP_400_BAD_REQUEST)

    serializer = VacancyApplicationsSerializer(vacancy_application, data=data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# PUT сформировать создателем (дата формирования). Происходит проверка на обязательные поля
@swagger_auto_schema(method='put', request_body=VacancyApplicationsSerializer)
@api_view(["PUT"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def UpdateStatusUser(request, app_id):
    try:
        if request.user.is_staff or request.user.is_superuser:
            vacancy_application = VacancyApplications.objects.get(app_id=app_id)
        else:
            vacancy_application = VacancyApplications.objects.get(app_id=app_id, creator=request.user, status=1)
    except VacancyApplications.DoesNotExist:
        return Response({"Ошибка": "Заявка на создание вакансии не найдена"}, status=status.HTTP_404_NOT_FOUND)

    if vacancy_application.status != 1:
        return Response({"Ошибка": "Заявку нельзя изменить, так как она не в статусе 'Черновик'"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    required_fields = ['vacancy_name', 'vacancy_responsibilities', 'vacancy_requirements']

    missing_fields = [field for field in required_fields if not getattr(vacancy_application, field)]

    if missing_fields:
        return Response(
            {"Ошибка": f"Не заполнены обязательные поля: {', '.join(missing_fields)}"},
            status=status.HTTP_400_BAD_REQUEST
        )

    vacancy_application.status = 3
    vacancy_application.submitted = timezone.now()
    vacancy_application.save()

    serializer = VacancyApplicationsSerializer(vacancy_application, many=False)
    return Response(serializer.data, status=status.HTTP_200_OK)


# PUT завершить/отклонить модератором. При завершить/отклонении заявки проставляется модератор и дата завершения. Одно из доп. полей заявки или м-м рассчитывается при завершении заявки (вычисление стоимости заказа, даты доставки в течении месяца, вычисления в м-м).
@swagger_auto_schema(method='put', request_body=VacancyApplicationsSerializer)
@api_view(["PUT"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsManager | IsAdmin])
def UpdateStatusAdmin(request, app_id):
    try:
        vacancy_application = VacancyApplications.objects.get(app_id=app_id)
    except VacancyApplications.DoesNotExist:
        return Response({"Ошибка": "Заявка на создание вакансии не найдена"}, status=status.HTTP_404_NOT_FOUND)

    request_status = int(request.data["status"])

    if request_status not in [4, 5]:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    if vacancy_application.status != 3:
        if request_status in [4, 5]:
            return Response({"Ошибка": "Заявка уже завершена/отклонена."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        return Response({"Ошибка": "Заявка ещё не сформирована"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    vacancy_application.completed = timezone.now()
    vacancy_application.status = request_status
    vacancy_application.moderator = request.user
    vacancy_application.save()

    serializer = VacancyApplicationsSerializer(vacancy_application, many=False)

    return Response(serializer.data)


# DELETE удаление (дата формирования)
@api_view(["DELETE"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsManager | IsAdmin])
def DeleteVacancyApplication(request, app_id):
    try:
        vacancy_application = VacancyApplications.objects.get(app_id=app_id)
    except VacancyApplications.DoesNotExist:
        return Response({"Ошибка": "Заявка на создание вакансии не найдена"}, status=status.HTTP_404_NOT_FOUND)

    if vacancy_application.status == 1:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    vacancy_application.status = 2
    vacancy_application.save()

    serializer = VacancyApplicationsSerializer(vacancy_application, many=False)

    return Response(serializer.data)


# Домен м-м
# DELETE удаление из заявки (без PK м-м)
@api_view(["DELETE"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def DeleteCityFromVacancyApplication(request, mm_id):
    try:
        city_vacancy_application = CitiesVacancyApplications.objects.get(mm_id=mm_id)
    except CitiesVacancyApplications.DoesNotExist:
        return Response({"Ошибка": "Связь между городом и заявкой не найдена"}, status=status.HTTP_404_NOT_FOUND)

    # Сохраняем ID заявки перед удалением связи
    app_id = city_vacancy_application.app_id_id
    vacancy_application = VacancyApplications.objects.get(app_id=app_id)

    if not request.user.is_staff or request.user.is_superuser:
        if vacancy_application.creator != request.user or vacancy_application.status != 1:
            return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)

    # Удаляем связь
    city_vacancy_application.delete()

    # Обновляем данные заявки
    try:
        vacancy_application = VacancyApplications.objects.get(app_id=app_id)
    except VacancyApplications.DoesNotExist:
        return Response({"Ошибка": "Заявка на создание вакансии не найдена после удаления города"}, status=status.HTTP_404_NOT_FOUND)

    # Сериализуем обновлённую заявку
    serializer = VacancyApplicationsSerializer(vacancy_application, many=False)

    # Возвращаем обновлённые данные заявки
    return Response(serializer.data, status=status.HTTP_200_OK)


# PUT изменение количества/порядка/значения в м-м (без PK м-м)
@swagger_auto_schema(method='put', request_body=CitiesVacancyApplicationsSerializer)
@api_view(["PUT"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def UpdateVacancyApplication(request, mm_id):
    try:
        city_vacancy_application = CitiesVacancyApplications.objects.get(mm_id=mm_id)
    except CitiesVacancyApplications.DoesNotExist:
        return Response({"Ошибка": "Связь между городом и заявкой не найдена"}, status=status.HTTP_404_NOT_FOUND)

    app_id = city_vacancy_application.app_id_id
    vacancy_application = VacancyApplications.objects.get(app_id=app_id)

    if not request.user.is_staff or request.user.is_superuser:
        if vacancy_application.creator != request.user or vacancy_application.status != 1:
            return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)

    count = request.data.get("count")

    if count is not None:
        city_vacancy_application.count = count
        city_vacancy_application.save()
        serializer = CitiesVacancyApplicationsSerializer(city_vacancy_application, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response({"Ошибка": "Количество не предоставлено"}, status=status.HTTP_400_BAD_REQUEST)


# Домен пользователь
# PUT пользователя (личный кабинет)
@swagger_auto_schema(method='put', request_body=UserSerializer)
@api_view(["PUT"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def UpdateUser(request, user_id):
    if not User.objects.filter(id=user_id).exists():
        return Response({"detail": "Пользователь не найден."}, status=status.HTTP_404_NOT_FOUND)

    user = User.objects.get(id=user_id)

    if not request.user.is_superuser:
        if user != request.user:
            return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)

    serializer = UserSerializer(user, data=request.data, many=False, partial=True)

    if not serializer.is_valid():
        return Response(status=status.HTTP_409_CONFLICT)

    serializer.save()

    return Response(serializer.data)


class UserViewSet(viewsets.ModelViewSet):
    """Класс, описывающий методы работы с пользователями
    Осуществляет связь с таблицей пользователей в базе данных
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    model_class = User

    """def get_authenticators(self):
        if self.action in ['create']:
            authentication_classes = [AllowAny] # Отключаем аутентификацию
        else:
            authentication_classes = [CsrfExemptSessionAuthentication()]  # Используем
        return [authenticate() for authenticate in authentication_classes]"""

    http_method_names = ['create', 'list', 'get', 'post', 'delete']

    def get_permissions(self):
        if self.action in ['create']:
            permission_classes = [AllowAny]
        elif self.action in ['list']:
            permission_classes = [IsAdmin | IsManager ]
        else:
            permission_classes = [IsAdmin]
        return [permission() for permission in permission_classes]

    def create(self, request):
        """
        Функция регистрации новых пользователей
        Если пользователя c указанным в request email ещё нет, в БД будет добавлен новый пользователь.
        """
        if self.model_class.objects.filter(username=request.data['username']).exists():
            return Response({'status': 'Exist'}, status=400)
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            print(serializer.data)
            self.model_class.objects.create_user(username=serializer.data['username'],
                                     password=serializer.data['password'],
                                     is_superuser=serializer.data['is_superuser'],
                                     is_staff=serializer.data['is_staff'])
            return Response({'status': 'Success'}, status=200)
        return Response({'status': 'Error', 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


#@csrf_exempt
@swagger_auto_schema(method='post', request_body=UserSerializer)
@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([])
def login_view(request):
    data = request.data
    username = data.get("username")
    password = data.get("password")
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return HttpResponse("{'status': 'ok'}")
    else:
        return HttpResponse("{'status': 'error', 'error': 'login failed'}")


#@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([CsrfExemptSessionAuthentication])
def logout_view(request):
    logout(request)
    return Response({'status': 'Success'})


# Connect to our Redis instance
session_storage = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)