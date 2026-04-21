from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('proposals', '0003_portfolioproject_external_links_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='portfolioproject',
            name='client_name',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='portfolioproject',
            name='role',
            field=models.CharField(
                blank=True, default='', max_length=200,
                help_text='e.g. "Lead artist & creative director"',
            ),
        ),
        migrations.AddField(
            model_name='portfolioproject',
            name='brief',
            field=models.TextField(blank=True, default='', help_text='The problem / starting point'),
        ),
        migrations.AddField(
            model_name='portfolioproject',
            name='outcome',
            field=models.TextField(blank=True, default='', help_text='What happened. Numbers welcome.'),
        ),
        migrations.AddField(
            model_name='portfolioproject',
            name='metrics',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
