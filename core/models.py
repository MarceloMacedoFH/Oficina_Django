from django.db import models

class Cliente(models.Model):
    nome = models.CharField(max_length=100)
    cpf_cnpj = models.CharField(max_length=18, unique=True, verbose_name="CPF/CNPJ")
    telefone = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    endereco = models.TextField(blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome
    

class Veiculo(models.Model):
    # Relacionamos o veículo ao cliente. Se o cliente for deletado, os carros também são.
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='veiculos')
    placa = models.CharField(max_length=7, unique=True)
    modelo = models.CharField(max_length=50)
    marca = models.CharField(max_length=50)
    ano = models.PositiveIntegerField()
    cor = models.CharField(max_length=20, blank=True, null=True)
    chassi = models.CharField(max_length=17, blank=True, null=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.modelo} ({self.placa})"