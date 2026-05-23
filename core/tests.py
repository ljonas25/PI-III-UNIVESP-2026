"""
Suite de testes — Controle de Veículos
Cobertura: models, forms, validators, views (autenticadas e não autenticadas)
Executar: pytest   ou   coverage run -m pytest && coverage report
"""

from django.test import TestCase, Client
from django.urls import reverse
from core.models import Usuario, Veiculo, Registro, ModeloVeiculo
from core.forms import validar_cpf, VeiculoForm, RegistroForm, UsuarioCadastroForm

# ---------------------------------------------------------------------------
# CPFs matematicamente válidos usados nos testes
# ---------------------------------------------------------------------------
CPF_VALIDO_1 = '529.982.247-25'
CPF_VALIDO_2 = '111.444.777-35'
SENHA_TESTE = 'Senha@Teste123'


# ===========================================================================
# 1. VALIDAÇÃO DE CPF
# ===========================================================================

class TestValidarCPF(TestCase):

    def test_cpf_valido_com_formatacao(self):
        self.assertTrue(validar_cpf(CPF_VALIDO_1))

    def test_cpf_valido_sem_formatacao(self):
        # A função remove pontos e traços antes de validar
        self.assertTrue(validar_cpf('52998224725'))

    def test_cpf_segundo_valido(self):
        self.assertTrue(validar_cpf(CPF_VALIDO_2))

    def test_cpf_digitos_todos_iguais(self):
        self.assertFalse(validar_cpf('111.111.111-11'))

    def test_cpf_zeros(self):
        self.assertFalse(validar_cpf('000.000.000-00'))

    def test_cpf_digito_verificador_errado(self):
        # Último dígito alterado de 25 para 24
        self.assertFalse(validar_cpf('529.982.247-24'))

    def test_cpf_muito_curto(self):
        self.assertFalse(validar_cpf('123.456.789'))

    def test_cpf_vazio(self):
        self.assertFalse(validar_cpf(''))


# ===========================================================================
# 2. MODEL — Veiculo
# ===========================================================================

