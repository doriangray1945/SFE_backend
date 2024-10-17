from django.contrib import admin
from .models import *


admin.site.register(VacancyApplications)
admin.site.register(Cities)
admin.site.register(CitiesVacancyApplications)

