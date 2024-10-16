from app.models import Cities, Applications, CitiesApplications
from app.models import AuthUser
from rest_framework import serializers


class CitiesSerializer(serializers.ModelSerializer):
    # StringRelatedField вернет строковое представление объекта, то есть его имя
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Cities
        # Сериализуем все поля
        fields = ["city_id", "name", "population", "salary", "unemployment_rate", "description", "url", "status", "user"]


class UserSerializer(serializers.ModelSerializer):
    cities_set = CitiesSerializer(many=True, read_only=True)

    class Meta:
        model = AuthUser
        fields = ["id", "first_name", "last_name", "cities_set"]


