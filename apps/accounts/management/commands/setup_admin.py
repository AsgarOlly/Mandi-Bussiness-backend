import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.accounts.models import Role, UserProfile

class Command(BaseCommand):
    help = 'Create or initialize the default administrator user safely without exposed passwords in login'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default=os.getenv('ADMIN_USERNAME', 'admin'))
        parser.add_argument('--password', type=str, default=os.getenv('ADMIN_PASSWORD', ''))
        parser.add_argument('--email', type=str, default='admin@fruiterp.com')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']

        if not password:
            self.stdout.write(self.style.WARNING("No password provided via --password or ADMIN_PASSWORD env var."))
            import secrets
            password = secrets.token_urlsafe(12)
            self.stdout.write(self.style.SUCCESS(f"Generated secure initial password: {password}"))

        super_role, _ = Role.objects.get_or_create(
            code='SUPER_ADMIN',
            defaults={'name': 'Super Admin', 'description': 'Full System Administrator'}
        )

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': 'System',
                'last_name': 'Admin',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            }
        )

        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()

        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={'role': super_role, 'employee_code': 'EMP-001', 'status': 'ACTIVE'}
        )
        if profile.role != super_role:
            profile.role = super_role
            profile.save()

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"Successfully {action} admin user '{username}'."))
