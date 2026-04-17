from django import forms
from .models import OrdemServico, ItemPeca, ItemServico,Veiculo

class OSForm(forms.ModelForm):
    class Meta:
        model = OrdemServico
        fields = ['cliente', 'veiculo', 'status', 'observacoes']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'veiculo': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. Começa com a lista vazia por segurança
        self.fields['veiculo'].queryset = Veiculo.objects.none()

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
ItemPecaFormSet = forms.inlineformset_factory(
    OrdemServico, ItemPeca, fields=['peca', 'quantidade', 'preco_unitario'],
    extra=1, can_delete=True, min_num=0, validate_min=False,
    widgets={
        'peca': forms.Select(attrs={'class': 'form-select item-select', 'data-tipo': 'peca'}),
        'quantidade': forms.NumberInput(attrs={'class': 'form-control item-qty'}),
        'preco_unitario': forms.NumberInput(attrs={'class': 'form-control item-price', 'readonly': 'readonly'}),
    }
)
for form in ItemPecaFormSet.form.base_fields.values(): form.required = False

ItemServicoFormSet = forms.inlineformset_factory(
    OrdemServico, ItemServico, fields=['servico', 'quantidade', 'preco_unitario'],
    extra=1, can_delete=True, min_num=0, validate_min=False,
    widgets={
        'servico': forms.Select(attrs={'class': 'form-select item-select', 'data-tipo': 'servico'}),
        'quantidade': forms.NumberInput(attrs={'class': 'form-control item-qty'}),
        'preco_unitario': forms.NumberInput(attrs={'class': 'form-control item-price', 'readonly': 'readonly'}),
    }
)
for form in ItemServicoFormSet.form.base_fields.values(): form.required = False