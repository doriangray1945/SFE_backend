from rest_framework.response import Response
from rest_framework import status
from app.serializers import *
from rest_framework.decorators import api_view, permission_classes,authentication_classes
from .minio import add_pic
from app.models import *
from django.contrib.auth.models import User, AnonymousUser
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from drf_yasg.utils import swagger_auto_schema
from django.contrib.auth import authenticate, login, logout
from drf_yasg import openapi

from rest_framework.permissions import AllowAny
from rest_framework import viewsets
from django.conf import settings
import uuid
from app.permissions import *
from rest_framework.authentication import SessionAuthentication

import random

from rest_framework.pagination import PageNumberPagination


# класс аутентификации, который исключает CSRF для сессий
class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # Отключаем CSRF-проверку


def GetDraftVacancyApplication(request):
    current_user = request.user
    return VacancyApplications.objects.filter(creator=current_user.id, status=1).first()  # так как у пользователя только один черновик, то берем первый элемент, иначе None


#ДОМЕН УСЛУГИ
# GET список с фильтрацией. В списке услуг возвращается id заявки-черновика этого пользователя для страницы заявки и количество услуг в этой заявке
@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter(
            'city_name',
            openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            required=False,
        )
    ],
    responses={
        status.HTTP_200_OK: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "cities": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "city_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "name": openapi.Schema(type=openapi.TYPE_STRING, nullable=False),
                            "population": openapi.Schema(type=openapi.TYPE_STRING, nullable=False),
                            "salary": openapi.Schema(type=openapi.TYPE_STRING, nullable=False),
                            "unemployment_rate": openapi.Schema(type=openapi.TYPE_STRING, nullable=False),
                            "description": openapi.Schema(type=openapi.TYPE_STRING, nullable=False),
                            "url": openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    ),
                    nullable=False,
                ),
                "draft_vacancy_application": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    nullable=True,
                ),
                "count": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    nullable=True,
                ),
            },
        )
    },
)
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
        "count": count
    }

    return Response(response, status=status.HTTP_200_OK)


# GET одна запись
@swagger_auto_schema(
    method='get',
    responses={
        status.HTTP_200_OK: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "city_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "name": openapi.Schema(type=openapi.TYPE_STRING, nullable=False),
                "population": openapi.Schema(type=openapi.TYPE_STRING, nullable=False),
                "salary": openapi.Schema(type=openapi.TYPE_STRING, nullable=False),
                "unemployment_rate": openapi.Schema(type=openapi.TYPE_STRING, nullable=False),
                "description": openapi.Schema(type=openapi.TYPE_STRING, nullable=False),
                "url": openapi.Schema(type=openapi.TYPE_STRING),
            },
        )
    },
)
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
        city = Cities.objects.get(city_id=city_id, status=1)
    except Cities.DoesNotExist:
        return Response({"Ошибка": "Город не найден"}, status=status.HTTP_404_NOT_FOUND)

    city.status = 2
    city.save()

    cities = Cities.objects.filter(status=1)
    serializer = CitiesSerializer(cities, many=True)
    return Response(serializer.data)


