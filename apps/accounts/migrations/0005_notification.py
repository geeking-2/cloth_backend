from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_alter_user_role_audienceprofile'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[
                    ('invite', 'Invite'),
                    ('invite_response', 'Invite response'),
                    ('broadcast', 'Broadcast'),
                    ('rsvp', 'RSVP'),
                    ('follow', 'Follow'),
                    ('ticket_sold', 'Ticket sold'),
                    ('booking', 'Booking'),
                    ('waitlist', 'Waitlist'),
                ], max_length=30)),
                ('title', models.CharField(max_length=200)),
                ('body', models.CharField(blank=True, default='', max_length=500)),
                ('url', models.CharField(blank=True, default='', max_length=300)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='notifications_sent', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['user', 'read_at', '-created_at'],
                                         name='accounts_no_user_id_idx')],
            },
        ),
    ]
