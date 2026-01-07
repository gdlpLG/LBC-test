from model import Search, Parameters
import lbc
import database

def handle(ad: lbc.Ad, search_name: str):
    """
    Handles a new ad found by the searcher.
    1. Prints the ad to the console.
    2. Saves the ad to the SQLite database.
    """
    # --- 1. Print to console ---
    print(f"============== [{search_name}] Nouvelle annonce !==============")
    print(f"Titre : {ad.subject}")
    print(f"Prix : {ad.price} €")
    print(f"Localisation : {ad.location.city_label}")
    print(f"Date : {ad.index_date}")
    print(f"URL : {ad.url}")
    print(f"Description : \n{ad.body[:200]}...")
    print("-" * 60)

    # --- 2. Save to database ---
    ad_data = {
        'id': ad.id,
        'search_name': search_name,
        'title': ad.subject,
        'price': ad.price,
        'location': ad.location.city_label,
        'date': str(ad.index_date),
        'url': ad.url,
        'description': ' '.join(ad.body.splitlines())
    }
    
    if database.add_ad(ad_data):
        print(f"Annonce sauvegardée dans la base de données.")
    else:
        print(f"Annonce déjà présente dans la base de données.")
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