# POST добавления в заявку-черновик. Заявка создается пустой, указывается автоматически создатель, дата создания и статус, остальные поля указываются через PUT или смену статуса
@swagger_auto_schema(method='post', responses={
        status.HTTP_200_OK: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "vacancy_application": openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "app_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="Уникальный идентификатор заявки."),
                        "status": openapi.Schema(type=openapi.TYPE_INTEGER, description="Статус заявки."),
                        "date_created": openapi.Schema(type=openapi.TYPE_STRING, format="date-time", description="Дата и время создания заявки."),
                        "creator": openapi.Schema(type=openapi.TYPE_STRING, description="Имя пользователя, создавшего заявку."),
                        "moderator": openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description="Имя модератора заявки (если есть)."),
                        "date_submitted": openapi.Schema(type=openapi.TYPE_STRING, format="date-time", nullable=True, description="Дата отправки заявки."),
                        "date_completed": openapi.Schema(type=openapi.TYPE_STRING, format="date-time", nullable=True, description="Дата завершения заявки."),
                        "vacancy_name": openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description="Название вакансии."),
                        "vacancy_responsibilities": openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description="Обязанности вакансии."),
                        "vacancy_requirements": openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description="Требования вакансии."),
                        "duration_days": openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True, description="Продолжительность обработки заявки в днях."),
                    },
                ),
                "cities": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "city_id": openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "city_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                    "name": openapi.Schema(type=openapi.TYPE_STRING, nullable=False),
                                    "population": openapi.Schema(type=openapi.TYPE_STRING, nullable=False),
                                    "salary": openapi.Schema(type=openapi.TYPE_STRING, nullable=False),
                                    "unemployment_rate": openapi.Schema(type=openapi.TYPE_STRING, nullable=False),
                                    "description": openapi.Schema(type=openapi.TYPE_STRING, nullable=False),
                                    "url": openapi.Schema(type=openapi.TYPE_STRING),
                                },
                            ),
                            "count": openapi.Schema(type=openapi.TYPE_INTEGER, description="Количество записей для данного города."),
                        },
                    ),
                    description="Список городов, привязанных к заявке."
                ),
            },
        ),
    })
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

    vacancy_application_serializer = VacancyApplicationsSerializer(draft_vacancy_application, many=False)

    cities_vacancy_applications = CitiesVacancyApplications.objects.filter(app_id=draft_vacancy_application)
    cities_serializer = CitiesVacancyApplicationsSerializer(cities_vacancy_applications, many=True, fields=["city_id", "count"])

    response_data = {
        'vacancy_application': vacancy_application_serializer.data,
        'cities': cities_serializer.data
    }

    return Response(response_data, status=status.HTTP_200_OK)


# POST добавление изображения. Добавление изображения по id услуги, старое изображение заменяется/удаляется. minio только в этом методе и удалении!
@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "image": openapi.Schema(
                type=openapi.TYPE_STRING,
                format="binary",
                description="Новое изображение для города."
            )
        },
        required=["image"],
    ),
    responses={
        status.HTTP_200_OK: CitiesSerializer,
        status.HTTP_400_BAD_REQUEST: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "Ошибка": openapi.Schema(type=openapi.TYPE_STRING, example="Изображение не предоставлено."),
            },
        ),
        status.HTTP_404_NOT_FOUND: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "Ошибка": openapi.Schema(type=openapi.TYPE_STRING, example="Город не найден."),
            },
        ),
    }
)
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
class VacancyApplicationsPagination(PageNumberPagination):
    page_size = 50  # Стандартное количество записей на страницу
    page_size_query_param = 'limit'
    max_page_size = 1000


