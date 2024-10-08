from django.contrib import admin
from .models import *

admin.site.register(Applications)
admin.site.register(Cities)
admin.site.register(CitiesApplications)