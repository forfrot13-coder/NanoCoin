# game/api_urls.py
"""
API URL configuration for the game.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    PlayerProfileViewSet, ShopViewSet, MarketplaceViewSet,
    QuestViewSet, AchievementViewSet, PrestigeViewSet, LeaderboardViewSet
)

router = DefaultRouter()
router.register(r'player/profile', PlayerProfileViewSet, basename='player-profile')
router.register(r'shop', ShopViewSet, basename='shop')
router.register(r'marketplace', MarketplaceViewSet, basename='marketplace')
router.register(r'quests', QuestViewSet, basename='quests')
router.register(r'achievements', AchievementViewSet, basename='achievements')
router.register(r'prestige', PrestigeViewSet, basename='prestige')
router.register(r'leaderboard', LeaderboardViewSet, basename='leaderboard')

urlpatterns = [
    path('', include(router.urls)),
]
