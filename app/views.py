from rest_framework.response import Response
from rest_framework import status
from app.serializers import *
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from .minio import add_pic


from django.shortcuts import render, get_object_or_404
from app.models import *
from django.contrib.auth.models import User
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db import connection
from django.utils.dateparse import parse_datetime


"""
def GetCurrentUser():
    return User.objects.filter(is_superuser=False).first()


def GetDraftApplication():
    current_user = GetCurrentUser()
    return Applications.objects.filter(creator=current_user.id, status=1).first()  # так как у пользователя только один черновик, то берем первый элемент, иначе None


def GetAppCitiesCount(app_id):
    return CitiesApplications.objects.filter(app_id=app_id).count()


def GetCities(request):
    search_name = request.GET.get("search_name", "")
    cities = Cities.objects.filter(name__istartswith=search_name, status=1)

    context = {
        "search_name": search_name,  # запоминание ввода для поиска
        "cities": cities
    }

    # Получаем черновик заявки (без привязки к пользователю)
    draft_application = GetDraftApplication()
    if draft_application:
        context["cities_count"] = GetAppCitiesCount(draft_application.app_id)
        context["draft_application"] = draft_application
    else:
        context["draft_application"] = None
        context["cities_count"] = 0  # Например, можно установить 0, если черновик отсутствует

    return render(request, "home_page.html", context)


def GetCityById(city_id):
    return get_object_or_404(Cities, city_id=city_id, status=1)


def city(request, city_id):
    context = {
        "city_id": city_id,  # Используем city_id из объекта
        "city": GetCityById(city_id)
    }

    return render(request, "city_page.html", context)


def GetApplicationById(app_id):
    return get_object_or_404(Applications, app_id=app_id, status=1)


def application(request, app_id):
    cities_applications = CitiesApplications.objects.filter(app_id=app_id)
    cities_ids = cities_applications.values_list('city_id', flat=True)
    cities = Cities.objects.filter(city_id__in=cities_ids, status=1)

    cities_with_count = {}
    for item in cities_applications:
        cities_with_count[item.city_id.city_id] = item.count

    cities_list = []
    for city in cities:
        cities_list.append({
            'item': city,
            'count': cities_with_count.get(city.city_id)  # Получаем значение count для данного города
        })

    context = {
        "application": GetApplicationById(app_id),
        "cities": cities_list
    }

    return render(request, "application_page.html", context)


def add_city_to_draft(request):
    if request.method == 'POST':
        city_id = request.POST.get('city_id')
        draft_application = GetDraftApplication()

        # если черновика нет, создаем новый
        if draft_application is None:
            draft_application = Applications.objects.create(
                date_created=timezone.now(),  # Время создания
                creator=GetCurrentUser(),  # Создатель заявки
                status=1,  # Статус "Действует"
                submitted=timezone.now(),  # Установим время подачи
                completed=None,  # Если не завершена, то None
                moderator=None,  # Если не модератор, то None
                vacancy={
                    "name": "Врач-невролог",
                    "requirements": "высшее медицинское образование, опыт работы не менее 3-х лет по специальности, клиентоориентированность",
                    "responsibilities": "оказание квалифицированной лечебно-профилактической помощи детям, ведение амбулаторного приема"
                }
            )

        # есть ли уже этот город в черновике
        existing_entry = CitiesApplications.objects.filter(app_id=draft_application, city_id=city_id).first()

        if existing_entry:
            # увеличиваем, если город уже есть в заявке
            existing_entry.count += 1
            existing_entry.save()
        else:
            # если города нет в заявке, создаем новую запись
            CitiesApplications.objects.create(
                app_id=draft_application,
                city_id=Cities.objects.get(city_id=city_id),
                count=1  # Начинаем с 1
            )

        return HttpResponseRedirect(reverse('home_page'))

    return HttpResponseRedirect(reverse('home_page'))


def delete_application(request):
    if request.method == 'POST':
        app_id = request.POST.get('app_id')

        # проверяем, существует ли заявка с таким ID
        application = Applications.objects.filter(app_id=app_id).first()
        if application:
            # выполняем SQL-запрос для изменения статуса заявки на "Удалена"
            with connection.cursor() as cursor:
                cursor.execute("UPDATE applications SET status = 2 WHERE app_id = %s", [app_id])

        return HttpResponseRedirect(reverse('home_page'))"""


# Лаб 3
def user():
    try:
        user1 = AuthUser.objects.get(id=1)
    except:
        user1 = AuthUser(id=1, first_name="Иван", last_name="Иванов", password=1234, username="user1")
        user1.save()
    return user1


def GetCurrentUser():
    return User.objects.filter(is_superuser=False).first()


def GetModerator():
    return User.objects.filter(is_superuser=True).first()


