from app.models import Cities, VacancyApplications, CitiesVacancyApplications
from app.models import AuthUser
from rest_framework import serializers


class CitiesSerializer(serializers.ModelSerializer):
    # StringRelatedField вернет строковое представление объекта, то есть его имя
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Cities
        # Сериализуем все поля
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    cities_set = CitiesSerializer(many=True, read_only=True)

    class Meta:
        model = AuthUser
        fields = ["id", "first_name", "last_name", "cities_set"]


