"""
Django admin customization.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from core import models

from .models import Compra, ItemCompra, ItemPedido


class ItemCompraInline(admin.TabularInline):
    model = ItemCompra
    extra = 1


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    inlines = [ItemCompraInline]
    list_display = ('id', 'comprador', 'status', 'data_compra')
    search_fields = ('comprador__email',)
    list_filter = ('status', 'data_compra')


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 1


class PedidoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'status', 'criado_em')
    search_fields = ('usuario__email', 'status')
    list_filter = ('usuario', 'status')
    ordering = ('-criado_em', 'usuario')
    inlines = [ItemPedidoInline]


class UserAdmin(BaseUserAdmin):
    ordering = ['id']

    list_display = ['email', 'name', 'role', 'birth_date', 'is_staff']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (
            _('Personal Info'),
            {
                'fields': (
                    'name',
                    'role',
                    'birth_date',
                    'profile_image',
                    'bio',
                    'phone',
                )
            },
        ),
        (
            _('Permissions'),
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                )
            },
        ),
        (_('Important dates'), {'fields': ('last_login',)}),
        (_('Groups'), {'fields': ('groups',)}),
        (_('User Permissions'), {'fields': ('user_permissions',)}),
    )

    readonly_fields = ['last_login']

    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'password1',
                    'password2',
                    'name',
                    'role',
                    'birth_date',
                    'profile_image',
                    'bio',
                    'phone',
                    'is_active',
                    'is_staff',
                    'is_superuser',
                ),
            },
        ),
    )


admin.site.register(models.User, UserAdmin)
admin.site.register(models.Produto)
admin.site.register(models.Categoria)
admin.site.register(models.BuscaImagem)
admin.site.register(models.ImagemProduto)
admin.site.register(models.Favorito)
admin.site.register(models.Venda)
admin.site.register(models.Seguidor)
admin.site.register(models.HistoricoPesquisa)
admin.site.register(models.Notificacao)
admin.site.register(models.SessaoLogin)

admin.site.register(models.Pedido, PedidoAdmin)
