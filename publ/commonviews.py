# coding=latin-1
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from publ.models import *
from publ.settings import EMAIL_DOMAIN, NOMBRE_INSTITUCION
from datetime import datetime

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
def adduserdata(request, data, isPanel=False):
    # ADICIONA EL USUARIO A LA SESSION

    if 'persona' not in request.session:
        if not request.user.is_authenticated:
            raise Exception('Usuario no autentificado en el sistema')
        request.session['persona'] = Persona.objects.get(usuario=request.user)
    data['persona'] = persona = request.session['persona']
    tipoentrada = 'UXplora'
    if 'tipoentrada' in request.session:
        data['tipoentrada'] = tipoentrada = request.session['tipoentrada'] if request.session['tipoentrada'] else "UXplora"
    else:
        data['tipoentrada'] = tipoentrada = "UXplora"
    if 'ultimo_acceso' not in request.session:
            request.session['ultimo_acceso'] = datetime.now()
    if request.method == 'GET':
        if 'ret' in request.GET:
            data['ret'] = request.GET['ret']
        if 'mensj' in request.GET:
            data['mensj'] = request.GET['mensj']
        if 'useModal' in request.GET:
            data['useModal'] = int(request.GET['useModal']) == 1
    data['nombresistema'] = request.session['nombresistema']
    data['tiposistema'] = request.session['tiposistema']
    data['currenttime'] = datetime.now()
    data['remotenameaddr'] = '%s' % (request.META['SERVER_NAME'])
    data['remoteaddr'] = '%s - %s' % (get_client_ip(request), request.META['SERVER_NAME'])
    eUser = persona.usuario
    request.user.is_superuser = False
    data['request'] = request
    data['perfilprincipal'] = perfilprincipal = request.session['perfilprincipal']
    data['perfiles_usuario'] = request.session['perfiles']
    data['info'] = request.GET['info'] if 'info' in request.GET else ''
    data['check_session'] = False
    if 'grupos_usuarios' not in request.session:
        request.session['grupos_usuarios'] = request.user.groups.all()
    data['grupos_usuarios'] = request.session['grupos_usuarios']

# CIERRA LA SESSION DEL USUARIO
def logout_user(request):
    logout(request)
    return HttpResponseRedirect("/login")

@transaction.atomic()
def login_user(request):
    data = {}
    if EMAIL_DOMAIN in request.META['HTTP_HOST']:
        if 'uxplora' not in request.META['HTTP_HOST']:
            return HttpResponseRedirect('/login')

    data['currenttime'] = datetime.now()
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'login':
                try:
                    data = {}
                    user = authenticate(username=request.POST['user'].lower().strip(), password=request.POST['pass'])
                    if user is not None:
                        if not user.is_active:
                            return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, usuario no activo.'})
                        else:
                            if Persona.objects.filter(usuario=user).exists():
                                persona = Persona.objects.filter(usuario=user)[0]
                                if persona.tiene_perfil():
                                    app = 'research'
                                    if not Group.objects.filter(pk=1, user=persona.usuario): #asignar grupo de administrativo
                                        usuario = User.objects.get(pk=persona.usuario.id)
                                        g = Group.objects.get(pk=1)
                                        g.user_set.add(usuario)
                                        g.save()
                                    perfiles = persona.mis_perfilesusuarios_app(app)
                                    perfilprincipal = persona.perfilusuario_principal(perfiles, app)
                                    if not perfilprincipal:
                                        if not Administrativo.objects.filter(status=True, persona=persona):
                                            administrativo = Administrativo(persona=persona, activo=True)
                                            administrativo.save(request)
                                            if not PerfilUsuario.objects.filter(status=True, administrativo=administrativo):
                                                perfil = PerfilUsuario(persona=persona, administrativo=administrativo)
                                                perfil.save(request)
                                        perfilprincipal = persona.perfilusuario_principal(perfiles, app)
                                    request.session.set_expiry(240 * 60)
                                    login(request, user)
                                    request.session['perfiles'] = perfiles
                                    request.session['persona'] = persona
                                    # request.session['capippriva'] = capippriva
                                    request.session['tiposistema'] = app
                                    request.session['perfilprincipal'] = perfilprincipal
                                    nombresistema = u'Sistema UXplora'
                                    request.session['nombresistema'] = nombresistema
                                    adduserdata(request, data)
                                    return JsonResponse({"result": "ok", "sessionid": request.session.session_key})
                                else:
                                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existen perfiles activos.'})
                            else:
                                return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existe el usuario.'})
                    else:
                        return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, credenciales incorrectas.'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, Error en el sistema. {}'.format(str(ex))})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'persona' in request.session:
            return HttpResponseRedirect("/")
        try:
            data['title'] = "Inicio de Sesión | LOG STORE"
            data['currenttime'] = datetime.now()
            data['institucion'] = NOMBRE_INSTITUCION
            data['fecha_actual'] = datetime.now().date()
            return render(request, "login/login.html", data)
        except Exception as ex:
            import sys
            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            pass
