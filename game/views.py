from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from django.db.models import Q

from .models import (
    PlayerProfile,
    GameItem,
    Inventory,
    PromoCode,
    UsedPromo,
    MarketListing,
    Achievement,
    UserAchievement,
    AuctionListing,
    UserQuest,
)

import random


DEFAULT_ACHIEVEMENTS = [
    {
        'code': 'coins_1k',
        'title': 'تازه پولدار',
        'description': 'رسیدن به ۱,۰۰۰ کوین',
        'icon': 'fas fa-coins',
        'target_coins': 1000,
        'target_diamonds': 0,
        'target_miners': 0,
        'reward_coins': 0,
        'reward_diamonds': 2,
    },
    {
        'code': 'coins_100k',
        'title': 'میلیونر کوچولو',
        'description': 'رسیدن به ۱۰۰,۰۰۰ کوین',
        'icon': 'fas fa-gem',
        'target_coins': 100000,
        'target_diamonds': 0,
        'target_miners': 0,
        'reward_coins': 0,
        'reward_diamonds': 10,
    },
    {
        'code': 'diamond_10',
        'title': 'کالکتر الماس',
        'description': 'جمع کردن ۱۰ الماس',
        'icon': 'fas fa-diamond',
        'target_coins': 0,
        'target_diamonds': 10,
        'target_miners': 0,
        'reward_coins': 2000,
        'reward_diamonds': 0,
    },
    {
        'code': 'miner_owner',
        'title': 'اولین ماینر',
        'description': 'داشتن حداقل یک ماینر',
        'icon': 'fas fa-hammer',
        'target_coins': 0,
        'target_diamonds': 0,
        'target_miners': 1,
        'reward_coins': 500,
        'reward_diamonds': 1,
    },
]

DEFAULT_QUESTS = [
    {
        'code': 'click_500',
        'title': '۵۰۰ کلیک',
        'quest_type': 'CLICK',
        'goal': 500,
        'reward_coins': 1000,
        'reward_diamonds': 2,
        'reward_xp': 50,
    },
    {
        'code': 'click_2k',
        'title': '۲۰۰۰ کلیک',
        'quest_type': 'CLICK',
        'goal': 2000,
        'reward_coins': 4000,
        'reward_diamonds': 5,
        'reward_xp': 150,
    },
    {
        'code': 'mine_5',
        'title': '۵ بار ماین',
        'quest_type': 'MINE',
        'goal': 5,
        'reward_coins': 5000,
        'reward_diamonds': 3,
        'reward_xp': 100,
    },
]


def ensure_default_achievements():
    for data in DEFAULT_ACHIEVEMENTS:
        Achievement.objects.get_or_create(
            code=data['code'],
            defaults={
                'title': data['title'],
                'description': data['description'],
                'icon': data['icon'],
                'target_coins': data['target_coins'],
                'target_diamonds': data['target_diamonds'],
                'target_miners': data['target_miners'],
                'reward_coins': data['reward_coins'],
                'reward_diamonds': data['reward_diamonds'],
            },
        )


def check_achievements(profile: PlayerProfile):
    ensure_default_achievements()

    miners_count = Inventory.objects.filter(player=profile, item__item_type='MINER', quantity__gt=0).count()
    achievements = Achievement.objects.all()

    unlocked_codes = set(
        UserAchievement.objects.filter(player=profile).values_list('achievement__code', flat=True)
    )

    newly_unlocked = []
    for ach in achievements:
        if ach.code in unlocked_codes:
            continue
        if ach.target_coins and profile.coins < ach.target_coins:
            continue
        if ach.target_diamonds and profile.diamonds < ach.target_diamonds:
            continue
        if ach.target_miners and miners_count < ach.target_miners:
            continue
        ua = UserAchievement.objects.create(player=profile, achievement=ach)
        if ach.reward_coins:
            profile.coins += ach.reward_coins
        if ach.reward_diamonds:
            profile.diamonds += ach.reward_diamonds
        newly_unlocked.append(ua)

    if newly_unlocked:
        profile.save()
    return newly_unlocked


def ensure_daily_quests(user):
    today = timezone.now().date()
    for q in DEFAULT_QUESTS:
        uq, _ = UserQuest.objects.get_or_create(
            user=user,
            code=q['code'],
            defaults={
                'title': q['title'],
                'quest_type': q['quest_type'],
                'goal': q['goal'],
                'reward_coins': q['reward_coins'],
                'reward_diamonds': q['reward_diamonds'],
                'reward_xp': q['reward_xp'],
                'reset_at': today,
            }
        )
        if uq.reset_at != today:
            uq.progress = 0
            uq.completed = False
            uq.reset_at = today
            uq.save()


