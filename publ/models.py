# -*- coding: UTF-8 -*-
import operator
import os
import random
import time
import sys
from datetime import datetime, timedelta, date
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User, Group
from django.contrib.sessions.models import Session
from django.db import models, connection, connections
from django.db.models import Count, PROTECT, Sum, Avg, Min, Max, F, OuterRef, Subquery, FloatField
from django.contrib.postgres.fields import JSONField
from django.db.models.query import QuerySet
from django.db.models.query_utils import Q
from django.core.files.storage import FileSystemStorage
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
import collections
from django.utils.timezone import now
from django.core.cache import cache

from publ.funciones import ModeloBase, null_to_numeric

#from sagest.models import TIPO_SOLICITUD_PUBLICACION

unicode = str

import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')


TIPO_DOCUMENTO = (
    (1, u'CÉDULA'),
    (2, u'PASAPORTE'),
    (3, u"RUC"),
)
TIPO_CELULAR = (
    (1, u'CLARO'),
    (2, u'MOVISTAR'),
    (3, u'CNT'),
    (4, u'OTRO')
)

class Sexo(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Sexo"
        verbose_name_plural = u"Sexos"
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(Sexo, self).save(*args, **kwargs)

class Pais(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u"Nombre")
    codigo = models.CharField(max_length=10, default="", verbose_name=u"Código SENESCYT")
    nacionalidad = models.CharField(default='', max_length=100, verbose_name=u"Nacionalidad")

    @staticmethod
    def flexbox_query(q, extra=None):
        if extra:
            return eval('Pais.objects.filter(Q(nombre__contains="%s") | Q(codigo__contains="%s")).filter(%s).distinct()[:25]' % (q, q, extra))
        return Pais.objects.filter(Q(nombre__contains=q) | Q(codigo__contains=q)).distinct()[:25]

    def flexbox_repr(self):
        return self.__str__()

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"País"
        verbose_name_plural = u"Paises"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def en_uso(self):
        return self.provincia_set.values('id').all().exists()

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.codigo = self.codigo.upper()
        self.nacionalidad = self.nacionalidad.upper()
        super(Pais, self).save(*args, **kwargs)

class Provincia(ModeloBase):
    pais = models.ForeignKey(Pais, blank=True, null=True, verbose_name=u'País', on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=100, verbose_name=u"Nombre")
    codigo = models.CharField(max_length=10, default="", verbose_name=u"Código SENESCYT")

    @staticmethod
    def flexbox_query(q, extra=None):
        if extra:
            return eval('Provincia.objects.filter(Q(nombre__contains="%s") | Q(codigo__contains="%s")).filter(%s).distinct()[:25]' % (q, q, extra))
        return Provincia.objects.filter(Q(nombre__contains=q) | Q(codigo__contains=q)).distinct()[:25]

    def flexbox_repr(self):
        return self.__str__()

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Provincia"
        verbose_name_plural = u"Provincias"
        ordering = ['nombre']
        unique_together = ('nombre', 'pais')

    def en_uso(self):
        return self.canton_set.values('id').all().exists()

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(Provincia, self).save(*args, **kwargs)

class Canton(ModeloBase):
    provincia = models.ForeignKey(Provincia, blank=True, null=True, verbose_name=u'Provincia', on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=100, verbose_name=u"Nombre")
    codigo = models.CharField(max_length=10, default="", verbose_name=u"Código SENESCYT")

    @staticmethod
    def flexbox_query(q, extra=None):
        if extra:
            return eval('Canton.objects.filter(Q(nombre__contains="%s") | Q(codigo__contains="%s")).filter(%s).distinct()[:25]' % (q, q, extra))
        return Canton.objects.filter(Q(nombre__contains=q) | Q(codigo__contains=q)).distinct()[:25]

    def flexbox_repr(self):
        return self.__str__()

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Canton"
        verbose_name_plural = u"Cantones"
        ordering = ['nombre']
        unique_together = ('nombre', 'provincia')

    def en_uso(self):
        return self.parroquia_set.values('id').all().exists()

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.codigo = self.codigo.upper()
        super(Canton, self).save(*args, **kwargs)

class Parroquia(ModeloBase):
    canton = models.ForeignKey(Canton, blank=True, null=True, verbose_name=u'Caton', on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    codigo = models.CharField(max_length=10, default="", verbose_name=u"Código SENESCYT")

    @staticmethod
    def flexbox_query(q, extra=None):
        if extra:
            return eval('Parroquia.objects.filter(Q(nombre__contains="%s") | Q(codigo__contains="%s")).filter(%s).distinct()[:25]' % (q, q, extra))
        return Parroquia.objects.filter(Q(nombre__contains=q) | Q(codigo__contains=q)).distinct()[:25]

    def flexbox_repr(self):
        return self.__str__()

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Parroquia"
        verbose_name_plural = u"Parroquias"
        ordering = ['nombre']
        unique_together = ('nombre', 'canton')

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(Parroquia, self).save(*args, **kwargs)


class Persona(ModeloBase):
    nombres = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    apellido1 = models.CharField(default='', max_length=50, verbose_name=u"1er Apellido")
    apellido2 = models.CharField(default='', max_length=50, verbose_name=u"2do Apellido")
    tipo_documento = models.IntegerField(choices=TIPO_DOCUMENTO, default=0, verbose_name=u'Tipo documento')
    documento = models.CharField(default='', max_length=20, verbose_name=u"Documento", blank=True, db_index=True)
    nacimiento = models.DateField(verbose_name=u"Fecha de nacimiento o constitución")
    sexo = models.ForeignKey(Sexo, default=2, verbose_name=u'Sexo', on_delete=models.CASCADE)
    paisnacimiento = models.ForeignKey(Pais, blank=True, null=True, related_name='+', verbose_name=u'País de nacimiento', on_delete=models.CASCADE)
    provincianacimiento = models.ForeignKey(Provincia, blank=True, null=True, related_name='+', verbose_name=u"Provincia de nacimiento", on_delete=models.CASCADE)
    cantonnacimiento = models.ForeignKey(Canton, blank=True, null=True, related_name='+', verbose_name=u"Canton de nacimiento", on_delete=models.CASCADE)
    parroquianacimiento = models.ForeignKey(Parroquia, blank=True, null=True, related_name='+', verbose_name=u"Parroquia de nacimiento", on_delete=models.CASCADE)
    nacionalidad = models.CharField(default='', max_length=100, verbose_name=u'Nacionalidad')
    pais = models.ForeignKey(Pais, blank=True, null=True, related_name='+', verbose_name=u'País residencia', on_delete=models.CASCADE)
    provincia = models.ForeignKey(Provincia, blank=True, null=True, related_name='+', verbose_name=u"Provincia de residencia", on_delete=models.CASCADE)
    canton = models.ForeignKey(Canton, blank=True, null=True, related_name='+', verbose_name=u"Canton de residencia", on_delete=models.CASCADE)
    parroquia = models.ForeignKey(Parroquia, blank=True, null=True, related_name='+', verbose_name=u"Parroquia de residencia", on_delete=models.CASCADE)
    sector = models.CharField(default='', max_length=300, verbose_name=u"Sector de residencia")
    ciudad = models.CharField(default='', max_length=50, verbose_name=u"Ciudad de residencia")
    direccion = models.CharField(default='', max_length=300, verbose_name=u"Calle principal")
    direccion2 = models.CharField(default='', max_length=300, verbose_name=u"Calle secundaria")
    num_direccion = models.CharField(default='', max_length=15, verbose_name=u"Numero")
    referencia = models.CharField(default='', max_length=100, verbose_name=u"Referencia")
    telefono = models.CharField(default='', max_length=50, verbose_name=u"Telefono movil")
    email = models.CharField(default='', max_length=200, verbose_name=u"Correo electronico personal")
    usuario = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    tipocelular = models.IntegerField(choices=TIPO_CELULAR, default=0, verbose_name=u'Tipo celular')

    def nombre_completo(self):
        return u'%s %s %s' % (self.nombres, self.apellido1, self.apellido2)

    def nombre_completo_inverso(self):
        return u'%s %s %s' % (self.apellido1, self.apellido2, self.nombres)

    def nombre_minus(self):
        try:
            nombreslist = self.nombres.split(' ')
            nombrepersona = self.nombres.capitalize()
            if len(nombreslist) == 2:
                nombrepersona = '{} {}'.format(str(nombreslist[0]).capitalize(), str(nombreslist[1]).capitalize())
                return u'%s' % (nombrepersona)
            elif len(nombreslist) == 3:
                nombrepersona = '{} {} {}'.format(str(nombreslist[0]).capitalize(), str(nombreslist[1]).capitalize(), str(nombreslist[2]).capitalize())
                return u'%s' % (nombrepersona)
            else:
                return u'%s' % (nombrepersona)
        except Exception as ex:
            return self.nombres.capitalize()

    def nombre_completo_minus(self):
            apellido1list = self.apellido1.split(' ')
            apellido1=self.apellido1.capitalize()
            if len(apellido1list) == 2:
                apellido1 = '{} {}'.format(str(apellido1list[0]).capitalize(), str(apellido1list[1]).capitalize())
            elif len(apellido1list) == 3:
                apellido1 = '{} {} {}'.format(str(apellido1list[0]).capitalize(), str(apellido1list[1]).capitalize(),
                                                  str(apellido1list[2]).capitalize())
            apellido2list = self.apellido2.split(' ')
            apellido2 = self.apellido2.capitalize()
            if len(apellido2list) == 2:
                apellido2 = '{} {}'.format(str(apellido2list[0]).capitalize(), str(apellido2list[1]).capitalize())
            elif len(apellido2list) == 3:
                apellido2 = '{} {} {}'.format(str(apellido2list[0]).capitalize(), str(apellido2list[1]).capitalize(),
                                              str(apellido2list[2]).capitalize())
            completo = '{} {} {}'.format(str(self.nombre_minus()),str(apellido1),str(apellido2))
            return u'%s' % (completo)

    def __str__(self):
        return u'%s %s %s' % (self.apellido1, self.apellido2, self.nombres)

    class Meta:
        verbose_name = u"Persona"
        verbose_name_plural = u"Personal"
        ordering = ['apellido1', 'apellido2', 'nombres']

    @staticmethod
    def flexbox_query(q, extra=None):
        if ' ' in q:
            s = q.split(" ")
            if extra:
                return eval(
                    'Persona.objects.filter(Q(apellido1__contains="%s") & Q(apellido2__contains="%s")).filter(%s).distinct()[:25]' % (
                        s[0], s[1], extra))
            return Persona.objects.filter((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) | (
                    Q(apellido1__contains=s[0]) & Q(nombres__contains=s[1])) | (
                                                  Q(apellido2__contains=s[0]) & Q(nombres__contains=s[1])) | (
                                                  Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1])) | (
                                                  Q(nombres__contains=s[0]) & Q(apellido2__contains=s[1])) | (
                                              Q(nombres__contains=s[0] + ' ' + s[1]))).distinct()[:25]
        if extra:
            return eval(
                'Persona.objects.filter(Q(nombres__contains="%s") | Q(apellido1__contains="%s") | Q(apellido2__contains="%s") | Q(documento__contains="%s")).filter(%s).distinct()[:25]' % (
                    q, q, q, q, extra))
        return Persona.objects.filter(Q(nombres__contains=q) | Q(apellido1__contains=q) | Q(apellido2__contains=q) | Q(
            documento__contains=q)).distinct()[:25]

    def en_uso(self):
        return self.perfilusuario_set.values("id").filter(status=True).exists()

    def administrativo(self):
        if self.administrativo_set.values("id").exists():
            return self.administrativo_set.all()[0]
        return None

    def en_grupo(self, grupo):
        return self.usuario.groups.values("id").filter(id=grupo).exists()

    def en_grupos(self, lista):
        return self.usuario.groups.values("id").filter(id__in=lista).exists()

    def grupos(self):
        return self.usuario.groups.all().distinct()

    def tiene_perfil(self):
        return self.perfilusuario_set.filter(visible=True).values("id").exists()

    def mis_perfilesusuarios_app(self, app):
        if app == 'uxplora':
            # return self.perfilusuario_set.exclude(administrativo__isnull=True).exclude(status=False)
            return self.perfilusuario_set.filter(visible=True).exclude(status=False)
        else:
            return self.perfilusuario_set.filter(visible=True).exclude(status=False).order_by('id')

    def perfilusuario_principal(self, perfiles, app):
        if app == 'uxplora':
            if perfiles.values("id").filter(administrativo__isnull=False, administrativo__activo=True, persona__usuario__is_superuser=True).exists():
                return perfiles.filter(administrativo__isnull=False, visible=True, administrativo__activo=True)[0]
            elif perfiles.values("id").filter(administrativo__isnull=False, administrativo__activo=True).exists():
                return perfiles.filter(administrativo__isnull=False, visible=True, administrativo__activo=True)[0]
        return None