def GetDraftVacancyApplication():
    current_user = GetCurrentUser()
    return VacancyApplications.objects.filter(creator=current_user.id, status=1).first()  # так как у пользователя только один черновик, то берем первый элемент, иначе None


#ДОМЕН УСЛУГИ
# GET список. В списке услуг возвращается id заявки-черновика этого пользователя для страницы заявки в статусе черновик
@api_view(["GET"])
def CitiesList(request):
    city_name = request.GET.get('city_name', '')
    cities = Cities.objects.filter(status=1, name__istartswith=city_name)
    serializer = CitiesSerializer(cities, many=True)
    draft_vacancy_application = GetDraftVacancyApplication().app_id
    response = {
        "cities": serializer.data,
        "draft_vacancy_application": draft_vacancy_application
    }
    return Response(response, status=status.HTTP_200_OK)


# GET одна запись
@api_view(["GET"])
def GetCityById(request, city_id):
    try:
        city = Cities.objects.get(city_id=city_id, status=1)
    except Cities.DoesNotExist:
        return Response({"Ошибка": "Город не найден"}, status=status.HTTP_404_NOT_FOUND)

    serializer = CitiesSerializer(city, many=False)

    return Response(serializer.data, status=status.HTTP_200_OK)


# POST добавление
@api_view(["POST"])
def CreateCity(request):
    city_data = request.data.copy()
    city_data.pop('image', None)

    serializer = CitiesSerializer(data=city_data)
    serializer.is_valid(raise_exception=True)  # Проверка валидности с автоматической обработкой ошибок
    new_city = serializer.save()  # Сохраняем новую деталь
    # Обновляем и возвращаем данные с новой деталью
    return Response(CitiesSerializer(new_city).data, status=status.HTTP_201_CREATED)


# PUT изменение
@api_view(["PUT"])
def EditCity(request, city_id):
    try:
        city = Cities.objects.get(city_id=city_id)
    except Cities.DoesNotExist:
        return Response({"Ошибка": "Город не найден"}, status=status.HTTP_404_NOT_FOUND)

    city_data = request.data.copy()
    city_data.pop('image', None)

    serializer = CitiesSerializer(city, data=city_data)
    serializer.is_valid(raise_exception=True)
    edited_city = serializer.save()

    # Обработка изменения изображения, если оно предоставлено
    pic = request.FILES.get("pic")
    if pic:
        pic_result = add_pic(edited_city, pic)
        if 'error' in pic_result.data:
            return pic_result  # Возвращаем ошибку, если загрузка изображения не удалась

    # Возвращаем обновлённые данные детали
    return Response(CitiesSerializer(edited_city).data, status=status.HTTP_200_OK)


# DELETE удаление. Удаление изображения встроено в метод удаления услуги
@api_view(["DELETE"])
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
@api_view(["POST"])
def AddCityToDraft(request, city_id):
    try:
        city = Cities.objects.get(city_id=city_id)
    except Cities.DoesNotExist:
        return Response({"error": "Город не найден"}, status=status.HTTP_404_NOT_FOUND)

    draft_vacancy_application = GetDraftVacancyApplication()

    # если черновика нет, создаем новый
    if draft_vacancy_application is None:
        draft_vacancy_application = VacancyApplications.objects.create(
            date_created=timezone.now(),  # Время создания
            creator=GetCurrentUser(),  # Создатель заявки
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
@api_view(["POST"])
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
def VacancyApplicationsList(request):
    status = int(request.GET.get("status", 0))
    date_submitted_start = request.GET.get("date_submitted_start")
    date_submitted_end = request.GET.get("date_submitted_end")

    vacancy_applications = VacancyApplications.objects.exclude(status__in=[1, 2])

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
def GetVacancyApplicationById(request, app_id):
    try:
        vacancy_application = VacancyApplications.objects.get(app_id=app_id)
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
@api_view(["PUT"])
def UpdateVacancyApplication(request, app_id):
    try:
        vacancy_application = VacancyApplications.objects.get(app_id=app_id)
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
@api_view(["PUT"])
def UpdateStatusUser(request, app_id):
    try:
        vacancy_application = VacancyApplications.objects.get(app_id=app_id)
    except VacancyApplications.DoesNotExist:
        return Response({"Ошибка": "Заявка на создание вакансии не найдена"}, status=status.HTTP_404_NOT_FOUND)

    if vacancy_application.status == 1:
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
@api_view(["PUT"])
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

    vacancy_application.completed = timezone.now()
    vacancy_application.status = request_status
    vacancy_application.moderator = GetModerator()
    vacancy_application.save()

    serializer = VacancyApplicationsSerializer(vacancy_application, many=False)

    return Response(serializer.data)


# DELETE удаление (дата формирования)
@api_view(["DELETE"])
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
