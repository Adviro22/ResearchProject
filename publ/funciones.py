# coding=utf-8
from __future__ import division

import re
import sys
from datetime import timedelta, date, time
from operator import itemgetter
import os
import json
import io as StringIO

from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, connection, connections
from django.contrib.admin.models import LogEntry, ADDITION, DELETION, CHANGE
from django.contrib.auth.models import User, Group, _user_has_perm
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.http import HttpResponse

import unicodedata
import socket
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime


unicode = str


class MiPaginador(Paginator):
    def __init__(self, object_list, per_page, orphans=0, allow_empty_first_page=True, rango=5):
        super(MiPaginador, self).__init__(object_list, per_page, orphans=orphans, allow_empty_first_page=allow_empty_first_page)
        self.rango = rango
        self.paginas = []
        self.primera_pagina = False
        self.ultima_pagina = False

    def rangos_paginado(self, pagina):
        left = pagina - self.rango
        right = pagina + self.rango
        if left < 1:
            left = 1
        if right > self.num_pages:
            right = self.num_pages
        self.paginas = range(left, right + 1)
        self.primera_pagina = True if left > 1 else False
        self.ultima_pagina = True if right < self.num_pages else False
        self.ellipsis_izquierda = left - 1
        self.ellipsis_derecha = right + 1


def remover_caracteres_especiales_unicode(cadena):
    return cadena.replace(u'ñ', u'n').replace(u'Ñ', u'N').replace(u'Á', u'A').replace(u'á', u'a').replace(u'É', u'E').replace(u'é', u'e').replace(u'Í', u'I').replace(u'í', u'i').replace(u'Ó', u'O').replace(u'ó', u'o').replace(u'Ú', u'U').replace(u'ú', u'u')


def remover_comilla_simple(cadena):
    return cadena.replace(u"'", u'')


def remover_caracteres_tildes_unicode(cadena):
    return cadena.replace(u'Á', u'A').replace(u'á', u'a').replace(u'É', u'E').replace(u'é', u'e').replace(u'Í',
                                                                                                          u'I').replace(
        u'í', u'i').replace(u'Ó', u'O').replace(u'ó', u'o').replace(u'Ú', u'U').replace(u'ú', u'u')


def elimina_tildes(cadena):
    s = ''.join((c for c in unicodedata.normalize('NFD', unicode(cadena)) if unicodedata.category(c) != 'Mn'))
    # return s.decode()
    return s


def remover_caracteres(texto, caracteres_a_remover):
    string = ''.join(c for c in texto if c not in caracteres_a_remover)
    return string


def remover_atributo_style_html(html):
    style = re.compile(' style\=.*?\".*?\"')
    html = re.sub(style, '', html)
    return html



def calculate_username(persona, variant=1):
    alfabeto = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',
                'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    s = persona.nombres.lower().split(' ')
    while '' in s:
        s.remove('')
    if persona.apellido2:
        usernamevariant = s[0][0] + persona.apellido1.lower() + persona.apellido2.lower()[0]
    else:
        usernamevariant = s[0][0] + persona.apellido1.lower()
    usernamevariant = usernamevariant.replace(' ', '').replace(u'ñ', 'n').replace(u'á', 'a').replace(u'é', 'e').replace(
        u'í', 'i').replace(u'ó', 'o').replace(u'ú', 'u')
    usernamevariantfinal = ''
    for letra in usernamevariant:
        if letra in alfabeto:
            usernamevariantfinal += letra
    if variant > 1:
        usernamevariantfinal += str(variant)

    if not User.objects.filter(username=usernamevariantfinal).exclude(persona=persona).exists():
        return usernamevariantfinal
    else:
        return calculate_username(persona, variant + 1)


def logproceso(mensaje, accion, user=None):
    if accion == "del":
        logaction = DELETION
    elif accion == "add":
        logaction = ADDITION
    else:
        logaction = CHANGE

    LogEntry.objects.log_action(
        user_id=1,
        content_type_id=None,
        object_id=None,
        object_repr='',
        action_flag=logaction,
        change_message=unicode(mensaje))





def convertir_fecha(s):
    if ':' in s:
        sep = ':'
    elif '-' in s:
        sep = '-'
    else:
        sep = '/'

    return date(int(s.split(sep)[2]), int(s.split(sep)[1]), int(s.split(sep)[0]))


