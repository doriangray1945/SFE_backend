from rest_framework.response import Response
from rest_framework import status
from app.serializers import *
from rest_framework.decorators import api_view
from .minio import add_pic
from app.models import *
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.contrib.auth import authenticate, logout


def GetCurrentUser():
    return User.objects.filter(is_superuser=False).first()


def GetModerator():
    return User.objects.filter(is_superuser=True).first()


def GetDraftVacancyApplication():
    current_user = GetCurrentUser()
    return VacancyApplications.objects.filter(creator=current_user.id, status=1).first()  # так как у пользователя только один черновик, то берем первый элемент, иначе None


#ДОМЕН УСЛУГИ
# GET список с фильтрацией. В списке услуг возвращается id заявки-черновика этого пользователя для страницы заявки и количество услуг в этой заявке
@api_view(["GET"])
def CitiesList(request):
    city_name = request.GET.get("city_name", '')
    cities = Cities.objects.filter(status=1, name__istartswith=city_name)
    serializer = CitiesSerializer(cities, many=True)

    if GetDraftVacancyApplication():
        app_id = GetDraftVacancyApplication().app_id
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

    serializer = CitiesSerializer(city, data=city_data, partial=True)
    serializer.is_valid(raise_exception=True)
    edited_city = serializer.save()

    # Обработка изменения изображения, если оно предоставлено
    pic = request.FILES.get("image")
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


# Домен м-м
# DELETE удаление из заявки (без PK м-м)
@api_view(["DELETE"])
def DeleteCityFromVacancyApplication(request, mm_id):
    try:
        city_vacancy_application = CitiesVacancyApplications.objects.get(mm_id=mm_id)
    except CitiesVacancyApplications.DoesNotExist:
        return Response({"Ошибка": "Связь между городом и заявкой не найдена"}, status=status.HTTP_404_NOT_FOUND)

    # Сохраняем ID заявки перед удалением связи
    app_id = city_vacancy_application.app_id_id

    # Удаляем связь
    city_vacancy_application.delete()

    # Обновляем данные заявки
    try:
        vacancy_application = VacancyApplications.objects.get(app_id=app_id)
    except VacancyApplications.DoesNotExist:
        return Response({"Ошибка": "Заявка на создание вакансии не найдена после удаления города"}, status=status.HTTP_404_NOT_FOUND)

    # Сериализуем обновлённую отправку
    serializer = VacancyApplicationsSerializer(vacancy_application, many=False)

    # Возвращаем обновлённые данные отправки
    return Response(serializer.data, status=status.HTTP_200_OK)


# PUT изменение количества/порядка/значения в м-м (без PK м-м)
@api_view(["PUT"])
def UpdateVacancyApplication(request, mm_id):
    try:
        city_vacancy_application = CitiesVacancyApplications.objects.get(mm_id=mm_id)
    except CitiesVacancyApplications.DoesNotExist:
        return Response({"Ошибка": "Связь между городом и заявкой не найдена"}, status=status.HTTP_404_NOT_FOUND)

    count = request.data.get("count")

    if count is not None:
        city_vacancy_application.count = count
        city_vacancy_application.save()
        serializer = CitiesVacancyApplicationsSerializer(city_vacancy_application, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response({"Ошибка": "Количество не предоставлено"}, status=status.HTTP_400_BAD_REQUEST)


# Домен пользователь
# POST регистрация
@api_view(["POST"])
def register(request):
    serializer = UserRegisterSerializer(data=request.data)

    # Проверка валидности данных
    if not serializer.is_valid():
        return Response({"Ошибка": "Некорректные данные"}, status=status.HTTP_400_BAD_REQUEST)

    # Сохранение нового пользователя
    user = serializer.save()

    # Сериализация и возврат данных нового пользователя
    serializer = UserSerializer(user)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# PUT пользователя (личный кабинет)
@api_view(["PUT"])
def UpdateUser(request, user_id):
    if not User.objects.filter(id=user_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    user = User.objects.get(id=user_id)
    serializer = UserSerializer(user, data=request.data, many=False, partial=True)

    if not serializer.is_valid():
        return Response(status=status.HTTP_409_CONFLICT)

    serializer.save()

    return Response(serializer.data)


# POST аутентификация
@api_view(["POST"])
def login(request):
    serializer = UserLoginSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

    user = authenticate(**serializer.data)
    if user is None:
        return Response(status=status.HTTP_401_UNAUTHORIZED)

    return Response(status=status.HTTP_200_OK)


# POST деавторизация
@api_view(["POST"])
def logout_view(request):
    # request.user.auth_token.delete()
    logout(request)

    return Response(status=status.HTTP_200_OK)