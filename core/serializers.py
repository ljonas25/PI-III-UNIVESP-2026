from rest_framework import serializers
from .models import Usuario, Veiculo, Registro

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['cpf', 'senha', 'papel', 'funcao']

class VeiculoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Veiculo
        fields = ['id', 'placa', 'marca', 'modelo', 'origem']

class RegistroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Registro
        fields = ['id', 'data_hora', 'tipo', 'observacoes', 'veiculo', 'usuario']