class TestVeiculoModel(TestCase):

    def test_placa_salva_em_uppercase(self):
        v = Veiculo.objects.create(
            placa='abc1234', proprietario='Teste', marca='Fiat', modelo='Uno'
        )
        self.assertEqual(v.placa, 'ABC1234')

    def test_placa_remove_hifen(self):
        v = Veiculo.objects.create(
            placa='ABC-1234', proprietario='Teste', marca='Fiat', modelo='Uno'
        )
        self.assertEqual(v.placa, 'ABC1234')

    def test_placa_mercosul_uppercase(self):
        v = Veiculo.objects.create(
            placa='abc1d23', proprietario='Teste', marca='VW', modelo='Gol'
        )
        self.assertEqual(v.placa, 'ABC1D23')

    def test_str_retorna_placa_e_proprietario(self):
        v = Veiculo.objects.create(
            placa='ABC1234', proprietario='João Silva', marca='Fiat', modelo='Uno'
        )
        self.assertEqual(str(v), 'ABC1234 - João Silva')

    def test_placa_deve_ser_unica(self):
        Veiculo.objects.create(
            placa='ABC1234', proprietario='João', marca='Fiat', modelo='Uno'
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Veiculo.objects.create(
                placa='ABC1234', proprietario='Maria', marca='VW', modelo='Gol'
            )


# ===========================================================================
# 3. MODEL — Usuario
# ===========================================================================

class TestUsuarioModel(TestCase):

    def test_create_user_basico(self):
        user = Usuario.objects.create_user(
            cpf=CPF_VALIDO_1, password=SENHA_TESTE,
            papel='usuario', funcao='Agente'
        )
        self.assertEqual(user.cpf, CPF_VALIDO_1)
        self.assertTrue(user.check_password(SENHA_TESTE))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_sem_cpf_levanta_valueerror(self):
        with self.assertRaises(ValueError):
            Usuario.objects.create_user(cpf='', password=SENHA_TESTE)

    def test_create_superuser(self):
        user = Usuario.objects.create_superuser(
            cpf=CPF_VALIDO_2, password=SENHA_TESTE,
            papel='administrador', funcao='Admin'
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_str_retorna_cpf(self):
        user = Usuario.objects.create_user(
            cpf=CPF_VALIDO_1, password=SENHA_TESTE,
            papel='usuario', funcao='Agente'
        )
        self.assertEqual(str(user), CPF_VALIDO_1)


# ===========================================================================
# 4. MODEL — Registro
# ===========================================================================

class TestRegistroModel(TestCase):

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            cpf=CPF_VALIDO_1, password=SENHA_TESTE,
            papel='usuario', funcao='Agente'
        )
        self.veiculo = Veiculo.objects.create(
            placa='ABC1234', proprietario='João', marca='Fiat', modelo='Uno'
        )

    def test_criacao_registro_entrada(self):
        registro = Registro.objects.create(
            tipo='Entrada',
            veiculo=self.veiculo,
            usuario=self.usuario,
        )
        self.assertEqual(registro.tipo, 'Entrada')
        self.assertEqual(registro.veiculo.placa, 'ABC1234')

    def test_str_registro(self):
        registro = Registro.objects.create(
            tipo='Saída', veiculo=self.veiculo, usuario=self.usuario
        )
        self.assertIn('Saída', str(registro))
        self.assertIn('ABC1234', str(registro))


# ===========================================================================
# 5. FORM — VeiculoForm
# ===========================================================================

class TestVeiculoForm(TestCase):

    def setUp(self):
        self.modelo = ModeloVeiculo.objects.create(marca='Fiat', modelo='Uno')

    def _form(self, placa):
        return VeiculoForm(data={
            'placa': placa,
            'proprietario': 'João Silva',
            'modelo_predefinido': self.modelo.pk,
        })

    def test_placa_padrao_antigo_valida(self):
        self.assertTrue(self._form('ABC1234').is_valid())

    def test_placa_mercosul_valida(self):
        self.assertTrue(self._form('ABC1D23').is_valid())

    def test_placa_com_hifen_valida(self):
        # Form deve aceitar e normalizar
        self.assertTrue(self._form('ABC-1234').is_valid())

    def test_placa_curta_invalida(self):
        self.assertFalse(self._form('AB1234').is_valid())

    def test_placa_formato_errado_invalida(self):
        # Começa com número — inválido
        self.assertFalse(self._form('1234ABC').is_valid())

    def test_placa_vazia_invalida(self):
        self.assertFalse(self._form('').is_valid())

    def test_clean_placa_normaliza_para_uppercase(self):
        form = self._form('abc1234')
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['placa'], 'ABC1234')


# ===========================================================================
# 6. FORM — RegistroForm
# ===========================================================================

class TestRegistroForm(TestCase):

    def setUp(self):
        self.veiculo = Veiculo.objects.create(
            placa='ABC1234', proprietario='João', marca='Fiat', modelo='Uno'
        )

    def test_registro_entrada_valido(self):
        form = RegistroForm(data={
            'tipo': 'Entrada',
            'observacoes': 'Teste de entrada',
            'veiculo': self.veiculo.pk,
        })
        self.assertTrue(form.is_valid())

    def test_registro_saida_valido(self):
        form = RegistroForm(data={
            'tipo': 'Saída',
            'observacoes': '',
            'veiculo': self.veiculo.pk,
        })
        self.assertTrue(form.is_valid())

    def test_registro_sem_veiculo_invalido(self):
        form = RegistroForm(data={'tipo': 'Entrada', 'observacoes': ''})
        self.assertFalse(form.is_valid())


# ===========================================================================
# 7. FORM — UsuarioCadastroForm
# ===========================================================================

