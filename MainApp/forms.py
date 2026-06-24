"""
MainApp/forms.py — versión segura y extendida
"""
import re, html
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Post, Tag, UserProfile


# ── Utilidades de sanitización ────────────────────────────────
def sanitize_text(value: str) -> str:
    return html.escape(value.strip())

def no_html_tags(value: str):
    if re.search(r'<[^>]+>', value):
        raise ValidationError('El campo no puede contener etiquetas HTML.', code='xss_attempt')


# ── Formulario de Post ────────────────────────────────────────
class PostForm(forms.ModelForm):
    class Meta:
        model  = Post
        fields = ['titulo', 'resumen', 'contenido', 'imagen', 'tags', 'publicado']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Título del post…',
                'maxlength': '200', 'autocomplete': 'off',
            }),
            'resumen': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
                'placeholder': 'Resumen breve (opcional)…', 'maxlength': '300',
            }),
            'contenido': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 10,
                'placeholder': 'Escribe aquí el contenido…', 'maxlength': '20000',
            }),
            'imagen': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'tags': forms.CheckboxSelectMultiple(),
            'publicado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'titulo': 'Título', 'resumen': 'Resumen', 'contenido': 'Contenido',
            'imagen': 'Imagen de portada', 'tags': 'Etiquetas', 'publicado': 'Publicar ahora',
        }

    def clean_titulo(self):
        v = self.cleaned_data.get('titulo', '')
        no_html_tags(v)
        return sanitize_text(v)

    def clean_resumen(self):
        v = self.cleaned_data.get('resumen', '')
        no_html_tags(v)
        return sanitize_text(v)

    def clean_contenido(self):
        v = self.cleaned_data.get('contenido', '')
        no_html_tags(v)
        return html.escape(v.strip())

    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')
        if imagen and hasattr(imagen, 'content_type'):
            if not imagen.content_type.startswith('image/'):
                raise ValidationError('Solo se permiten archivos de imagen.')
            if imagen.size > 5 * 1024 * 1024:
                raise ValidationError('La imagen no puede superar 5 MB.')
        return imagen


# ── Filtro de posts ───────────────────────────────────────────
class PostFilterForm(forms.Form):
    q = forms.CharField(
        required=False, label='Buscar',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Buscar posts…', 'autocomplete': 'off',
        }),
    )
    autor = forms.ChoiceField(
        required=False, label='Autor',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )
    tag = forms.ChoiceField(
        required=False, label='Tag',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )
    fecha_desde = forms.DateField(
        required=False, label='Desde',
        widget=forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
    )
    fecha_hasta = forms.DateField(
        required=False, label='Hasta',
        widget=forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        autores = User.objects.filter(posts__isnull=False).distinct()
        self.fields['autor'].choices = [('', 'Todos los autores')] + [
            (str(u.id), u.get_full_name() or u.username) for u in autores
        ]
        tags = Tag.objects.all()
        self.fields['tag'].choices = [('', 'Todos los tags')] + [
            (str(t.id), t.nombre) for t in tags
        ]

    def clean_autor(self):
        v = self.cleaned_data.get('autor', '')
        if v and not v.isdigit():
            raise ValidationError('ID de autor inválido.')
        return v

    def clean_q(self):
        v = self.cleaned_data.get('q', '')
        no_html_tags(v)
        return v.strip()[:100]

    def clean(self):
        c = super().clean()
        d, h = c.get('fecha_desde'), c.get('fecha_hasta')
        if d and h and d > h:
            raise ValidationError('"Desde" no puede ser posterior a "Hasta".')
        return c


# ── Login ─────────────────────────────────────────────────────
class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label='Usuario', max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Nombre de usuario',
            'autofocus': True, 'autocomplete': 'username',
        }),
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 'placeholder': 'Contraseña',
            'autocomplete': 'current-password',
        }),
    )

    def clean_username(self):
        v = self.cleaned_data.get('username', '')
        if not re.match(r'^[\w.@+\-]+$', v):
            raise ValidationError('Nombre de usuario inválido.')
        return v


# ── Registro ──────────────────────────────────────────────────
class CustomUserCreationForm(UserCreationForm):
    username = forms.CharField(
        label='Usuario', max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario', 'autocomplete': 'username'}),
    )
    email = forms.EmailField(
        label='Correo',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'tu@email.com', 'autocomplete': 'email'}),
    )
    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña segura', 'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repite la contraseña', 'autocomplete': 'new-password'}),
    )

    class Meta:
        model  = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_username(self):
        v = self.cleaned_data.get('username', '')
        if not re.match(r'^[\w.@+\-]+$', v):
            raise ValidationError('Solo letras, números y @/./+/-/_')
        return v

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        if User.objects.filter(email=email).exists():
            raise ValidationError('Ya existe una cuenta con ese correo.')
        return email


# ── Perfil de usuario ─────────────────────────────────────────
class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        required=False, label='Nombre',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu nombre'}),
    )
    last_name = forms.CharField(
        required=False, label='Apellido',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu apellido'}),
    )
    email = forms.EmailField(
        required=False, label='Correo',
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model  = UserProfile
        fields = ['bio', 'avatar', 'website']
        widgets = {
            'bio':     forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Cuéntanos sobre ti…', 'maxlength': '500'}),
            'avatar':  forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://…'}),
        }

    def clean_bio(self):
        v = self.cleaned_data.get('bio', '')
        no_html_tags(v)
        return sanitize_text(v)

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar and hasattr(avatar, 'content_type'):
            if not avatar.content_type.startswith('image/'):
                raise ValidationError('Solo se permiten imágenes.')
            if avatar.size > 2 * 1024 * 1024:
                raise ValidationError('El avatar no puede superar 2 MB.')
        return avatar
