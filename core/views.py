from rest_framework import viewsets
from .models import Usuario, Veiculo, Registro
from .serializers import UsuarioSerializer, VeiculoSerializer, RegistroSerializer
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from .forms import VeiculoForm, RegistroForm, UsuarioCadastroForm, apenas_numeros_cpf, formatar_cpf, formatar_cpf_hifen
from collections import defaultdict
from datetime import datetime
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.utils import timezone
from xhtml2pdf import pisa
from .utils.pdf import link_callback
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.core.cache import cache
from django.views.decorators.http import require_GET, require_POST


# ---------------------------------------------------------------------------
# API REST
# ---------------------------------------------------------------------------
class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer

class VeiculoViewSet(viewsets.ModelViewSet):
    queryset = Veiculo.objects.all()
    serializer_class = VeiculoSerializer

class RegistroViewSet(viewsets.ModelViewSet):
    queryset = Registro.objects.all()
    serializer_class = RegistroSerializer


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------
def login_view(request):
    if request.method == "POST":
        cpf_digitado = (request.POST.get('cpf') or '').strip()
        senha = request.POST.get('senha')

        # Compatibilidade com usuários antigos e novos:
        # Compatibilidade com usuários antigos e novos:
        # tenta CPF como digitado, padrão antigo com ponto, padrão com hífen e somente números.
        tentativas = []
        for valor in (cpf_digitado, formatar_cpf(cpf_digitado), formatar_cpf_hifen(cpf_digitado), apenas_numeros_cpf(cpf_digitado)):
            if valor and valor not in tentativas:
                tentativas.append(valor)

        user = None
        for cpf in tentativas:
            user = authenticate(request, username=cpf, password=senha)
            if user is not None:
                break

        if user is not None:
            login(request, user)
            return redirect('home')
        return render(request, 'core/login.html', {'error': 'CPF ou senha inválidos.'})
    return render(request, 'core/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@require_POST
@csrf_protect
def verificar_admin_view(request):
    """
    Verifica a senha de qualquer admin para liberar acesso ao cadastro de usuários.
    Chamado via Fetch API no modal da tela de login.
    """
    senha = request.POST.get('senha', '').strip()
    if not senha:
        return JsonResponse({'ok': False, 'erro': 'Informe a senha do administrador.'})

    admins = Usuario.objects.filter(is_staff=True)
    for admin in admins:
        if admin.check_password(senha):
            request.session['cadastro_autorizado'] = True
            return JsonResponse({'ok': True})

    return JsonResponse({'ok': False, 'erro': 'Senha incorreta. Tente novamente.'})


# ---------------------------------------------------------------------------
# Home — coleta e estrutura os dados do dia
# ---------------------------------------------------------------------------
def _dados_home():
    hoje = timezone.now().date()

    # Todos os registros de hoje, ordenados por hora
    qs = (
        Registro.objects
        .filter(data_hora__date=hoje)
        .select_related('veiculo')
        .order_by('data_hora')
    )

    total_entradas = qs.filter(tipo='Entrada').count()
    total_saidas   = qs.filter(tipo='Saída').count()

    # Agrupa por veículo para determinar status atual
    por_veiculo = defaultdict(list)
    for r in qs:
        por_veiculo[r.veiculo_id].append(r)

    dentro = []   # último registro do dia é Entrada (ainda lá)
    saidas = []   # último registro do dia é Saída (já foi)

    for vid, regs in por_veiculo.items():
        ultimo = regs[-1]
        veiculo = ultimo.veiculo

        if ultimo.tipo == 'Entrada':
            # Está dentro agora
            dentro.append({
                'placa':        veiculo.placa,
                'proprietario': veiculo.proprietario,
                'entrada':      timezone.localtime(ultimo.data_hora).strftime('%H:%M'),
                'entrada_ts':   int(ultimo.data_hora.timestamp() * 1000),  # ms para JS
                'modelo':       f'{veiculo.marca} {veiculo.modelo}'.strip() or 'Modelo não informado',
            })
        else:
            # Saiu — encontra a entrada correspondente mais recente
            entrada_rec = None
            for r in reversed(regs[:-1]):
                if r.tipo == 'Entrada':
                    entrada_rec = r
                    break

            item = {
                'placa':        veiculo.placa,
                'proprietario': veiculo.proprietario,
                'modelo':       f'{veiculo.marca} {veiculo.modelo}'.strip() or 'Modelo não informado',
                'saida':        timezone.localtime(ultimo.data_hora).strftime('%H:%M'),
                'entrada':      '—',
                'duracao':      '—',
            }
            if entrada_rec:
                delta     = ultimo.data_hora - entrada_rec.data_hora
                total_min = int(delta.total_seconds() / 60)
                h, m      = divmod(total_min, 60)
                item['entrada'] = timezone.localtime(entrada_rec.data_hora).strftime('%H:%M')
                item['duracao'] = f'{h}h {m:02d}min' if h else f'{m}min'
            saidas.append(item)

    # Ordena: dentro → mais recente primeiro; saidas → mais recente saída primeiro
    dentro.sort(key=lambda x: x['entrada_ts'], reverse=True)

    return {
        'total_entradas_hoje': total_entradas,
        'total_saidas_hoje':   total_saidas,
        'veiculos_dentro':     len(dentro),
        'dentro':              dentro,
        'saidas':              saidas,
    }


@login_required
def home_view(request):
    return render(request, 'core/home.html', _dados_home())


@login_required
@require_GET
def home_json_view(request):
    data = _dados_home()
    data['hora_atual'] = timezone.localtime().strftime('%H:%M:%S')
    return JsonResponse(data)


@login_required
def menu_view(request):
    return redirect('home')


# ---------------------------------------------------------------------------
# Views protegidas
# ---------------------------------------------------------------------------
@login_required
def cadastro_veiculo_view(request):
    if request.method == "POST":
        form = VeiculoForm(request.POST)
        if form.is_valid():
            mp = form.cleaned_data['modelo_predefinido']
            v  = form.save(commit=False)
            v.marca  = mp.marca
            v.modelo = mp.modelo
            v.save()
            messages.success(request, f'Veículo {v.placa} cadastrado com sucesso!')
            return redirect('home')
        messages.error(request, 'Corrija os erros no formulário.')
    else:
        form = VeiculoForm()
    return render(request, 'core/cadastro_veiculo.html', {'form': form})


@login_required
def registro_view(request):
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            reg = form.save(commit=False)
            reg.usuario = request.user
            reg.save()
            cache.delete_many([f'dashboard_data_{p}' for p in ['7', '15', '30', '90']])
            messages.success(request, f'{reg.tipo} de {reg.veiculo.placa} registrada com sucesso!')
            return redirect('historico')
        messages.error(request, 'Selecione um veículo válido antes de registrar.')
    else:
        form = RegistroForm()
    return render(request, 'core/registro.html', {'form': form})


def _aplicar_filtros(request, queryset=None):
    if queryset is None:
        queryset = Registro.objects.select_related('veiculo', 'usuario').all()

    data_inicio_str = request.GET.get('data_inicio') or request.GET.get('data')
    data_fim_str    = request.GET.get('data_fim')
    tipo            = request.GET.get('tipo', '').strip()
    veiculo_q       = request.GET.get('veiculo', '').strip()
    proprietario_q  = request.GET.get('usuario', '').strip()

    if data_inicio_str:
        try:
            queryset = queryset.filter(
                data_hora__gte=datetime.strptime(data_inicio_str, "%Y-%m-%d"))
        except ValueError:
            pass

    if data_fim_str:
        try:
            queryset = queryset.filter(
                data_hora__lte=datetime.strptime(data_fim_str, "%Y-%m-%d")
                .replace(hour=23, minute=59, second=59))
        except ValueError:
            pass
    elif data_inicio_str:
        try:
            d = datetime.strptime(data_inicio_str, "%Y-%m-%d")
            queryset = queryset.filter(
                data_hora__range=(d, d.replace(hour=23, minute=59, second=59)))
        except ValueError:
            pass

    if tipo:           queryset = queryset.filter(tipo=tipo)
    if veiculo_q:      queryset = queryset.filter(veiculo__placa__icontains=veiculo_q)
    if proprietario_q: queryset = queryset.filter(veiculo__proprietario__icontains=proprietario_q)

    return queryset.order_by('-data_hora'), {
        'data_inicio': data_inicio_str or '', 'data_fim': data_fim_str or '',
        'tipo': tipo, 'veiculo': veiculo_q, 'usuario': proprietario_q,
    }


@login_required
def historico_view(request):
    registros, filtros = _aplicar_filtros(request)
    page_obj = Paginator(registros, 10).get_page(request.GET.get("page"))
    return render(request, 'core/historico.html', {'page_obj': page_obj, 'filtros': filtros})


@login_required
@require_GET
def historico_json_view(request):
    registros, _ = _aplicar_filtros(request)
    data = [
        {
            'id':           r.id,
            'data':         timezone.localtime(r.data_hora).strftime('%d/%m/%Y'),
            'hora':         timezone.localtime(r.data_hora).strftime('%H:%M:%S'),
            'tipo':         r.tipo,
            'placa':        r.veiculo.placa,
            'proprietario': r.veiculo.proprietario,
            'observacoes':  r.observacoes or '',
        }
        for r in registros[:100]
    ]
    return JsonResponse({'registros': data, 'total': len(data)})


@login_required
@require_GET
def autocomplete_veiculo_view(request):
    termo = request.GET.get('q', '').strip().upper()
    if len(termo) < 2:
        return JsonResponse({'veiculos': []})
    v = Veiculo.objects.filter(
        placa__istartswith=termo
    ).values('id', 'placa', 'proprietario', 'marca', 'modelo')[:10]
    return JsonResponse({'veiculos': list(v)})


def cadastro_usuario_view(request):
    """
    Cadastro aberto para usuário comum.
    Para cadastrar administrador, o formulário exige a senha de um administrador ativo.
    """
    if request.method == "POST":
        form = UsuarioCadastroForm(request.POST)
        if form.is_valid():
            novo_usuario = form.save()
            request.session.pop('cadastro_autorizado', None)
            if novo_usuario.is_staff:
                messages.success(request, 'Administrador cadastrado com sucesso.')
            else:
                messages.success(request, 'Usuário cadastrado! Faça login para continuar.')
            return redirect('login')
        messages.error(request, 'Corrija os erros no formulário.')
    else:
        form = UsuarioCadastroForm()
    return render(request, 'core/cadastro_usuario.html', {'form': form})


@login_required
def configuracoes_view(request):
    return render(request, 'core/configuracoes.html')


@login_required
def historico_pdf_view(request):
    registros, filtros = _aplicar_filtros(request)
    template = get_template("core/historico_pdf.html")
    html = template.render({
        "registros": list(registros), "filtros": filtros,
        "agora": timezone.localtime(), "request": request,
    })
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename="historico.pdf"'
    pisa_status = pisa.CreatePDF(
        src=html, dest=response, link_callback=link_callback, encoding='utf-8'
    )
    if pisa_status.err:
        return HttpResponse("Erro ao gerar o PDF.", status=500)
    return response


@login_required
def dashboard_view(request):
    periodo = request.GET.get('periodo', '30')
    hoje = timezone.now().date()
    PERIODOS = {
        '7': 'Últimos 7 dias', '15': 'Últimos 15 dias',
        '30': 'Últimos 30 dias', '90': 'Últimos 90 dias',
    }
    if periodo not in PERIODOS:
        periodo = '30'

    dias = int(periodo)
    data_inicio = hoje - __import__('datetime').timedelta(days=dias - 1)
    cache_key = f'dashboard_data_{periodo}'
    ctx = cache.get(cache_key)

    if not ctx:
        rp = Registro.objects.filter(data_hora__date__gte=data_inicio)
        rt = Registro.objects.all()
        total_entradas  = rp.filter(tipo='Entrada').count()
        total_saidas    = rp.filter(tipo='Saída').count()
        total_registros = rp.count()
        total_hoje      = rt.filter(data_hora__date=hoje).count()
        veiculos_dentro = (
            Veiculo.objects.filter(registro__tipo='Entrada')
            .exclude(registro__tipo='Saída').distinct().count()
        )
        dados_raw = (
            rp.annotate(data=TruncDate('data_hora'))
            .values('data', 'tipo').annotate(total=Count('id')).order_by('data', 'tipo')
        )
        por_data = {}
        for item in dados_raw:
            d = item['data'].strftime('%d/%m')
            if d not in por_data:
                por_data[d] = {'Entrada': 0, 'Saída': 0}
            por_data[d][item['tipo']] = item['total']
        datas = list(por_data.keys())
        top_veiculos = (
            Registro.objects.filter(data_hora__date__gte=data_inicio)
            .values('veiculo__placa', 'veiculo__proprietario')
            .annotate(acessos=Count('id')).order_by('-acessos')[:5]
        )
        ctx = {
            'total_entradas': total_entradas, 'total_saidas': total_saidas,
            'total_registros': total_registros, 'total_hoje': total_hoje,
            'veiculos_dentro': veiculos_dentro,
            'datas': datas,
            'entradas_dia': [por_data[d]['Entrada'] for d in datas],
            'saidas_dia':   [por_data[d]['Saída']   for d in datas],
            'top_veiculos': list(top_veiculos),
            'periodo': periodo, 'periodos': PERIODOS,
            'data_inicio_fmt': data_inicio.strftime('%d/%m/%Y'),
        }
        cache.set(cache_key, ctx, 300)

    return render(request, 'core/dashboard.html', ctx)
