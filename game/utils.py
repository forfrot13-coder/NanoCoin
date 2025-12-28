# game/utils.py
from django.db.models import Sum, F, Q
from django.core.cache import cache
from django.conf import settings
from .models import PlayerProfile, Inventory, GameItem, MarketListing


def calculate_mining_power(profile):
    """
    Calculate total mining power for a player based on active miners.
    """
    result = Inventory.objects.filter(
        player=profile,
        item__item_type='MINER',
        is_active=True
    ).aggregate(
        total=Sum(F('item__mining_rate') * F('quantity'))
    )
    return result.get('total') or 0


def calculate_mining_consumption(profile):
    """
    Calculate total electricity consumption for active miners.
    """
    result = Inventory.objects.filter(
        player=profile,
        item__item_type='MINER',
        is_active=True
    ).aggregate(
        total=Sum(F('item__electricity_consumption') * F('quantity'))
    )
    return result.get('total') or 0


def get_player_with_stats(profile_id):
    """
    Get player profile with all related data and calculated stats.
    """
    profile = PlayerProfile.objects.select_related(
        'user', 'equipped_skin', 'avatar', 'slot_1', 'slot_2', 'slot_3'
    ).get(id=profile_id)
    profile.mining_power = calculate_mining_power(profile)
    return profile


def get_optimized_inventory(player):
    """
    Get inventory with optimized select_related queries.
    """
    return Inventory.objects.filter(
        player=player,
        quantity__gt=0
    ).select_related('item').order_by('-quantity')


def get_optimized_miners(profile):
    """
    Get miners with optimized queries and aggregated stats.
    """
    miners = Inventory.objects.filter(
        player=profile,
        item__item_type='MINER',
        quantity__gt=0
    ).select_related('item')
    
    stats = miners.filter(is_active=True).aggregate(
        total_rate=Sum(F('item__mining_rate') * F('quantity')),
        total_consumption=Sum(F('item__electricity_consumption') * F('quantity'))
    )
    
    return miners, stats


def get_optimized_market_listings(exclude_profile=None):
    """
    Get market listings with optimized queries.
    """
    queryset = MarketListing.objects.select_related(
        'item', 'seller', 'seller__user'
    ).order_by('-created_at')
    
    if exclude_profile:
        queryset = queryset.exclude(seller=exclude_profile)
    
    return queryset[:100]


def get_optimized_leaderboard(limit=100):
    """
    Get leaderboard with optimized queries.
    """
    return PlayerProfile.objects.select_related('user').order_by('-diamonds')[:limit]


# Cache Manager for Redis caching
class CacheManager:
    CACHE_TIMEOUTS = {
        'leaderboard': 3600,  # 1 hour
        'player_stats': 300,  # 5 minutes
        'market_listings': 60,  # 1 minute
        'shop_items': 300,  # 5 minutes
    }
    
    @staticmethod
    def get_leaderboard(page=1, page_size=100):
        """
        Get cached leaderboard or compute and cache it.
        """
        cache_key = f'leaderboard_{page}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        
        offset = (page - 1) * page_size
        leaderboard = list(PlayerProfile.objects.select_related('user').order_by(
            '-diamonds'
        )[offset:offset + page_size])
        
        cache.set(cache_key, leaderboard, CacheManager.CACHE_TIMEOUTS['leaderboard'])
        return leaderboard
    
    @staticmethod
    def get_player_stats(profile_id):
        """
        Get cached player stats or compute and cache.
        """
        cache_key = f'player_stats_{profile_id}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            profile = get_player_with_stats(profile_id)
            stats = {
                'coins': profile.coins,
                'diamonds': profile.diamonds,
                'mining_power': profile.mining_power,
                'click_level': profile.click_level,
            }
            cache.set(cache_key, stats, CacheManager.CACHE_TIMEOUTS['player_stats'])
            return stats
        except PlayerProfile.DoesNotExist:
            return None
    
    @staticmethod
    def invalidate_leaderboard():
        """
        Invalidate all leaderboard cache pages.
        """
        for page in range(1, 10):  # Assuming max 1000 players
            cache.delete(f'leaderboard_{page}')
    
    @staticmethod
    def invalidate_player_stats(profile_id):
        """
        Invalidate specific player stats cache.
        """
        cache.delete(f'player_stats_{profile_id}')
    
    @staticmethod
    def invalidate_market_listings():
        """
        Invalidate market listings cache.
        """
        cache.delete('market_listings_all')
    
    @staticmethod
    def get_shop_items():
        """
        Get cached shop items.
        """
        cache_key = 'shop_items_all'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        
        items = list(GameItem.objects.filter(
            price_diamonds__gt=0,
            is_hidden_in_shop=False
        ).exclude(item_type='ENERGY'))
        
        cache.set(cache_key, items, CacheManager.CACHE_TIMEOUTS['shop_items'])
        return items
