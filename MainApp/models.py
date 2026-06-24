from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse


class Tag(models.Model):
    """Etiqueta de categoría para posts."""
    nombre = models.CharField(max_length=50, unique=True, verbose_name="Nombre")
    slug   = models.SlugField(max_length=50, unique=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

    def __str__(self):
        return self.nombre


class Post(models.Model):
    titulo    = models.CharField(max_length=200, verbose_name="Título")
    contenido = models.TextField(verbose_name="Contenido")
    resumen   = models.CharField(
        max_length=300, blank=True,
        verbose_name="Resumen",
        help_text="Descripción corta (opcional). Si se deja vacío se genera del contenido."
    )
    imagen    = models.ImageField(
        upload_to='posts/%Y/%m/',
        blank=True, null=True,
        verbose_name="Imagen de portada"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts', verbose_name="Tags")
    autor = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='posts', verbose_name="Autor"
    )
    fecha_creacion     = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última actualización")
    publicado          = models.BooleanField(default=True, verbose_name="Publicado")

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = "Post"
        verbose_name_plural = "Posts"
        indexes = [
            models.Index(fields=['autor', '-fecha_creacion']),
            models.Index(fields=['publicado', '-fecha_creacion']),
        ]

    def __str__(self):
        return self.titulo

    def get_absolute_url(self):
        return reverse('blog:post_detail', kwargs={'pk': self.pk})

    def get_resumen(self):
        """Devuelve el resumen o los primeros 200 chars del contenido."""
        if self.resumen:
            return self.resumen
        return self.contenido[:200] + ('…' if len(self.contenido) > 200 else '')


class UserProfile(models.Model):
    """Perfil extendido del usuario."""
    user    = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio     = models.TextField(max_length=500, blank=True, verbose_name="Biografía")
    avatar  = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="Avatar")
    website = models.URLField(blank=True, verbose_name="Sitio web")

    def __str__(self):
        return f"Perfil de {self.user.username}"
