from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('MainApp.urls', namespace='blog')),
]

# Servir media local solo en desarrollo sin Azure
if settings.DEBUG and not settings.AZURE_ACCOUNT_NAME:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
