# Generated by Django 2.0.7 on 2018-08-03 22:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0018_comment_sku'),
    ]

    operations = [
        migrations.AddField(
            model_name='sku',
            name='commentNum',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sku',
            name='rate',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
