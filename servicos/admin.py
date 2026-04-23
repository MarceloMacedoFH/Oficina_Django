from django.contrib import admin
from .models import OrdemServico



@admin.register(OrdemServico)
class OrdemServicoAdmin(admin.ModelAdmin):
    # Ajuste o list_display para usar o nome correto do campo no model
    list_display = ('id', 'cliente', 'veiculo', 'status', 'valor_total', 'data_entrada')
    
    # Se você colocou o total como readonly para o admin não editar na mão
    readonly_fields = ('valor_total', 'data_entrada')