@swagger_auto_schema(
    method="get",
    manual_parameters=[
        openapi.Parameter(
            "status",
            openapi.IN_QUERY,
            description="Статус заявки.",
            type=openapi.TYPE_INTEGER,
            required=False,
        ),
        openapi.Parameter(
            "date_submitted_start",
            openapi.IN_QUERY,
            description="Начальная дата подачи заявки (в формате YYYY-MM-DDTHH:MM:SS).",
            type=openapi.TYPE_STRING,
            format="date-time",
            required=False,
        ),
        openapi.Parameter(
            "date_submitted_end",
            openapi.IN_QUERY,
            description="Конечная дата подачи заявки (в формате YYYY-MM-DDTHH:MM:SS).",
            type=openapi.TYPE_STRING,
            format="date-time",
            required=False,
        ),
        openapi.Parameter(
            "page",
            openapi.IN_QUERY,
            description="Номер страницы для пагинации.",
            type=openapi.TYPE_INTEGER,
            required=False,
        ),
        openapi.Parameter(
            "limit",
            openapi.IN_QUERY,
            description="Количество записей на странице.",
            type=openapi.TYPE_INTEGER,
            required=False,
        ),
    ],
    responses={
        status.HTTP_200_OK: openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "app_id": openapi.Schema(
                        type=openapi.TYPE_INTEGER,
                        description="Уникальный идентификатор заявки."
                    ),
                    "status": openapi.Schema(
                        type=openapi.TYPE_INTEGER,
                        description="Статус заявки: 1 - 'Черновик', 2 - 'Удалена', 3 - 'Сформирована', 4 - 'Завершена', 5 - 'Отклонена'.",
                    ),
                    "date_created": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        format="date-time",
                        description="Дата и время создания заявки.",
                        nullable=False,
                    ),
                    "creator": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Имя пользователя, который создал заявку.",
                        nullable=False,
                    ),
                    "moderator": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        nullable=True,
                        description="Имя модератора, обработавшего заявку (если есть)."
                    ),
                    "date_submitted": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        format="date-time",
                        nullable=True,
                        description="Дата и время отправки заявки (если была отправлена)."
                    ),
                    "date_completed": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        format="date-time",
                        nullable=True,
                        description="Дата и время завершения заявки (если была завершена)."
                    ),
                    "vacancy_name": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        nullable=True,
                        description="Название вакансии."
                    ),
                    "vacancy_responsibilities": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        nullable=True,
                        description="Обязанности по вакансии."
                    ),
                    "vacancy_requirements": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        nullable=True,
                        description="Требования к вакансии."
                    ),
                    "duration_days": openapi.Schema(
                        type=openapi.TYPE_INTEGER,
                        nullable=True,
                        description="Продолжительность обработки заявки в днях (если доступно)."
                    ),
                },
            ),
        )
    },
)
@api_view(["GET"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def VacancyApplicationsList(request):
    status_filter = int(request.GET.get("status", 0))
    date_submitted_start = request.GET.get("date_submitted_start")
    date_submitted_end = request.GET.get("date_submitted_end")

    # Получаем параметры пагинации
    page = int(request.GET.get("page", 1))  # Страница по умолчанию - 1
    limit = int(request.GET.get("limit", 50))  # Количество записей на странице по умолчанию - 50

    # Фильтрация по статусу
    if request.user.is_staff or request.user.is_superuser:
        vacancy_applications = VacancyApplications.objects.exclude(status__in=[1, 2])
    else:
        vacancy_applications = VacancyApplications.objects.exclude(status__in=[1, 2])
        vacancy_applications = vacancy_applications.filter(creator=request.user)

    if status_filter:
        vacancy_applications = vacancy_applications.filter(status=status_filter)

    if date_submitted_start:
        start_datetime = parse_datetime(date_submitted_start).replace(hour=0, minute=0, second=0, microsecond=0)
        vacancy_applications = vacancy_applications.filter(date_submitted__gte=start_datetime)

    if date_submitted_end:
        end_datetime = parse_datetime(date_submitted_end).replace(hour=23, minute=59, second=59, microsecond=0)
        vacancy_applications = vacancy_applications.filter(date_submitted__lte=end_datetime)

    # Применяем пагинацию
    paginator = VacancyApplicationsPagination()
    paginator.page_size = limit  # Устанавливаем размер страницы
    result_page = paginator.paginate_queryset(vacancy_applications, request)

    # Сериализация данных
    serializer = VacancyApplicationsSerializer(result_page, many=True)

    # Возвращаем результаты с пагинацией
    return paginator.get_paginated_response(serializer.data)


# GET одна запись (поля заявки + ее услуги). При получении заявки возвращется список ее услуг с картинками
@swagger_auto_schema(
    method='get',
    responses={
        status.HTTP_200_OK: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "vacancy_application": openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "app_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="Уникальный идентификатор заявки."),
                        "status": openapi.Schema(type=openapi.TYPE_INTEGER, description="Статус заявки."),
                        "date_created": openapi.Schema(type=openapi.TYPE_STRING, format="date-time", description="Дата и время создания заявки."),
                        "creator": openapi.Schema(type=openapi.TYPE_STRING, description="Имя пользователя, создавшего заявку."),
                        "moderator": openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description="Имя модератора заявки (если есть)."),
                        "date_submitted": openapi.Schema(type=openapi.TYPE_STRING, format="date-time", nullable=True, description="Дата отправки заявки."),
                        "date_completed": openapi.Schema(type=openapi.TYPE_STRING, format="date-time", nullable=True, description="Дата завершения заявки."),
                        "vacancy_name": openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description="Название вакансии."),
                        "vacancy_responsibilities": openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description="Обязанности вакансии."),
                        "vacancy_requirements": openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description="Требования вакансии."),
                        "duration_days": openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True, description="Продолжительность обработки заявки в днях."),
                    },
                ),
                "cities": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "city_id": openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "city_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                    "name": openapi.Schema(type=openapi.TYPE_STRING, nullable=False),
                                    "population": openapi.Schema(type=openapi.TYPE_STRING, nullable=False),
                                    "salary": openapi.Schema(type=openapi.TYPE_STRING, nullable=False),
                                    "unemployment_rate": openapi.Schema(type=openapi.TYPE_STRING, nullable=False),
                                    "description": openapi.Schema(type=openapi.TYPE_STRING, nullable=False),
                                    "url": openapi.Schema(type=openapi.TYPE_STRING),
                                },
                            ),
                            "count": openapi.Schema(type=openapi.TYPE_INTEGER, description="Количество записей для данного города."),
                        },
                    ),
                    description="Список городов, привязанных к заявке."
                ),
            },
        ),
        status.HTTP_404_NOT_FOUND: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "Ошибка": openapi.Schema(type=openapi.TYPE_STRING, description="Сообщение об ошибке.")
            },
        ),
    }
)
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
    cities_serializer = CitiesVacancyApplicationsSerializer(cities_vacancy_applications, many=True, fields=["city_id", "count"])

    response_data = {
        'vacancy_application': vacancy_application_serializer.data,
        'cities': cities_serializer.data
    }

    return Response(response_data, status=status.HTTP_200_OK)


