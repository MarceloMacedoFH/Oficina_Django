from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from .models import OrdemServico, Pecas, Servico, ItemPeca, Veiculo, Cliente
from .forms import OSForm, ItemPecaFormSet, ItemServicoFormSet, ClienteForm, VeiculoForm

@login_required
def lista_ordens_servico(request): 
    ordens = OrdemServico.objects.all().order_by('-id')
    return render(request, 'servicos/lista_os.html', {'ordens': ordens})

@login_required
def nova_os(request):
    if request.method == 'POST':
        form = OSForm(request.POST)
        
        # TRUQUE DE ARQUITETURA: Criamos a OS em memória (commit=False)
        # Isso permite validar os formsets filhos sem gravar o pai no banco ainda.
        os_temp = form.save(commit=False)
        
        # Passamos a instância para que o Django cuide de ligar as ForeignKeys sozinho
        formset_pecas = ItemPecaFormSet(request.POST, instance=os_temp, prefix='itens_pecas')
        formset_servicos = ItemServicoFormSet(request.POST, instance=os_temp, prefix='itens_servicos')

        if form.is_valid() and formset_pecas.is_valid() and formset_servicos.is_valid():
            try:
                with transaction.atomic():
                    # 1. Salva a OS no banco (agora ela tem um ID definitivo)
                    ordem_servico = form.save()
                    
                    # 2. Atualiza a referência dos formsets com a OS salva
                    formset_pecas.instance = ordem_servico
                    formset_servicos.instance = ordem_servico

                    # 3. O Django salva os itens, deleta os marcados (se houver) 
                    # e aciona os seus métodos save() customizados de estoque automaticamente
                    formset_pecas.save()
                    formset_servicos.save()

                    # 4. Atualiza totalizador
                    ordem_servico.atualizar_total()
                
                messages.success(request, "Ordem de Serviço gravada com sucesso!")
                return redirect('lista_os')
            
            except ValueError as e:
                # Captura os erros gerados pelas suas travas de Estoque no model
                messages.error(request, f"Trava de Estoque: {str(e)}")
            except Exception as e:
                messages.error(request, f"Erro de persistência: {str(e)}")
        else:
            # BLINDAGEM CONTRA ERRO SILENCIOSO: Mostra na tela exatamente qual campo falhou
            for error in form.errors.values():
                messages.error(request, f"Erro na OS: {error}")
            
            for form_errado in formset_pecas.errors:
                for erro in form_errado.values():
                    messages.error(request, f"Erro nas Peças: {erro}")
                    
            for form_errado in formset_servicos.errors:
                for erro in form_errado.values():
                    messages.error(request, f"Erro nos Serviços: {erro}")
                    
            messages.warning(request, "Falha na validação. Os campos com erro foram impedidos de gravar.")
    else:
        form = OSForm()
        formset_pecas = ItemPecaFormSet(prefix='itens_pecas')
        formset_servicos = ItemServicoFormSet(prefix='itens_servicos')

    # Filtro visual para a tela: exibe apenas peças disponíveis
    for f in formset_pecas.forms:
        f.fields['peca'].queryset = Pecas.objects.filter(ativo=True, estoque_atual__gt=0).order_by('descricao')

    return render(request, 'servicos/form_os.html', {
        'form': form, 
        'formset_pecas': formset_pecas, 
        'formset_servicos': formset_servicos,
        'editando': False
    })