class Administrativo(ModeloBase):
    persona = models.ForeignKey(Persona, verbose_name=u"Persona", on_delete=models.CASCADE)
    fechaingreso = models.DateField(verbose_name=u'Fecha ingreso')
    activo = models.BooleanField(default=True, verbose_name=u"Activo")

    def __str__(self):
        return u'%s' % self.persona

    class Meta:
        verbose_name = u"Administrativo"
        verbose_name_plural = u"Administrativos"
        ordering = ['persona']
        unique_together = ('persona',)

    @staticmethod
    def flexbox_query(q, extra=None):
        if ' ' in q:
            s = q.split(" ")
            return Administrativo.objects.filter(
                Q(persona__apellido1__contains=s[0]) & Q(persona__apellido2__contains=s[1])).distinct()[:25]
        return Administrativo.objects.filter(
            Q(persona__nombres__contains=q) | Q(persona__apellido1__contains=q) | Q(persona__apellido2__contains=q) | Q(
                persona__documento__contains=q)).distinct()[:25]

    def flexbox_repr(self):
        return self.persona.documento + " - " + self.persona.nombre_completo_inverso() + " - " + self.id.__str__()

    def flexbox_alias(self):
        return [self.persona.documento, self.persona.nombre_completo()]

class PerfilUsuario(ModeloBase):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE)
    administrativo = models.ForeignKey(Administrativo, blank=True, null=True, verbose_name=u'Administrativo', on_delete=models.CASCADE)
    visible = models.BooleanField(default=True, verbose_name=u'Visible')

    def __str__(self):
        if self.es_administrativo():
            return u'%s' % "ADMINISTRATIVO"
        else:
            return u'%s' % "OTRO PERFIL"

    class Meta:
        ordering = ['persona', 'administrativo']
        unique_together = ('persona', 'administrativo',)

    def es_administrativo(self):
        return null_to_numeric(self.administrativo_id) > 0


    def tipo(self):
        if self.es_administrativo():
            return "ADMINISTRATIVO"
        else:
            return "NO DEFINIDO"

    def activo(self):
        if self.es_administrativo():
            return self.administrativo.activo
        return False
