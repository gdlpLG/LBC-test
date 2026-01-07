import random
import lbc
import database
from config import handle
from analyzer import analyze_results, generate_batch_summaries
from nlp import parse_sentence
from model import Search, Parameters
from searcher import Searcher

# Constantes pour le style
VERSION = "5.1"
BORDER = "=" * 60
SUB_BORDER = "-" * 40

def run_viewer():
    print(f"\n{BORDER}")
    print("      📜 CONSULTATION DES ANNONCES SAUVEGARDÉES")
    print(f"{BORDER}")
    all_ads = database.get_all_ads()
    if not all_ads: 
        print(" > Aucune annonce en base de données.")
        return
    
    all_ads.sort(key=lambda x: x.get('date') or '', reverse=True)
    print(f"Total: {len(all_ads)} annonce(s)\n")
    
    for i, ad in enumerate(all_ads):
        summary = ad.get('ai_summary') or "[Analyse IA en attente...]"
        print(f"#{i+1} | {ad.get('title','N/A')} | {ad.get('price','N/A')}€")
        print(f"   📍 {ad.get('location','N/A')} | {ad.get('date','N/A')}")
        print(f"   🤖 Résumé : {summary}")
        print(f"   🔗 URL : {ad.get('url','N/A')}")
        print(f"{SUB_BORDER}")

def run_batch_summary_generation():
    print(f"\n{BORDER}")
    print("      🤖 GÉNÉRATION DE RÉSUMÉS PAR IA (BATCH)")
    print(f"{BORDER}")
    ads_to_summarize = database.get_ads_without_summary()
    if not ads_to_summarize: 
        print(" > Toutes les annonces ont déjà été analysées.")
        return
        
    print(f" > {len(ads_to_summarize)} annonce(s) en attente d'analyse.")
    confirm = input(" Lancer le traitement ? (o/n) > ")
    if confirm.lower() != 'o': return

    summaries = generate_batch_summaries(ads_to_summarize)
    if summaries:
        database.update_summaries_in_batch(summaries)
        print("\n ✅ Analyse terminée et sauvegardée.")
    else:
        print("\n ❌ L'analyse a échoué ou a été annulée.")

def run_quick_search():
    print(f"\n{BORDER}")
    print("      🔍 RECHERCHE RAPIDE INSTANTANÉE")
    print(f"{BORDER}")
    text = input(" Que cherchez-vous ? > ")
    city = input(" Ville (laisser vide pour France entière) > ")
    
    try:
        if city:
            from utils import get_coordinates
            coords = get_coordinates(city)
            if coords:
                lat, lng, zip_code = coords
                loc = [lbc.City(lat=lat, lng=lng, city=city, radius=20000)] # 20km par défaut
            else:
                print(f" ⚠️ Ville '{city}' non trouvée. Recherche France entière.")
                loc = None
        else:
            loc = None
            
        client = lbc.Client()
        response = client.search(text=text, locations=loc, limit=15, sort=lbc.Sort.NEWEST)
        ads = response.ads
        
        if not ads:
            print(" > Aucun résultat trouvé.")
            return

        print(f"\n--- {len(ads)} derniers résultats trouvés ---\n")
        for ad in ads:
            print(f" 🕒 {ad.index_date} | {ad.subject} | {ad.price}€")
            print(f" 🔗 {ad.url}\n")
    except Exception as e:
        print(f" ❌ Erreur : {e}")

def run_nlp_watch():
    print(f"\n{BORDER}")
    print("      📡 CONFIGURATION D'UNE VEILLE INTELLIGENTE")
    print(f"{BORDER}")
    user_sentence = input(" Décrivez votre recherche (ex: 'un macbook air m2 à Lyon moins de 900€')\n > ")
    
    try:
        criteria = parse_sentence(user_sentence)
        print(f"\n--- Interprétation des critères ---")
        print(f"  📦 Quoi  : {criteria['text']}")
        print(f"  📍 Où    : {criteria['location'] or 'France Entière'}")
        print(f"  💰 Prix  : {criteria['price_min'] or 0}€ - {criteria['price_max'] or '∞'}€")
        
        if input("\n Activer cette veille ? (o/n) > ").lower() != 'o':
            print(" -> Annulé.")
            return
        
        # Délai intelligent pour éviter les bans (15-25 min)
        delay_seconds = random.randint(900, 1500)
        
        # Validation de la ville
        city_obj = None
        if criteria['location']:
            from utils import get_coordinates
            coords = get_coordinates(criteria['location'])
            if coords:
                lat, lng, zip_code = coords
                city_obj = lbc.City(
                    lat=lat, 
                    lng=lng, 
                    city=criteria['location'], 
                    radius=criteria['radius'] * 1000 if criteria['radius'] else 10000
                )
            else:
                print(f" ⚠️ Ville '{criteria['location']}' non reconnue. La recherche se fera sur toute la France.")
            
        params = Parameters(
            text=criteria['text'], 
            locations=[city_obj] if city_obj else None, 
            price=(criteria['price_min'], criteria['price_max'])
        )
        
        search = Search(name=f"Veille: {criteria['text']}", parameters=params, handler=handle, delay=delay_seconds)
        searcher = Searcher(searches=[search])
        
        print(f"\n ✅ Veille lancée. Prochaine vérification dans environ {round(delay_seconds/60)} minutes.")
        print(" (Appuyez sur Ctrl+C pour arrêter le programme)")
        searcher.start()

    except Exception as e:
        print(f" ❌ Une erreur est survenue lors de la configuration : {e}")

def main():
    database.initialize_db()
    while True:
        print(f"\n{BORDER}")
        print(f"          🏠 LBC FINDER V{VERSION} - MENU PRINCIPAL")
        print(f"{BORDER}")
        print(" 1. 🔍 Recherche rapide")
        print(" 2. 📡 Lancer une veille active (NLP)")
        print(" 3. 📊 Analyse Top 10 (Meilleures affaires)")
        print(" 4. 🤖 Générer les résumés IA manquants")
        print(" 5. 📂 Consulter vos annonces sauvegardées")
        print(" 6. 🚪 Quitter")
        print(f"{BORDER}")
        
        choice = input(" Votre choix > ")
        
        if choice == '1':
            run_quick_search()
        elif choice == '2':
            run_nlp_watch()
            break 
        elif choice == '3': 
            st = input(" Mot-clé à analyser en base > ")
            try:
                ip_input = input(" Votre prix idéal (€) > ")
                ip = float(ip_input)
                analyze_results(st, ip)
            except ValueError:
                print(" ! Prix invalide.")
        elif choice == '4': 
            run_batch_summary_generation()
        elif choice == '5': 
            run_viewer()
        elif choice == '6': 
            print("\n 👋 Au revoir !")
            break
        else: 
            print(" ! Choix invalide.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n 👋 Programme interrompu. À bientôt !")