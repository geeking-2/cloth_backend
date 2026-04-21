from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TicketWaitlist',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('notified_at', models.DateTimeField(blank=True, null=True)),
                ('tier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='waitlist_entries', to='tickets.tickettier')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='waitlists', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at'],
                'indexes': [models.Index(fields=['tier', 'created_at'],
                                         name='tickets_tic_tier_id_idx')],
                'unique_together': {('tier', 'user')},
            },
        ),
    ]
