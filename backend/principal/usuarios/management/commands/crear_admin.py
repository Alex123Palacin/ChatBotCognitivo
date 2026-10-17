from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email

from usuarios.models import Perfil


class Command(BaseCommand):
    help = 'Crea un administrador local. La contraseña se solicita sin mostrarla.'

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True)
        parser.add_argument('--nombre', default='Administrador')

    def handle(self, *args, **options):
        email = options['email'].strip().lower()
        try:
            validate_email(email)
        except ValidationError as exc:
            raise CommandError('Escribe una dirección de correo válida.') from exc
        User = get_user_model()
        if len(email) > 150 or User.objects.filter(username=email).exists():
            raise CommandError('El correo ya existe o supera 150 caracteres.')
        password = getpass('Contraseña: ')
        if password != getpass('Repite la contraseña: '):
            raise CommandError('Las contraseñas no coinciden.')
        usuario = User(username=email, email=email, first_name=options['nombre'], is_staff=True, is_superuser=False)
        try:
            validate_password(password, user=usuario)
        except ValidationError as exc:
            raise CommandError(' '.join(exc.messages)) from exc
        usuario.set_password(password)
        usuario.save()
        Perfil.objects.create(usuario=usuario)
        self.stdout.write(self.style.SUCCESS(f'Administrador creado: {email}'))
