from searcher import Searcher
from model import Search, Parameters
import lbc
from config import handle
from analyzer import analyze_results
import database
from nlp import parse_sentence

def run_quick_search():
    """
    Runs a one-shot search, ordered by date, to align with Leboncoin's default sorting.
    """
    print("\n--- Lancement d'une recherche rapide (20 dernières annonces) ---")
    text = input("Que recherchez-vous ? > ")
    city_name = input("Dans quelle ville ? (Laissez vide pour la France entière) > ")

    print(f"\nRecherche des 20 dernières annonces pour '{text}'...")
    try:
        locations = [lbc.City.from_string(name=city_name)] if city_name else None
        ads = lbc.search(text=text, locations=locations, limit=20, sort=lbc.Sort.NEWEST)

    except Exception as e:
        print(f"Erreur durant la recherche : {e}")
        return

    if not ads:
        print("Aucune annonce trouvée pour cette recherche.")
        return

    print(f"\n--- {len(ads)} dernières annonces trouvées ---\n")
    for i, ad in enumerate(ads):
        print(f"#{i+1} | {ad.index_date.strftime('%d-%m-%Y %H:%M')}")
        print(f"  Titre: {ad.subject}")
        print(f"  Prix: {ad.price} €")
        print(f"  Lieu: {ad.location.city_label}")
        print(f"  URL: {ad.url}\n")

def run_nlp_watch():
    """
    Configures and runs a continuous watch based on a natural language sentence.
    """
    print("\n--- Configuration d'une veille par langage naturel ---")
    print("Décrivez ce que vous cherchez en une phrase.")
    print(r"Ex: Cherche une Renault Clio 5 sur Bordeaux avec un budget max de 15000 euros")
    user_sentence = input("> ")

    try:
        criteria = parse_sentence(user_sentence)
        
        print("\n--- Critères de recherche interprétés ---")
        print(f"  Quoi : {criteria['text']}")
        print(f"  Où : {criteria['location'] or 'France entière'}")
        print(f"  Prix min : {criteria['price_min'] or 'Non spécifié'}")
        print(f"  Prix max : {criteria['price_max'] or 'Non spécifié'}")
        print("-" * 40)
        
        confirm = input("Ces critères sont-ils corrects ? (oui/non) > ").lower()
        if confirm != 'oui':
            print("Opération annulée.")
            return

        # Prepare parameters for the search
        locations = [lbc.City.from_string(name=criteria['location'])] if criteria['location'] else None
        
        params = Parameters(
            text=criteria['text'],
            locations=locations,
            price=(criteria['price_min'], criteria['price_max'])
        )

        search_name = f"Veille NLP: {criteria['text']}"
        search = Search(name=search_name, parameters=params, handler=handle, delay=600)

        searcher = Searcher(searches=[search])
        print(f"\nLancement de la veille '{search_name}'. Le programme va maintenant chercher de nouvelles annonces toutes les 10 minutes.")
        searcher.start()
        print("La veille est active. Vous pouvez fermer cette fenêtre si vous le souhaitez.")

    except Exception as e:
        print(f"Une erreur est survenue lors de la configuration de la veille : {e}")


def main() -> None:
    database.initialize_db()

    while True:
        print("\n--- LBC Finder V2 ---")
        print("1. Recherche rapide (identique au site)")
        print("2. Lancer une veille par langage naturel")
        print("3. Analyser les résultats de la veille")
        print("4. Quitter")
        choice = input("Que souhaitez-vous faire ? > ")

        if choice == '1':
            run_quick_search()
            break
        elif choice == '2':
            run_nlp_watch()
            break
        elif choice == '3':
            print("\n--- Analyse des résultats sauvegardés ---")
            search_text = input("Texte de la recherche à analyser (ex: clio 5, porsche 944) > ")
            while True:
                try:
                    ideal_price = float(input("Votre prix idéal pour cette recherche ? > "))
                    break
                except ValueError:
                    print("Veuillez entrer un nombre valide.")
            analyze_results(search_text, ideal_price)
            break
        elif choice == '4':
            print("Au revoir !")
            break
        else:
            print("Choix invalide, veuillez réessayer.")

if __name__ == "__main__":
    main()