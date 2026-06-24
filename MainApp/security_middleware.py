"""
MainApp/security_middleware.py
==============================
Middleware de seguridad personalizado:
  1. Inyecta cabeceras Content-Security-Policy (CSP) → bloquea XSS externo
  2. Rate limiting en /login/ → frena fuerza bruta / SQL-injection automático
"""

import time
from collections import defaultdict
from threading import Lock

from django.conf import settings
from django.http import HttpResponse


# ── Almacén en memoria para rate limiting ─────────────────────
# En producción con múltiples workers usa Redis (django-ratelimit).
_login_attempts: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


class RateLimitMiddleware:
    """
    Limita intentos de login por IP.
    Configurable en settings:
        RATE_LIMIT_LOGIN_MAX    (default 10)
        RATE_LIMIT_LOGIN_WINDOW (default 300 segundos)
    """

    LOGIN_PATH = '/login/'

    def __init__(self, get_response):
        self.get_response = get_response
        self.max_attempts = getattr(settings, 'RATE_LIMIT_LOGIN_MAX', 10)
        self.window = getattr(settings, 'RATE_LIMIT_LOGIN_WINDOW', 300)

    def __call__(self, request):
        if request.method == 'POST' and self.LOGIN_PATH in request.path:
            ip = self._get_ip(request)
            if self._is_rate_limited(ip):
                return HttpResponse(
                    '<h2>Demasiados intentos. Espera 5 minutos.</h2>',
                    status=429,
                    content_type='text/html; charset=utf-8',
                )

        response = self.get_response(request)

        # ── Inyectar cabeceras de seguridad ──────────────────
        csp = getattr(settings, 'CSP_POLICY', None)
        if csp:
            response['Content-Security-Policy'] = csp

        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

        return response

    # ── Helpers ──────────────────────────────────────────────

    def _get_ip(self, request) -> str:
        """Obtiene la IP real considerando proxies confiables."""
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')

    def _is_rate_limited(self, ip: str) -> bool:
        now = time.time()
        with _lock:
            # Eliminar intentos fuera de la ventana
            _login_attempts[ip] = [
                t for t in _login_attempts[ip]
                if now - t < self.window
            ]
            if len(_login_attempts[ip]) >= self.max_attempts:
                return True
            _login_attempts[ip].append(now)
            return False
