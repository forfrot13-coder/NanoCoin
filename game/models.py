# game/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

class GameItem(models.Model):
    ITEM_TYPES = [
        ('MINER', 'ماینر'),
        ('GENERATOR', 'ژنراتور/باتری'),
        ('SKIN', 'اسکین'),
        ('AVATAR', 'آواتار'),
        ('LOOT', 'لوت باکس'),
        ('MATERIAL', 'متریال'),
        ('ENERGY', 'پک انرژی'),
        ('BUFF', 'باف/Artifact'),
    ]

    name = models.CharField(max_length=100)
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES)
    item_code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='items/', blank=True, null=True)
    
    # اقتصاد
    price_diamonds = models.IntegerField(default=0)
    sell_price = models.IntegerField(default=0) # قیمت فروش به سیستم
    stock = models.IntegerField(default=-1) # -1 یعنی نامحدود
    is_hidden_in_shop = models.BooleanField(default=False)

    # ویژگی‌های ماینر
    mining_rate = models.IntegerField(default=0, help_text="تولید سکه در ساعت")
    electricity_consumption = models.IntegerField(default=0, help_text="مصرف برق وات")
    miner_diamond_chance = models.FloatField(default=0, help_text="شانس پیدا کردن الماس (درصد در ساعت)")

    # ویژگی‌های باف (Slot Items)
    buff_mining_speed = models.FloatField(default=0, help_text="درصد افزایش سرعت ماین")
    buff_click_coins = models.IntegerField(default=0, help_text="سکه اضافه در هر کلیک")
    buff_luck = models.FloatField(default=0, help_text="درصد افزایش شانس (الماس و دراپ)")

    # ویژگی‌های دراپ (برای آیتم‌هایی که با کلیک پیدا میشن)
    can_drop = models.BooleanField(default=False)
    drop_chance = models.FloatField(default=0, help_text="شانس دراپ شدن در هر کلیک (درصد)")

    def __str__(self):
        return f"{self.name} ({self.get_item_type_display()})"

class PlayerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='playerprofile') # دسترسی راحت تر
    
    # منابع
    coins = models.BigIntegerField(default=0)
    diamonds = models.IntegerField(default=0)
    
    # انرژی کلیک
    energy = models.IntegerField(default=1000)
    max_energy = models.IntegerField(default=1000)
    
    # برق ماینرها
    electricity = models.IntegerField(default=5000)
    max_electricity = models.IntegerField(default=5000)
    click_level = models.IntegerField(default=1)
    click_xp = models.IntegerField(default=0)
    click_xp_to_next = models.IntegerField(default=100)
    active_boost_until = models.DateTimeField(null=True, blank=True)
    boost_multiplier = models.FloatField(default=1.0)

    # آیتم‌های فعال
    equipped_skin = models.ForeignKey(GameItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipped_by_users')
    avatar = models.ForeignKey(GameItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='avatar_users')
    
    # اسلات‌های باف (Artifacts)
    slot_1 = models.ForeignKey(GameItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='slot1_users')
    slot_2 = models.ForeignKey(GameItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='slot2_users')
    slot_3 = models.ForeignKey(GameItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='slot3_users')

    # زمان‌ها
    last_mined_at = models.DateTimeField(null=True, blank=True)
    last_daily_claim = models.DateTimeField(null=True, blank=True)
    daily_streak = models.IntegerField(default=0)

    def __str__(self):
        return self.user.username

class Inventory(models.Model):
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE)
    item = models.ForeignKey(GameItem, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('player', 'item') # جلوگیری از تکرار آیتم در دیتابیس

    def __str__(self):
        return f"{self.player.user.username} - {self.item.name} ({self.quantity})"

class MarketListing(models.Model):
    seller = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE)
    item = models.ForeignKey(GameItem, on_delete=models.CASCADE)
    price = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item.name} by {self.seller.user.username}"

class PromoCode(models.Model):
    code = models.CharField(max_length=50, unique=True)
    reward_coins = models.IntegerField(default=0)
    reward_diamonds = models.IntegerField(default=0)
    max_uses = models.IntegerField(default=100)
    current_uses = models.IntegerField(default=0)
    expiry_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.code

class UsedPromo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.ForeignKey(PromoCode, on_delete=models.CASCADE)
    used_at = models.DateTimeField(auto_now_add=True)

QUEST_TYPE_CHOICES = [
    ('CLICK', 'Click'),
    ('MINE', 'Mine'),
]

class UserQuest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=50)
    title = models.CharField(max_length=100)
    quest_type = models.CharField(max_length=10, choices=QUEST_TYPE_CHOICES)
    goal = models.IntegerField(default=0)
    progress = models.IntegerField(default=0)
    reward_coins = models.IntegerField(default=0)
    reward_diamonds = models.IntegerField(default=0)
    reward_xp = models.IntegerField(default=0)
    reset_at = models.DateField(null=True, blank=True)
    completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'code')

    def __str__(self):
        return f"{self.user.username} - {self.code}"

class Achievement(models.Model):
    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="FontAwesome or emoji code")
    target_coins = models.BigIntegerField(default=0)
    target_diamonds = models.IntegerField(default=0)
    target_miners = models.IntegerField(default=0)
    reward_coins = models.IntegerField(default=0)
    reward_diamonds = models.IntegerField(default=0)

    def __str__(self):
        return self.title

class UserAchievement(models.Model):
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE)
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    achieved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('player', 'achievement')

    def __str__(self):
        return f"{self.player.user.username} - {self.achievement.title}"

class AuctionListing(models.Model):
    seller = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE)
    item = models.ForeignKey(GameItem, on_delete=models.CASCADE)
    starting_price = models.IntegerField()
    current_price = models.IntegerField()
    current_bidder = models.ForeignKey(PlayerProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='bids')
    buy_now_price = models.IntegerField(null=True, blank=True)
    ends_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Auction: {self.item.name} by {self.seller.user.username}"

# --- سیگنال برای ساخت خودکار پروفایل ---
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        PlayerProfile.objects.get_or_create(user=instance)


class PrestigeMultiplier(models.Model):
    """
    Tracks player's prestige level and multiplier.
    Prestige allows players to reset progress for permanent bonuses.
    """
    player = models.OneToOneField(PlayerProfile, on_delete=models.CASCADE, related_name='prestige')
    prestige_count = models.IntegerField(default=0)
    prestige_multiplier = models.FloatField(default=1.0)
    last_prestige_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.player.user.username} - Prestige {self.prestige_count}"
    
    def calculate_next_milestone(self):
        """Calculate coins needed for next prestige."""
        base_cost = 1_000_000
        return int(base_cost * (1.5 ** self.prestige_count))


class PrestigeReward(models.Model):
    """
    Predefined rewards for reaching prestige milestones.
    """
    prestige_level = models.IntegerField()
    reward_type = models.CharField(max_length=20, choices=[
        ('DIAMONDS', 'Diamonds'),
        ('BONUS_MULTIPLIER', 'Bonus Multiplier'),
        ('SPECIAL_ITEM', 'Special Item'),
    ])
    reward_amount = models.IntegerField()
    description = models.TextField(blank=True)
    
    class Meta:
        unique_together = ('prestige_level', 'reward_type')
    
    def __str__(self):
        return f"Prestige {self.prestige_level} - {self.reward_type}: {self.reward_amount}"
