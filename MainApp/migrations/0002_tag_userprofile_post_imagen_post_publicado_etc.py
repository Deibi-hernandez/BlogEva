from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('MainApp', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=50, unique=True, verbose_name='Nombre')),
                ('slug', models.SlugField(unique=True)),
            ],
            options={'verbose_name': 'Tag', 'verbose_name_plural': 'Tags', 'ordering': ['nombre']},
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bio', models.TextField(blank=True, max_length=500, verbose_name='Biografía')),
                ('avatar', models.ImageField(blank=True, null=True, upload_to='avatars/', verbose_name='Avatar')),
                ('website', models.URLField(blank=True, verbose_name='Sitio web')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='post',
            name='imagen',
            field=models.ImageField(blank=True, null=True, upload_to='posts/%Y/%m/', verbose_name='Imagen de portada'),
        ),
        migrations.AddField(
            model_name='post',
            name='publicado',
            field=models.BooleanField(default=True, verbose_name='Publicado'),
        ),
        migrations.AddField(
            model_name='post',
            name='resumen',
            field=models.CharField(blank=True, max_length=300, verbose_name='Resumen'),
        ),
        migrations.AddField(
            model_name='post',
            name='tags',
            field=models.ManyToManyField(blank=True, related_name='posts', to='MainApp.tag', verbose_name='Tags'),
        ),
        migrations.AddIndex(
            model_name='post',
            index=models.Index(fields=['autor', '-fecha_creacion'], name='mainapp_pos_autor_i_idx'),
        ),
        migrations.AddIndex(
            model_name='post',
            index=models.Index(fields=['publicado', '-fecha_creacion'], name='mainapp_pos_publica_idx'),
        ),
    ]
