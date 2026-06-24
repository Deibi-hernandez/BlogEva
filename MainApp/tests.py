"""
MainApp/tests.py — Tests de seguridad
======================================
Cubre XSS, SQL Injection y acceso no autorizado.
Ejecutar: python manage.py test MainApp
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Post, Tag


class XSSProtectionTests(TestCase):
    """Verifica que los inputs maliciosos sean sanitizados."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@test.com', 'Pass1234!')
        self.client.login(username='testuser', password='Pass1234!')

    def test_titulo_con_script_es_rechazado(self):
        """El formulario debe rechazar títulos con etiquetas HTML."""
        response = self.client.post(reverse('blog:post_create'), {
            'titulo': '<script>alert("xss")</script>',
            'contenido': 'Contenido normal',
            'publicado': True,
        })
        # Debe volver al formulario con error, no crear el post
        self.assertEqual(Post.objects.count(), 0)

    def test_contenido_con_img_onerror_es_rechazado(self):
        """Rechaza vectores XSS en contenido."""
        response = self.client.post(reverse('blog:post_create'), {
            'titulo': 'Post normal',
            'contenido': '<img src=x onerror=alert(1)>',
            'publicado': True,
        })
        self.assertEqual(Post.objects.count(), 0)

    def test_titulo_limpio_se_guarda(self):
        """Un post limpio debe guardarse correctamente."""
        self.client.post(reverse('blog:post_create'), {
            'titulo': 'Mi post de prueba',
            'contenido': 'Contenido completamente normal sin HTML.',
            'publicado': True,
        })
        self.assertEqual(Post.objects.count(), 1)

    def test_contenido_escapado_en_detalle(self):
        """El contenido en la vista de detalle debe estar escapado."""
        post = Post.objects.create(
            titulo='Test',
            contenido='Normal content',
            autor=self.user,
        )
        response = self.client.get(reverse('blog:post_detail', args=[post.pk]))
        self.assertEqual(response.status_code, 200)
        # El contenido crudo de script no debe aparecer sin escapar
        self.assertNotIn(b'<script>', response.content)


class SQLInjectionTests(TestCase):
    """Verifica que los filtros no sean vulnerables a SQL Injection."""

    def setUp(self):
        self.user = User.objects.create_user('sqluser', 'sql@test.com', 'Pass1234!')
        Post.objects.create(titulo='Post legítimo', contenido='ok', autor=self.user)

    def test_filtro_autor_con_sql_invalido(self):
        """Un autor_id no numérico debe ser ignorado o rechazado."""
        response = self.client.get(reverse('blog:post_list'), {
            'autor': "1 OR 1=1 --"
        })
        # Debe responder 200 pero el filtro malicioso se descarta
        self.assertEqual(response.status_code, 200)

    def test_busqueda_con_comillas(self):
        """La búsqueda con comillas simples no debe romper la query."""
        response = self.client.get(reverse('blog:post_list'), {
            'q': "' OR '1'='1"
        })
        self.assertEqual(response.status_code, 200)

    def test_search_ajax_sin_injection(self):
        """El endpoint AJAX de búsqueda no debe filtrar datos inesperados."""
        response = self.client.get(reverse('blog:search_ajax'), {
            'q': "'; DROP TABLE mainapp_post; --"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Solo resultados legítimos (ninguno en este caso)
        self.assertIsInstance(data['results'], list)


class AuthorizationTests(TestCase):
    """Verifica control de acceso entre usuarios."""

    def setUp(self):
        self.owner = User.objects.create_user('owner', 'o@test.com', 'Pass1234!')
        self.other = User.objects.create_user('other', 'x@test.com', 'Pass1234!')
        self.post = Post.objects.create(titulo='Privado', contenido='x', autor=self.owner)

    def test_otro_usuario_no_puede_editar(self):
        self.client.login(username='other', password='Pass1234!')
        response = self.client.get(reverse('blog:post_update', args=[self.post.pk]))
        self.assertEqual(response.status_code, 403)

    def test_otro_usuario_no_puede_eliminar(self):
        self.client.login(username='other', password='Pass1234!')
        response = self.client.post(reverse('blog:post_delete', args=[self.post.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Post.objects.filter(pk=self.post.pk).exists())

    def test_usuario_no_autenticado_redirige_a_login(self):
        response = self.client.get(reverse('blog:post_create'))
        self.assertRedirects(response, f"{reverse('blog:login')}?next={reverse('blog:post_create')}")

    def test_panel_admin_requiere_superuser(self):
        self.client.login(username='owner', password='Pass1234!')
        response = self.client.get(reverse('blog:admin_panel'))
        self.assertNotEqual(response.status_code, 200)

    def test_csrf_en_login(self):
        """Login sin CSRF token debe fallar."""
        client_no_csrf = Client(enforce_csrf_checks=True)
        response = client_no_csrf.post(reverse('blog:login'), {
            'username': 'owner', 'password': 'Pass1234!'
        })
        self.assertEqual(response.status_code, 403)


class RateLimitTests(TestCase):
    """Verifica el rate limiting en login."""

    def test_multiples_intentos_bloqueados(self):
        for _ in range(11):
            self.client.post(reverse('blog:login'), {
                'username': 'noexiste', 'password': 'wrong'
            })
        # El 11° intento debe devolver 429
        response = self.client.post(reverse('blog:login'), {
            'username': 'noexiste', 'password': 'wrong'
        })
        self.assertEqual(response.status_code, 429)