def update_quest_progress(user, quest_type, amount=1):
    today = timezone.now().date()
    quests = UserQuest.objects.filter(user=user, quest_type=quest_type)
    for uq in quests:
        if uq.reset_at != today:
            uq.progress = 0
            uq.completed = False
            uq.reset_at = today
        if uq.completed:
            uq.save()
            continue
        uq.progress += amount
        if uq.progress >= uq.goal:
            uq.completed = True
            profile = user.playerprofile
            profile.coins += uq.reward_coins
            profile.diamonds += uq.reward_diamonds
            profile.click_xp += uq.reward_xp
            profile.save()
        uq.save()


# صفحات
@login_required(login_url='/login/')
def index(request):
    profile, _ = PlayerProfile.objects.get_or_create(user=request.user)
    energy_percent = (profile.energy / 1000) * 100

    ensure_daily_quests(request.user)
    quests = UserQuest.objects.filter(user=request.user).order_by('code')
    now = timezone.now()
    active_boost = None
    if profile.active_boost_until and profile.active_boost_until > now and profile.boost_multiplier > 1:
        active_boost = {
            'multiplier': profile.boost_multiplier,
            'seconds_left': int((profile.active_boost_until - now).total_seconds())
        }

    context = {
        'profile': profile,
        'energy_percent': energy_percent,
        'quests': quests,
        'active_boost': active_boost
    }
    return render(request, 'index.html', context)


def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


# صفحات بازی
@login_required(login_url='/login/')
def shop_page(request):
    items = GameItem.objects.filter(price_diamonds__gt=0, is_hidden_in_shop=False).exclude(item_type='ENERGY')

    category = request.GET.get('cat')
    if category and category != 'ALL':
        items = items.filter(item_type=category)

    search_query = request.GET.get('q')
    if search_query:
        items = items.filter(
            Q(name__icontains=search_query) |
            Q(item_code__icontains=search_query)
        )

    return render(request, 'shop.html', {
        'items': items,
        'current_cat': category
    })


@login_required(login_url='/login/')
def miner_room(request):
    profile = request.user.playerprofile
    miners = Inventory.objects.filter(player=profile, item__item_type='MINER', quantity__gt=0)
    active_miners = miners.filter(is_active=True)
    total_rate = sum(m.item.mining_rate * m.quantity for m in active_miners)
    total_consumption = sum(m.item.electricity_consumption * m.quantity for m in active_miners)

    energy_packs = GameItem.objects.filter(item_type='ENERGY')

    return render(request, 'miner_room.html', {
        'miners': miners,
        'profile': profile,
        'total_rate': total_rate,
        'total_consumption': total_consumption,
        'energy_packs': energy_packs
    })


@login_required(login_url='/login/')
def market_page(request):
    listings = MarketListing.objects.exclude(seller=request.user.playerprofile).order_by('-created_at')
    my_inventory = Inventory.objects.filter(player=request.user.playerprofile, quantity__gt=0)
    auctions = AuctionListing.objects.filter(is_active=True, ends_at__gt=timezone.now()).select_related('item', 'seller', 'current_bidder')

    return render(request, 'market.html', {
        'listings': listings,
        'my_inventory': my_inventory,
        'auctions': auctions,
    })


@login_required(login_url='/login/')
def inventory_page(request):
    profile = request.user.playerprofile
    inventory_items = Inventory.objects.filter(player=profile, quantity__gt=0).exclude(item__item_type='ENERGY')
    return render(request, 'inventory.html', {
        'inventory_items': inventory_items,
        'profile': profile
    })


@login_required(login_url='/login/')
def leaderboard_page(request):
    top_players = PlayerProfile.objects.order_by('-diamonds')[:10]
    return render(request, 'leaderboard.html', {'top_players': top_players})


@login_required(login_url='/login/')
def casino_page(request):
    profile = request.user.playerprofile
    return render(request, 'casino.html', {'profile': profile})


@login_required(login_url='/login/')
def profile_page(request):
    profile = request.user.playerprofile
    my_avatars = Inventory.objects.filter(player=profile, item__item_type='AVATAR')
    user_achievements = UserAchievement.objects.filter(player=profile).select_related('achievement').order_by('-achieved_at')
    all_achievements = Achievement.objects.all()
    return render(request, 'profile.html', {
        'profile': profile,
        'my_avatars': my_avatars,
        'user_achievements': user_achievements,
        'all_achievements': all_achievements,
    })


@login_required(login_url='/login/')
def achievements_page(request):
    profile = request.user.playerprofile
    user_achievements = UserAchievement.objects.filter(player=profile).select_related('achievement')
    unlocked = {ua.achievement_id for ua in user_achievements}
    ensure_default_achievements()
    achievements = Achievement.objects.all()
    return render(request, 'achievements.html', {
        'achievements': achievements,
        'unlocked': unlocked,
    })


