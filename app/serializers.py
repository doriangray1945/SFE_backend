from .models import *
from rest_framework import serializers
from django.contrib.auth.models import User



class CitiesSerializer(serializers.ModelSerializer):
    """# StringRelatedField вернет строковое представление объекта, то есть его имя
    user = serializers.StringRelatedField(read_only=True)"""
    #count = serializers.SerializerMethodField()

    class Meta:
        model = Cities
        #fields = '__all__'
        fields = ["city_id", "name", "population", "salary", "unemployment_rate", "description", "url"]


class VacancyApplicationsSerializer(serializers.ModelSerializer):
    creator = serializers.SlugRelatedField(slug_field='username', queryset=User.objects.all())
    moderator = serializers.SlugRelatedField(slug_field='username', queryset=User.objects.all())

    class Meta:
        model = VacancyApplications
        fields = "__all__"


class CitiesVacancyApplicationsSerializer(serializers.ModelSerializer):
    city_id = CitiesSerializer()
    count = serializers.IntegerField()

    class Meta:
        model = CitiesVacancyApplications
        fields = ["app_id", "city_id", "count"]

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop('fields', None)  # Получаем список полей из аргументов
        super().__init__(*args, **kwargs)
        if fields is not None:
            # Оставляем только указанные поля
            allowed = set(fields)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class UserSerializer(serializers.ModelSerializer):
    is_staff = serializers.BooleanField(default=False, required=False)
    is_superuser = serializers.BooleanField(default=False, required=False)

    class Meta:
        #model = CustomUser
        #fields = ("id", "email", "password", "first_name", "last_name", "date_joined", "password", "username") # Для PUT пользователя
        model = User
        fields = ("id", "email", "password", "first_name", "last_name", "date_joined", "username", "is_staff", "is_superuser") # Для PUT пользователя
