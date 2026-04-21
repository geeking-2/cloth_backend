from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0001_initial'),
        ('reviews', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Wipe any existing rows so new non-nullable fields can be added cleanly
        migrations.RunSQL(
            sql='DELETE FROM reviews_review;',
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Drop the OneToOne constraint on booking by replacing the FK
        migrations.AlterField(
            model_name='review',
            name='booking',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='reviews',
                to='bookings.booking',
            ),
        ),
        migrations.AddField(
            model_name='review',
            name='reviewee',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='reviews_received',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='review',
            name='direction',
            field=models.CharField(
                choices=[
                    ('creator_to_venue', 'Creator → Venue'),
                    ('venue_to_creator', 'Venue → Creator'),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterUniqueTogether(
            name='review',
            unique_together={('booking', 'reviewer')},
        ),
    ]