# API ها
def _require_auth_json(request):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'برای انجام این درخواست باید لاگین کنید'}, status=401)
    return None


def _deduct_diamonds(profile: PlayerProfile, amount: int):
    if amount < 1:
        return False, JsonResponse({'status': 'error', 'message': 'مبلغ شرط نامعتبر است'}, status=400)
    if profile.diamonds < amount:
        return False, JsonResponse({'status': 'error', 'message': 'الماس کافی ندارید'}, status=400)
    profile.diamonds -= amount
    return True, None


def click_coin(request):
    auth_error = _require_auth_json(request)
    if auth_error:
        return auth_error
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method allowed'}, status=405)

    with transaction.atomic():
        profile = PlayerProfile.objects.select_for_update().get(user=request.user)

        if profile.energy < 1:
            cost = 2
            refill_amount = 50
            return JsonResponse({
                'status': 'error',
                'message': 'انرژی کافی نیست',
                'can_refill': True,
                'refill_cost': cost,
                'refill_amount': refill_amount
            }, status=400)

        profile.energy -= 1

        extra_coins = 0
        luck_multiplier = 1.0

        active_slots = [profile.slot_1, profile.slot_2, profile.slot_3]
        for item in active_slots:
            if item:
                extra_coins += item.buff_click_coins
                if item.buff_luck > 0:
                    luck_multiplier += (item.buff_luck / 100)

        base_coin = 1 + (profile.click_level - 1)  # هر لول کلیک +1 کوین پایه
        boost_active = profile.active_boost_until and profile.active_boost_until > timezone.now() and profile.boost_multiplier > 1
        current_multiplier = profile.boost_multiplier if boost_active else 1.0
        if not boost_active and profile.boost_multiplier != 1.0:
            profile.boost_multiplier = 1.0
            profile.active_boost_until = None

        gained = int((base_coin + extra_coins) * current_multiplier)
        gained = max(gained, 1)
        profile.coins += gained
        
        diamond_found = False
        chance_threshold = 1 * luck_multiplier 
        
        if random.uniform(0, 1000) <= chance_threshold:
            profile.diamonds += 1
            diamond_found = True

        # XP برای لول کلیک
        profile.click_xp += gained
        leveled_up = False
        while profile.click_xp >= profile.click_xp_to_next:
            profile.click_xp -= profile.click_xp_to_next
            profile.click_level += 1
            profile.click_xp_to_next = int(profile.click_xp_to_next * 1.35)
            leveled_up = True

        loot_found = None
        droppable_items = GameItem.objects.filter(can_drop=True)
        for item in droppable_items:
            final_drop_chance = item.drop_chance * luck_multiplier
            if random.uniform(0, 100) <= final_drop_chance:
                inv_item, _ = Inventory.objects.get_or_create(player=profile, item=item)
                inv_item.quantity += 1
                inv_item.save()
                loot_found = item.name
                break

        profile.save()
        check_achievements(profile)

        return JsonResponse({
            'status': 'success',
            'new_coins': profile.coins,
            'new_diamonds': profile.diamonds,
            'new_energy': profile.energy,
            'loot': loot_found,
            'diamond_found': diamond_found,
            'click_level': profile.click_level,
            'click_xp': profile.click_xp,
            'click_xp_to_next': profile.click_xp_to_next,
            'leveled_up': leveled_up,
            'boost_multiplier': current_multiplier,
            'boost_seconds': int((profile.active_boost_until - timezone.now()).total_seconds()) if boost_active else 0
        })


def buy_item(request):
    auth_error = _require_auth_json(request)
    if auth_error:
        return auth_error
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid Request'}, status=405)

    item_id = request.POST.get('item_id')
    if not item_id:
        return JsonResponse({'status': 'error', 'message': 'آیتم نامعتبر است'}, status=400)

    with transaction.atomic():
        try:
            item = GameItem.objects.select_for_update().get(id=item_id)
        except GameItem.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'آیتم یافت نشد'}, status=404)

        profile = PlayerProfile.objects.select_for_update().get(user=request.user)

        if item.is_hidden_in_shop or item.price_diamonds <= 0:
            return JsonResponse({'status': 'error', 'message': 'خرید این آیتم مجاز نیست'}, status=400)

        if item.stock == 0:
            return JsonResponse({'status': 'error', 'message': 'موجودی آیتم تمام شده است'}, status=400)

        if profile.diamonds < item.price_diamonds:
            return JsonResponse({'status': 'error', 'message': 'الماس کافی ندارید'}, status=400)

        profile.diamonds -= item.price_diamonds

        if item.item_type == 'ENERGY':
            profile.electricity = profile.max_electricity
        else:
            if item.stock > 0:
                item.stock -= 1
            inv_item, _ = Inventory.objects.select_for_update().get_or_create(
                player=profile, item=item, defaults={'quantity': 0}
            )
            inv_item.quantity += 1
            inv_item.save()
            item.save()

        profile.save()
        check_achievements(profile)
        return JsonResponse({'status': 'success', 'message': f'{item.name} با موفقیت خریداری شد'})


