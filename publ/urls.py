from django.urls import re_path, path
from publ import publicaciones

urlpatterns = [
    path('', publicaciones.view_prueba, name='index'),
    re_path(r'^publicaciones', publicaciones.view, name='publicaciones'),
    path('mood-publicaciones/', publicaciones.view_publicaciones, name='publicaciones'),
]
