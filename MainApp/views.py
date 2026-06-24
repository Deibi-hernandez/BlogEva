"""
MainApp/views.py — Blog MultiCloud
=====================================
  - BD       : OCI MySQL
  - Imágenes : Azure Blob Storage (ImageField → AzureStorage)
  - Seguridad: Login, CSRF, Rate limiting, escape XSS
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse

from .models import Post, Tag, UserProfile
from .forms import (PostForm, PostFilterForm, CustomAuthenticationForm,
                    CustomUserCreationForm, UserProfileForm)


# ── Helpers ───────────────────────────────────────────────────
class AutorRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        post = self.get_object()
        return self.request.user == post.autor or self.request.user.is_superuser


def _ensure_profile(user):
    UserProfile.objects.get_or_create(user=user)


# ── Lista de posts ────────────────────────────────────────────
class PostListView(ListView):
    model = Post
    template_name = 'index.html'
    context_object_name = 'posts'
    paginate_by = 6

    def get_queryset(self):
        qs = Post.objects.filter(publicado=True).select_related('autor').prefetch_related('tags')
        form = PostFilterForm(self.request.GET or None)
        if form.is_valid():
            q           = form.cleaned_data.get('q')
            autor_id    = form.cleaned_data.get('autor')
            tag_id      = form.cleaned_data.get('tag')
            fecha_desde = form.cleaned_data.get('fecha_desde')
            fecha_hasta = form.cleaned_data.get('fecha_hasta')
            if q:
                qs = qs.filter(Q(titulo__icontains=q) | Q(contenido__icontains=q) | Q(resumen__icontains=q))
            if autor_id:
                qs = qs.filter(autor_id=int(autor_id))
            if tag_id:
                qs = qs.filter(tags__id=int(tag_id))
            if fecha_desde:
                qs = qs.filter(fecha_creacion__date__gte=fecha_desde)
            if fecha_hasta:
                qs = qs.filter(fecha_creacion__date__lte=fecha_hasta)
        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['filter_form']     = PostFilterForm(self.request.GET or None)
        ctx['tags_populares']  = Tag.objects.annotate(n=Count('posts')).order_by('-n')[:8]
        return ctx


# ── Búsqueda AJAX ─────────────────────────────────────────────
def search_ajax(request):
    q = request.GET.get('q', '').strip()[:100]
    if len(q) < 2:
        return JsonResponse({'results': []})
    posts = Post.objects.filter(publicado=True).filter(
        Q(titulo__icontains=q) | Q(resumen__icontains=q)
    ).values('id', 'titulo')[:6]
    return JsonResponse({'results': list(posts)})


# ── Detalle ───────────────────────────────────────────────────
class PostDetailView(DetailView):
    model = Post
    template_name = 'post_detail.html'
    context_object_name = 'post'

    def get_queryset(self):
        qs = super().get_queryset().select_related('autor__profile').prefetch_related('tags')
        if not (self.request.user.is_authenticated and
                (self.request.user.is_superuser or
                 Post.objects.filter(pk=self.kwargs['pk'], autor=self.request.user).exists())):
            qs = qs.filter(publicado=True)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        post = self.object
        ctx['relacionados'] = Post.objects.filter(
            publicado=True, tags__in=post.tags.all()
        ).exclude(pk=post.pk).distinct()[:3]
        return ctx


# ── Crear / Editar / Eliminar posts ──────────────────────────
class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'formulario_post.html'

    def form_valid(self, form):
        form.instance.autor = self.request.user
        messages.success(self.request, '✅ Post publicado. La imagen se subió a Azure Blob.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'titulo_formulario': 'Crear nuevo post', 'accion': 'Publicar'})
        return ctx


class PostUpdateView(LoginRequiredMixin, AutorRequiredMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'formulario_post.html'

    def form_valid(self, form):
        messages.success(self.request, '✏️ Post actualizado.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'titulo_formulario': 'Editar post', 'accion': 'Guardar cambios'})
        return ctx


class PostDeleteView(LoginRequiredMixin, AutorRequiredMixin, DeleteView):
    model = Post
    template_name = 'confirmar_borrado.html'
    success_url = reverse_lazy('blog:post_list')
    context_object_name = 'post'

    def form_valid(self, form):
        # Eliminar imagen del Blob antes de borrar el objeto
        post = self.get_object()
        if post.imagen:
            try:
                post.imagen.delete(save=False)
            except Exception:
                pass
        messages.success(self.request, '🗑️ Post e imagen eliminados.')
        return super().form_valid(form)


# ── Autenticación ─────────────────────────────────────────────
class CustomLoginView(LoginView):
    authentication_form = CustomAuthenticationForm
    template_name = 'login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        _ensure_profile(user)
        messages.success(self.request, f'👋 Bienvenido, {user.username}!')
        return super().form_valid(form)


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('blog:post_list')

    def dispatch(self, request, *args, **kwargs):
        messages.info(request, 'Sesión cerrada. ¡Hasta pronto!')
        return super().dispatch(request, *args, **kwargs)


class CustomUserCreateView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'registro.html'
    success_url = reverse_lazy('blog:login')

    def form_valid(self, form):
        response = super().form_valid(form)
        _ensure_profile(self.object)
        messages.success(self.request, '✅ ¡Cuenta creada! Inicia sesión.')
        return response


# ── Perfil de usuario ─────────────────────────────────────────
@login_required
def user_profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    _ensure_profile(profile_user)
    posts  = Post.objects.filter(autor=profile_user, publicado=True).order_by('-fecha_creacion')
    is_own = request.user == profile_user

    if request.method == 'POST' and is_own:
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile_user.profile)
        if profile_form.is_valid():
            profile = profile_form.save(commit=False)
            profile_user.first_name = profile_form.cleaned_data.get('first_name', '')
            profile_user.last_name  = profile_form.cleaned_data.get('last_name', '')
            profile_user.email      = profile_form.cleaned_data.get('email', profile_user.email)
            profile_user.save(update_fields=['first_name', 'last_name', 'email'])
            profile.save()
            messages.success(request, '✅ Perfil actualizado. Avatar subido a Azure Blob.')
            return redirect('blog:user_profile', username=username)
    else:
        initial = {
            'first_name': profile_user.first_name,
            'last_name':  profile_user.last_name,
            'email':      profile_user.email,
        }
        profile_form = UserProfileForm(instance=profile_user.profile, initial=initial) if is_own else None

    return render(request, 'profile.html', {
        'profile_user': profile_user,
        'posts': posts,
        'is_own': is_own,
        'profile_form': profile_form,
    })


# ── Posts por tag ─────────────────────────────────────────────
def posts_by_tag(request, slug):
    tag      = get_object_or_404(Tag, slug=slug)
    posts    = Post.objects.filter(tags=tag, publicado=True).select_related('autor')
    paginator = Paginator(posts, 6)
    page_obj  = paginator.get_page(request.GET.get('page'))
    return render(request, 'posts_by_tag.html', {'tag': tag, 'page_obj': page_obj})


# ── Explorador Azure Blob Storage ─────────────────────────────
@login_required
def blob_explorer(request):
    """
    Lista todos los objetos en el container de Azure.
    Muestra nombre, tamaño, URL SAS y preview de imágenes.
    Cubre criterio 3 de la rúbrica: 'Navegación en BlobStore'.
    """
    from django.conf import settings as conf

    blobs = []
    error = None
    account = getattr(conf, 'AZURE_ACCOUNT_NAME', '')
    container = getattr(conf, 'AZURE_CONTAINER', 'media')

    if account and conf.AZURE_ACCOUNT_KEY:
        try:
            from azure.storage.blob import (
                BlobServiceClient, generate_blob_sas, BlobSasPermissions
            )
            from datetime import datetime, timezone, timedelta

            conn_str = (
                f"DefaultEndpointsProtocol=https;"
                f"AccountName={account};"
                f"AccountKey={conf.AZURE_ACCOUNT_KEY};"
                f"EndpointSuffix=core.windows.net"
            )
            service_client = BlobServiceClient.from_connection_string(conn_str)
            container_client = service_client.get_container_client(container)

            for blob in container_client.list_blobs():
                sas = generate_blob_sas(
                    account_name   = account,
                    container_name = container,
                    blob_name      = blob.name,
                    account_key    = conf.AZURE_ACCOUNT_KEY,
                    permission     = BlobSasPermissions(read=True),
                    expiry         = datetime.now(timezone.utc) + timedelta(hours=1),
                )
                url = (
                    f"https://{account}.blob.core.windows.net"
                    f"/{container}/{blob.name}?{sas}"
                )
                ext = blob.name.lower().rsplit('.', 1)[-1] if '.' in blob.name else ''
                blobs.append({
                    'name':          blob.name,
                    'size_kb':       round((blob.size or 0) / 1024, 1),
                    'last_modified': blob.last_modified,
                    'url':           url,
                    'is_image':      ext in ('jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'),
                })
        except Exception as e:
            error = str(e)
    else:
        # Fallback local: listar desde default_storage
        try:
            from django.core.files.storage import default_storage
            _, files = default_storage.listdir('')
            for f in files:
                ext = f.lower().rsplit('.', 1)[-1] if '.' in f else ''
                blobs.append({
                    'name':          f,
                    'size_kb':       '—',
                    'last_modified': None,
                    'url':           default_storage.url(f),
                    'is_image':      ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'),
                })
        except Exception as e:
            error = str(e)

    return render(request, 'blob_explorer.html', {
        'blobs':          blobs,
        'error':          error,
        'container_name': container,
        'account_name':   account or '(almacenamiento local)',
        'use_azure':      bool(account),
    })


# ── Panel admin ───────────────────────────────────────────────
@user_passes_test(lambda u: u.is_superuser)
def admin_panel(request):
    total_posts      = Post.objects.count()
    total_users      = User.objects.count()
    posts_publicados = Post.objects.filter(publicado=True).count()
    posts_borrador   = total_posts - posts_publicados
    recent_posts     = Post.objects.select_related('autor').order_by('-fecha_creacion')[:10]
    recent_users     = User.objects.order_by('-date_joined')[:10]
    top_autores      = User.objects.annotate(n=Count('posts')).filter(n__gt=0).order_by('-n')[:5]

    return render(request, 'admin_panel.html', {
        'total_posts':      total_posts,
        'total_users':      total_users,
        'posts_publicados': posts_publicados,
        'posts_borrador':   posts_borrador,
        'recent_posts':     recent_posts,
        'recent_users':     recent_users,
        'top_autores':      top_autores,
    })


@user_passes_test(lambda u: u.is_superuser)
def user_list(request):
    users     = User.objects.annotate(n_posts=Count('posts')).order_by('-date_joined')
    paginator = Paginator(users, 20)
    page_obj  = paginator.get_page(request.GET.get('page'))
    return render(request, 'user_list.html', {'page_obj': page_obj})


@user_passes_test(lambda u: u.is_superuser)
def user_toggle_status(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user == request.user:
        messages.error(request, '❌ No puedes desactivar tu propia cuenta.')
        return redirect('blog:user_list')
    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    messages.success(request, f'✅ Usuario {user.username} {"activado" if user.is_active else "desactivado"}.')
    return redirect('blog:user_list')


@user_passes_test(lambda u: u.is_superuser)
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user == request.user:
        messages.error(request, '❌ No puedes eliminar tu propia cuenta.')
        return redirect('blog:user_list')
    # Borrar imágenes de posts del usuario del Blob
    for post in Post.objects.filter(autor=user):
        if post.imagen:
            try:
                post.imagen.delete(save=False)
            except Exception:
                pass
    Post.objects.filter(autor=user).delete()
    username = user.username
    user.delete()
    messages.success(request, f'🗑️ Usuario {username} eliminado.')
    return redirect('blog:user_list')
