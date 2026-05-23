from django.contrib import admin
from .models import Usuario, Veiculo, Registro
from django.contrib.auth.admin import UserAdmin

## classe antiga - testando a nova
#@admin.register(Usuario)
#class UsuarioAdmin(admin.ModelAdmin):
#    list_display = ('cpf', 'papel', 'funcao', 'is_staff')
#    search_fields = ('cpf', 'funcao')
#    list_filter = ('papel', 'is_staff')
#    ordering = ('cpf',)

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('cpf', 'papel', 'funcao', 'is_staff', 'is_superuser')
    search_fields = ('cpf', 'funcao')
    list_filter = ('papel', 'is_staff', 'is_superuser')
    ordering = ('cpf',)

    fieldsets = (
        (None, {'fields': ('cpf', 'password')}),
        ('Informações Pessoais', {'fields': ('papel', 'funcao')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Datas Importantes', {'fields': ('last_login',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('cpf', 'password1', 'password2', 'papel', 'funcao', 'is_staff', 'is_superuser')}
        ),
    )

    filter_horizontal = ('groups', 'user_permissions',)


@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = ('placa', 'proprietario', 'marca', 'modelo')
    search_fields = ('placa', 'proprietario')
    list_filter = ('marca',)
    ordering = ('placa',)

@admin.register(Registro)
class RegistroAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'data_hora', 'veiculo', 'usuario')
    search_fields = ('veiculo__placa', 'usuario__cpf')
    list_filter = ('tipo', 'data_hora')
    ordering = ('-data_hora',)