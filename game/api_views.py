# game/api_views.py
"""
REST API Views using Django REST Framework ViewSets.
"""
from rest_framework import viewsets, views, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, F, Q
import random

from .models import (
    PlayerProfile, GameItem, Inventory, MarketListing,
    UserQuest, UserAchievement, Achievement, AuctionListing
)
from .serializers import (
    PlayerProfileSerializer, GameItemSerializer, InventorySerializer,
    MarketListingSerializer, UserQuestSerializer, UserAchievementSerializer,
    AchievementSerializer, AuctionListingSerializer
)
from .utils import (
    calculate_mining_power, get_optimized_inventory,
    get_optimized_miners, get_optimized_market_listings
)
from .prestige_utils import PrestigeSystem


class PlayerProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for player profile operations.
    """
    serializer_class = PlayerProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PlayerProfile.objects.filter(user=self.request.user)
    
    def get_object(self):
        return self.request.user.playerprofile
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's profile."""
        profile = request.user.playerprofile
        profile.mining_power = calculate_mining_power(profile)
        serializer = self.get_serializer(profile)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def click(self, request):
        """Handle click action for coins."""
        with transaction.atomic():
            profile = PlayerProfile.objects.select_for_update().get(user=request.user)
            
            if profile.energy < 1:
                return Response({
                    'status': 'error',
                    'message': 'انرژی کافی نیست',
                    'can_refill': True,
                    'refill_cost': 2,
                    'refill_amount': 50
                }, status=status.HTTP_400_BAD_REQUEST)
            
            profile.energy -= 1
            
            # Calculate click value with buffs
            extra_coins = 0
            luck_multiplier = 1.0
            active_slots = [profile.slot_1, profile.slot_2, profile.slot_3]
            
            for item in active_slots:
                if item:
                    extra_coins += item.buff_click_coins
                    if item.buff_luck > 0:
                        luck_multiplier += (item.buff_luck / 100)
            
            base_coin = 1 + (profile.click_level - 1)
            boost_active = (
                profile.active_boost_until and 
                profile.active_boost_until > timezone.now() and 
                profile.boost_multiplier > 1
            )
            current_multiplier = profile.boost_multiplier if boost_active else 1.0
            
            gained = max(int((base_coin + extra_coins) * current_multiplier), 1)
            profile.coins += gained
            
            # Diamond drop chance
            diamond_found = False
            if random.uniform(0, 1000) <= 1 * luck_multiplier:
                profile.diamonds += 1
                diamond_found = True
            
            # XP and level up
            profile.click_xp += gained
            leveled_up = False
            while profile.click_xp >= profile.click_xp_to_next:
                profile.click_xp -= profile.click_xp_to_next
                profile.click_level += 1
                profile.click_xp_to_next = int(profile.click_xp_to_next * 1.35)
                leveled_up = True
            
            profile.save()
            
            return Response({
                'status': 'success',
                'coins': profile.coins,
                'diamonds': profile.diamonds,
                'energy': profile.energy,
                'gained': gained,
                'diamond_found': diamond_found,
                'click_level': profile.click_level,
                'click_xp': profile.click_xp,
                'click_xp_to_next': profile.click_xp_to_next,
                'leveled_up': leveled_up,
            })
    
    @action(detail=False, methods=['post'])
    def collect_mine(self, request):
        """Collect mining rewards."""
        with transaction.atomic():
            profile = PlayerProfile.objects.select_for_update().get(user=request.user)
            now = timezone.now()
            last_time = profile.last_mined_at or now
            diff = now - last_time
            hours_passed = diff.total_seconds() / 3600
            
            if hours_passed < 0.016:  # Less than 1 minute
                return Response({
                    'status': 'error',
                    'message': 'صبر کنید تا ماینرها تولید کنند'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            miners = Inventory.objects.select_for_update().filter(
                player=profile, item__item_type='MINER', is_active=True
            ).select_related('item')
            
            # Calculate production with multipliers
            mining_multiplier = 1.0
            active_slots = [profile.slot_1, profile.slot_2, profile.slot_3]
            for item in active_slots:
                if item:
                    mining_multiplier += (item.buff_mining_speed / 100)
            
            total_production = 0
            total_consumption = 0
            diamond_income = 0
            
            for inv in miners:
                qty = inv.quantity
                miner = inv.item
                total_production += (miner.mining_rate * qty) * mining_multiplier
                total_consumption += miner.electricity_consumption * qty
                
                if miner.miner_diamond_chance > 0:
                    chance_factor = (miner.miner_diamond_chance / 100) * hours_passed * qty
                    if chance_factor > 1:
                        diamond_income += int(chance_factor)
                    elif random.random() < chance_factor:
                        diamond_income += 1
            
            if total_production == 0:
                return Response({
                    'status': 'error',
                    'message': 'ماینر فعالی ندارید'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            required_electricity = int(total_consumption * hours_passed)
            
            if profile.electricity <= 0 and required_electricity > 0:
                return Response({
                    'status': 'error',
                    'message': 'برق کافی نیست'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            actual_hours = hours_passed
            if required_electricity > profile.electricity:
                if total_consumption > 0:
                    ratio = profile.electricity / required_electricity
                    actual_hours = hours_passed * ratio
                profile.electricity = 0
            else:
                profile.electricity -= required_electricity
            
            coin_income = int(total_production * actual_hours)
            
            profile.coins += coin_income
            profile.diamonds += diamond_income
            profile.last_mined_at = now
            profile.save()
            
            return Response({
                'status': 'success',
                'total_coins': profile.coins,
                'total_diamonds': profile.diamonds,
                'electricity': profile.electricity,
                'earned': coin_income,
                'diamonds_earned': diamond_income,
                'message': f'{coin_incoin:,} سکه و {diamond_income} الماس دریافت شد'
            })
    
    @action(detail=False, methods=['post'])
    def buy_item(self, request):
        """Buy an item from the shop."""
        item_id = request.data.get('item_id')
        if not item_id:
            return Response({
                'status': 'error',
                'message': 'آیتم نامعتبر است'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            try:
                item = GameItem.objects.select_for_update().get(id=item_id)
            except GameItem.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': 'آیتم یافت نشد'
                }, status=status.HTTP_404_NOT_FOUND)
            
            profile = PlayerProfile.objects.select_for_update().get(user=request.user)
            
            if item.is_hidden_in_shop or item.price_diamonds <= 0:
                return Response({
                    'status': 'error',
                    'message': 'خرید این آیتم مجاز نیست'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if item.stock == 0:
                return Response({
                    'status': 'error',
                    'message': 'موجودی آیتم تمام شده است'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if profile.diamonds < item.price_diamonds:
                return Response({
                    'status': 'error',
                    'message': 'الماس کافی ندارید'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            profile.diamonds -= item.price_diamonds
            
            if item.item_type == 'ENERGY':
                profile.electricity = profile.max_electricity
            else:
                if item.stock > 0:
                    item.stock -= 1
                    item.save()
                
                inv_item, _ = Inventory.objects.select_for_update().get_or_create(
                    player=profile, item=item, defaults={'quantity': 0}
                )
                inv_item.quantity += 1
                inv_item.save()
            
            profile.save()
            
            return Response({
                'status': 'success',
                'message': f'{item.name} با موفقیت خریداری شد',
                'diamonds': profile.diamonds
            })
    
    @action(detail=False, methods=['get'])
    def inventory(self, request):
        """Get player's inventory."""
        inventory = get_optimized_inventory(request.user.playerprofile)
        serializer = InventorySerializer(inventory, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def miners(self, request):
        """Get player's miners with stats."""
        miners, stats = get_optimized_miners(request.user.playerprofile)
        return Response({
            'miners': InventorySerializer(miners, many=True).data,
            'total_rate': stats['total_rate'] or 0,
            'total_consumption': stats['total_consumption'] or 0
        })


class ShopViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for shop operations.
    """
    serializer_class = GameItemSerializer
    permission_classes = [IsAuthenticated]
    queryset = GameItem.objects.filter(price_diamonds__gt=0, is_hidden_in_shop=False)
    
    def get_queryset(self):
        queryset = super().get_queryset().exclude(item_type='ENERGY')
        
        category = self.request.query_params.get('cat')
        if category and category != 'ALL':
            queryset = queryset.filter(item_type=category)
        
        search = self.request.query_params.get('q')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(item_code__icontains=search)
            )
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get available categories."""
        categories = GameItem.ITEM_TYPES
        return Response(categories)


class MarketplaceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for marketplace operations.
    """
    serializer_class = MarketListingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = MarketListing.objects.select_related(
            'item', 'seller', 'seller__user'
        ).exclude(seller=self.request.user.playerprofile).order_by('-created_at')
        
        return queryset[:100]
    
    @action(detail=False, methods=['post'])
    def list_item(self, request):
        """List an item on the marketplace."""
        item_id = request.data.get('item_id')
        price = request.data.get('price')
        
        try:
            price = int(price)
        except (TypeError, ValueError):
            return Response({
                'status': 'error',
                'message': 'قیمت نامعتبر است'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if price < 1:
            return Response({
                'status': 'error',
                'message': 'قیمت باید بزرگتر از صفر باشد'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            profile = PlayerProfile.objects.select_for_update().get(user=request.user)
            
            try:
                inv_item = Inventory.objects.select_for_update().get(
                    player=profile, item_id=item_id, quantity__gt=0
                )
            except Inventory.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': 'آیتم در موجودی شما نیست'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            inv_item.quantity -= 1
            inv_item.save()
            
            listing = MarketListing.objects.create(
                seller=profile,
                item=inv_item.item,
                price=price
            )
            
            return Response({
                'status': 'success',
                'message': 'آگهی با موفقیت ثبت شد',
                'listing': MarketListingSerializer(listing).data
            })
    
    @action(detail=False, methods=['post'])
    def buy(self, request):
        """Buy an item from the marketplace."""
        listing_id = request.data.get('listing_id')
        
        with transaction.atomic():
            try:
                listing = MarketListing.objects.select_for_update().get(id=listing_id)
            except MarketListing.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': 'آگهی پیدا نشد'
                }, status=status.HTTP_404_NOT_FOUND)
            
            buyer = PlayerProfile.objects.select_for_update().get(user=request.user)
            
            if listing.seller == buyer:
                return Response({
                    'status': 'error',
                    'message': 'نمی‌توانید آگهی خودتان را بخرید'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if buyer.diamonds < listing.price:
                return Response({
                    'status': 'error',
                    'message': 'الماس کافی ندارید'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            seller = PlayerProfile.objects.select_for_update().get(pk=listing.seller_id)
            
            tax = int(listing.price * 0.1)
            seller_profit = listing.price - tax
            
            buyer.diamonds -= listing.price
            seller.diamonds += seller_profit
            
            buyer.save()
            seller.save()
            
            buyer_inv, _ = Inventory.objects.select_for_update().get_or_create(
                player=buyer, item=listing.item, defaults={'quantity': 0}
            )
            buyer_inv.quantity += 1
            buyer_inv.save()
            
            listing.delete()
            
            return Response({
                'status': 'success',
                'message': f'{listing.item.name} با موفقیت خریداری شد'
            })


class QuestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for quest operations.
    """
    serializer_class = UserQuestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserQuest.objects.filter(user=self.request.user).order_by('code')
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active (incomplete) quests."""
        quests = self.get_queryset().filter(completed=False)
        serializer = self.get_serializer(quests, many=True)
        return Response(serializer.data)


class AchievementViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for achievement operations.
    """
    serializer_class = UserAchievementSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserAchievement.objects.filter(
            player=self.request.user.playerprofile
        ).select_related('achievement').order_by('-achieved_at')
    
    @action(detail=False, methods=['get'])
    def all(self, request):
        """Get all achievements with unlock status."""
        user_achievements = set(
            UserAchievement.objects.filter(
                player=request.user.playerprofile
            ).values_list('achievement_id', flat=True)
        )
        
        achievements = Achievement.objects.all()
        result = []
        for ach in achievements:
            result.append({
                'id': ach.id,
                'code': ach.code,
                'title': ach.title,
                'description': ach.description,
                'icon': ach.icon,
                'unlocked': ach.id in user_achievements,
                'target_coins': ach.target_coins,
                'target_diamonds': ach.target_diamonds,
                'target_miners': ach.target_miners,
            })
        
        return Response(result)


class PrestigeViewSet(viewsets.ViewSet):
    """
    API endpoint for prestige operations.
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get current prestige status."""
        profile = request.user.playerprofile
        info = PrestigeSystem.get_prestige_info(profile)
        return Response(info)
    
    @action(detail=False, methods=['post'])
    def do(self, request):
        """Execute prestige operation."""
        profile = request.user.playerprofile
        result = PrestigeSystem.do_prestige(profile)
        
        if result.get('success'):
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class LeaderboardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for leaderboard.
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def top(self, request):
        """Get top players."""
        limit = int(request.query_params.get('limit', 100))
        players = PlayerProfile.objects.select_related('user').order_by('-diamonds')[:limit]
        
        result = []
        for i, player in enumerate(players, 1):
            result.append({
                'rank': i,
                'id': player.id,
                'username': player.user.username,
                'diamonds': player.diamonds,
                'coins': player.coins,
                'mining_power': calculate_mining_power(player),
            })
        
        return Response(result)