def convertir_hora(s):
    if ':' in s:
        sep = ':'
    return time(int(s.split(sep)[0]), int(s.split(sep)[1]))


def convertir_hora_completa(s):
    if ':' in s:
        sep = ':'
    return time(int(s.split(sep)[0]), int(s.split(sep)[1]), int(s.split(sep)[2]))


def convertir_fecha_invertida(s):
    if ':' in s:
        sep = ':'
    elif '-' in s:
        sep = '-'
    else:
        sep = '/'
    return date(int(s.split(sep)[0]), int(s.split(sep)[1]), int(s.split(sep)[2]))



def formato24h(hora):
    horas = hora.partition(":")[0]
    minutos = hora.partition(":")[2].partition(" ")[0]
    meridiano = hora.partition(":")[2].partition(" ")[2]
    if meridiano == "AM":
        if horas == "12":
            return "00" + ":" + minutos + ":00"
        else:
            return horas + ":" + minutos + ":00"
    else:
        if horas == "12":
            return horas + ":" + minutos + ":00"
        else:
            return str(int(horas) + 12) + ":" + minutos + ":00"


def formato12h(hora):
    horas = hora.partition(":")[0]
    minutos = hora.partition(":")[2].partition(" ")[0]
    if horas >= "12":
        if horas == "12":
            return horas + ":" + minutos + " PM"
        else:
            return str(int(horas) - 12) + ":" + minutos + " PM"
    else:
        if horas == "0":
            return "12:" + minutos + " AM"
        else:
            return horas + ":" + minutos + " AM"


def remover_caracteres_especiales(cadena):
    s = ''.join((c for c in unicodedata.normalize('NFD', unicode(cadena)) if unicodedata.category(c) != 'Mn'))
    # return s.decode()
    return s


def to_unicode(s):
    if isinstance(s, unicode):
        return s

    from locale import getpreferredencoding

    for cp in (getpreferredencoding(), "cp1255", "cp1250"):
        try:
            return unicode(s, cp)
        except UnicodeDecodeError:
            pass
        raise Exception("Conversion to unicode failed")


def generar_nombre(nombre, original):
    ext = ""
    if original.find(".") > 0:
        ext = original[original.rfind("."):]
    fecha = datetime.now().date()
    hora = datetime.now().time()
    return nombre + fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__() + ext.lower()