def claim_mining(request):
    auth_error = _require_auth_json(request)
    if auth_error:
        return auth_error
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method allowed'}, status=405)

    with transaction.atomic():
        profile = PlayerProfile.objects.select_for_update().get(user=request.user)
        now = timezone.now()
        last_time = profile.last_mined_at or now
        diff = now - last_time
        hours_passed = diff.total_seconds() / 3600

        if hours_passed < 0.016:
            return JsonResponse({'status': 'error', 'message': '???? ??? ???!'}, status=400)

        user_items = Inventory.objects.select_for_update().filter(player=profile, item__item_type='MINER', is_active=True)

        mining_multiplier = 1.0
        active_slots = [profile.slot_1, profile.slot_2, profile.slot_3]
        for item in active_slots:
            if item:
                mining_multiplier += (item.buff_mining_speed / 100)

        total_production = 0
        total_consumption = 0
        diamond_income = 0

        for inv in user_items:
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
            profile.last_mined_at = now
            profile.save()
            return JsonResponse({'status': 'error', 'message': '?????? ???? ????? ??????'}, status=400)

        required_electricity = int(total_consumption * hours_passed)

        if profile.electricity <= 0 and required_electricity > 0:
            return JsonResponse({'status': 'error', 'message': '??? ??????!'}, status=400)

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
        update_quest_progress(request.user, 'MINE', 1)
        check_achievements(profile)

    return JsonResponse({
        'status': 'success',
        'message': f'{coin_income} ???? ? {diamond_income} ????? ?? ??? ??????',
        'new_coins': profile.coins,
        'new_diamonds': profile.diamonds,
        'new_electricity': profile.electricity
    })

def create_listing(request):
    auth_error = _require_auth_json(request)
    if auth_error:
        return auth_error
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid Request'}, status=405)

    item_id = request.POST.get('item_id')
    price_raw = request.POST.get('price')

    try:
        price = int(price_raw)
    except (TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'قیمت نامعتبر است'}, status=400)

    if price < 1:
        return JsonResponse({'status': 'error', 'message': 'قیمت باید بزرگتر از صفر باشد'}, status=400)

    with transaction.atomic():
        profile = PlayerProfile.objects.select_for_update().get(user=request.user)
        try:
            inv_item = Inventory.objects.select_for_update().get(player=profile, item_id=item_id, quantity__gt=0)
        except Inventory.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'آیتم در موجودی شما نیست'}, status=400)

        inv_item.quantity -= 1
        inv_item.save()
        MarketListing.objects.create(seller=profile, item=inv_item.item, price=price)
        return JsonResponse({'status': 'success', 'message': 'آگهی با موفقیت ثبت شد'})


def buy_listing(request):
    auth_error = _require_auth_json(request)
    if auth_error:
        return auth_error
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid Request'}, status=405)

    listing_id = request.POST.get('listing_id')

    with transaction.atomic():
        try:
            listing = MarketListing.objects.select_for_update().get(id=listing_id)
        except MarketListing.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'آگهی پیدا نشد'}, status=404)

        buyer = PlayerProfile.objects.select_for_update().get(user=request.user)

        if listing.seller == buyer:
            return JsonResponse({'status': 'error', 'message': 'نمی‌توانید آگهی خودتان را بخرید'}, status=400)

        if buyer.diamonds < listing.price:
            return JsonResponse({'status': 'error', 'message': 'الماس کافی ندارید'}, status=400)

        seller = PlayerProfile.objects.select_for_update().get(pk=listing.seller_id)

        tax = int(listing.price * 0.1)
        seller_profit = listing.price - tax

        buyer.diamonds -= listing.price
        seller.diamonds += seller_profit

        buyer.save()
        seller.save()

        buyer_inv, _ = Inventory.objects.select_for_update().get_or_create(player=buyer, item=listing.item, defaults={'quantity': 0})
        buyer_inv.quantity += 1
        buyer_inv.save()

        listing.delete()
        check_achievements(buyer)
        check_achievements(seller)
        return JsonResponse({'status': 'success', 'message': f'{listing.item.name} با موفقیت خریداری شد'})


