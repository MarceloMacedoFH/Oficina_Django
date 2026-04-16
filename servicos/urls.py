from django.urls import path
from . import views

urlpatterns = [
    # Mude o 'name' para bater exatamente com o que o template pede
    path('', views.lista_ordens_servico, name='lista_os'), 
    path('nova/', views.nova_os, name='nova_os'),
    path('buscar-preco/', views.buscar_preco, name='buscar_preco'),
    path('alterar-status/<int:os_id>/', views.alterar_status_os, name='alterar_status_os'),
    path('editar/<int:pk>/', views.editar_os, name='editar_os'),
    path('imprimir/<int:pk>/', views.imprimir_os, name='imprimir_os'),
    path('dashboard/', views.dashboard, name='dashboard'),
]