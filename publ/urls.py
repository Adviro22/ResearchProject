from django.urls import re_path
from publ import publicaciones

urlpatterns = [
    re_path(r'^publicaciones', publicaciones.view, name='publicaciones'),
]
