from django.db import models
from django.db.models import Sum, F
from core.models import Cliente, Veiculo # Ajuste conforme a localização real dos seus models

class Pecas(models.Model):
    descricao = models.CharField(max_length=100, verbose_name="Descrição")
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço de Venda")
    estoque_atual = models.IntegerField(default=0, verbose_name="Stock Atual")
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.descricao} (Stock: {self.estoque_atual})"

    class Meta:
        verbose_name = "Peça"
        verbose_name_plural = "Peças"

class Servico(models.Model):
    descricao = models.CharField(max_length=100, verbose_name="Descrição")
    valor_mao_de_obra = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Mão de Obra")

    def __str__(self):
        return self.descricao

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
        """Soma o total de peças e serviços e atualiza a OS"""
        total_pecas = self.itens_pecas.aggregate(
            total=Sum(F('quantidade') * F('preco_unitario'))
        )['total'] or 0
        
        total_servicos = self.itens_servicos.aggregate(
            total=Sum(F('quantidade') * F('preco_unitario'))
        )['total'] or 0
        
        self.valor_total = total_pecas + total_servicos
        # Usamos update para evitar disparar o save() recursivamente se houver sinais
        OrdemServico.objects.filter(pk=self.pk).update(valor_total=self.valor_total)

    def __str__(self):
        return f"OS {self.id} - {self.cliente.nome}"

class ItemPeca(models.Model):
    ordem_servico = models.ForeignKey(OrdemServico, related_name='itens_pecas', on_delete=models.CASCADE)
    peca = models.ForeignKey(Pecas, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        # 1. Preenche o preço unitário se estiver vazio (vindo do cadastro da peça)
        if not self.preco_unitario:
            self.preco_unitario = self.peca.preco_venda

        # 2. Lógica de Gestão de Stock Inteligente
        if self.pk:
            # Caso de Edição: Compara a quantidade antiga com a nova
            antigo = ItemPeca.objects.get(pk=self.pk)
            diferenca = self.quantidade - antigo.quantidade
            
            if diferenca != 0:
                if self.peca.estoque_atual >= diferenca:
                    # Se aumentou a qtd, baixa o excedente. Se diminuiu, devolve.
                    self.peca.estoque_atual -= diferenca
                    self.peca.save()
                else:
                    raise ValueError(f"Saldo insuficiente para {self.peca.descricao}. Stock: {self.peca.estoque_atual}")
        else:
            # Caso de Inclusão Nova
            if self.peca.estoque_atual >= self.quantidade:
                self.peca.estoque_atual -= self.quantidade
                self.peca.save()
            else:
                raise ValueError(f"Saldo insuficiente para {self.peca.descricao}. Stock: {self.peca.estoque_atual}")

        super().save(*args, **kwargs)
        # 3. Atualiza o total da OS pai
        self.ordem_servico.atualizar_total()

    def delete(self, *args, **kwargs):
        # Devolve o stock ao excluir o item da OS
        self.peca.estoque_atual += self.quantidade
        self.peca.save()
        os = self.ordem_servico
        super().delete(*args, **kwargs)
        os.atualizar_total()

class ItemServico(models.Model):
    os = models.ForeignKey(OrdemServico, related_name='itens_servicos', on_delete=models.CASCADE)
    servico = models.ForeignKey(Servico, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self.preco_unitario:
            self.preco_unitario = self.servico.valor_mao_de_obra
        super().save(*args, **kwargs)
        self.os.atualizar_total()

    def delete(self, *args, **kwargs):
        os = self.os
        super().delete(*args, **kwargs)
        os.atualizar_total()