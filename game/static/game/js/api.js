/**
 * Game API Client
 * Unified JavaScript client for all game API endpoints
 */
class GameAPI {
    constructor() {
        this.baseURL = '/api';
        this.csrfToken = this.getCSRFToken();
    }

    getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        // Try to get from meta tag as fallback
        const meta = document.querySelector('[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const response = await fetch(url, {
            method: options.method || 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken,
                ...options.headers,
            },
            body: options.body ? JSON.stringify(options.body) : undefined,
            credentials: 'same-origin',
        });

        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'Request failed');
        }
        
        return data;
    }

    // Player Profile
    async getProfile() {
        return this.request('/player/profile/me/');
    }

    async click() {
        return this.request('/player/profile/click/', { method: 'POST' });
    }

    async collectMine() {
        return this.request('/player/profile/collect-mine/', { method: 'POST' });
    }

    async buyItem(itemId) {
        return this.request('/player/profile/buy_item/', { 
            method: 'POST',
            body: { item_id: itemId }
        });
    }

    async getInventory() {
        return this.request('/player/profile/inventory/');
    }

    async getMiners() {
        return this.request('/player/profile/miners/');
    }

    // Shop
    async getShopItems(category = null) {
        let endpoint = '/shop/';
        if (category && category !== 'ALL') {
            endpoint += `?cat=${category}`;
        }
        return this.request(endpoint);
    }

    async getShopCategories() {
        return this.request('/shop/categories/');
    }

    // Marketplace
    async getMarketListings() {
        return this.request('/marketplace/');
    }

    async listItem(itemId, price) {
        return this.request('/marketplace/list_item/', {
            method: 'POST',
            body: { item_id: itemId, price: price }
        });
    }

    async buyListing(listingId) {
        return this.request('/marketplace/buy/', {
            method: 'POST',
            body: { listing_id: listingId }
        });
    }

    // Quests
    async getQuests() {
        return this.request('/quests/');
    }

    async getActiveQuests() {
        return this.request('/quests/active/');
    }

    // Achievements
    async getAchievements() {
        return this.request('/achievements/all/');
    }

    async getUnlockedAchievements() {
        return this.request('/achievements/');
    }

    // Prestige
    async getPrestigeStatus() {
        return this.request('/prestige/status/');
    }

    async doPrestige() {
        return this.request('/prestige/do/', { method: 'POST' });
    }

    // Leaderboard
    async getLeaderboard(limit = 100) {
        return this.request(`/leaderboard/top/?limit=${limit}`);
    }

    // Casino
    async playBlackjack(bet) {
        return this.request('/casino/blackjack/', {
            method: 'POST',
            body: { bet: bet }
        });
    }

    async playCrash(bet, target) {
        return this.request('/casino/crash/', {
            method: 'POST',
            body: { bet: bet, target: target }
        });
    }

    async playSlots(bet) {
        return this.request('/casino/slots/', {
            method: 'POST',
            body: { bet: bet }
        });
    }

    // Promo Codes
    async redeemCode(code) {
        return this.request('/redeem/', {
            method: 'POST',
            body: { code: code }
        });
    }

    // Energy & Boosts
    async refillEnergy() {
        return this.request('/energy/refill/', { method: 'POST' });
    }

    async activateBoost() {
        return this.request('/boost/activate/', { method: 'POST' });
    }

    // Equipment
    async equipSkin(itemId) {
        return this.request('/equip/', {
            method: 'POST',
            body: { item_id: itemId }
        });
    }

    async equipAvatar(itemId) {
        return this.request('/equip-avatar/', {
            method: 'POST',
            body: { item_id: itemId }
        });
    }

    async equipSlot(itemId, slotNum) {
        return this.request('/equip-slot/', {
            method: 'POST',
            body: { item_id: itemId, slot_num: slotNum }
        });
    }

    async toggleMiner(itemId, active) {
        return this.request('/miner/toggle/', {
            method: 'POST',
            body: { item_id: itemId, active: active ? '1' : '0' }
        });
    }

    async sellToShop(itemId) {
        return this.request('/sell-shop/', {
            method: 'POST',
            body: { item_id: itemId }
        });
    }
}

// Global instance
window.gameAPI = new GameAPI();
