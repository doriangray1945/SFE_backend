from django.shortcuts import render, get_object_or_404
from app.models import Cities, VacancyApplications, CitiesVacancyApplications
from django.contrib.auth.models import User
from django.utils import timezone

from django.http import HttpResponseRedirect
from django.urls import reverse

from django.db import connection


def GetCurrentUser():
    return User.objects.filter(is_superuser=False).first()


def GetDraftVacancyApplication():
    current_user = GetCurrentUser()
    return VacancyApplications.objects.filter(creator=current_user.id, status=1).first()  # так как у пользователя только один черновик, то берем первый элемент, иначе None


def GetAppCitiesCount(app_id):
    return CitiesVacancyApplications.objects.filter(app_id=app_id).count()


def GetCities(request):
    city_name = request.GET.get("city_name", "")
    cities = Cities.objects.filter(name__istartswith=city_name, status=1)

    context = {
        "city_name": city_name,  # запоминание ввода для поиска
        "cities": cities
    }

    # Получаем черновик заявки (без привязки к пользователю)
    draft_vacancy_application = GetDraftVacancyApplication()
    if draft_vacancy_application:
        context["cities_count"] = GetAppCitiesCount(draft_vacancy_application.app_id)
        context["draft_vacancy_application"] = draft_vacancy_application
    else:
        context["draft_vacancy_application"] = None
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


def GetVacancyApplicationById(app_id):
    try:
        return VacancyApplications.objects.get(app_id=app_id, status=1)
    except VacancyApplications.DoesNotExist:
        return None


def vacancy_application(request, app_id):
    vacancy_application = GetVacancyApplicationById(app_id)
    if not vacancy_application:
        return HttpResponseRedirect(reverse('home_page'))

    cities_vacancy_applications = CitiesVacancyApplications.objects.filter(app_id=app_id)
    cities_ids = cities_vacancy_applications.values_list('city_id', flat=True)
    cities = Cities.objects.filter(city_id__in=cities_ids, status=1)

    cities_with_count = {}
    for item in cities_vacancy_applications:
        cities_with_count[item.city_id.city_id] = item.count

    cities_list = []
    for city in cities:
        cities_list.append({
            'item': city,
            'count': cities_with_count.get(city.city_id)  # Получаем значение count для данного города
        })

    context = {
        "vacancy_application": vacancy_application,
        "cities": cities_list
    }

    return render(request, "vacancy_application_page.html", context)


def add_city_to_draft(request):
    if request.method == 'POST':
        city_id = request.POST.get('city_id')
        draft_vacancy_application = GetDraftVacancyApplication()

        # если черновика нет, создаем новый
        if draft_vacancy_application is None:
            draft_vacancy_application = VacancyApplications.objects.create(
                date_created=timezone.now(),  # Время создания
                creator=GetCurrentUser(),  # Создатель заявки
                status=1,  # Статус "Действует"
                submitted=timezone.now(),  # Установим время подачи
                moderator=None,  # Если не модератор, то None
                vacancy_name="Врач-невролог",
                vacancy_requirements="высшее медицинское образование, опыт работы не менее 3-х лет по специальности, клиентоориентированность",
                vacancy_responsibilities="оказание квалифицированной лечебно-профилактической помощи детям, ведение амбулаторного приема"
            )

        # есть ли уже этот город в черновике
        existing_entry = CitiesVacancyApplications.objects.filter(app_id=draft_vacancy_application, city_id=city_id).first()

        if existing_entry:
            # увеличиваем, если город уже есть в заявке
            existing_entry.count += 1
            existing_entry.save()
        else:
            # если города нет в заявке, создаем новую запись
            CitiesVacancyApplications.objects.create(
                app_id=draft_vacancy_application,
                city_id=Cities.objects.get(city_id=city_id),
                count=1  # Начинаем с 1
            )

        return HttpResponseRedirect(reverse('home_page'))

    return HttpResponseRedirect(reverse('home_page'))


def delete_vacancy_application(request):
    if request.method == 'POST':
        app_id = request.POST.get('app_id')

        # проверяем, существует ли заявка с таким ID
        vacancy_application = VacancyApplications.objects.filter(app_id=app_id).first()
        if vacancy_application:
            # выполняем SQL-запрос для изменения статуса заявки на "Удалена"
            with connection.cursor() as cursor:
                cursor.execute("UPDATE vacancy_applications SET status = 2 WHERE app_id = %s", [app_id])

        return HttpResponseRedirect(reverse('home_page'))