def _finalize_auction(auction: AuctionListing):
    """Finalize an expired auction; returns (finalized, response)."""
    if not auction.is_active:
        return True, None

    now = timezone.now()
    if auction.ends_at > now:
        return False, None

    seller = PlayerProfile.objects.select_for_update().get(pk=auction.seller_id)

    if auction.current_bidder:
        buyer = PlayerProfile.objects.select_for_update().get(pk=auction.current_bidder_id)
        tax = int(auction.current_price * 0.1)
        seller_profit = auction.current_price - tax
        seller.diamonds += seller_profit
        buyer_inv, _ = Inventory.objects.select_for_update().get_or_create(
            player=buyer, item=auction.item, defaults={'quantity': 0}
        )
        buyer_inv.quantity += 1
        buyer_inv.save()
        seller.save()
        auction.is_active = False
        auction.save()
        check_achievements(buyer)
        check_achievements(seller)
        return True, JsonResponse({'status': 'success', 'message': 'حراج به پایان رسید و برنده مشخص شد'})
    else:
        # no bids -> برگرداندن آیتم به فروشنده
        seller_inv, _ = Inventory.objects.select_for_update().get_or_create(
            player=seller, item=auction.item, defaults={'quantity': 0}
        )
        seller_inv.quantity += 1
        seller_inv.save()
        auction.is_active = False
        auction.save()
        return True, JsonResponse({'status': 'error', 'message': 'حراج بدون پیشنهاد پایان یافت و آیتم برگشت داده شد'})


def create_auction(request):
    auth_error = _require_auth_json(request)
    if auth_error:
        return auth_error
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid Request'}, status=405)

    item_id = request.POST.get('item_id')
    start_raw = request.POST.get('start_price')
    buy_now_raw = request.POST.get('buy_now_price')
    duration_hours_raw = request.POST.get('duration_hours', '24')

    try:
        start_price = int(start_raw)
        if start_price < 1:
            raise ValueError
    except (TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'قیمت شروع نامعتبر است'}, status=400)

    buy_now_price = None
    if buy_now_raw:
        try:
            buy_now_price = int(buy_now_raw)
            if buy_now_price < start_price:
                return JsonResponse({'status': 'error', 'message': 'خرید فوری باید بزرگتر از قیمت شروع باشد'}, status=400)
        except (TypeError, ValueError):
            return JsonResponse({'status': 'error', 'message': 'خرید فوری نامعتبر است'}, status=400)

    try:
        duration_hours = int(duration_hours_raw)
        if duration_hours < 1 or duration_hours > 168:
            raise ValueError
    except (TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'مدت زمان نامعتبر است'}, status=400)

    with transaction.atomic():
        profile = PlayerProfile.objects.select_for_update().get(user=request.user)
        try:
            inv_item = Inventory.objects.select_for_update().get(player=profile, item_id=item_id, quantity__gt=0)
        except Inventory.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'آیتم در موجودی نیست'}, status=404)

        inv_item.quantity -= 1
        inv_item.save()

        AuctionListing.objects.create(
            seller=profile,
            item=inv_item.item,
            starting_price=start_price,
            current_price=start_price,
            current_bidder=None,
            buy_now_price=buy_now_price,
            ends_at=timezone.now() + timedelta(hours=duration_hours),
            is_active=True,
        )

        return JsonResponse({'status': 'success', 'message': 'حراج ایجاد شد'})


def bid_auction(request):
    auth_error = _require_auth_json(request)
    if auth_error:
        return auth_error
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid Request'}, status=405)

    auction_id = request.POST.get('auction_id')
    bid_raw = request.POST.get('bid_amount')
    buy_now_flag = request.POST.get('buy_now') == '1'

    with transaction.atomic():
        try:
            auction = AuctionListing.objects.select_for_update().get(id=auction_id)
        except AuctionListing.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'حراج پیدا نشد'}, status=404)

        finalized, resp = _finalize_auction(auction)
        if finalized:
            return resp or JsonResponse({'status': 'error', 'message': 'حراج فعال نیست'}, status=400)

        buyer = PlayerProfile.objects.select_for_update().get(user=request.user)
        if auction.seller_id == buyer.id:
            return JsonResponse({'status': 'error', 'message': 'نمی‌توانید حراج خود را بخرید'}, status=400)

        if buy_now_flag:
            if not auction.buy_now_price:
                return JsonResponse({'status': 'error', 'message': 'خرید فوری فعال نیست'}, status=400)
            price = auction.buy_now_price
            if buyer.diamonds < price:
                return JsonResponse({'status': 'error', 'message': 'الماس کافی ندارید'}, status=400)

            # refund previous bidder if exists
            if auction.current_bidder_id:
                prev_bidder = PlayerProfile.objects.select_for_update().get(pk=auction.current_bidder_id)
                prev_bidder.diamonds += auction.current_price
                prev_bidder.save()

            tax = int(price * 0.1)
            seller_profit = price - tax

            seller = PlayerProfile.objects.select_for_update().get(pk=auction.seller_id)
            buyer.diamonds -= price
            seller.diamonds += seller_profit

            buyer_inv, _ = Inventory.objects.select_for_update().get_or_create(
                player=buyer, item=auction.item, defaults={'quantity': 0}
            )
            buyer_inv.quantity += 1
            buyer_inv.save()

            buyer.save()
            seller.save()

            auction.is_active = False
            auction.save()
            check_achievements(buyer)
            check_achievements(seller)
            return JsonResponse({'status': 'success', 'message': 'آیتم با خرید فوری دریافت شد'})

        # normal bid
        try:
            bid_amount = int(bid_raw)
        except (TypeError, ValueError):
            return JsonResponse({'status': 'error', 'message': 'مبلغ پیشنهاد نامعتبر است'}, status=400)

        min_allowed = auction.current_price + 1
        if bid_amount < min_allowed:
            return JsonResponse({'status': 'error', 'message': f'حداقل پیشنهاد {min_allowed} الماس است'}, status=400)

        if buyer.diamonds < bid_amount:
            return JsonResponse({'status': 'error', 'message': 'الماس کافی ندارید'}, status=400)

        # refund previous bidder
        if auction.current_bidder_id:
            prev_bidder = PlayerProfile.objects.select_for_update().get(pk=auction.current_bidder_id)
            prev_bidder.diamonds += auction.current_price
            prev_bidder.save()

        buyer.diamonds -= bid_amount
        buyer.save()

        auction.current_bidder = buyer
        auction.current_price = bid_amount
        auction.save()

        return JsonResponse({'status': 'success', 'message': 'پیشنهاد ثبت شد'})


