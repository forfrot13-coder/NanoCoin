# game/admin.py
from django.contrib import admin
from .models import (
    PlayerProfile, GameItem, Inventory, MarketListing, PromoCode, 
    UsedPromo, Achievement, UserAchievement, AuctionListing, 
    UserQuest, PrestigeMultiplier, PrestigeReward
)

# تنظیمات نمایش پروفایل کاربر
@admin.register(PlayerProfile)
class PlayerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'coins', 'diamonds', 'energy', 'electricity', 'click_level')
    search_fields = ('user__username',)
    readonly_fields = ('user',)

# تنظیمات نمایش آیتم‌های بازی
@admin.register(GameItem)
class GameItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'item_type', 'price_diamonds', 'stock', 'item_code')
    list_filter = ('item_type', 'is_hidden_in_shop')
    search_fields = ('name', 'item_code')

# تنظیمات نمایش اینونتوری (چه کسی چه دارد)
@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('player', 'item', 'quantity', 'is_active')
    list_filter = ('item__item_type', 'is_active')
    search_fields = ('player__user__username', 'item__name')

@admin.register(MarketListing)
class MarketListingAdmin(admin.ModelAdmin):
    list_display = ('item', 'seller', 'price', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('seller__user__username', 'item__name')

@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'reward_coins', 'reward_diamonds', 'current_uses', 'max_uses')
    search_fields = ('code',)

@admin.register(AuctionListing)
class AuctionListingAdmin(admin.ModelAdmin):
    list_display = ('item', 'seller', 'current_price', 'buy_now_price', 'ends_at', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('seller__user__username', 'item__name')

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'target_coins', 'target_diamonds', 'target_miners')
    search_fields = ('title', 'code')

@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('player', 'achievement', 'achieved_at')
    list_filter = ('achievement',)
    search_fields = ('player__user__username',)

@admin.register(UserQuest)
class UserQuestAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'title', 'quest_type', 'progress', 'goal', 'completed')
    list_filter = ('quest_type', 'completed')
    search_fields = ('user__username', 'code')

@admin.register(PrestigeMultiplier)
class PrestigeMultiplierAdmin(admin.ModelAdmin):
    list_display = ('player', 'prestige_count', 'prestige_multiplier', 'last_prestige_date')
    search_fields = ('player__user__username',)

@admin.register(PrestigeReward)
class PrestigeRewardAdmin(admin.ModelAdmin):
    list_display = ('prestige_level', 'reward_type', 'reward_amount', 'description')
    list_filter = ('prestige_level', 'reward_type')

# ثبت مدل‌های ساده
admin.site.register(UsedPromo)