# PUT изменения полей заявки по теме
@swagger_auto_schema(
    method='put',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'vacancy_name': openapi.Schema(type=openapi.TYPE_STRING, example="Senior Developer"),
            'vacancy_responsibilities': openapi.Schema(type=openapi.TYPE_STRING, example="Develop new features and maintain existing ones"),
            'vacancy_requirements': openapi.Schema(type=openapi.TYPE_STRING, example="3+ years experience in React and Node.js"),
        }
    ),
    responses={
        status.HTTP_200_OK: VacancyApplicationsSerializer,
        status.HTTP_400_BAD_REQUEST: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "Ошибка": openapi.Schema(type=openapi.TYPE_STRING, example="Нет данных для обновления или поля не разрешены."),
            },
        ),
        status.HTTP_404_NOT_FOUND: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "Ошибка": openapi.Schema(type=openapi.TYPE_STRING, example="Заявка на создание вакансии не найдена."),
            },
        ),
    }
)
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
@swagger_auto_schema(
    method='put',
    responses={
        status.HTTP_200_OK: VacancyApplicationsSerializer,
        status.HTTP_400_BAD_REQUEST: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "Ошибка": openapi.Schema(type=openapi.TYPE_STRING, example="Не заполнены данные о вакансии."),
            },
        ),
        status.HTTP_404_NOT_FOUND: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "Ошибка": openapi.Schema(type=openapi.TYPE_STRING, example="Заявка на создание вакансии не найдена."),
            },
        ),
        status.HTTP_405_METHOD_NOT_ALLOWED: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "Ошибка": openapi.Schema(type=openapi.TYPE_STRING, example="Заявку нельзя изменить, так как она не в статусе 'Черновик'."),
            },
        ),
    }
)
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
    vacancy_application.date_submitted = timezone.now()
    vacancy_application.save()

    serializer = VacancyApplicationsSerializer(vacancy_application, many=False)
    return Response(serializer.data, status=status.HTTP_200_OK)