def play_blackjack(request):
    auth_error = _require_auth_json(request)
    if auth_error:
        return auth_error
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid Request'}, status=405)

    bet_raw = request.POST.get('bet')
    try:
        bet = int(bet_raw)
    except (TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'مبلغ شرط نامعتبر است'}, status=400)

    with transaction.atomic():
        profile = PlayerProfile.objects.select_for_update().get(user=request.user)
        ok, resp = _deduct_diamonds(profile, bet)
        if not ok:
            return resp

        # ساده‌شده: کارت‌های جمع رندوم بین 15 تا 23
        player_score = random.randint(16, 22)
        dealer_score = random.randint(15, 24)
        result = 'lose'
        payout = 0

        if player_score > 21:
            result = 'bust'
        elif dealer_score > 21 or player_score > dealer_score:
            result = 'win'
            payout = bet * 2
        elif player_score == dealer_score:
            result = 'push'
            payout = bet  # برگشت شرط

        if payout:
            profile.diamonds += payout
        profile.save()
        check_achievements(profile)

    return JsonResponse({
        'status': 'success',
        'result': result,
        'player': player_score,
        'dealer': dealer_score,
        'net_change': payout - bet if payout else -bet,
        'diamonds': profile.diamonds,
    })


def play_crash(request):
    auth_error = _require_auth_json(request)
    if auth_error:
        return auth_error
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid Request'}, status=405)

    bet_raw = request.POST.get('bet')
    target_raw = request.POST.get('target')
    try:
        bet = int(bet_raw)
        target = float(target_raw)
    except (TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'مقدار شرط یا ضریب نامعتبر است'}, status=400)
    if target < 1.1 or target > 10:
        return JsonResponse({'status': 'error', 'message': 'ضریب باید بین 1.1 و 10 باشد'}, status=400)

    with transaction.atomic():
        profile = PlayerProfile.objects.select_for_update().get(user=request.user)
        ok, resp = _deduct_diamonds(profile, bet)
        if not ok:
            return resp

        # توزیع ساده برای ضریب
        roll = random.random()
        if roll < 0.05:
            crash_at = 0.9
        elif roll < 0.35:
            crash_at = round(random.uniform(1.1, 2.0), 2)
        elif roll < 0.8:
            crash_at = round(random.uniform(2.0, 4.0), 2)
        else:
            crash_at = round(random.uniform(4.0, 10.0), 2)

        win = crash_at >= target
        payout = 0
        if win:
            payout = int(bet * target)
            profile.diamonds += payout

        profile.save()
        check_achievements(profile)

    return JsonResponse({
        'status': 'success',
        'crash_at': crash_at,
        'win': win,
        'net_change': payout - bet if win else -bet,
        'diamonds': profile.diamonds,
    })


def play_slots(request):
    auth_error = _require_auth_json(request)
    if auth_error:
        return auth_error
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid Request'}, status=405)

    bet_raw = request.POST.get('bet')
    try:
        bet = int(bet_raw)
    except (TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'مبلغ شرط نامعتبر است'}, status=400)

    reels = ['🍌', '💎', '⭐', '7️⃣', '🍀', '🔥']

    with transaction.atomic():
        profile = PlayerProfile.objects.select_for_update().get(user=request.user)
        ok, resp = _deduct_diamonds(profile, bet)
        if not ok:
            return resp

        spin = [random.choice(reels) for _ in range(3)]
        payout = 0
        if len(set(spin)) == 1:
            # سه تا یکی
            symbol = spin[0]
            multiplier = {'🍌': 5, '⭐': 7, '💎': 12, '7️⃣': 20, '🍀': 10, '🔥': 15}.get(symbol, 5)
            payout = bet * multiplier
        elif len(set(spin)) == 2:
            payout = bet * 2

        if payout:
            profile.diamonds += payout
            profile.coins += payout * 10

        profile.save()
        check_achievements(profile)

    return JsonResponse({
        'status': 'success',
        'spin': spin,
        'payout': payout,
        'net_change': payout - bet if payout else -bet,
        'diamonds': profile.diamonds,
        'coins': profile.coins,
    })