def obtener_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("gmail.com", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

#FUNCION VALIDA ERRONEAMENTE VARIAS CÉDULAS
# def validarcedula(numero):
#     suma = 0
#     residuo = 0
#     pri = False
#     pub = False
#     nat = False
#     numeroprovincias = 24
#     modulo = 11
#     if numero.__len__() != 10:
#         return 'El número de cédula no es válido, debe tener 10 dígitos'
#     prov = numero[0:2]
#     if int(prov) > numeroprovincias or int(prov) <= 0:
#         return 'El código de la provincia (dos primeros dígitos) es inválido'
#     d1 = numero[0:1]
#     d2 = numero[1:2]
#     d3 = numero[2:3]
#     d4 = numero[3:4]
#     d5 = numero[4:5]
#     d6 = numero[5:6]
#     d7 = numero[6:7]
#     d8 = numero[7:8]
#     d9 = numero[8:9]
#     d10 = numero[9:10]
#     p1 = 0
#     p2 = 0
#     p3 = 0
#     p4 = 0
#     p5 = 0
#     p6 = 0
#     p7 = 0
#     p8 = 0
#     p9 = 0
#     if int(d3) == 7 or int(d3) == 8:
#         return 'El tercer dígito ingresado es inválido'
#     if int(d3) < 6:
#         nat = True
#         p1 = int(d1) * 2
#         if p1 >= 10:
#             p1 -= 9
#         p2 = int(d2) * 1
#         if p2 >= 10:
#             p2 -= 9
#         p3 = int(d3) * 2
#         if p3 >= 10:
#             p3 -= 9
#         p4 = int(d4) * 1
#         if p4 >= 10:
#             p4 -= 9
#         p5 = int(d5) * 2
#         if p5 >= 10:
#             p5 -= 9
#         p6 = int(d6) * 1
#         if p6 >= 10:
#             p6 -= 9
#         p7 = int(d7) * 2
#         if p7 >= 10:
#             p7 -= 9
#         p8 = int(d8) * 1
#         if p8 >= 10:
#             p8 -= 9
#         p9 = int(d9) * 2
#         if p9 >= 10:
#             p9 -= 9
#         modulo = 10
#     elif int(d3) == 6:
#         pub = True
#         p1 = int(d1) * 3
#         p2 = int(d2) * 2
#         p3 = int(d3) * 7
#         p4 = int(d4) * 6
#         p5 = int(d5) * 5
#         p6 = int(d6) * 4
#         p7 = int(d7) * 3
#         p8 = int(d8) * 2
#         p9 = 0
#     elif int(d3) == 9:
#         pri = True
#         p1 = int(d1) * 4
#         p2 = int(d2) * 3
#         p3 = int(d3) * 2
#         p4 = int(d4) * 7
#         p5 = int(d5) * 6
#         p6 = int(d6) * 5
#         p7 = int(d7) * 4
#         p8 = int(d8) * 3
#         p9 = int(d9) * 2
#     suma = p1 + p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9
#     residuo = suma % modulo
#     if residuo == 0:
#         digitoverificador = 0
#     else:
#         digitoverificador = modulo - residuo
#     if nat:
#         if digitoverificador != int(d10):
#             return 'El número de cédula de la persona natural es incorrecto'
#         else:
#             return 'Ok'
#     else:
#         return 'El número de cédula introducido es incorrecto'
#VALIDAR IDENTIFICACIÓN CÉDULA Y RUC
# def validarcedula(nro, tipo=0):
#     nro = nro.replace("-", "").replace(" ", "")
#     if not nro.isdigit():
#         return "Por favor digitar solo números"
#     total = 0
#     if tipo == 0:  # cedula y r.u.c persona natural
#         base = 10
#         d_ver = int(nro[9])  # digito verificador
#         multip = (2, 1, 2, 1, 2, 1, 2, 1, 2)
#     elif tipo == 1:  # r.u.c. publicos
#         base = 11
#         d_ver = int(nro[8])
#         multip = (3, 2, 7, 6, 5, 4, 3, 2)
#     elif tipo == 2:  # r.u.c. juridicos y extranjeros sin cedula
#         base = 11
#         d_ver = int(nro[9])
#         multip = (4, 3, 2, 7, 6, 5, 4, 3, 2)
#     if len(nro) < base:
#         return f"Identificación ingresada tiene menos de {base} números"
#     for i in range(0, len(multip)):
#         p = int(nro[i]) * multip[i]
#         if tipo == 0:
#             total += p if p < 10 else int(str(p)[0]) + int(str(p)[1])
#         else:
#             total += p
#     mod = total % base
#     val = base - mod if mod != 0 else 0
#     if val!=d_ver:
#         return 'Número de identificación ingresada es incorrecta.'
#     return 'Ok'
def validarcedula(cedula):
    # Eliminar posibles caracteres no numéricos
    cedula = cedula.replace("-", "").replace(" ", "")

    # Verificar si la cédula tiene la longitud correcta
    if len(cedula) != 10:
        return "Cédula ingresada tiene menos de 10 números"

    # Verificar si todos los caracteres son dígitos
    if not cedula.isdigit():
        return "Por favor digitar solo números"

    # Verificar el dígito de verificación
    provincia = int(cedula[0:2])
    if provincia==30:
        # if not cedula.startswith('3050'):
        #     return 'Identificación incorrecta'
        #     # Obtiene los dígitos de la cédula
        # digitos = [int(d) for d in cedula]
        # # Obtiene el dígito verificador
        # verificador = digitos[9]
        # # Calcula la suma ponderada de los dígitos
        # suma_ponderada = sum(digitos[i] * (2 ** (9 - i)) for i in range(9))
        # # Calcula el dígito verificador esperado
        # verificador_esperado = (10 - (suma_ponderada % 10)) % 10
        # # Comprueba si el dígito verificador coincide
        # valido=verificador == verificador_esperado
        return 'Ok'
    else:
        if provincia < 1 or provincia > 24:
            return "Primero dos dígitos incorrecto"

        tercer_digito = int(cedula[2])
        if tercer_digito < 0 or tercer_digito > 6:
            return "Tercer digito fuera de rango"

        coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
        verificador = int(cedula[9])

        # Calcular el dígito de verificación esperado
        suma = 0
        for i in range(9):
            digito = int(cedula[i])
            producto = digito * coeficientes[i]
            if producto >= 10:
                producto -= 9
            suma += producto

        digito_verificador_esperado = 0
        if suma % 10 != 0:
            digito_verificador_esperado = 10 - (suma % 10)

        # Comparar el dígito de verificación ingresado con el esperado
        if verificador != digito_verificador_esperado:
            return "Cédula incorrecta"

        # Si todas las verificaciones pasaron, la cédula es válida
        return "Ok"


def puede_realizar_accion(request, permiso):
    if request.user.has_perm(permiso):
        return True
    raise Exception('Permiso denegado.')


def puede_realizar_accion_is_superuser(request, permiso):
    # Active superusers have all permissions.
    if _user_has_perm(request.user, permiso, None):
        return True
    raise Exception('Permiso denegado.')


def puede_ver_todoadmision(request, permiso):
    if request.user.has_perm(permiso):
        return True
    else:
        return False


def puede_realizar_accion_afirmativo(request, permiso):
    if request.user.has_perm(permiso):
        return True
    return False


def puede_realizar_acciones_afirmativo(request, permiso_list):
    if request.user.has_perms(permiso_list):
        return True
    return False






(MON, TUE, WED, THU, FRI, SAT, SUN) = range(7)


def addworkdays(start, days, holidays=(), workdays=(MON, TUE, WED, THU, FRI)):
    weeks, days = divmod(days, len(workdays))
    result = start + timedelta(weeks=weeks)
    lo, hi = min(start, result), max(start, result)
    count = len([h for h in holidays if lo <= h <= hi])
    days += count * (-1 if days < 0 else 1)
    for _ in range(days):
        result += timedelta(days=1)
        while result in holidays or result.weekday() not in workdays:
            result += timedelta(days=1)
    return result


def bad_json(mensaje=None, error=None, extradata=None):
    data = {'result': 'bad'}
    if mensaje:
        data.update({'mensaje': mensaje})
    if error:
        if error == 0:
            data.update({"mensaje": "Solicitud incorrecta."})
        elif error == 1:
            data.update({"mensaje": "Error al guardar los datos."})
        elif error == 2:
            data.update({"mensaje": "Error al eliminar los datos."})
        elif error == 3:
            data.update({"mensaje": "Error al obtener los datos."})
        elif error == 4:
            data.update({"mensaje": "No tiene permisos para realizar esta acción."})
        elif error == 5:
            data.update({"mensaje": "Error al generar la información."})
        else:
            data.update({"mensaje": "Error en el sistema."})
    if extradata:
        data.update(extradata)
    return HttpResponse(json.dumps(data), content_type="application/json")


def ok_json(data=None, simple=None):
    if data:
        if not simple:
            if 'result' not in data.keys():
                data.update({"result": "ok"})
    else:
        data = {"result": "ok"}
    return HttpResponse(json.dumps(data), content_type="application/json")


def fechaletra_corta(fecha):
    fechafinal = ''
    if fecha.day == 1:
        fechafinal += 'al primer día '
    if fecha.day == 2:
        fechafinal += 'a los dos días '
    if fecha.day == 3:
        fechafinal += 'a los tres días '
    if fecha.day == 4:
        fechafinal += 'a los cuatro días '
    if fecha.day == 5:
        fechafinal += 'a los cinco días '
    if fecha.day == 6:
        fechafinal += 'a los seis días '
    if fecha.day == 7:
        fechafinal += 'a los siete días '
    if fecha.day == 8:
        fechafinal += 'a los ocho días '
    if fecha.day == 9:
        fechafinal += 'a los nueve días '
    if fecha.day == 10:
        fechafinal += 'a los diez días '
    if fecha.day == 11:
        fechafinal += 'a los once días '
    if fecha.day == 12:
        fechafinal += 'a los doce días '
    if fecha.day == 13:
        fechafinal += 'a los trece días '
    if fecha.day == 14:
        fechafinal += 'a los catorce días '
    if fecha.day == 15:
        fechafinal += 'a los quince días '
    if fecha.day == 16:
        fechafinal += 'a los dieciseis días '
    if fecha.day == 17:
        fechafinal += 'a los diecisiete días '
    if fecha.day == 18:
        fechafinal += 'a los dieciocho días '
    if fecha.day == 19:
        fechafinal += 'a los diecinueve días '
    if fecha.day == 20:
        fechafinal += 'a los veinte días '
    if fecha.day == 21:
        fechafinal += 'a los veintiun días '
    if fecha.day == 22:
        fechafinal += 'a los veintidos días '
    if fecha.day == 23:
        fechafinal += 'a los veintitres días '
    if fecha.day == 24:
        fechafinal += 'a los veinticuatro días '
    if fecha.day == 25:
        fechafinal += 'a los veinticinco días '
    if fecha.day == 26:
        fechafinal += 'a los veintiseis días '
    if fecha.day == 27:
        fechafinal += 'a los veintisiete días '
    if fecha.day == 28:
        fechafinal += 'a los veintiocho días '
    if fecha.day == 29:
        fechafinal += 'a los veintinueve días '
    if fecha.day == 30:
        fechafinal += 'a los treinta días '
    if fecha.day == 31:
        fechafinal += 'a los treinta y un días '
    if fecha.month == 1:
        fechafinal += 'del mes de Enero del '
    if fecha.month == 2:
        fechafinal += 'del mes de Febrero del '
    if fecha.month == 3:
        fechafinal += 'del mes de Marzo del '
    if fecha.month == 4:
        fechafinal += 'del mes de Abril del '
    if fecha.month == 5:
        fechafinal += 'del mes de Mayo del '
    if fecha.month == 6:
        fechafinal += 'del mes de Junio del '
    if fecha.month == 7:
        fechafinal += 'del mes de Julio del '
    if fecha.month == 8:
        fechafinal += 'del mes de Agosto del '
    if fecha.month == 9:
        fechafinal += 'del mes de Septiembre del '
    if fecha.month == 10:
        fechafinal += 'del mes de Octubre del '
    if fecha.month == 11:
        fechafinal += 'del mes de Noviembre del '
    if fecha.month == 12:
        fechafinal += 'del mes de Diciembre del '
    if fecha.year == 1998:
        fechafinal += 'mil novecientos noventa y ocho'
    if fecha.year == 1999:
        fechafinal += 'mil novecientos noventa y nueve'
    if fecha.year == 2000:
        fechafinal += 'dos mil'
    if fecha.year == 2001:
        fechafinal += 'dos mil uno'
    if fecha.year == 2002:
        fechafinal += 'dos mil dos'
    if fecha.year == 2003:
        fechafinal += 'dos mil tres'
    if fecha.year == 2004:
        fechafinal += 'dos mil cuatro'
    if fecha.year == 2005:
        fechafinal += 'dos mil cinco'
    if fecha.year == 2006:
        fechafinal += 'dos mil seis'
    if fecha.year == 2007:
        fechafinal += 'dos mil siete'
    if fecha.year == 2008:
        fechafinal += 'dos mil ocho'
    if fecha.year == 2009:
        fechafinal += 'dos mil nueve'
    if fecha.year == 2010:
        fechafinal += 'dos mil diez'
    if fecha.year == 2011:
        fechafinal += 'dos mil once'
    if fecha.year == 2012:
        fechafinal += 'dos mil doce'
    if fecha.year == 2013:
        fechafinal += 'dos mil trece'
    if fecha.year == 2014:
        fechafinal += 'dos mil catorce'
    if fecha.year == 2015:
        fechafinal += 'dos mil quince'
    if fecha.year == 2016:
        fechafinal += 'dos mil dieciseis'
    if fecha.year == 2017:
        fechafinal += 'dos mil diecisiete'
    if fecha.year == 2018:
        fechafinal += 'dos mil dieciocho'
    if fecha.year == 2019:
        fechafinal += 'dos mil diecinueve'
    if fecha.year == 2020:
        fechafinal += 'dos mil veinte'
    if fecha.year == 2021:
        fechafinal += 'dos mil veintiuno'
    if fecha.year == 2022:
        fechafinal += 'dos mil veintidos'
    if fecha.year == 2023:
        fechafinal += 'dos mil veintitres'
    if fecha.year == 2024:
        fechafinal += 'dos mil veinticuatro'
    if fecha.year == 2025:
        fechafinal += 'dos mil veinticinco'
    if fecha.year == 2026:
        fechafinal += 'dos mil veintiseis'
    if fecha.year == 2027:
        fechafinal += 'dos mil veintisiete'
    if fecha.year == 2028:
        fechafinal += 'dos mil veintiocho'
    if fecha.year == 2029:
        fechafinal += 'dos mil veintinueve'
    if fecha.year == 2030:
        fechafinal += 'dos mil treinta'
    return fechafinal


def fields_model(classname, app):
    try:
        d = locals()
        exec('from %s.models import %s' % (app, classname), globals(), d)
        # exec('from %s.models import %s' % (app, classname))
        fields = eval(classname + '._meta.get_fields()')
        return fields
    except:
        return []


def field_default_value_model(field):
    try:
        value = str(field)
        return value if 'django.db.models.fields.NOT_PROVIDED' not in value else ''
    except:
        return ''


def sumar_hora(hora_1, hora_2):
    minuto_aux = 0
    hora_aux = 0
    horas_letras_aux = ''
    minutos_letras_aux = ''
    segundos_letras_aux = ''

    lista1 = hora_1.split(":")
    hora1 = int(lista1[0])
    minuto1 = int(lista1[1])
    segundo1 = int(lista1[2])

    lista2 = hora_2.split(":")
    hora2 = int(lista2[0])
    minuto2 = int(lista2[1])
    segundo2 = int(lista2[2])
    # sumar segundos
    segundos = int(segundo1) + int(segundo2)
    if segundos >= 60:
        segundos = segundos - 60
        minuto_aux = 1

    # sumar minutos
    minutos = int(minuto1) + int(minuto2)
    if minutos >= 60:
        minutos = minutos - 60 + minuto_aux
        hora_aux = 1

    # sumar horas
    horas = hora1 + hora2 + hora_aux

    if segundos < 9:
        segundos_letras_aux = "0" + str(segundos)
    else:
        segundos_letras_aux = str(segundos)

    if minutos < 9:
        minutos_letras_aux = "0" + str(minutos)
    else:
        minutos_letras_aux = str(minutos)

    if horas < 9:
        horas_letras_aux = "0" + str(horas)
    else:
        horas_letras_aux = str(horas)

    resultado = horas_letras_aux + ":" + minutos_letras_aux + ":" + segundos_letras_aux
    return str(resultado)




def null_to_numeric(valor, decimales=None):
    if decimales:
        return round((valor if valor else 0), decimales)
    return valor if valor else 0


def null_to_decimal(valor, decimales=None):
    if not decimales is None and not valor is None:
        if decimales > 0:
            sql = """SELECT round(%s::numeric,%s)""" % (valor, decimales)
            cursor = connections['sga_select'].cursor()
            cursor.execute(sql)
            results = cursor.fetchall()
            return float(results[0][0])
            # return float(Decimal(repr(valor) if valor else 0).quantize(Decimal('.' + ''.zfill(decimales - 1) + '1')) if valor else 0)
            # return float(Decimal(valor.__str__() if valor else 0).quantize(Decimal('.' + ''.zfill(decimales - 1) + '1'), rounding=ROUND_HALF_UP) if valor else 0)
        else:
            sql = """SELECT round(%s::numeric,%s)""" % (valor, 0)
            cursor = connections['sga_select'].cursor()
            cursor.execute(sql)
            results = cursor.fetchall()
            return float(results[0][0])
            # return float(Decimal(valor.__str__() if valor else 0).quantize(Decimal('0')))
    return valor if valor else 0



def convertir_fecha_invertida_hora(s):
    if ':' in s:
        sep = ':'
    elif '-' in s:
        sep = '-'
    else:
        sep = '/'
    return datetime(int(s.split(sep)[0]), int(s.split(sep)[1]), int(s.split(sep)[2]), int(s.split(sep)[3]),
                    int(s.split(sep)[4]))


def convertir_fecha_hora(s):
    fecha = s.split(' ')[0]
    hora = s.split(' ')[1]
    if '/' in fecha:
        sep = ':'
    elif '-' in fecha:
        sep = '-'
    else:
        sep = ':'
    return datetime(int(fecha.split(sep)[2]), int(fecha.split(sep)[1]), int(fecha.split(sep)[0]),
                    int(hora.split(':')[0]), int(hora.split(':')[1]))


def convertir_fecha_hora_invertida(s):
    fecha = s.split(' ')[0]
    hora = s.split(' ')[1]
    if '/' in fecha:
        sep = ':'
    elif '-' in fecha:
        sep = '-'
    else:
        sep = ':'
    return datetime(int(fecha.split(sep)[0]), int(fecha.split(sep)[1]), int(fecha.split(sep)[2]),
                    int(hora.split(':')[0]), int(hora.split(':')[1]))


def restar_hora(hora1, hora2):
    formato = "%H:%M:%S"
    h1 = datetime.strptime(hora1, formato)
    h2 = datetime.strptime(hora2, formato)
    resultado = h1 - h2
    return str(resultado)


def years_ago(years, stardate, day=None):
    if day:
        day -= 1
    else:
        day = stardate.day
    month = stardate.month
    year = stardate.year
    try:
        return date(year - years, month, day)
    except Exception as ex:
        pass
        return years_ago(years, stardate, day)


def years_future(years, stardate, day=None):
    if day:
        day -= 1
    else:
        day = stardate.day
    month = stardate.month
    year = stardate.year
    try:
        return date(year + years, month, day)
    except Exception as ex:
        pass
        return years_ago(years, stardate, day)


def calcula_edad(fnacimiento):
    hoy = date.today()
    return hoy.year - fnacimiento.year - ((hoy.month, hoy.day) < (fnacimiento.month, fnacimiento.day))


def calcula_edad_fn_fc(fnacimiento, fechacalculo):
    return fechacalculo.year - fnacimiento.year - ((fechacalculo.month, fechacalculo.day) < (fnacimiento.month, fnacimiento.day))


def suma_dias_habiles(fecha, dias):
    try:
        h = dias
        ds = 5 - fecha.weekday()  # distancia al sabado
        s = 0
        if h >= ds:
            s = s + 2
            h = h - ds

        s = s + h / 5 * 2
        return datetime.fromordinal(fecha.toordinal() + int(dias) + int(s))
    except Exception as ex:
        return datetime.now().date()


class ModeloBase(models.Model):
    """ Modelo base para todos los modelos del proyecto """
    from django.contrib.auth.models import User
    status = models.BooleanField(default=True)
    usuario_creacion = models.ForeignKey(User, related_name='+', blank=True, null=True, on_delete=models.SET_NULL)
    fecha_creacion = models.DateTimeField(blank=True, null=True)
    usuario_modificacion = models.ForeignKey(User, related_name='+', blank=True, null=True, on_delete=models.SET_NULL)
    fecha_modificacion = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        usuario = None
        fecha_modificacion = datetime.now()
        fecha_creacion = None
        if len(args):
            usuario = args[0].user.id
        for key, value in kwargs.items():
            if 'usuario_id' == key:
                usuario = value
            if 'fecha_modificacion' == key:
                fecha_modificacion = value
            if 'fecha_creacion' == key:
                fecha_creacion = value
        if self.id:
            self.usuario_modificacion_id = usuario if usuario else 1
            self.fecha_modificacion = fecha_modificacion
        else:
            self.usuario_creacion_id = usuario if usuario else 1
            self.fecha_creacion = fecha_modificacion
            if fecha_creacion:
                self.fecha_creacion = fecha_creacion
        models.Model.save(self)

    class Meta:
        abstract = True



# NUMERO A LETRAS
def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


def convertirfecha(fecha):
    try:
        return date(int(fecha[6:10]), int(fecha[3:5]), int(fecha[0:2]))
    except Exception as ex:
        return datetime.now().date()


def convertirfechahora(fecha):
    try:
        return datetime(int(fecha[0:4]), int(fecha[5:7]), int(fecha[8:10]), int(fecha[11:13]), int(fecha[14:16]),
                        int(fecha[17:19]))
    except Exception as ex:
        return datetime.now()


def convertirfechahorainvertida(fecha):
    try:
        return datetime(int(fecha[6:10]), int(fecha[3:5]), int(fecha[0:2]), int(fecha[11:13]), int(fecha[14:16]),
                        int(fecha[17:19]))
    except Exception as ex:
        return datetime.now()


def convertirfecha2(fecha):
    try:
        return date(int(fecha[0:4]), int(fecha[5:7]), int(fecha[8:10]))
    except Exception as ex:
        return datetime.now().date()