from model import Search, Parameters
import lbc
import database
# analyzer.generate_summary is no longer called here.

def handle(ad: lbc.Ad, search_name: str):
    """
    Handles a new ad found by the searcher.
    It now ONLY saves the ad to the database with a NULL summary.
    The summary generation is now a separate, manual step.
    """
    # --- 1. Print base info for immediate notification ---
    print(f"============== [{search_name}] Nouvelle annonce trouvée !==============")
    print(f"Titre : {ad.subject}")
    print(f"Prix : {ad.price} €")
    print(f"Localisation : {ad.location.city_label}")
    print(f"URL : {ad.url}")
    print("-" * 60)

    # --- 2. Save to database (without summary) ---
    ad_data = {
        'id': ad.id,
        'search_name': search_name,
        'title': ad.subject,
        'price': ad.price,
        'location': ad.location.city_label,
        'date': str(ad.index_date),
        'url': ad.url,
        'description': ' '.join(ad.body.splitlines()),
        'ai_summary': None # Save with a null summary
    }
    
    # The add_ad function will need to be updated to handle this
    if database.add_ad(ad_data):
        print(f"Annonce sauvegardée. Générez le résumé plus tard via le menu principal.")
    else:
        # This case is less likely to be seen by the user now,
        # as the ID check prevents the handler from being called for old ads.
        pass # No need to print anything for duplicates
    print("=" * 60)

# Default search configuration (can be used for testing)
location = lbc.City( 
    lat=48.85994982004764,
    lng=2.33801967847424,
    radius=10_000, # 10 km
    city="Paris"
)

CONFIG = [
    Search(
        name="Test Paris",
        parameters=Parameters(
            text="appartement",
            locations=[location],
            category=lbc.Category.IMMOBILIER,
            price=[100_000, 300_000]
        ),
        delay=60 * 10, # Check every 10 minutes 
        handler=handle
    ),
]