def redeem_code(request):
    auth_error = _require_auth_json(request)
    if auth_error:
        return auth_error
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid Request'}, status=405)

    code_text = request.POST.get('code', '').strip()
    user = request.user

    with transaction.atomic():
        try:
            promo = PromoCode.objects.select_for_update().get(code=code_text)
        except PromoCode.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'کد پیدا نشد'}, status=404)

        profile = PlayerProfile.objects.select_for_update().get(user=user)

        if promo.expiry_date and timezone.now() > promo.expiry_date:
            return JsonResponse({'status': 'error', 'message': 'کد منقضی شده است'}, status=400)
        if promo.current_uses >= promo.max_uses:
            return JsonResponse({'status': 'error', 'message': 'حداکثر استفاده از این کد انجام شده است'}, status=400)
        if UsedPromo.objects.filter(user=user, code=promo).exists():
            return JsonResponse({'status': 'error', 'message': 'این کد قبلا توسط شما استفاده شده است'}, status=400)

        profile.coins += promo.reward_coins
        profile.diamonds += promo.reward_diamonds
        profile.save()
        check_achievements(profile)

        promo.current_uses += 1
        promo.save()
        UsedPromo.objects.create(user=user, code=promo)

        return JsonResponse({'status': 'success', 'message': f'{promo.reward_diamonds} الماس دریافت کردید'})


def equip_skin(request):
    auth_error = _require_auth_json(request)
    if auth_error:
        return auth_error
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid Request'}, status=405)

    item_id = request.POST.get('item_id')
    profile = request.user.playerprofile
    try:
        inventory_item = Inventory.objects.get(player=profile, item_id=item_id)
    except Inventory.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'آیتم در موجودی نیست'}, status=404)

    if inventory_item.item.item_type != 'SKIN':
        return JsonResponse({'status': 'error', 'message': 'این آیتم پوسته نیست'}, status=400)

    profile.equipped_skin = inventory_item.item
    profile.save()
    return JsonResponse({'status': 'success', 'message': 'پوسته equip شد'})


def equip_avatar(request):
    auth_error = _require_auth_json(request)
    if auth_error:
        return auth_error
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid Request'}, status=405)

    item_id = request.POST.get('item_id')
    profile = request.user.playerprofile
    try:
        inv_item = Inventory.objects.get(player=profile, item_id=item_id)
    except Inventory.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'آیتم در موجودی نیست'}, status=404)

    if inv_item.item.item_type != 'AVATAR':
        return JsonResponse({'status': 'error', 'message': 'این آیتم آواتار نیست'}, status=400)

    profile.avatar = inv_item.item
    profile.save()
    return JsonResponse({'status': 'success', 'message': 'آواتار equip شد'})


def equip_slot(request):
    auth_error = _require_auth_json(request)
    if auth_error:
        return auth_error
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid Request'}, status=405)

    item_id = request.POST.get('item_id')
    slot_num = request.POST.get('slot_num')
    profile = request.user.playerprofile

    if slot_num not in ('1', '2', '3'):
        return JsonResponse({'status': 'error', 'message': 'شماره اسلات نامعتبر است'}, status=400)

    with transaction.atomic():
        profile = PlayerProfile.objects.select_for_update().get(pk=profile.pk)

        if not item_id:
            if slot_num == '1':
                profile.slot_1 = None
            elif slot_num == '2':
                profile.slot_2 = None
            else:
                profile.slot_3 = None
            profile.save()
            return JsonResponse({'status': 'success', 'message': 'اسلات خالی شد'})

        try:
            inv_item = Inventory.objects.get(player=profile, item_id=item_id)
        except Inventory.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'آیتم در موجودی نیست'}, status=404)

        if slot_num == '1':
            profile.slot_1 = inv_item.item
        elif slot_num == '2':
            profile.slot_2 = inv_item.item
        else:
            profile.slot_3 = inv_item.item

        profile.save()
        return JsonResponse({'status': 'success', 'message': 'اسلات تنظیم شد'})


