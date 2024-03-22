# -*- coding: UTF-8 -*-
from _decimal import Decimal
from django import template
from django.db.models import Q
register = template.Library()

@register.simple_tag
def ver_valor_dict(diccionario, llave):
    return diccionario[llave]

def callmethod(obj, methodname):
    method = getattr(obj, methodname)
    if "__callArg" in obj.__dict__:
        ret = method(*obj.__callArg)
        del obj.__callArg
        return ret
    return method()

def args(obj, arg):
    if "__callArg" not in obj.__dict__:
        obj.__callArg = []
    obj.__callArg.append(arg)
    return obj
def encrypt(value):
    if value == None:
       return value
    myencrip = ""
    if type(value) != str:
        value = str(value)
    i = 1
    for c in value.zfill(20):
        myencrip = myencrip + chr(int(44450/350) - ord(c) + int(i/int(9800/4900)))
        i = i + 1
    return myencrip

register.filter("encrypt", encrypt)