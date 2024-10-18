from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, time

class Cities(models.Model):
    STATUS_CHOICES = [
        (1, 'Действует'),
        (2, 'Удалена')
    ]
    city_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, blank=False, null=False)
    population = models.CharField(max_length=20, blank=False, null=False)
    salary = models.CharField(max_length=10, blank=False, null=False)
    unemployment_rate = models.CharField(max_length=10, blank=False, null=False)
    description = models.CharField(max_length=500, blank=False, null=False)
    url = models.CharField(max_length=100, blank=True, null=True)
    status = models.IntegerField(choices=STATUS_CHOICES, default=1, blank=False, null=False)

    class Meta:
        managed = True
        db_table = 'cities'


class VacancyApplications(models.Model):
    STATUS_CHOICES = [
        (1, 'Черновик'),
        (2, 'Удалена'),
        (3, 'Сформирована'),
        (4, 'Завершена'),
        (5, 'Отклонена'),
    ]
    app_id = models.AutoField(primary_key=True)
    status = models.IntegerField(choices=STATUS_CHOICES, default=1, blank=False, null=False)
    date_created = models.DateTimeField(blank=False, null=False)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_applications', blank=False, null=False)

    submitted = models.DateTimeField(blank=True, null=True)
    completed = models.DateTimeField(blank=True, null=True)
    moderator = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='moderated_applications',blank=True, null=True)

    vacancy_name = models.TextField(blank=True, null=True)
    vacancy_responsibilities = models.TextField(blank=True, null=True)
    vacancy_requirements = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'vacancy_applications'

    def GetCities(self):
        return CitiesVacancyApplications.objects.filter(app=self).values_list('cities', flat=True)


class CitiesVacancyApplications(models.Model):
    mm_id = models.AutoField(primary_key=True)
    city_id = models.ForeignKey('Cities', models.DO_NOTHING, blank=False, null=False)
    app_id = models.ForeignKey('VacancyApplications', models.DO_NOTHING, blank=False, null=False)
    count = models.IntegerField(default=1, blank=False, null=False)

    class Meta:
        managed = True
        db_table = 'cities_vacancy_applications'
        constraints = [
            models.UniqueConstraint(fields=['city_id', 'app_id'], name='unique constraint')
        ]


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField(default=False)
    username = models.CharField(unique=True, max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now=True)
    first_name = models.CharField(max_length=150)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    class Meta:
        managed = False
        db_table = 'auth_user'