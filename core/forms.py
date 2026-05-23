from django import forms
from .models import Veiculo, Registro, Usuario, ModeloVeiculo

PAPEIS_CHOICES = [
    ('usuario', 'Usuário'),
    ('administrador', 'Administrador')
]

def apenas_numeros_cpf(cpf: str) -> str:
    return ''.join(filter(str.isdigit, cpf or ''))


def formatar_cpf(cpf: str) -> str:
    """Padrão antigo do sistema: 000.000.000.00"""
    numeros = apenas_numeros_cpf(cpf)
    if len(numeros) != 11:
        return cpf or ''
    return f'{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}.{numeros[9:]}'


def formatar_cpf_hifen(cpf: str) -> str:
    """Compatibilidade: também tenta 000.000.000-00 no login."""
    numeros = apenas_numeros_cpf(cpf)
    if len(numeros) != 11:
        return cpf or ''
    return f'{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}'


def validar_cpf(cpf: str) -> bool:
    cpf = apenas_numeros_cpf(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in range(9, 11):
        soma = sum(int(cpf[num]) * ((i + 1) - num) for num in range(0, i))
        digito = ((soma * 10) % 11) % 10
        if int(cpf[i]) != digito:
            return False
    return True


class VeiculoForm(forms.ModelForm):
    modelo_predefinido = forms.ModelChoiceField(
        queryset=ModeloVeiculo.objects.all().order_by('marca', 'modelo'),
        required=True,
        label="Escolha Marca e Modelo",
        empty_label="--- Selecione ---"
    )

    class Meta:
        model = Veiculo
        fields = ['placa', 'proprietario']
        widgets = {
            'placa': forms.TextInput(attrs={
                'placeholder': 'AAA1234',
                'style': 'text-transform:uppercase;',
                'maxlength': '8'
            }),
            'proprietario': forms.TextInput(attrs={'placeholder': 'Proprietário'}),
        }
        labels = {
            'placa': 'Placa do Veículo',
            'proprietario': 'Nome do Proprietário',
        }

    def clean_placa(self):
        import re
        placa = self.cleaned_data['placa'].upper().replace("-", "")
        if len(placa) != 7:
            raise forms.ValidationError("A placa deve conter exatamente 7 caracteres.")
        if not re.match(r'^[A-Z]{3}[0-9A-Z]{4}$', placa):
            raise forms.ValidationError("Formato de placa inválido. Use AAA1234.")
        return placa


class RegistroForm(forms.ModelForm):
    class Meta:
        model = Registro
        fields = ['tipo', 'observacoes', 'veiculo']
        widgets = {
            'tipo': forms.Select(choices=[('Entrada', 'Entrada'), ('Saída', 'Saída')]),
            'observacoes': forms.Textarea(attrs={'placeholder': 'Observações'}),
        }


class UsuarioCadastroForm(forms.ModelForm):
    senha2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirme a senha',
            'autocomplete': 'new-password'
        }),
        label="Confirme a Senha"
    )
    papel = forms.ChoiceField(choices=PAPEIS_CHOICES, required=True, label="Papel")
    funcao = forms.CharField(
        required=False,
        label="Nome do usuário",
        widget=forms.TextInput(attrs={
            'placeholder': 'Nome do usuário / servidor (opcional)',
            'autocomplete': 'name'
        })
    )
    senha_admin = forms.CharField(
        required=False,
        label="Senha do administrador",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Obrigatória apenas para cadastrar administrador',
            'autocomplete': 'off'
        })
    )

    class Meta:
        model = Usuario
        fields = ['cpf', 'funcao', 'password', 'papel']
        widgets = {
            'cpf': forms.TextInput(attrs={
                'placeholder': '000.000.000.00',
                'maxlength': '14'
            }),
            'password': forms.PasswordInput(attrs={
                'placeholder': 'Senha',
                'autocomplete': 'new-password'
            }),
        }
        labels = {
            'cpf': 'CPF',
            'funcao': 'Nome do usuário',
            'password': 'Senha',
            'papel': 'Papel',
        }

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf', '')
        if not validar_cpf(cpf):
            raise forms.ValidationError("CPF inválido!")

        cpf_formatado = formatar_cpf(cpf)
        cpf_hifen     = formatar_cpf_hifen(cpf)
        cpf_numeros   = apenas_numeros_cpf(cpf)

        # Evita duplicidade mesmo com formatos distintos de CPF cadastrado
        if Usuario.objects.filter(cpf__in=[cpf_formatado, cpf_hifen, cpf_numeros]).exists():
            raise forms.ValidationError("Este CPF já está cadastrado.")

        return cpf_formatado  # salva no padrão 000.000.000.00

    def clean_funcao(self):
        """
        CORREÇÃO CRÍTICA: o campo funcao no model não tem blank=True.
        Se o usuário deixar em branco, Django levanta ValidationError internamente
        em _post_clean() e o formulário falha silenciosamente.
        Aqui garantimos que funcao NUNCA chega vazio ao model:
        usa o CPF já validado como fallback.
        """
        v = (self.cleaned_data.get('funcao') or '').strip()
        if not v:
            # CPF já foi validado neste ponto (é o primeiro campo em Meta.fields)
            cpf = self.cleaned_data.get('cpf', '')
            v = cpf or 'Usuário'
        return v

    def clean(self):
        cleaned_data = super().clean()
        senha     = cleaned_data.get("password")
        senha2    = cleaned_data.get("senha2")
        papel     = cleaned_data.get("papel")
        senha_admin = (cleaned_data.get("senha_admin") or "").strip()

        # Senhas devem ser iguais
        if senha and senha2 and senha != senha2:
            self.add_error('senha2', "As senhas não conferem!")

        # ------------------------------------------------------------------
        # Regra de negócio:
        #   • "usuario"       → cadastro livre, sem verificação extra
        #   • "administrador" → precisa da senha de um admin já existente
        #                       (exceto quando não existe nenhum admin ainda)
        # ------------------------------------------------------------------
        if papel == "administrador":
            admins = Usuario.objects.filter(is_active=True, is_staff=True)
            if admins.exists():
                if not senha_admin:
                    self.add_error(
                        'senha_admin',
                        "Informe a senha de um administrador para criar outro administrador."
                    )
                elif not any(adm.check_password(senha_admin) for adm in admins):
                    self.add_error('senha_admin', "Senha de administrador incorreta.")
            # Se não existe nenhum admin, permite criar o primeiro sem restrição.

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        # Sempre seta a senha com hash (nunca salva texto puro)
        user.set_password(self.cleaned_data["password"])

        # Define permissões de acordo com o papel escolhido
        if self.cleaned_data.get("papel") == "administrador":
            user.is_staff      = True
            user.is_superuser  = True
            user.papel         = "administrador"
        else:
            user.is_staff      = False
            user.is_superuser  = False
            user.papel         = "usuario"

        # Garante que funcao nunca fique em branco no banco
        # (clean_funcao() já previne isso, mas mantemos como segurança extra)
        if not (user.funcao or '').strip():
            user.funcao = user.cpf or 'Usuário'

        if commit:
            user.save()
        return user