def sell_to_shop(request):
    auth_error = _require_auth_json(request)
    if auth_error:
        return auth_error
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid Request'}, status=405)

    item_id = request.POST.get('item_id')
    profile = request.user.playerprofile
    with transaction.atomic():
        try:
            inv_item = Inventory.objects.select_for_update().get(player=profile, item_id=item_id, quantity__gt=0)
        except Inventory.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'آیتم در موجودی نیست'}, status=404)

        item = inv_item.item
        if item.sell_price <= 0:
            return JsonResponse({'status': 'error', 'message': 'این آیتم قابل فروش نیست'}, status=400)

        profile = PlayerProfile.objects.select_for_update().get(pk=profile.pk)
        profile.diamonds += item.sell_price
        inv_item.quantity -= 1
        inv_item.save()
        update_quest_progress(request.user, 'CLICK', 1)
        profile.save()
        check_achievements(profile)
        return JsonResponse({'status': 'success', 'message': f'{item.sell_price} الماس دریافت شد'})

def energy_refill_click(request):
    auth_error = _require_auth_json(request)
    if auth_error:
        return auth_error
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid Request'}, status=405)

    cost = 2
    amount = 50
    with transaction.atomic():
        profile = PlayerProfile.objects.select_for_update().get(user=request.user)
        if profile.diamonds < cost:
            return JsonResponse({'status': 'error', 'message': 'الماس کافی نیست'}, status=400)
        profile.diamonds -= cost
        profile.energy = min(profile.max_energy, profile.energy + amount)
        profile.save()
    return JsonResponse({'status': 'success', 'new_energy': profile.energy, 'diamonds': profile.diamonds})

def toggle_miner(request):
    auth_error = _require_auth_json(request)
    if auth_error:
        return auth_error
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid Request'}, status=405)

    item_id = request.POST.get('item_id')
    active_raw = request.POST.get('active')
    active = active_raw == '1'

    with transaction.atomic():
        try:
            inv = Inventory.objects.select_for_update().get(player=request.user.playerprofile, item_id=item_id, item__item_type='MINER')
        except Inventory.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'ماینر یافت نشد'}, status=404)

        inv.is_active = active
        inv.save()
        return JsonResponse({'status': 'success', 'message': 'حالت ماینر به‌روز شد', 'active': inv.is_active})


def activate_boost(request):
    auth_error = _require_auth_json(request)
    if auth_error:
        return auth_error
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid Request'}, status=405)

    cost = 5
    multiplier = 2.0
    duration_minutes = 15

    with transaction.atomic():
        profile = PlayerProfile.objects.select_for_update().get(user=request.user)
        now = timezone.now()
        if profile.diamonds < cost:
            return JsonResponse({'status': 'error', 'message': 'الماس کافی نیست'}, status=400)
        profile.diamonds -= cost
        base_time = profile.active_boost_until if profile.active_boost_until and profile.active_boost_until > now else now
        profile.active_boost_until = base_time + timedelta(minutes=duration_minutes)
        profile.boost_multiplier = multiplier
        profile.save()
    return JsonResponse({
        'status': 'success',
        'boost_multiplier': multiplier,
        'boost_seconds': int((profile.active_boost_until - timezone.now()).total_seconds()),
        'diamonds': profile.diamonds
    })


def claim_daily_reward(request):
    auth_error = _require_auth_json(request)
    if auth_error:
        return auth_error
    if request.method != 'POST':
        return JsonResponse({'status': 'error'}, status=405)

    profile = request.user.playerprofile
    now = timezone.now()

    rewards = [
        {'coins': 500, 'diamonds': 0},
        {'coins': 1000, 'diamonds': 0},
        {'coins': 1500, 'diamonds': 0},
        {'coins': 2000, 'diamonds': 0},
        {'coins': 2500, 'diamonds': 5},
        {'coins': 5000, 'diamonds': 10},
        {'coins': 10000, 'diamonds': 50},
    ]

    with transaction.atomic():
        profile = PlayerProfile.objects.select_for_update().get(pk=profile.pk)
        if profile.last_daily_claim:
            last_date = profile.last_daily_claim.date()
            today_date = now.date()
            if last_date == today_date:
                return JsonResponse({'status': 'error', 'message': 'امروز پاداش گرفته‌اید'}, status=400)
            if (today_date - last_date).days > 1:
                profile.daily_streak = 0

        if profile.daily_streak < 7:
            profile.daily_streak += 1
        else:
            profile.daily_streak = 1

        reward = rewards[profile.daily_streak - 1]
        profile.coins += reward['coins']
        profile.diamonds += reward['diamonds']
        profile.last_daily_claim = now
        profile.save()
        check_achievements(profile)

    return JsonResponse({
        'status': 'success',
        'message': f'روز {profile.daily_streak} پاداش دریافت شد',
        'streak': profile.daily_streak,
        'new_coins': profile.coins,
        'new_diamonds': profile.diamonds
    })
