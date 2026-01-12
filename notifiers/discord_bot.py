import requests
from typing import Dict, Any

class DiscordNotifier:
    """
    Handles sending rich embed notifications to Discord via Webhooks.
    """
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_ad_notification(self, ad: Dict[str, Any], is_pepite: bool = False, price_drop: bool = False, content: str = None):
        if not self.webhook_url:
            return

        title_prefix = "✨ " if is_pepite else ""
        if price_drop:
            title_prefix = "📉 "
            
        color = 0x10B981 # Green for general/pepite
        if price_drop:
            color = 0x4F46E5 # Indigo for price drop
        elif is_pepite:
            color = 0xF59E0B # Gold for pepite

        # Score visualization
        score = ad.get('ai_score', 0)
        score_stars = "⭐" * int(score) if score else "Non noté"

        embed = {
            "title": f"{title_prefix}{ad['title']}",
            "url": ad['url'],
            "color": color,
            "fields": [
                {"name": "💰 Prix", "value": f"{ad['price']} €", "inline": True},
                {"name": "📍 Lieu", "value": ad.get('location', 'Inconnu'), "inline": True},
                {"name": "⭐ Note IA", "value": f"{score}/10 {score_stars}", "inline": False},
                {"name": "📦 Source", "value": ad.get('source', 'LBC'), "inline": True}
            ],
            "footer": {"text": f"Veille : {ad.get('search_name', 'Manuelle')}"}
        }

        if ad.get('image_url'):
            embed["thumbnail"] = {"url": ad['image_url']}
        
        if ad.get('ai_summary'):
            embed["description"] = f"**Résumé IA :** {ad['ai_summary']}"

        payload = {
            "username": "LBC Finder AI",
            "avatar_url": "https://raw.githubusercontent.com/FortAwesome/Font-Awesome/6.x/svgs/solid/rocket.svg",
            "embeds": [embed]
        }
        
        if content:
            payload["content"] = content

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"[Discord Error] {e}")
            return False

    def test_notification(self):
        payload = {
            "content": "🚀 **Test réussi !** Votre bot LBC Finder est prêt à envoyer des alertes."
        }
        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"[Discord Test Error] {e}")
            return False
