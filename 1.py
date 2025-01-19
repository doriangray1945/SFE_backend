import sys
import os
import django

# Указываем путь к настройкам вашего проекта Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'labs.settings')

# Инициализируем Django
django.setup()
from django.utils import timezone
from datetime import timedelta
import random
from faker import Faker
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '', 'app')))
from django.contrib.auth.models import User, AnonymousUser
from app.models import VacancyApplications  # Импортируйте модель VacancyApplications

fake = Faker()

# Генерация случайных данных для новой заявки
def generate_vacancy_application():
    # Генерация случайных данных для вакансии
    creator = random.choice(User.objects.all())  # выбираем случайного пользователя как создателя
    status = random.choice([3, 4, 5])  # случайный статус
    date_created = fake.date_this_decade()  # дата создания заявки
    date_submitted = date_created + timedelta(days=random.randint(1, 5)) if random.random() > 0.3 else None
    date_completed = date_created + timedelta(days=random.randint(6, 15)) if random.random() > 0.5 else None
    moderator = None
    duration_days = None

    if date_submitted is None:
        # Если date_submitted = null, то остальные поля тоже должны быть null
        date_completed = None
        moderator = None
        duration_days = None
    else:
        # Если date_submitted не null, остальные поля могут быть null
        if date_completed is None:
            # Если date_completed = null, то модератор и duration_days могут быть null
            moderator = random.choice(User.objects.all()) if random.random() > 0.2 else None
            duration_days = random.randint(1, 30) if random.random() > 0.3 else None
        else:
            # Если date_completed не null, то moderator и duration_days должны быть не null
            moderator = random.choice(User.objects.all())  # случайный модератор
            duration_days = random.randint(1, 30)  # случайная длительность

    # Данные о вакансии
    vacancy_name = fake.job()
    vacancy_responsibilities = fake.sentence()
    vacancy_requirements = fake.sentence()

    # Создание и сохранение записи в модели VacancyApplications
    application = VacancyApplications(
        status=status,
        date_created=date_created,
        creator=creator,
        date_submitted=date_submitted,
        date_completed=date_completed,
        moderator=moderator,
        vacancy_name=vacancy_name,
        vacancy_responsibilities=vacancy_responsibilities,
        vacancy_requirements=vacancy_requirements,
        duration_days=duration_days
    )
    application.save()

# Генерация 100000 заявок и сохранение в базу данных
for _ in range(50000):
    generate_vacancy_application()
