from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import OrdemServico
from financeiro.models import Lancamento
from django.utils import timezone

@receiver(post_save, sender=OrdemServico)
def gerar_financeiro(sender, instance, created, **kwargs):
    # Se a OS foi finalizada e ainda não tem um lançamento financeiro vinculado
    if instance.status == 'FIN' and not Lancamento.objects.filter(os=instance).exists():
        Lancamento.objects.create(
            descricao=f"Recebimento OS #{instance.id} - Placa {instance.veiculo.placa}",
            valor=instance.valor_total,
            tipo='ENT',
            data_vencimento=timezone.now().date(),
            os=instance,
            pago=False # Fica pendente até o dono confirmar o dinheiro no caixa
        )