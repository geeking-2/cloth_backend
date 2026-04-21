from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_notification'),
    ]

    operations = [
        migrations.AddField(
            model_name='venueprofile',
            name='stripe_account_id',
            field=models.CharField(blank=True, default='', max_length=80),
        ),
        migrations.AddField(
            model_name='venueprofile',
            name='stripe_charges_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='venueprofile',
            name='stripe_payouts_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='venueprofile',
            name='stripe_details_submitted',
            field=models.BooleanField(default=False),
        ),
    ]
