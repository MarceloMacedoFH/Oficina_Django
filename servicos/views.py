from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from .models import OrdemServico, Pecas, Servico, ItemPeca
from .forms import OSForm, ItemPecaFormSet, ItemServicoFormSet
from django.db import transaction

@login_required
def lista_ordens_servico(request): # Nome alterado para bater com o urls.py
    ordens = OrdemServico.objects.all().order_by('-id')
    return render(request, 'servicos/lista_os.html', {'ordens': ordens})

@login_required
def nova_os(request):
    if request.method == 'POST':
        form = OSForm(request.POST)
        formset_pecas = ItemPecaFormSet(request.POST)
        formset_servicos = ItemServicoFormSet(request.POST)

        if form.is_valid() and formset_pecas.is_valid() and formset_servicos.is_valid():
            try:
                with transaction.atomic():
                    ordem_servico = form.save()
                    
                    # Processa Peças (ignora linhas vazias ou sem quantidade)
                    pecas_disponiveis = Pecas.objects.filter(ativo=True ).order_by('descricao')
                    for item in pecas_disponiveis:
                        if hasattr(item, 'peca') and item.peca and item.quantidade > 0:
                            item.ordem_servico = ordem_servico
                            item.save()

                    # Processa Serviços
                    servicos = formset_servicos.save(commit=False)
                    for item in servicos:
                        if hasattr(item, 'servico') and item.servico and item.quantidade > 0:
                            item.os = ordem_servico
                            item.save()

                    ordem_servico.atualizar_total()
                
                messages.success(request, "Ordem de Serviço criada com sucesso!")
                return redirect('lista_os')
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = OSForm()
        formset_pecas = ItemPecaFormSet()
        formset_servicos = ItemServicoFormSet()

    # --- CORREÇÃO CRÍTICA AQUI ---
    # Filtra o campo 'peca' dentro de cada formulário do formset antes de renderizar
    for f in formset_pecas.forms:
        f.fields['peca'].queryset = Pecas.objects.filter(ativo=True, estoque_atual__gt=0).order_by('descricao')

    return render(request, 'servicos/form_os.html', {
        'form': form, 
        'formset_pecas': formset_pecas, 
        'formset_servicos': formset_servicos
    })

@login_required
def editar_os(request, pk):
    os_instancia = get_object_or_404(OrdemServico, pk=pk)
    
    # Validação de status que definimos anteriormente
    if os_instancia.status != 'ORC':
        messages.warning(request, "Apenas orçamentos podem ser editados.")
        return redirect('lista_os')

    if request.method == 'POST':
        # IMPORTANTE: Passar a 'instance' aqui é o que garante o UPDATE em vez de um novo INSERT
        form = OSForm(request.POST, instance=os_instancia)
        formset_pecas = ItemPecaFormSet(request.POST, instance=os_instancia)
        formset_servicos = ItemServicoFormSet(request.POST, instance=os_instancia)

        if form.is_valid() and formset_pecas.is_valid() and formset_servicos.is_valid():
            try:
                with transaction.atomic():
                    # 1. Guarda o cabeçalho
                    ordem_servico = form.save()
                    
                    # 2. Guarda os formsets diretamente (isso processa deletes e updates)
                    formset_pecas.save()
                    formset_servicos.save()
                    
                    # 3. Recalcula o total
                    ordem_servico.atualizar_total()
                
                messages.success(request, f"OS #{ordem_servico.id} atualizada com sucesso!")
                return redirect('lista_os')
            except ValueError as e:
                messages.error(request, str(e))
    else:
        # Carregamento inicial (GET)
        form = OSForm(instance=os_instancia)
        formset_pecas = ItemPecaFormSet(instance=os_instancia)
        formset_servicos = ItemServicoFormSet(instance=os_instancia)

    return render(request, 'servicos/form_os.html', {
        'form': form,
        'formset_pecas': formset_pecas,
        'formset_servicos': formset_servicos,
        'editando': True
    })

@login_required
def buscar_preco(request):
    tipo = request.GET.get('tipo')
    item_id = request.GET.get('id')
    try:
        if tipo == 'peca':
            item = Pecas.objects.get(id=item_id)
            return JsonResponse({'preco': float(item.preco_venda), 'estoque': item.estoque_atual})
        item = Servico.objects.get(id=item_id)
        return JsonResponse({'preco': float(item.valor_mao_de_obra)})
    except:
        return JsonResponse({'preco': 0}, status=404)