class TestUsuarioCadastroForm(TestCase):

    def _dados(self, cpf=CPF_VALIDO_1, senha='Senha@123', senha2='Senha@123', papel='usuario'):
        return {'cpf': cpf, 'password': senha, 'senha2': senha2, 'papel': papel}

    def test_formulario_valido(self):
        form = UsuarioCadastroForm(data=self._dados())
        self.assertTrue(form.is_valid())

    def test_senhas_diferentes_invalido(self):
        form = UsuarioCadastroForm(data=self._dados(senha2='OutraSenha'))
        self.assertFalse(form.is_valid())
        self.assertIn('senha2', form.errors)

    def test_cpf_invalido(self):
        form = UsuarioCadastroForm(data=self._dados(cpf='111.111.111-11'))
        self.assertFalse(form.is_valid())
        self.assertIn('cpf', form.errors)

    def test_administrador_recebe_is_staff(self):
        form = UsuarioCadastroForm(data=self._dados(papel='administrador'))
        self.assertTrue(form.is_valid())
        usuario = form.save()
        self.assertTrue(usuario.is_staff)
        self.assertTrue(usuario.is_superuser)

    def test_usuario_comum_nao_e_staff(self):
        form = UsuarioCadastroForm(data=self._dados(papel='usuario'))
        self.assertTrue(form.is_valid())
        usuario = form.save()
        self.assertFalse(usuario.is_staff)


# ===========================================================================
# 8. VIEW — Login
# ===========================================================================

