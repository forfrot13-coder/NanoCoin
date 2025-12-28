# game/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    GameItem, PlayerProfile, Inventory, MarketListing,
    UserQuest, UserAchievement, Achievement, AuctionListing
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        read_only_fields = ['id', 'username']


class GameItemSerializer(serializers.ModelSerializer):
    item_type_display = serializers.CharField(source='get_item_type_display', read_only=True)
    
    class Meta:
        model = GameItem
        fields = [
            'id', 'name', 'item_type', 'item_type_display', 'item_code',
            'description', 'image', 'price_diamonds', 'sell_price', 'stock',
            'is_hidden_in_shop', 'mining_rate', 'electricity_consumption',
            'miner_diamond_chance', 'buff_mining_speed', 'buff_click_coins',
            'buff_luck', 'can_drop', 'drop_chance'
        ]
        read_only_fields = ['id']


class InventorySerializer(serializers.ModelSerializer):
    item = GameItemSerializer(read_only=True)
    item_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Inventory
        fields = ['id', 'item', 'item_id', 'quantity', 'is_active']
        read_only_fields = ['id']


class PlayerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    equipped_skin = GameItemSerializer(read_only=True)
    avatar = GameItemSerializer(read_only=True)
    slot_1 = GameItemSerializer(read_only=True)
    slot_2 = GameItemSerializer(read_only=True)
    slot_3 = GameItemSerializer(read_only=True)
    mining_power = serializers.SerializerMethodField()
    
    class Meta:
        model = PlayerProfile
        fields = [
            'id', 'user', 'coins', 'diamonds', 'energy', 'max_energy',
            'electricity', 'max_electricity', 'click_level', 'click_xp',
            'click_xp_to_next', 'active_boost_until', 'boost_multiplier',
            'equipped_skin', 'avatar', 'slot_1', 'slot_2', 'slot_3',
            'last_mined_at', 'daily_streak', 'mining_power'
        ]
        read_only_fields = ['id', 'user', 'mining_power']
    
    def get_mining_power(self, obj):
        from .utils import calculate_mining_power
        return calculate_mining_power(obj)


class MarketListingSerializer(serializers.ModelSerializer):
    item = GameItemSerializer(read_only=True)
    seller_username = serializers.CharField(source='seller.user.username', read_only=True)
    
    class Meta:
        model = MarketListing
        fields = [
            'id', 'item', 'seller_username', 'price', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class UserQuestSerializer(serializers.ModelSerializer):
    quest_type_display = serializers.CharField(source='get_quest_type_display', read_only=True)
    
    class Meta:
        model = UserQuest
        fields = [
            'id', 'code', 'title', 'quest_type', 'quest_type_display',
            'goal', 'progress', 'reward_coins', 'reward_diamonds',
            'reward_xp', 'completed'
        ]
        read_only_fields = ['id']


class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = [
            'id', 'code', 'title', 'description', 'icon',
            'target_coins', 'target_diamonds', 'target_miners',
            'reward_coins', 'reward_diamonds'
        ]
        read_only_fields = ['id']


class UserAchievementSerializer(serializers.ModelSerializer):
    achievement = AchievementSerializer(read_only=True)
    
    class Meta:
        model = UserAchievement
        fields = ['id', 'achievement', 'achieved_at']
        read_only_fields = ['id', 'achieved_at']


class AuctionListingSerializer(serializers.ModelSerializer):
    item = GameItemSerializer(read_only=True)
    seller_username = serializers.CharField(source='seller.user.username', read_only=True)
    current_bidder_username = serializers.CharField(
        source='current_bidder.user.username', read_only=True, allow_null=True
    )
    
    class Meta:
        model = AuctionListing
        fields = [
            'id', 'item', 'seller_username', 'starting_price', 'current_price',
            'current_bidder_username', 'buy_now_price', 'ends_at', 'is_active'
        ]
        read_only_fields = ['id']


class PrestigeMultiplierSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import PrestigeMultiplier
        model = PrestigeMultiplier
        fields = ['prestige_count', 'prestige_multiplier', 'last_prestige_date']
