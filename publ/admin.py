from django.contrib import admin
from publ.models import *
from django.contrib.auth.models import Permission

admin.site.register(Permission)
admin.site.register(Pais)
admin.site.register(Provincia)
admin.site.register(Canton)
admin.site.register(Parroquia)
admin.site.register(Persona)
admin.site.register(Administrativo)
admin.site.register(PerfilUsuario)