class TestLoginView(TestCase):

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            cpf=CPF_VALIDO_1, password=SENHA_TESTE,
            papel='usuario', funcao='Agente'
        )

    def test_get_retorna_200(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_login_valido_redireciona_para_menu(self):
        response = self.client.post(reverse('login'), {
            'cpf': CPF_VALIDO_1, 'senha': SENHA_TESTE
        })
        self.assertRedirects(response, reverse('menu'))

    def test_login_senha_errada_exibe_erro(self):
        response = self.client.post(reverse('login'), {
            'cpf': CPF_VALIDO_1, 'senha': 'senhaerrada'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CPF ou senha inválidos')

    def test_login_cpf_inexistente_exibe_erro(self):
        response = self.client.post(reverse('login'), {
            'cpf': '000.000.000-00', 'senha': SENHA_TESTE
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CPF ou senha inválidos')


# ===========================================================================
# 9. VIEWS — Proteção por autenticação (sem login → redireciona)
# ===========================================================================

class TestViewsNaoAutenticado(TestCase):
    """
    Garante que @login_required está ativo em todas as views protegidas.
    Sem login, o Django redireciona para /login/?next=<url>.
    """

    def _deve_redirecionar(self, url_name):
        response = self.client.get(reverse(url_name))
        self.assertEqual(response.status_code, 302,
            msg=f"View '{url_name}' deveria redirecionar (302) sem autenticação")
        self.assertIn('/login/', response['Location'])

    def test_menu_exige_login(self):
        self._deve_redirecionar('menu')

    def test_historico_exige_login(self):
        self._deve_redirecionar('historico')

    def test_dashboard_exige_login(self):
        self._deve_redirecionar('dashboard')

    def test_registro_exige_login(self):
        self._deve_redirecionar('registro')

    def test_cadastro_veiculo_exige_login(self):
        self._deve_redirecionar('cadastro_veiculo')

    def test_cadastro_usuario_exige_login(self):
        self._deve_redirecionar('cadastro_usuario')

    def test_historico_pdf_exige_login(self):
        self._deve_redirecionar('historico_pdf')


# ===========================================================================
# 10. VIEWS — Acesso com login ativo
# ===========================================================================

class TestViewsAutenticado(TestCase):

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            cpf=CPF_VALIDO_1, password=SENHA_TESTE,
            papel='usuario', funcao='Agente'
        )
        self.client.login(username=CPF_VALIDO_1, password=SENHA_TESTE)

    def test_menu_retorna_200(self):
        response = self.client.get(reverse('menu'))
        self.assertEqual(response.status_code, 200)

    def test_historico_retorna_200(self):
        response = self.client.get(reverse('historico'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_retorna_200(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_registro_get_retorna_200(self):
        response = self.client.get(reverse('registro'))
        self.assertEqual(response.status_code, 200)

    def test_cadastro_veiculo_get_retorna_200(self):
        response = self.client.get(reverse('cadastro_veiculo'))
        self.assertEqual(response.status_code, 200)


# ===========================================================================
# 11. VIEW — Registro de entrada/saída (POST)
# ===========================================================================

class TestRegistroViewPost(TestCase):

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            cpf=CPF_VALIDO_1, password=SENHA_TESTE,
            papel='usuario', funcao='Agente'
        )
        self.veiculo = Veiculo.objects.create(
            placa='XYZ5678', proprietario='Maria', marca='VW', modelo='Gol'
        )
        self.client.login(username=CPF_VALIDO_1, password=SENHA_TESTE)

    def test_post_valido_cria_registro(self):
        response = self.client.post(reverse('registro'), {
            'tipo': 'Entrada',
            'observacoes': 'Visita agendada',
            'veiculo': self.veiculo.pk,
        })
        self.assertRedirects(response, reverse('historico'))
        self.assertEqual(Registro.objects.count(), 1)

    def test_registro_associa_usuario_logado(self):
        self.client.post(reverse('registro'), {
            'tipo': 'Entrada',
            'observacoes': '',
            'veiculo': self.veiculo.pk,
        })
        registro = Registro.objects.first()
        self.assertEqual(registro.usuario, self.usuario)

    def test_post_invalido_nao_cria_registro(self):
        # POST sem veiculo — form inválido
        self.client.post(reverse('registro'), {
            'tipo': 'Entrada',
            'observacoes': '',
        })
        self.assertEqual(Registro.objects.count(), 0)


# ===========================================================================
# 12. VIEW — Filtros do Histórico
# ===========================================================================

class TestHistoricoFiltros(TestCase):

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            cpf=CPF_VALIDO_1, password=SENHA_TESTE,
            papel='usuario', funcao='Agente'
        )
        self.v1 = Veiculo.objects.create(
            placa='AAA1111', proprietario='Carlos', marca='Fiat', modelo='Uno'
        )
        self.v2 = Veiculo.objects.create(
            placa='BBB2222', proprietario='Ana', marca='VW', modelo='Gol'
        )
        Registro.objects.create(tipo='Entrada', veiculo=self.v1, usuario=self.usuario)
        Registro.objects.create(tipo='Saída',   veiculo=self.v2, usuario=self.usuario)
        self.client.login(username=CPF_VALIDO_1, password=SENHA_TESTE)

    def test_filtro_tipo_entrada(self):
        response = self.client.get(reverse('historico'), {'tipo': 'Entrada'})
        self.assertEqual(response.status_code, 200)
        page_obj = response.context['page_obj']
        self.assertEqual(len(page_obj), 1)
        self.assertEqual(page_obj[0].tipo, 'Entrada')

    def test_filtro_tipo_saida(self):
        response = self.client.get(reverse('historico'), {'tipo': 'Saída'})
        page_obj = response.context['page_obj']
        self.assertEqual(len(page_obj), 1)
        self.assertEqual(page_obj[0].tipo, 'Saída')

    def test_filtro_por_placa(self):
        response = self.client.get(reverse('historico'), {'veiculo': 'AAA'})
        page_obj = response.context['page_obj']
        self.assertEqual(len(page_obj), 1)
        self.assertEqual(page_obj[0].veiculo.placa, 'AAA1111')

    def test_sem_filtro_retorna_todos(self):
        response = self.client.get(reverse('historico'))
        page_obj = response.context['page_obj']
        self.assertEqual(len(page_obj), 2)


# ===========================================================================
# 13. VIEW — Dashboard métricas
# ===========================================================================

class TestDashboard(TestCase):

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            cpf=CPF_VALIDO_1, password=SENHA_TESTE,
            papel='usuario', funcao='Agente'
        )
        self.veiculo = Veiculo.objects.create(
            placa='ABC1234', proprietario='João', marca='Fiat', modelo='Uno'
        )
        Registro.objects.create(tipo='Entrada', veiculo=self.veiculo, usuario=self.usuario)
        Registro.objects.create(tipo='Saída',   veiculo=self.veiculo, usuario=self.usuario)
        self.client.login(username=CPF_VALIDO_1, password=SENHA_TESTE)

    def test_dashboard_contagens_corretas(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['total_entradas'], 1)
        self.assertEqual(response.context['total_saidas'], 1)
        self.assertEqual(response.context['total_registros'], 2)

    def test_dashboard_total_hoje(self):
        response = self.client.get(reverse('dashboard'))
        # Os registros foram criados agora, então total_hoje deve ser 2
        self.assertEqual(response.context['total_hoje'], 2)
