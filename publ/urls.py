from django.urls import re_path, path
from publ import publicaciones

urlpatterns = [
    path('', publicaciones.view_index, name='index'),
    re_path(r'^publicaciones', publicaciones.view, name='publicaciones'),
]
