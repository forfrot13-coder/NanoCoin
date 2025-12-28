# game/prestige_utils.py
"""
Prestige system utilities for the game.
When players prestige, they reset their progress but gain permanent multipliers and diamonds.
"""
from django.db import transaction
from django.utils import timezone
from .models import PlayerProfile, Inventory, PrestigeMultiplier, PrestigeReward


class PrestigeSystem:
    """
    Handles all prestige-related operations.
    """
    
    BASE_PRESTIGE_COST = 1_000_000  # Base coins required for first prestige
    PRESTIGE_COST_MULTIPLIER = 1.5  # Each prestige increases cost by 50%
    DIAMOND_REWARD_RATE = 0.005  # 0.5% of current coins as diamonds
    
    @classmethod
    def get_next_prestige_cost(cls, profile):
        """
        Calculate the coins required for the next prestige.
        """
        prestige_stats, _ = PrestigeMultiplier.objects.get_or_create(player=profile)
        cost = int(cls.BASE_PRESTIGE_COST * (cls.PRESTIGE_COST_MULTIPLIER ** prestige_stats.prestige_count))
        return cost
    
    @classmethod
    def can_prestige(cls, profile):
        """
        Check if player can prestige (has enough coins).
        """
        cost = cls.get_next_prestige_cost(profile)
        return profile.coins >= cost
    
    @classmethod
    @transaction.atomic
    def do_prestige(cls, profile):
        """
        Execute the prestige process for a player.
        Returns a dict with prestige results.
        """
        prestige_stats = PrestigeMultiplier.objects.select_for_update().get(player=profile)
        
        # Check requirements
        required_coins = cls.get_next_prestige_cost(profile)
        if profile.coins < required_coins:
            return {
                'success': False,
                'error': f'Not enough coins. Need {required_coins:,} coins.'
            }
        
        # Calculate rewards
        diamonds_earned = int(profile.coins * cls.DIAMOND_REWARD_RATE)
        
        # Delete all inventory items
        Inventory.objects.filter(player=profile).delete()
        
        # Reset player profile
        profile.coins = 0
        profile.diamonds += diamonds_earned
        profile.energy = profile.max_energy
        profile.electricity = profile.max_electricity
        profile.click_level = 1
        profile.click_xp = 0
        profile.click_xp_to_next = 100
        profile.active_boost_until = None
        profile.boost_multiplier = 1.0
        profile.equipped_skin = None
        profile.avatar = None
        profile.slot_1 = None
        profile.slot_2 = None
        profile.slot_3 = None
        profile.save()
        
        # Update prestige stats
        prestige_stats.prestige_count += 1
        prestige_stats.prestige_multiplier += 0.1
        prestige_stats.last_prestige_date = timezone.now()
        prestige_stats.save()
        
        return {
            'success': True,
            'prestige_level': prestige_stats.prestige_count,
            'prestige_multiplier': prestige_stats.prestige_multiplier,
            'diamonds_earned': diamonds_earned,
            'message': f'Prestige successful! Earned {diamonds_earned:,} diamonds.'
        }
    
    @classmethod
    def get_prestige_info(cls, profile):
        """
        Get current prestige status for a player.
        """
        prestige_stats, created = PrestigeMultiplier.objects.get_or_create(player=profile)
        
        return {
            'prestige_count': prestige_stats.prestige_count,
            'prestige_multiplier': prestige_stats.prestige_multiplier,
            'next_prestige_cost': cls.get_next_prestige_cost(profile),
            'can_prestige': cls.can_prestige(profile),
            'last_prestige_date': prestige_stats.last_prestige_date,
        }
    
    @classmethod
    def apply_prestige_multiplier(cls, profile, base_value, multiplier_type='all'):
        """
        Apply prestige multiplier to a base value.
        
        Args:
            profile: PlayerProfile instance
            base_value: The value to multiply
            multiplier_type: 'mining', 'click', 'all'
        """
        prestige_stats, _ = PrestigeMultiplier.objects.get_or_create(player=profile)
        
        multiplier = prestige_stats.prestige_multiplier
        
        if multiplier_type == 'mining':
            # Mining gets full prestige multiplier
            return int(base_value * multiplier)
        elif multiplier_type == 'click':
            # Clicking gets partial multiplier (50%)
            click_multiplier = 1 + (multiplier - 1) * 0.5
            return int(base_value * click_multiplier)
        else:
            # Full multiplier for everything
            return int(base_value * multiplier)