@login_required
def editar_os(request, pk):
    os_instancia = get_object_or_404(OrdemServico, pk=pk)
    
    if os_instancia.status != 'ORC':
        messages.warning(request, "Apenas orçamentos podem ser editados.")
        return redirect('lista_os')

    if request.method == 'POST':
        form = OSForm(request.POST, instance=os_instancia)
        formset_pecas = ItemPecaFormSet(request.POST, instance=os_instancia, prefix='itens_pecas')
        formset_servicos = ItemServicoFormSet(request.POST, instance=os_instancia, prefix='itens_servicos')

        if form.is_valid() and formset_pecas.is_valid() and formset_servicos.is_valid():
            try:
                with transaction.atomic():
                    ordem_servico = form.save()
                    formset_pecas.save()
                    formset_servicos.save()
                    ordem_servico.atualizar_total()
                
                messages.success(request, f"OS #{ordem_servico.id} atualizada com sucesso!")
                return redirect('lista_os')
            except ValueError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Erro na validação do formulário de Edição. Revise os valores informados.")
    else:
        form = OSForm(instance=os_instancia)
        formset_pecas = ItemPecaFormSet(instance=os_instancia, prefix='itens_pecas')
        formset_servicos = ItemServicoFormSet(instance=os_instancia, prefix='itens_servicos')

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
def buscar_veiculos_cliente(request):
    cliente_id = request.GET.get('cliente_id')
    if not cliente_id:
        return JsonResponse([], safe=False)
    veiculos = Veiculo.objects.filter(cliente_id=cliente_id).values('id', 'modelo', 'placa').distinct()
    return JsonResponse(list(veiculos), safe=False)

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

@login_required
def dashboard(request):
    hoje = timezone.now().date()
    
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
        # Tratamento para garantir que a vírgula do front não quebre o Decimal
        preco_raw = request.POST.get('preco').replace(',', '.')
        produto.preco_venda = preco_raw
        produto.estoque_atual = request.POST.get('estoque')
        produto.ativo = 'ativo' in request.POST 
        
        produto.save()
        messages.success(request, f"Produto '{produto.descricao}' atualizado com sucesso!")
    
    return redirect('lista_estoque') # Sempre volta para a listagem

@login_required
def excluir_produto(request, pk):
    produto = get_object_or_404(Pecas, pk=pk)
    em_uso = ItemPeca.objects.filter(peca=produto).exists()

    if em_uso:
        produto.ativo = False
        produto.save()
        messages.warning(request, f"O produto '{produto.descricao}' possui histórico em OS e foi apenas BLOQUEADO.")
    else:
        produto.delete()
        messages.success(request, f"Produto '{produto.descricao}' excluído com sucesso.")
    
    return redirect('lista_estoque')


@login_required
def lista_clientes(request):
    clientes = Cliente.objects.all().order_by('nome')
    form = ClienteForm()
    
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cliente cadastrado com sucesso!")
            return redirect('lista_clientes')
            
    return render(request, 'servicos/lista_clientes.html', {
        'clientes': clientes, 
        'form': form
    })

@login_required
def editar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    
    if request.method == 'POST':
        cliente.nome = request.POST.get('nome')
        # Tratamento para garantir que a vírgula do front não quebre o Decimal
        cliente.cpf_cnpj = request.POST.get('cpfcnp')
        cliente.telefone = request.POST.get('telefone')
        cliente.email = request.POST.get('email')
        cliente.endereco = request.POST.get('endereco')
        cliente.ativo = 'ativo' in request.POST 
        
        cliente.save()
        messages.success(request, f"Cliente '{cliente.nome}' atualizado com sucesso!")
    
    return redirect('lista_clientes') # Sempre volta para a listagem

@login_required
def excluir_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    em_uso = Cliente.objects.filter(nome=cliente).exists()

    if em_uso:
        cliente.ativo = False
        cliente.save()
        messages.warning(request, f"O cliente '{cliente.nome}' possui histórico em OS e foi apenas BLOQUEADO.")
    else:
        cliente.delete()
        messages.success(request, f"cliente '{cliente.nome}' excluído com sucesso.")
    
    return redirect('lista_clientes')

@login_required
def lista_veiculos(request):
    veiculos = Veiculo.objects.all().order_by('-id')
    form = VeiculoForm()
    
    if request.method == 'POST':
        form = VeiculoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Veículo cadastrado com sucesso!")
            return redirect('lista_veiculos')
            
    return render(request, 'servicos/lista_veiculos.html', {
        'veiculos': veiculos, 
        'form': form
    })