# Generated by Django 2.0.7 on 2018-08-02 12:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0012_distribution'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='receiveTime',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
