# Generated by Django 2.0.7 on 2018-08-02 09:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0009_auto_20180802_0922'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='payTime',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]