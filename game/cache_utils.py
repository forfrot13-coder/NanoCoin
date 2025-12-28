# game/cache_utils.py
"""
Redis caching utilities for game performance optimization.
"""
from django.core.cache import cache
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


class GameCacheManager:
    """
    Centralized cache management for game data.
    """
    
    # Cache key prefixes
    LEADERBOARD_PREFIX = 'leaderboard'
    PLAYER_STATS_PREFIX = 'player_stats'
    MARKET_PREFIX = 'market_listings'
    SHOP_PREFIX = 'shop_items'
    
    # Cache TTLs in seconds
    TTL_LEADERBOARD = 3600  # 1 hour
    TTL_PLAYER = 300  # 5 minutes
    TTL_MARKET = 60  # 1 minute
    TTL_SHOP = 300  # 5 minutes
    
    @classmethod
    def get_leaderboard_key(cls, page=1):
        return f'{cls.LEADERBOARD_PREFIX}_{page}'
    
    @classmethod
    def get_player_key(cls, profile_id):
        return f'{cls.PLAYER_STATS_PREFIX}_{profile_id}'
    
    @classmethod
    def get_market_key(cls):
        return f'{cls.MARKET_PREFIX}_all'
    
    @classmethod
    def get_shop_key(cls):
        return f'{cls.SHOP_PREFIX}_all'
    
    @classmethod
    def get_leaderboard(cls, page=1):
        """Retrieve cached leaderboard page."""
        key = cls.get_leaderboard_key(page)
        return cache.get(key)
    
    @classmethod
    def set_leaderboard(cls, data, page=1):
        """Cache leaderboard page."""
        key = cls.get_leaderboard_key(page)
        cache.set(key, data, cls.TTL_LEADERBOARD)
    
    @classmethod
    def get_player_stats(cls, profile_id):
        """Retrieve cached player stats."""
        key = cls.get_player_key(profile_id)
        return cache.get(key)
    
    @classmethod
    def set_player_stats(cls, profile_id, data):
        """Cache player stats."""
        key = cls.get_player_key(profile_id)
        cache.set(key, data, cls.TTL_PLAYER)
    
    @classmethod
    def invalidate_leaderboard(cls):
        """Invalidate all leaderboard cache pages."""
        for page in range(1, 11):  # Support up to 1000 players
            cache.delete(cls.get_leaderboard_key(page))
    
    @classmethod
    def invalidate_player(cls, profile_id):
        """Invalidate specific player cache."""
        cache.delete(cls.get_player_key(profile_id))
    
    @classmethod
    def invalidate_market(cls):
        """Invalidate market listings cache."""
        cache.delete(cls.get_market_key())
    
    @classmethod
    def invalidate_shop(cls):
        """Invalidate shop items cache."""
        cache.delete(cls.get_shop_key())
    
    @classmethod
    def invalidate_all(cls):
        """Invalidate all game caches."""
        cls.invalidate_leaderboard()
        cls.invalidate_market()
        cls.invalidate_shop()


# Signal handlers for automatic cache invalidation
def setup_cache_signals():
    """
    Connect signal handlers for automatic cache invalidation.
    This should be called in the app's ready() method.
    """
    from .models import PlayerProfile, Inventory, MarketListing
    from .cache_utils import GameCacheManager
    
    @receiver(post_save, sender=PlayerProfile)
    def on_playerprofile_save(sender, instance, **kwargs):
        """Invalidate player stats cache when profile is updated."""
        GameCacheManager.invalidate_player(instance.id)
        GameCacheManager.invalidate_leaderboard()
    
    @receiver(post_save, sender=Inventory)
    def on_inventory_save(sender, instance, **kwargs):
        """Invalidate player stats when inventory changes."""
        if instance.player_id:
            GameCacheManager.invalidate_player(instance.player_id)
    
    @receiver(post_save, sender=MarketListing)
    def on_marketlisting_save(sender, instance, **kwargs):
        """Invalidate market cache when listings change."""
        GameCacheManager.invalidate_market()