# PUT завершить/отклонить модератором. При завершить/отклонении заявки проставляется модератор и дата завершения. Одно из доп. полей заявки или м-м рассчитывается при завершении заявки (вычисление стоимости заказа, даты доставки в течении месяца, вычисления в м-м).
@swagger_auto_schema(
    method='put',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'status': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description="Новый статус заявки (4 - Завершена, 5 - Отклонена)",
                example=4
            ),
        },
        required=['status']
    ),
    responses={
        status.HTTP_200_OK: VacancyApplicationsSerializer,
        status.HTTP_400_BAD_REQUEST: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "Ошибка": openapi.Schema(type=openapi.TYPE_STRING, example="Неверные данные или обязательные поля не заполнены."),
            },
        ),
        status.HTTP_404_NOT_FOUND: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "Ошибка": openapi.Schema(type=openapi.TYPE_STRING, example="Заявка на создание вакансии не найдена."),
            },
        ),
        status.HTTP_405_METHOD_NOT_ALLOWED: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "Ошибка": openapi.Schema(type=openapi.TYPE_STRING, example="Заявка ещё не сформирована или статус не разрешён."),
            },
        ),
    }
)
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
        return Response({"Ошибка": "Заявка ещё не сформирована"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    vacancy_application.date_completed = timezone.now()
    vacancy_application.status = request_status
    vacancy_application.moderator = request.user
    vacancy_application.duration_days = random.randint(1, 30)

    vacancy_application.save()

    serializer = VacancyApplicationsSerializer(vacancy_application, many=False)

    return Response(serializer.data)


# DELETE удаление (дата формирования)
@api_view(["DELETE"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def DeleteVacancyApplication(request, app_id):
    try:
        vacancy_application = VacancyApplications.objects.get(app_id=app_id)
    except VacancyApplications.DoesNotExist:
        return Response({"Ошибка": "Заявка на создание вакансии не найдена"}, status=status.HTTP_404_NOT_FOUND)

    """if vacancy_application.status == 1:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)"""

    vacancy_application.status = 2
    vacancy_application.save()

    serializer = VacancyApplicationsSerializer(vacancy_application, many=False)

    return Response(serializer.data)


# Домен м-м
# DELETE удаление из заявки (без PK м-м)
@api_view(["DELETE"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def DeleteCityFromVacancyApplication(request, app_id, city_id):
    try:
        city_vacancy_application = CitiesVacancyApplications.objects.get(app_id=app_id, city_id=city_id)
    except CitiesVacancyApplications.DoesNotExist:
        return Response({"Ошибка": "Связь между городом и заявкой не найдена"}, status=status.HTTP_404_NOT_FOUND)

    # Сохраняем ID заявки перед удалением связи
    vacancy_application = VacancyApplications.objects.get(app_id=app_id)

    if request.user.is_staff == False or request.user.is_superuser == False:
        if vacancy_application.creator != request.user or vacancy_application.status != 1:
            return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)

    # Удаляем связь
    city_vacancy_application.delete()

    """"# Проверяем, остались ли еще города в этой заявке
    city_vacancy_application = CitiesVacancyApplications.objects.filter(app_id=app_id)
    if not city_vacancy_application.exists():  # Если больше нет городов
        vacancy_application.status = 2
        vacancy_application.save()
        return Response({"detail": "Пустая заявка удалена"}, status=status.HTTP_200_OK)"""

    # Сериализуем обновлённую заявку
    serializer = CitiesVacancyApplicationsSerializer(city_vacancy_application, many=False)

    # Возвращаем обновлённые данные заявки
    return Response(serializer.data, status=status.HTTP_200_OK)


# PUT изменение количества/порядка/значения в м-м (без PK м-м)
@swagger_auto_schema(
    method='put',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'count': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description="Количество вакансий для данного города в заявке.",
                example=1
            ),
        },
        required=['count']
    ),
    responses={
        status.HTTP_200_OK: CitiesVacancyApplicationsSerializer,
        status.HTTP_400_BAD_REQUEST: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "Ошибка": openapi.Schema(type=openapi.TYPE_STRING, example="Количество не предоставлено"),
            },
        ),
        status.HTTP_403_FORBIDDEN: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "detail": openapi.Schema(type=openapi.TYPE_STRING, example="You do not have permission to perform this action."),
            },
        ),
        status.HTTP_404_NOT_FOUND: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "Ошибка": openapi.Schema(type=openapi.TYPE_STRING, example="Связь между городом и заявкой не найдена"),
            },
        ),
    }
)
@api_view(["PUT"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def UpdateVacancyApplication(request, app_id, city_id):
    try:
        city_vacancy_application = CitiesVacancyApplications.objects.get(app_id=app_id, city_id=city_id)
    except CitiesVacancyApplications.DoesNotExist:
        return Response({"Ошибка": "Связь между городом и заявкой не найдена"}, status=status.HTTP_404_NOT_FOUND)

    vacancy_application = VacancyApplications.objects.get(app_id=app_id)

    if request.user.is_staff == False or request.user.is_superuser == False:
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
    # Проверяем, существует ли пользователь
    if not User.objects.filter(id=user_id).exists():
        return Response({"detail": "Пользователь не найден."}, status=status.HTTP_404_NOT_FOUND)

    user = User.objects.get(id=user_id)

    # Проверяем права доступа
    if not request.user.is_superuser and user != request.user:
        return Response({"detail": "You don not have permission to do this action."}, status=status.HTTP_403_FORBIDDEN)

    data = request.data
    if 'password' in data:
        # Хэшируем пароль перед сохранением
        user.set_password(data['password'])
        data.pop('password', None)

    # Создаем сериализатор с partial=True для частичного обновления
    serializer = UserSerializer(user, data=data, partial=True)

    # Проверяем валидность данных
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Сохраняем обновленные данные
    serializer.save()

    return Response(serializer.data, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    """Класс, описывающий методы работы с пользователями
    Осуществляет связь с таблицей пользователей в базе данных
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    model_class = User

    http_method_names = ['create', 'list', 'get', 'post', 'delete']

    def get_permissions(self):
        if self.action in ['create']:
            permission_classes = [AllowAny]
        elif self.action in ['list']:
            permission_classes = [IsManager | IsAdmin]
        else:
            permission_classes = [IsAdmin]
        return [permission() for permission in permission_classes]

    @swagger_auto_schema(
        operation_description="Регистрация нового пользователя (только username и password)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='Имя пользователя'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Пароль пользователя', minLength=8),
            },
            required=['username', 'password']
        ),
        responses={
            200: openapi.Response('Успешная регистрация'),
            400: openapi.Response('Ошибка регистрации, например, если пользователь с таким username уже существует'),
        }
    )
    @authentication_classes([CsrfExemptSessionAuthentication])
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
@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'username': openapi.Schema(type=openapi.TYPE_STRING, description="Имя пользователя"),
            'password': openapi.Schema(type=openapi.TYPE_STRING, description="Пароль пользователя"),
        },
        required=['username', 'password']
    ),
    responses={
        status.HTTP_200_OK: openapi.Response(
            description="Успешная аутентификация",
            schema=UserSerializer
        ),
        status.HTTP_400_BAD_REQUEST: openapi.Response(
            description="Ошибка аутентификации, неверные данные",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                    "error": openapi.Schema(type=openapi.TYPE_STRING, example="Неверное имя пользователя или пароль."),
                },
            ),
        ),
        status.HTTP_409_CONFLICT: openapi.Response(
            description="Ошибка в данных пользователя",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                    "error": openapi.Schema(type=openapi.TYPE_STRING, example="Ошибка в данных пользователя."),
                },
            ),
        ),
    }
)
@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(request, username=username, password=password)

    if user is not None:
        random_key = str(uuid.uuid4())
        session_storage.set(random_key, username)

        serializer = UserSerializer(user, data=request.data, many=False, partial=True)

        if not serializer.is_valid():
            return Response(
                {"success": False, "error": "Ошибка в данных пользователя."},
                status=status.HTTP_409_CONFLICT
            )

        user_data = serializer.data
        response = Response(user_data, status=status.HTTP_200_OK)
        response.set_cookie('session_id', random_key)
        return response
    else:
        return Response(
            {"success": False, "error": "Неверное имя пользователя или пароль."},
            status=status.HTTP_400_BAD_REQUEST
        )


#@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([CsrfExemptSessionAuthentication])
def logout_view(request):

    session_id = request.COOKIES.get('session_id')

    if session_id:
        session_storage.delete(session_id)

        response = Response({'status': 'Success'}, status=200)
        response.delete_cookie('session_id')

        logout(request)

        request.user = AnonymousUser()

        return response
    else:
        return Response({'status': 'Error', 'message': 'No active session'}, status=400)


# Connect to our Redis instance
session_storage = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)