from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views # Importante

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ordens/', include('servicos.urls')),
    
    # Rotas de Autenticação
    path('', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]