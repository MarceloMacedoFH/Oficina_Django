from django.urls import path
from . import views

urlpatterns = [
    # Mude o 'name' para bater exatamente com o que o template pede
    path('', views.lista_ordens_servico, name='lista_os'), 
    path('nova/', views.nova_os, name='nova_os'),
    path('buscar-preco/', views.buscar_preco, name='buscar_preco'),
    path('buscar-veiculos/', views.buscar_veiculos_cliente, name='buscar_veiculos_cliente'),
    path('alterar-status/<int:os_id>/', views.alterar_status_os, name='alterar_status_os'),
    path('editar/<int:pk>/', views.editar_os, name='editar_os'),
    path('imprimir/<int:pk>/', views.imprimir_os, name='imprimir_os'),
    path('dashboard/', views.dashboard, name='dashboard'),    
    path('estoque/', views.lista_estoque, name='lista_estoque'),
    path('estoque/novo/', views.criar_produto, name='criar_produto'),
    path('estoque/editar/<int:pk>/', views.editar_produto, name='editar_produto'),
    path('estoque/excluir/<int:pk>/', views.excluir_produto, name='excluir_produto'),
    path('clientes/', views.lista_clientes, name='lista_clientes'),
    path('clientes/editar/<int:pk>/', views.editar_cliente, name='editar_cliente'),
    path('clientes/excluir/<int:pk>/', views.excluir_cliente, name='excluir_cliente'),
    path('veiculos/', views.lista_veiculos, name='lista_veiculos'),
    path('veiculos/editar/<int:pk>/', views.editar_veiculo, name='editar_veiculo'),
    path('veiculos/excluir/<int:pk>/', views.excluir_veiculo, name='excluir_veiculo'),
]