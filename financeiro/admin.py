from django.contrib import admin
from .models import Lancamento
from django.utils import timezone

@admin.register(Lancamento)
class LancamentoAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'valor', 'tipo', 'data_vencimento', 'pago')
    list_filter = ('tipo', 'pago', 'data_vencimento')
    search_fields = ('descricao',)
    
    # Ações personalizadas para dar baixa em lote
    actions = ['marcar_como_pago']

    def marcar_como_pago(self, request, queryset):
        queryset.update(pago=True, data_pagamento=timezone.now().date())
    marcar_como_pago.short_description = "Confirmar Pagamento Selecionado"