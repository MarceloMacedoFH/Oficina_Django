from django.db import models
from servicos.models import OrdemServico

class Lancamento(models.Model):
    TIPO_CHOICES = (
        ('ENT', 'Entrada (Receita)'),
        ('SAI', 'Saída (Despesa)'),
    )
    
    FORMA_PAGAMENTO = (
        ('DIN', 'Dinheiro'),
        ('CRT', 'Cartão de Crédito/Débito'),
        ('PIX', 'PIX'),
        ('BOL', 'Boleto'),
    )

    descricao = models.CharField(max_length=200)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    tipo = models.CharField(max_length=3, choices=TIPO_CHOICES)
    data_vencimento = models.DateField()
    data_pagamento = models.DateField(blank=True, null=True)
    pago = models.BooleanField(default=False)
    forma_pagamento = models.CharField(max_length=3, choices=FORMA_PAGAMENTO, blank=True, null=True)
    
    # Vinculamos opcionalmente a uma OS
    os = models.ForeignKey(OrdemServico, on_delete=models.SET_NULL, blank=True, null=True, related_name='financeiro')

    def __str__(self):
        return f"{self.tipo} - {self.descricao} - R$ {self.valor}"