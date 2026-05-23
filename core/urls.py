from django.urls import path
from . import views
from django.shortcuts import redirect
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('', lambda request: redirect('home') if request.user.is_authenticated else redirect('login'), name='root'),

    # Autenticação
    path('login/',         views.login_view,         name='login'),
    path('logout/',        views.logout_view,         name='logout'),
    path('verificar-admin/', views.verificar_admin_view, name='verificar_admin'),

    # Home
    path('home/',      views.home_view,      name='home'),
    path('home/json/', views.home_json_view, name='home_json'),

    # Menu (compatibilidade)
    path('menu/', views.menu_view, name='menu'),

    # Operação
    path('registro/',           views.registro_view,          name='registro'),
    path('historico/',          views.historico_view,          name='historico'),
    path('historico/json/',     views.historico_json_view,     name='historico_json'),
    path('historico/pdf/',      views.historico_pdf_view,      name='historico_pdf'),
    path('dashboard/',          views.dashboard_view,          name='dashboard'),

    # Cadastros
    path('cadastro-veiculo/',   views.cadastro_veiculo_view,   name='cadastro_veiculo'),
    path('cadastro-usuario/',   views.cadastro_usuario_view,   name='cadastro_usuario'),
    path('configuracoes/',      views.configuracoes_view,      name='configuracoes'),

    # Autocomplete
    path('veiculo/autocomplete/', views.autocomplete_veiculo_view, name='autocomplete_veiculo'),

    # API JWT
    path('api/token/',         TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(),    name='token_refresh'),
]