@login_required
def alterar_status_os(request, os_id):
    if request.method == 'POST':
        novo_status = request.POST.get('status')
        os_obj = get_object_or_404(OrdemServico, id=os_id)
        status_anterior = os_obj.status

        # Estorno de stock em cancelamento
        if novo_status == 'CAN' and status_anterior != 'CAN':
            for item in os_obj.itens_pecas.all():
                item.peca.estoque_atual += item.quantidade
                item.peca.save()
        
        # Re-validação de stock ao reabrir cancelada
        elif status_anterior == 'CAN' and novo_status != 'CAN':
            for item in os_obj.itens_pecas.all():
                if item.peca.estoque_atual >= item.quantidade:
                    item.peca.estoque_atual -= item.quantidade
                    item.peca.save()
                else:
                    return JsonResponse({'status': 'error', 'message': f'Sem stock: {item.peca.descricao}'}, status=400)

        os_obj.status = novo_status
        os_obj.save()
        return JsonResponse({'status': 'success', 'novo_label': os_obj.get_status_display()})
    
    
@login_required
def imprimir_os(request, pk):
    os_instancia = get_object_or_404(OrdemServico, pk=pk)
    return render(request, 'servicos/impressao_os.html', {'os': os_instancia})

from django.db.models import Sum
from django.utils import timezone
from .models import OrdemServico, Pecas

@login_required
def dashboard(request):
    hoje = timezone.now().date()
    
    # 1. Dados para os Cards
    os_aprovadas = OrdemServico.objects.filter(status='APR').count()
    
    faturamento = OrdemServico.objects.filter(
        status='FIN', 
        data_entrada__month=hoje.month
    ).aggregate(Sum('valor_total'))['valor_total__sum'] or 0
    
    pecas_sem_estoque = Pecas.objects.filter(estoque_atual__lte=0).count()
    
    os_em_atraso = OrdemServico.objects.filter(
        status__in=['ORC', 'APR'], 
        data_entrada__date__lt=hoje
    ).count()

    # 2. Últimas 5 Atividades (últimas OS criadas/modificadas)
    ultimas_atividades = OrdemServico.objects.all().order_by('-id')[:5]

    context = {
        'os_aprovadas': os_aprovadas,
        'faturamento': faturamento,
        'pecas_sem_estoque': pecas_sem_estoque,
        'os_em_atraso': os_em_atraso,
        'ultimas_atividades': ultimas_atividades,
    }
    return render(request, 'servicos/dashboard.html', context)

@login_required
def lista_estoque(request):
    pecas = Pecas.objects.all().order_by('descricao')
    return render(request, 'servicos/estoque.html', {'pecas': pecas})

@login_required
def criar_produto(request):
    if request.method == 'POST':
        descricao = request.POST.get('descricao')
        preco = request.POST.get('preco')
        estoque = request.POST.get('estoque')

        Pecas.objects.create(
            descricao=descricao,
            preco_venda=preco,
            estoque_atual=estoque
        )
        messages.success(request, "Produto cadastrado com sucesso!")
        return redirect('lista_estoque')
    
    return redirect('lista_estoque')

@login_required
def editar_produto(request, pk):
    produto = get_object_or_404(Pecas, pk=pk)
    
    if request.method == 'POST':
        produto.descricao = request.POST.get('descricao')
        produto.preco_venda = request.POST.get('preco').replace(',', '.')
        produto.estoque_atual = request.POST.get('estoque')
        # Captura o status do checkbox de ativação
        produto.ativo = 'ativo' in request.POST 
        
        produto.save()
        messages.success(request, f"Produto '{produto.descricao}' atualizado com sucesso!")
        return redirect('lista_estoque')
    
    return render(request, 'servicos/editar_produto.html', {'produto': produto})

@login_required
def excluir_produto(request, pk):
    produto = get_object_or_404(Pecas, pk=pk)
    
    # Verifica se o produto está em alguma OS (tabela de itens da OS)
    em_uso = ItemPeca.objects.filter(peca=produto).exists()

    if em_uso:
        produto.ativo = False
        produto.save()
        messages.warning(request, f"O produto '{produto.descricao}' possui histórico em OS e foi apenas BLOQUEADO.")
    else:
        produto.delete()
        messages.success(request, f"Produto '{produto.descricao}' excluído com sucesso.")
    
    return redirect('lista_estoque')