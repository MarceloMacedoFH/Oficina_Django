from django.contrib import admin
from .models import Cliente, Veiculo

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cpf_cnpj', 'telefone') # Colunas que aparecem na lista
    search_fields = ('nome', 'cpf_cnpj')           # Barra de busca

@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = ('placa', 'modelo', 'marca', 'cliente')
    list_filter = ('marca', 'ano')                 # Filtros na lateral direita
    search_fields = ('placa', 'modelo')