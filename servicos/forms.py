from django import forms
from django.forms import inlineformset_factory
from .models import OrdemServico,Veiculo,Cliente,ItemOS,Produto

class OSForm(forms.ModelForm):
    class Meta:
        model = OrdemServico
        fields = ['cliente', 'veiculo', 'status', 'data_entrega' , 'observacoes']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'veiculo': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'data_entrega': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'},format='%Y-%m-%d'),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. Começa com a lista vazia por segurança
        self.fields['veiculo'].queryset = Veiculo.objects.none()
        
        if self.instance.data_entrega:
            # Garante que o valor apareça no campo ao abrir para editar
            self.initial['data_entrega'] = self.instance.data_entrega.strftime('%Y-%m-%d')

        # 2. Se houver um cliente já selecionado (Edição ou erro de POST)
        if 'cliente' in self.data:
            try:
                cliente_id = int(self.data.get('cliente'))
                self.fields['veiculo'].queryset = Veiculo.objects.filter(cliente_id=cliente_id).distinct()
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.cliente:
            # Se for edição, traz apenas os veículos daquele cliente específico
            self.fields['veiculo'].queryset = self.instance.cliente.veiculos.all().distinct()

class ItemOSForm(forms.ModelForm):
    class Meta:
        model = ItemOS
        fields = ['produto', 'quantidade', 'preco_unitario']
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-select item-produto'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control item-quantidade', 'min': '1'}),
            'preco_unitario': forms.NumberInput(attrs={'class': 'form-control item-preco', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtra para que apenas produtos ativos apareçam no select da OS
        self.fields['produto'].queryset = Produto.objects.filter(ativo=True).order_by('descricao')

# A grande mágica: Substituímos o ItemPecaFormSet e ItemServicoFormSet por este único FormSet
ItemOSFormSet = inlineformset_factory(
    OrdemServico,
    ItemOS,
    form=ItemOSForm,
    extra=1,          # Uma linha vazia por padrão
    can_delete=True   # Permite remover itens da OS
)


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nome', 'cpf_cnpj', 'telefone', 'email', 'endereco', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'cpf_cnpj': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
        }

class VeiculoForm(forms.ModelForm):
    class Meta:
        model = Veiculo
        fields = ['cliente', 'modelo', 'placa', 'ano', 'cor']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control'}),
            'placa': forms.TextInput(attrs={'class': 'form-control'}),
            'ano': forms.NumberInput(attrs={'class': 'form-control'}),
            'cor': forms.TextInput(attrs={'class': 'form-control'}),
        }