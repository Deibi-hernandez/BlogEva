from django.contrib import admin
from django.utils.html import format_html
from .models import Post, Tag, UserProfile


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display  = ['nombre', 'slug', 'total_posts']
    prepopulated_fields = {'slug': ('nombre',)}
    search_fields = ['nombre']

    def total_posts(self, obj):
        return obj.posts.count()
    total_posts.short_description = "Posts"


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display   = ['titulo', 'autor', 'publicado', 'fecha_creacion', 'preview_imagen']
    list_filter    = ['publicado', 'fecha_creacion', 'autor', 'tags']
    search_fields  = ['titulo', 'contenido', 'autor__username']
    list_editable  = ['publicado']
    filter_horizontal = ['tags']
    date_hierarchy = 'fecha_creacion'
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']

    def preview_imagen(self, obj):
        if obj.imagen:
            return format_html('<img src="{}" width="50" height="50" style="object-fit:cover;border-radius:4px">', obj.imagen.url)
        return '—'
    preview_imagen.short_description = "Imagen"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'bio_preview', 'website']
    search_fields = ['user__username', 'user__email']

    def bio_preview(self, obj):
        return obj.bio[:60] + '…' if len(obj.bio) > 60 else obj.bio
    bio_preview.short_description = "Bio"
