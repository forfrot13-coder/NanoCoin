# game/urls.py
from django.urls import path
from . import views  # اینجا درسته چون views.py کنار همین فایل است

urlpatterns = [
    path('', views.index, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    
    path('shop/', views.shop_page, name='shop'),
    path('miners/', views.miner_room, name='miner_room'),
    path('inventory/', views.inventory_page, name='inventory'),
    path('market/', views.market_page, name='market'),
    path('casino/', views.casino_page, name='casino'),
    path('leaderboard/', views.leaderboard_page, name='leaderboard'),
    path('profile/', views.profile_page, name='profile'),
    path('achievements/', views.achievements_page, name='achievements'),

    # API ها
    path('api/click/', views.click_coin, name='click_coin'),
    path('api/buy/', views.buy_item, name='buy_item'),
    path('api/mine/', views.claim_mining, name='claim_mining'),
    path('api/daily/', views.claim_daily_reward, name='claim_daily'),
    
    path('api/equip/', views.equip_skin, name='equip_skin'),
    path('api/equip-avatar/', views.equip_avatar, name='equip_avatar'),
    path('api/equip-slot/', views.equip_slot, name='equip_slot'),
    path('api/sell-shop/', views.sell_to_shop, name='sell_shop'),
    path('api/miner/toggle/', views.toggle_miner, name='miner_toggle'),
    path('api/boost/activate/', views.activate_boost, name='activate_boost'),
    path('api/energy/refill/', views.energy_refill_click, name='energy_refill_click'),
    
    path('api/market/sell/', views.create_listing, name='market_sell'),
    path('api/market/buy/', views.buy_listing, name='market_buy'),
    path('api/auction/create/', views.create_auction, name='auction_create'),
    path('api/auction/bid/', views.bid_auction, name='auction_bid'),

    path('api/casino/blackjack/', views.play_blackjack, name='casino_blackjack'),
    path('api/casino/crash/', views.play_crash, name='casino_crash'),
    path('api/casino/slots/', views.play_slots, name='casino_slots'),
    
    path('api/redeem/', views.redeem_code, name='redeem_code'),
]
