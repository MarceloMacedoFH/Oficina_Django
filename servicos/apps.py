from django.apps import AppConfig

class ServicosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'servicos'

    def ready(self):
        # Isso garante que os sinais sejam registrados quando o Django iniciar
        import servicos.signals