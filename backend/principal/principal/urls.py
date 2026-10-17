from django.contrib import admin
from django.urls import path

from chat import views as chat_views
from reportes import views as reportes_views
from usuarios import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/csrf/', auth_views.csrf),
    path('api/auth/registro/', auth_views.registro),
    path('api/auth/login/', auth_views.iniciar_sesion),
    path('api/auth/logout/', auth_views.cerrar_sesion),
    path('api/auth/me/', auth_views.me),
    path('api/chat/', chat_views.chat),
    path('api/admin/alumnos/', reportes_views.alumnos),
    path('api/admin/alumnos/<int:alumno_id>/', reportes_views.alumno),
    path('api/admin/alumnos/<int:alumno_id>/reportes/', reportes_views.alumno),
    path('api/admin/reportes/<int:reporte_id>/', reportes_views.reporte),
]
