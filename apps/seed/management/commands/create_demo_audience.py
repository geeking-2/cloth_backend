from datetime import date
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from apps.accounts.models import AudienceProfile


class Command(BaseCommand):
    help = 'Create a demo audience user for testing the live site.'

    def handle(self, *args, **options):
        User = get_user_model()
        username = 'audience_demo'
        email = 'audience_demo@cultureconnect.test'
        password = 'AudienceDemo123!'

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'role': 'audience',
                'first_name': 'Alex',
                'last_name': 'Audience',
                'is_verified': True,
            },
        )
        user.role = 'audience'
        user.is_verified = True
        user.set_password(password)
        user.save()

        AudienceProfile.objects.get_or_create(
            user=user,
            defaults={
                'display_name': 'Alex Audience',
                'city': 'Brooklyn',
                'country': 'US',
                'date_of_birth': date(1995, 6, 15),
                'interests': ['Performance', 'Exhibitions', 'Workshops'],
                'is_public': True,
            },
        )

        self.stdout.write(self.style.SUCCESS(
            f'OK  username={username}  email={email}  password={password}  created={created}'
        ))
