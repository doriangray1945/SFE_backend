from app.models import Cities, VacancyApplications, CitiesVacancyApplications
from app.models import AuthUser
from rest_framework import serializers


class CitiesSerializer(serializers.ModelSerializer):
    """# StringRelatedField вернет строковое представление объекта, то есть его имя"""
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Cities
        #fields = '__all__'
        fields = ["city_id", "name", "population", "salary", "unemployment_rate", "description", "url", "status", "user"]


class VacancyApplicationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacancyApplications
        fields = "__all__"


class CitiesVacancyApplicationsSerializer(serializers.ModelSerializer):
    city_id = CitiesSerializer()  # Включаем сериализатор для города
    count = serializers.IntegerField()  # Количество услуг для города

    class Meta:
        model = CitiesVacancyApplications
        fields = ['city_id', 'count']


class UserSerializer(serializers.ModelSerializer):
    cities_set = CitiesSerializer(many=True, read_only=True)

    class Meta:
        model = AuthUser
        fields = ["id", "first_name", "last_name", "cities_set"]


