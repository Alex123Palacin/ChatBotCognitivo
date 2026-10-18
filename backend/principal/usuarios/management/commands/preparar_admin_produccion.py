import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from usuarios.models import Perfil


class Command(BaseCommand):
    help = 'Crea el administrador de producción con variables, sin restablecer una cuenta existente.'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_ADMIN_USERNAME', 'admin').strip().lower()
        password = os.environ.get('DJANGO_ADMIN_PASSWORD', '')
        permitir_admin_local = os.environ.get('DJANGO_ALLOW_INSECURE_ADMIN', '').strip().lower() == 'true'
        if not username or len(username) > 150:
            raise CommandError('DJANGO_ADMIN_USERNAME debe tener entre 1 y 150 caracteres.')
        try:
            UnicodeUsernameValidator()(username)
        except ValidationError as exc:
            raise CommandError('DJANGO_ADMIN_USERNAME contiene caracteres no permitidos.') from exc

        User = get_user_model()
        with transaction.atomic():
            usuario = User.objects.filter(username=username).first()
            if usuario:
                if not usuario.is_staff or not usuario.is_active:
                    raise CommandError('La cuenta indicada ya existe sin acceso administrativo activo; no se modificó.')
                if (usuario.check_password('admin') and not permitir_admin_local) or not usuario.has_usable_password():
                    raise CommandError('Cambia la contraseña local del administrador antes de publicar esta base.')
                Perfil.objects.get_or_create(usuario=usuario)
                self.stdout.write('El administrador ya existe; se conservaron su contraseña y sus permisos.')
                return

            usuario = User(username=username, first_name='Administrador', is_staff=True, is_superuser=False)
            if not password or len(password) > 128:
                raise CommandError('Configura DJANGO_ADMIN_PASSWORD con una contraseña propia de hasta 128 caracteres.')
            # Excepción explícita solicitada por el propietario para su despliegue.
            # No admite otras claves débiles ni se activa en la plantilla por defecto.
            if not (permitir_admin_local and username == 'admin' and password == 'admin'):
                try:
                    validate_password(password, user=usuario)
                except ValidationError as exc:
                    raise CommandError('DJANGO_ADMIN_PASSWORD: ' + ' '.join(exc.messages)) from exc
            usuario.set_password(password)
            usuario.save()
            Perfil.objects.create(usuario=usuario)
        self.stdout.write(self.style.SUCCESS('Administrador de producción creado. La contraseña no se muestra en los registros.'))
