# Generated by Django 2.0.7 on 2018-08-04 11:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0020_auto_20180804_1059'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='collageuser',
            name='sku',
        ),
        migrations.AddField(
            model_name='collageuser',
            name='collageSku',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='main.CollageSku'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='collage',
            name='endTime',
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name='collage',
            name='startTime',
            field=models.DateTimeField(),
        ),
    ]
