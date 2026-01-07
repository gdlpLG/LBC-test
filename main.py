from searcher import Searcher
from model import Search, Parameters
import lbc
from config import handle
from analyzer import analyze_results, generate_batch_summaries
import database
from nlp import parse_sentence
import random # Import the random module

def run_viewer():
    # ... (this function remains the same)
    pass

def run_batch_summary_generation():
    # ... (this function remains the same)
    pass

def run_quick_search():
    # ... (this function remains the same)
    pass

def run_nlp_watch():
    """
    Configures and runs a continuous watch with a randomized, longer delay
    to avoid IP bans and appear more human-like.
    """
    print("\n--- Configuration d'une veille par langage naturel ---")
    user_sentence = input("Décrivez votre recherche (ex: Clio 5 à Bordeaux, budget max 15000€) > ")
    try:
        criteria = parse_sentence(user_sentence)
        print(f"\nCritères interprétés:\n  Quoi: {criteria['text']}\n  Où: {criteria['location'] or 'France'}\n  Prix: {criteria['price_min']}-{criteria['price_max']}\n")
        
        if input("Lancer la veille ? (oui/non) > ").lower() != 'oui':
            print("Annulé.")
            return
        
        # --- Randomized Delay --- #
        delay_seconds = random.randint(900, 1500) # 15 to 25 minutes
        delay_minutes = round(delay_seconds / 60)
        
        params = Parameters(
            text=criteria['text'], 
            locations=[lbc.City.from_string(name=criteria['location'])] if criteria['location'] else None, 
            price=(criteria['price_min'], criteria['price_max'])
        )
        search = Search(name=f"Veille NLP: {criteria['text']}", parameters=params, handler=handle, delay=delay_seconds)
        searcher = Searcher(searches=[search])
        
        print(f"\nVeille lancée. Le programme cherchera de nouvelles annonces à un intervalle long et aléatoire (prochaine recherche dans ~{delay_minutes} minutes). ")
        searcher.start()

    except Exception as e:
        print(f"Une erreur est survenue: {e}")

def main() -> None:
    # ... (main menu logic remains the same)
    pass

# --- Full function definitions needed for the script to be complete ---

def run_viewer():
    print("\n--- Consultation des annonces sauvegardées ---")
    all_ads = database.get_all_ads()
    if not all_ads: return print("Aucune annonce sauvegardée.")
    all_ads.sort(key=lambda x: x.get('date') or '', reverse=True)
    print(f"\nAffichage de {len(all_ads)} annonce(s) :\n")
    for i, ad in enumerate(all_ads):
        summary = ad.get('ai_summary') or "[En attente]"
        print(f"#{i+1} | {ad.get('title','N/A')} | {ad.get('price','N/A')}€\n  Résumé: {summary}\n  URL: {ad.get('url','N/A')}\n")

def run_batch_summary_generation():
    print("\n--- Lancement du résumé par lot via IA ---")
    ads_to_summarize = database.get_ads_without_summary()
    if not ads_to_summarize: return print("Toutes les annonces ont déjà un résumé.")
    print(f"{len(ads_to_summarize)} annonce(s) en attente.")
    summaries = generate_batch_summaries(ads_to_summarize)
    if not summaries: return print("Génération de résumés annulée.")
    database.update_summaries_in_batch(summaries)
    print("\nProcessus de résumé par lot terminé.")

def run_quick_search():
    print("\n--- Recherche rapide --- ")
    text, city = input("Recherche > "), input("Ville > ")
    try:
        loc = [lbc.City.from_string(name=city)] if city else None
        ads = lbc.search(text=text, locations=loc, limit=20, sort=lbc.Sort.NEWEST)
        if ads: print(f"\n--- {len(ads)} annonces ---\n")
        for ad in ads: print(f"{ad.index_date.strftime('%H:%M')} | {ad.subject} | {ad.price}€ | {ad.url}\n")
    except Exception as e: print(f"Erreur: {e}")

def main():
    database.initialize_db()
    while True:
        print("\n--- LBC Finder V5 - Menu ---")
        print("1. Recherche rapide", "2. Lancer une veille", "3. Analyser (Top 10)", "4. Générer résumés IA", "5. Consulter les annonces", "6. Quitter", sep="\n")
        choice = input("> ")
        if choice == '1': run_quick_search(); break
        elif choice == '2': run_nlp_watch(); break
        elif choice == '3': 
            st = input("Texte à analyser > ")
            ip = float(input("Prix idéal > "))
            analyze_results(st, ip); break
        elif choice == '4': run_batch_summary_generation(); break
        elif choice == '5': run_viewer(); break
        elif choice == '6': print("Au revoir !"); break
        else: print("Choix invalide.")

if __name__ == "__main__":
    main()