from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from .models import OrdemServico, Pecas, Servico
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
                    pecas = formset_pecas.save(commit=False)
                    for item in pecas:
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

    return render(request, 'servicos/form_os.html', {
        'form': form, 'formset_pecas': formset_pecas, 'formset_servicos': formset_servicos
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