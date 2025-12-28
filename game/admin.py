# game/admin.py
from django.contrib import admin
from .models import PlayerProfile, GameItem, Inventory, MarketListing, PromoCode, UsedPromo, Achievement, UserAchievement, AuctionListing

# تنظیمات نمایش پروفایل کاربر
@admin.register(PlayerProfile)
class PlayerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'coins', 'diamonds', 'energy', 'electricity')
    search_fields = ('user__username',)

# تنظیمات نمایش آیتم‌های بازی
@admin.register(GameItem)
class GameItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'item_type', 'price_diamonds', 'stock', 'item_code')
    list_filter = ('item_type', 'is_hidden_in_shop')
    search_fields = ('name', 'item_code')

# تنظیمات نمایش اینونتوری (چه کسی چه دارد)
@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('player', 'item', 'quantity')
    list_filter = ('item__item_type',)
    search_fields = ('player__user__username', 'item__name')

@admin.register(MarketListing)
class MarketListingAdmin(admin.ModelAdmin):
    list_display = ('item', 'seller', 'price', 'created_at')

@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'reward_coins', 'reward_diamonds', 'current_uses', 'max_uses')

@admin.register(AuctionListing)
class AuctionListingAdmin(admin.ModelAdmin):
    list_display = ('item', 'seller', 'current_price', 'buy_now_price', 'ends_at', 'is_active')
    list_filter = ('is_active',)

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'target_coins', 'target_diamonds', 'target_miners')

@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('player', 'achievement', 'achieved_at')

# ثبت مدل‌های ساده
admin.site.register(UsedPromo)
