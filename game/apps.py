from django.apps import AppConfig


class GameConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'game'
    verbose_name = 'NanoCoin Game'
    
    def ready(self):
        """
        Called when the app is ready.
        Setup signal handlers for cache invalidation.
        """
        # Import and setup cache signal handlers
        try:
            from .cache_utils import setup_cache_signals
            setup_cache_signals()
        except Exception as e:
            # Cache setup might fail if Redis is not available
            # This is expected during development without Redis
            import warnings
            warnings.warn(f'Cache signals not setup: {e}')
