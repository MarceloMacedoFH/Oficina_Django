from django.contrib import admin
from .models import Servico, Pecas, OrdemServico, ItemPeca, ItemServico

class ItemPecaInline(admin.TabularInline):
    model = ItemPeca
    extra = 1

class ItemServicoInline(admin.TabularInline):
    model = ItemServico
    extra = 1

@admin.register(OrdemServico)
class OrdemServicoAdmin(admin.ModelAdmin):
    # Ajuste o list_display para usar o nome correto do campo no model
    list_display = ('id', 'cliente', 'veiculo', 'status', 'valor_total', 'data_entrada')
    
    # Se você colocou o total como readonly para o admin não editar na mão
    readonly_fields = ('valor_total', 'data_entrada')
    inlines = [ItemPecaInline, ItemServicoInline] 

admin.site.register(Servico)
admin.site.register(Pecas)