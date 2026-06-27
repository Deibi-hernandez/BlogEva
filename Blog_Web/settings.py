"""
Django settings — Blog_Web (MultiCloud: OCI MySQL + Azure Blob)
================================================================
  - Base de datos : OCI MySQL (túnel SSH → 127.0.0.1:3306)
  - Imágenes      : Azure Blob Storage (django-storages)
  - Seguridad     : variables de entorno, NUNCA credenciales en código
"""

from pathlib import Path
import os
from dotenv import load_dotenv
import urllib.request

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

TEMPLATES_DIR = BASE_DIR / 'templates'
STATIC_DIR    = BASE_DIR / 'static'
MEDIA_ROOT    = BASE_DIR / 'media'   # fallback local si no hay Azure

# ── Seguridad base ────────────────────────────────────────────
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
DEBUG      = os.getenv('DJANGO_DEBUG', 'False') == 'True'
ALLOWED_HOSTS = [h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')]
try:
    url = 'https://checkip.amazonaws.com'
    public_ip = urllib.request.urlopen(url, timeout=3).read().decode('utf-8').strip()
    if public_ip and public_ip not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(public_ip)
except Exception:
    pass

# ── Apps ──────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'storages',   # django-storages (Azure)
    'MainApp',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'MainApp.security_middleware.RateLimitMiddleware',
]

ROOT_URLCONF = 'Blog_Web.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [TEMPLATES_DIR],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ],
        'autoescape': True,
    },
}]

WSGI_APPLICATION = 'Blog_Web.wsgi.application'

# ════════════════════════════════════════════════════════════════
#  BASE DE DATOS — OCI MySQL
#  Requisito previo: túnel SSH activo en 127.0.0.1:3306
#  ssh -N -L 3306:10.0.1.212:3306 -p 22 -i ssh-key.key ocid1...
# ════════════════════════════════════════════════════════════════
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.mysql',
        'NAME':     os.environ['DB_NAME'],
        'USER':     os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST':     os.getenv('DB_HOST', '127.0.0.1'),
        'PORT':     os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# ════════════════════════════════════════════════════════════════
#  ALMACENAMIENTO — Azure Blob Storage
#  Todas las imágenes (posts + avatares) van al container de Azure.
#  Si las variables Azure no están definidas, cae a almacenamiento local.
# ════════════════════════════════════════════════════════════════
_AZURE_ACCOUNT = os.getenv('AZURE_ACCOUNT_NAME', '')
_AZURE_KEY     = os.getenv('AZURE_ACCOUNT_KEY', '')
_AZURE_CONT    = os.getenv('AZURE_CONTAINER', 'media')
_USE_AZURE     = bool(_AZURE_ACCOUNT and _AZURE_KEY)

# Exponer para las vistas (explorador de Blob)
AZURE_ACCOUNT_NAME = _AZURE_ACCOUNT
AZURE_ACCOUNT_KEY  = _AZURE_KEY
AZURE_CONTAINER    = _AZURE_CONT

if _USE_AZURE:
    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.azure_storage.AzureStorage',
            'OPTIONS': {
                'account_name':    _AZURE_ACCOUNT,
                'account_key':     _AZURE_KEY,
                'azure_container': _AZURE_CONT,
                'overwrite_files': True,
                'expiration_secs': 3600,   # URL SAS con 1 hora de vida
            },
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }
    MEDIA_URL = (
        f"https://{_AZURE_ACCOUNT}.blob.core.windows.net/{_AZURE_CONT}/"
    )
else:
    # ── Fallback local (desarrollo sin credenciales Azure) ────
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }
    MEDIA_URL = '/media/'

# ── Autenticación ─────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL           = 'blog:login'
LOGIN_REDIRECT_URL  = 'blog:post_list'
LOGOUT_REDIRECT_URL = 'blog:post_list'

# ── i18n ──────────────────────────────────────────────────────
LANGUAGE_CODE = 'es-es'
TIME_ZONE     = 'America/Santiago'
USE_I18N = True
USE_TZ   = True

# ── Archivos estáticos ────────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [STATIC_DIR]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Mensajes Bootstrap ────────────────────────────────────────
from django.contrib.messages import constants as messages_const
MESSAGE_TAGS = {
    messages_const.DEBUG:   'secondary',
    messages_const.INFO:    'info',
    messages_const.SUCCESS: 'success',
    messages_const.WARNING: 'warning',
    messages_const.ERROR:   'danger',
}

# ════════════════════════════════════════════════════════════════
#  CABECERAS DE SEGURIDAD HTTP
# ════════════════════════════════════════════════════════════════
SECURE_BROWSER_XSS_FILTER    = True
SECURE_CONTENT_TYPE_NOSNIFF  = True
X_FRAME_OPTIONS              = 'DENY'
SESSION_COOKIE_HTTPONLY      = True
CSRF_COOKIE_HTTPONLY         = True

# CSP ampliado para permitir imágenes desde Azure Blob
_azure_origin = (
    f"https://{_AZURE_ACCOUNT}.blob.core.windows.net"
    if _AZURE_ACCOUNT else ""
)
CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.jsdelivr.net; "
    "style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
    f"img-src 'self' data: {_azure_origin}; "
    "frame-ancestors 'none';"
)

# ── Rate limiting (login) ─────────────────────────────────────
RATE_LIMIT_LOGIN_MAX    = 10
RATE_LIMIT_LOGIN_WINDOW = 300
