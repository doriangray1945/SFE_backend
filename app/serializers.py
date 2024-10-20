from .models import *
from rest_framework import serializers
from django.contrib.auth.models import User
from app import views
from collections import OrderedDict


class CitiesSerializer(serializers.ModelSerializer):
    """# StringRelatedField вернет строковое представление объекта, то есть его имя
    user = serializers.StringRelatedField(read_only=True)"""
    #count = serializers.SerializerMethodField()

    class Meta:
        model = Cities
        #fields = '__all__'
        fields = ["city_id", "name", "population", "salary", "unemployment_rate", "description", "url", "status"]

    def get_fields(self):
        new_fields = OrderedDict()
        for name, field in super().get_fields().items():
            field.required = False
            new_fields[name] = field
        return new_fields

    """def get_count(self, obj):
        # Получаем черновое приложение вакансии
        draft_vacancy_application = views.GetDraftVacancyApplication()
        if draft_vacancy_application:
            city_vacancy_application = CitiesVacancyApplications.objects.filter(app_id=draft_vacancy_application.app_id, city_id=obj).first()
            if city_vacancy_application:
                return city_vacancy_application.count
        return 0  # Возвращаем 0, если чернового приложения вакансии нет"""


class VacancyApplicationsSerializer(serializers.ModelSerializer):
    #creator = serializers.SlugRelatedField(slug_field='username', queryset=User.objects.all())

    class Meta:
        model = VacancyApplications
        fields = "__all__"


class CitiesVacancyApplicationsSerializer(serializers.ModelSerializer):
    city_id = CitiesSerializer()  # Включаем сериализатор для города
    count = serializers.IntegerField()  # Количество услуг для города

    class Meta:
        model = CitiesVacancyApplications
        fields = ["mm_id", "app_id", "city_id", "count"]


"""class UserSerializer(serializers.ModelSerializer):
    cities_set = CitiesSerializer(many=True, read_only=True)

    class Meta:
        model = AuthUser
        fields = ["id", "first_name", "last_name", "cities_set"]"""


class UserSerializer(serializers.ModelSerializer):
    is_staff = serializers.BooleanField(default=False, required=False)
    is_superuser = serializers.BooleanField(default=False, required=False)
    class Meta:
        model = CustomUser
        #fields = ("id", "email", "password", "first_name", "last_name", "date_joined", "password", "username") # Для PUT пользователя
        fields = ["email", "password", "is_staff", "is_superuser"]


class UserRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "password", "first_name", "last_name", "date_joined", "password", "username")
        write_only_fields = ("password",)
        read_only_fields = ("id",)

    def create(self, validated_data):
        user = User.objects.create(
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            username=validated_data['username']
        )

        user.set_password(validated_data['password'])
        user.save()

        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)
