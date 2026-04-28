from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from .models import OrdemServico, Veiculo, Cliente,Produto, ItemOS
from .forms import ItemOSFormSet, OSForm, ClienteForm, VeiculoForm

@login_required
def lista_ordens_servico(request): 
    ordens = OrdemServico.objects.all().order_by('-id')
    return render(request, 'servicos/lista_os.html', {'ordens': ordens})

@login_required
def nova_os(request):
    if request.method == 'POST':
        form = OSForm(request.POST)
        os_temp = form.save(commit=False)
        
        # Agora usamos apenas um formset para tudo (Peças e Serviços)
        formset = ItemOSFormSet(request.POST, instance=os_temp)
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    os_temp.save()
                    formset.save()
                    os_temp.atualizar_total()
                messages.success(request, "Ordem de Serviço criada com sucesso!")
                return redirect('lista_os')
            except ValueError as e:
                messages.error(request, f"Erro ao salvar no banco: {e}")
        else:
            # Isso vai imprimir no terminal do VS Code exatamente qual campo falhou
            print("ERROS NO FORM:", form.errors)
            print("ERROS NO FORMSET:", formset.errors) 
            
            for i, f_err in enumerate(formset.errors):
                if f_err:
                    messages.error(request, f"Erro no Item {i+1}: {f_err}")
            
            messages.error(request, "Erro ao validar os dados. Verifique os campos.")
    else:
        form = OSForm()
        formset = ItemOSFormSet()
        
    return render(request, 'servicos/form_os.html', {
        'form': form, 
        'formset': formset
    })

@login_required
def editar_os(request, pk):
    os_instancia = get_object_or_404(OrdemServico, pk=pk)
    
    if os_instancia.status != 'ORC':
        messages.warning(request, "Apenas orçamentos podem ser editados.")
        return redirect('lista_os')

    if request.method == 'POST':
        form = OSForm(request.POST, instance=os_instancia)
        formset = ItemOSFormSet(request.POST, instance=os_instancia)
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    formset.save()
                    os_instancia.atualizar_total()
                messages.success(request, f"Ordem de Serviço #{pk} atualizada com sucesso!")
                return redirect('lista_os')
            except Exception as e:
                messages.error(request, f"Erro ao salvar: {e}")
    else:
        # ESTA PARTE É A QUE ESTAVA FALTANDO:
        # Define o form e o formset para quando a página for carregada (GET)
        form = OSForm(instance=os_instancia)
        formset = ItemOSFormSet(instance=os_instancia)

    # O dicionário de contexto agora sempre terá 'form' e 'formset' definidos
    return render(request, 'servicos/form_os.html', {
        'form': form,
        'formset': formset,
        'os': os_instancia
    })

@login_required
def buscar_preco(request):
    """Retorna o preço de venda de qualquer produto ou serviço"""
    produto_id = request.GET.get('id')
    if produto_id:
        produto = get_object_or_404(Produto, id=produto_id)
        return JsonResponse({'preco': float(produto.preco_venda)})
    return JsonResponse({'preco': 0.00})

@login_required
def buscar_veiculos_cliente(request):
    cliente_id = request.GET.get('cliente_id')
    # Importante: verifique se os campos 'id', 'modelo' e 'placa' existem no seu model Veiculo
    veiculos = Veiculo.objects.filter(cliente_id=cliente_id).values('id', 'modelo', 'placa')
    return JsonResponse(list(veiculos), safe=False)

@login_required
def alterar_status_os(request, os_id):
    if request.method == 'POST':
        # get_object_or_404 garante que se a OS não existir, ele não quebra o servidor
        os = get_object_or_404(OrdemServico, id=os_id)
        novo_status = request.POST.get('status')
        status_atu = os.status

        if status_atu in ['FIN', 'CAN']:
            messages.error(request, f"Esta OS está {os.get_status_display()} e não pode ser alterada.")
            return redirect('lista_os')
        
        os.status = novo_status
        os.save()
        return redirect('lista_os')
    
    return redirect('lista_os')
    
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
        financeiro__pago=True,
        financeiro__data_pagamento__month=hoje.month,
        financeiro__data_pagamento__year=hoje.year
    ).aggregate(Sum('valor_total'))['valor_total__sum'] or 0
    pecas_sem_estoque = Produto.objects.filter(estoque_atual__lte=0).count()
    os_em_atraso = OrdemServico.objects.filter(
        status__in=['APR'], 
        data_entrega__date__lt=hoje
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
    produto = Produto.objects.all().order_by('descricao')
    return render(request, 'servicos/estoque.html', {'produtos': produto})

@login_required
def criar_produto(request):
    if request.method == 'POST':
        descricao = request.POST.get('descricao')
        tipo = request.POST.get('tipo_produto')
        um = request.POST.get('unidade_medida')
        preco_compra = request.POST.get('preco_compra')
        preco_raw = request.POST.get('preco_venda').replace(',', '.')
        estoque = request.POST.get('estoque_atual')

        Produto.objects.create(
            descricao=descricao,
            tipo_produto = tipo,
            unidade_medida = um,
            preco_compra = preco_compra,
            preco_venda = preco_raw,
            estoque_atual=estoque
        )
        messages.success(request, "Produto cadastrado com sucesso!")
        return redirect('lista_estoque')
    
    return redirect('lista_estoque')

@login_required
def editar_produto(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    
    if request.method == 'POST':
        produto.descricao = request.POST.get('descricao')
        produto.tipo_produto = request.POST.get('tipo_produto')
        produto.unidade_medida = request.POST.get('unidade_medida')
        produto.preco_compra = request.POST.get('preco_compra')
        preco_raw = request.POST.get('preco_venda').replace(',', '.')
        produto.preco_venda = preco_raw
        produto.estoque_atual = request.POST.get('estoque_atual')
        produto.ativo = 'ativo' in request.POST 

        produto.save()
        messages.success(request, f"Produto '{produto.descricao}' atualizado com sucesso!")
    
    return redirect('lista_estoque') # Sempre volta para a listagem

@login_required
def excluir_produto(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    em_uso = ItemOS.objects.filter(produto=produto).exists()

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

@login_required
def editar_veiculo(request, pk):
    carro = get_object_or_404(Veiculo, pk=pk)

    if request.method == 'POST':        
        cliente = request.POST.get('cliente')
        carro.model = request.POST.get('modelo')
        carro.placa = request.POST.get('placa')
        carro.ano = request.POST.get('ano')
        carro.cor = request.POST.get('cor')
        carro.ativo = 'ativo' in request.POST 
        carro.save()
        messages.success(request, f"Veículo '{carro.modelo}' atualizado com sucesso!")
    
    return redirect('lista_veiculos') # Sempre volta para a listagem

@login_required
def excluir_veiculo(request, pk):
    carro = get_object_or_404(Veiculo, pk=pk)
    em_uso = OrdemServico.objects.filter(veiculo_id=carro).exists()

    if em_uso:
        carro.ativo = False
        carro.save()
        messages.warning(request, f"O veículo '{carro.modelo}' possui histórico em OS e foi apenas BLOQUEADO.")
    else:
        carro.delete()
        messages.success(request, f"veículo '{carro.modelo}' excluído com sucesso.")
    
    return redirect('lista_veiculos')