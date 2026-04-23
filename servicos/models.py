from django.db import models
from django.db.models import Sum, F
from core.models import Cliente, Veiculo # Ajuste conforme a localização real dos seus models

class Produto(models.Model):
    UNIDADE_CHOICES = [
        ('UN', 'Unidade'),
        ('CX', 'Caixa'),
        ('JG', 'Jogo'),
        ('MI', 'Milheiro'),
        ('M', 'Metros'),
        ('KG', 'Quilograma'),
    ]

    TIPO_CHOICES = [
        ('PA', 'Produto Acabado'),
        ('MP', 'Matéria Prima'),
        ('SV', 'Serviço'),
        ('MC', 'Material Consumo'),
        ('PI', 'Produto Intermediário'),
    ]

    descricao = models.CharField(max_length=100, verbose_name="Descrição")
    tipo_produto = models.CharField(max_length=2, choices=TIPO_CHOICES, default='PA', verbose_name="Tipo de Produto")
    unidade_medida = models.CharField(max_length=2, choices=UNIDADE_CHOICES, default='UN', verbose_name="Unidade de Medida")
    
    preco_compra = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Preço de Compra")
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço de Venda")
    
    estoque_atual = models.IntegerField(default=0, verbose_name="Estoque Atual")
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.descricao} ({self.get_unidade_medida_display()})"

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"

class OrdemServico(models.Model):
    STATUS_CHOICES = (
        ('ORC', 'Orçamento'),
        ('APR', 'Aprovado'),
        ('FIN', 'Finalizado'),
        ('CAN', 'Cancelado'),
    )

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    veiculo = models.ForeignKey(Veiculo, on_delete=models.CASCADE)
    data_entrada = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=3, choices=STATUS_CHOICES, default='ORC')
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    observacoes = models.TextField(blank=True, null=True)

    def atualizar_total(self):
        """Soma o total de itens (peças e serviços) e atualiza a OS"""
        total = self.itens_os.aggregate(
            total=Sum(F('quantidade') * F('preco_unitario'))
        )['total'] or 0
        
        self.valor_total = total
        OrdemServico.objects.filter(pk=self.pk).update(valor_total=self.valor_total)

    def __str__(self):
        return f"OS {self.id} - {self.cliente.nome}"

class ItemOS(models.Model):
    ordem_servico = models.ForeignKey(OrdemServico, related_name='itens_os', on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self.preco_unitario:
            self.preco_unitario = self.produto.preco_venda

        # IMPORTANTE: Serviços não devem baixar estoque
        if self.produto.tipo_produto != 'SV':
            if self.pk:
                antigo = ItemOS.objects.get(pk=self.pk)
                diferenca = self.quantidade - antigo.quantidade
                
                if diferenca != 0:
                    if self.produto.estoque_atual >= diferenca:
                        self.produto.estoque_atual -= diferenca
                        self.produto.save()
                    else:
                        raise ValueError(f"Saldo insuficiente para {self.produto.descricao}. Estoque: {self.produto.estoque_atual}")
            else:
                if self.produto.estoque_atual >= self.quantidade:
                    self.produto.estoque_atual -= self.quantidade
                    self.produto.save()
                else:
                    raise ValueError(f"Saldo insuficiente para {self.produto.descricao}. Estoque: {self.produto.estoque_atual}")

        super().save(*args, **kwargs)
        self.ordem_servico.atualizar_total()

    def delete(self, *args, **kwargs):
        # Devolve o estoque se não for serviço
        if self.produto.tipo_produto != 'SV':
            self.produto.estoque_atual += self.quantidade
            self.produto.save()
            
        os = self.ordem_servico
        super().delete(*args, **kwargs)
        os.atualizar_total()