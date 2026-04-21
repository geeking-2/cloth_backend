from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Create admin superuser and verify all demo users'

    def handle(self, *args, **options):
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                'admin', 'geektiste@gmail.com', 'admin123', role='venue', is_verified=True
            )
            self.stdout.write('Admin created')
        else:
            self.stdout.write('Admin already exists')

        count = User.objects.filter(is_verified=False).update(is_verified=True)
        self.stdout.write(f'Verified {count} users')
