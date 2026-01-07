import os
from flask import Flask, render_template, jsonify, request
import database
import analyzer

app = Flask(__name__)

# Config
app.config['SECRET_KEY'] = os.urandom(24)

@app.route('/')
def index():
    """Main page of the dashboard."""
    return render_template('index.html')

@app.route('/api/metadata')
def get_metadata():
    """Returns categories, regions and departments for the UI."""
    import lbc
    categories = [{"name": c.name.replace('_', ' ').capitalize(), "id": c.value} for c in lbc.Category]
    regions = [{"name": r.name.replace('_', ' ').capitalize(), "id": r.name} for r in lbc.Region]
    departments = [{"name": d.name.replace('_', ' ').capitalize(), "id": d.name} for d in lbc.Department]
    return jsonify({
        "categories": categories,
        "regions": regions,
        "departments": departments
    })

@app.route('/api/ads')
def get_ads():
    """API endpoint to get ads, optionally filtered by search name."""
    search_name = request.args.get('search_name')
    ads = database.get_all_ads()
    
    if search_name:
        ads = [a for a in ads if a.get('search_name') == search_name]
        
    # Sort by date descending
    ads.sort(key=lambda x: x.get('date') or '', reverse=True)
    return jsonify(ads)

@app.route('/api/analyze', methods=['POST'])
def trigger_analysis():
    """Trigger AI summary generation for ads without a summary."""
    ads_to_summarize = database.get_ads_without_summary()
    if not ads_to_summarize:
        return jsonify({"status": "no_ads", "message": "Aucune annonce à analyser."})
    
    # Due to user limits (20/day), we process them in ONE single call
    # We take a maximum of 40 ads per batch to leverage the 250k context window
    batch = ads_to_summarize[:40]
    
    # Process them search by search to apply correct context
    # For now, we take the context of the first ad's search
    search_name = batch[0].get('search_name')
    all_searches = database.get_active_searches()
    search_info = next((s for s in all_searches if s['name'] == search_name), {})
    context = search_info.get('ai_context')

    summaries = analyzer.generate_batch_summaries(batch, user_context=context)
    if summaries:
        # Pre-process summaries to ensure all keys exist
        processed = []
        for s in summaries:
            processed.append({
                "id": s.get("id"),
                "summary": s.get("summary"),
                "score": s.get("score", 5.0),
                "tips": s.get("tips", "")
            })
        database.update_summaries_in_batch(processed)
        return jsonify({
            "status": "success", 
            "count": len(summaries),
            "message": f"Analyse terminée pour {len(summaries)} annonces."
        })
    else:
        return jsonify({"status": "error", "message": "L'analyse IA a échoué."}), 500

@app.route('/api/stats')
def get_stats():
    """Get basic statistics for the dashboard."""
    all_ads = database.get_all_ads()
    without_summary = len(database.get_ads_without_summary())
    
    avg_price = 0
    if all_ads:
        prices = [float(a['price']) for a in all_ads if a['price']]
        if prices:
            avg_price = round(sum(prices) / len(prices), 2)

    return jsonify({
        "total_ads": len(all_ads),
        "pending_ai": without_summary,
        "avg_price": avg_price
    })

# --- Market Analysis Routes ---
@app.route('/api/market-stats')
def market_stats():
    query = request.args.get('query', '')
    if not query: return jsonify({})
    return jsonify(analyzer.get_market_stats(query))

# --- Search Management Routes ---
@app.route('/api/searches', methods=['GET', 'POST'])
def manage_searches():
    if request.method == 'GET':
        return jsonify(database.get_active_searches())
    
    # POST to add a new search (NLP style)
    from nlp import parse_sentence
    sentence = request.json.get('sentence', '')
    if not sentence: return jsonify({"error": "Empty sentence"}), 400
    
    criteria = parse_sentence(sentence)
    
    # Resolve coordinates if city is present
    lat, lng, zip_code = None, None, None
    if criteria['location']:
        from utils import get_coordinates
        result = get_coordinates(criteria['location'])
        if result:
            lat, lng, zip_code = result

    search_data = {
        "name": f"Veille: {criteria['text']} ({criteria['location'] or 'FR'})",
        "query_text": criteria['text'],
        "city": criteria['location'],
        "radius": criteria['radius'],
        "lat": lat,
        "lng": lng,
        "zip_code": zip_code,
        "price_min": criteria['price_min'],
        "price_max": criteria['price_max'],
        "category": None,
        "last_run": None,
        "is_active": 1,
        "ai_context": request.json.get('ai_context')
    }
    
    if database.save_search(search_data):
        # Save initial ads if provided
        initial_ads = request.json.get('initial_ads', [])
        for ad in initial_ads:
            ad['search_name'] = search_data['name']
            database.add_ad(ad)
        return jsonify({"status": "success", "search": search_data})
    return jsonify({"status": "error"}), 500

@app.route('/api/quick-search', methods=['POST'])
def quick_search():
    """Performs a live search with complex criteria."""
    import lbc
    data = request.json
    queries = data.get('queries', []) # List of keyword strings
    if not queries: queries = [data.get('query', '')]
    
    # Common parameters
    price_min = data.get('price_min')
    price_max = data.get('price_max')
    category = data.get('category')
    delivery = data.get('delivery', False)
    sort = data.get('sort', 'newest')
    owner_type = data.get('owner_type') # 'private', 'pro' or None
    title_only = data.get('title_only', False)
    
    # Location resolution
    locations = []
    if data.get('city'):
        from utils import get_coordinates
        res = get_coordinates(data['city'])
        if res:
            lat, lng, zip_code = res
            locations.append(lbc.City(lat=lat, lng=lng, city=data['city'], radius=int(data.get('radius', 10))*1000))
    elif data.get('department'):
        locations.append(getattr(lbc.Department, data['department']))
    elif data.get('region'):
        locations.append(getattr(lbc.Region, data['region']))

    client = lbc.Client()
    all_ads = []
    
    lbc_sort = lbc.Sort.NEWEST if sort == 'newest' else lbc.Sort.RELEVANCE
    lbc_category = getattr(lbc.Category, category) if category and category != '0' else None
    
    lbc_owner = None
    if owner_type == 'private': lbc_owner = lbc.OwnerType.PRIVATE
    elif owner_type == 'pro': lbc_owner = lbc.OwnerType.PRO

    # Execute all searches
    for q in queries:
        if not q: continue
        try:
            res = client.search(
                text=q,
                locations=locations if locations else None,
                category=lbc_category,
                price=(price_min, price_max),
                shippable=delivery,
                owner_type=lbc_owner,
                limit=50, # Augmenté pour capturer plus d'annonces
                sort=lbc_sort
            )
            for ad in res.ads:
                all_ads.append({
                    'id': str(ad.id),
                    'title': ad.subject,
                    'price': ad.price,
                    'location': ad.location.city_label,
                    'date': str(ad.index_date),
                    'url': ad.url,
                    'description': ad.body if hasattr(ad, 'body') and ad.body else "Pas de description.",
                    'image_url': ad.images[0] if hasattr(ad, 'images') and ad.images else None,
                    'is_pro': 1 if getattr(ad, 'is_pro', False) else 0,
                    'lat': ad.location.lat if hasattr(ad.location, 'lat') else None,
                    'lng': ad.location.lng if hasattr(ad.location, 'lng') else None,
                    'category': ad.category.name if hasattr(ad, 'category') and ad.category else None,
                    'ai_summary': None,
                    'ai_score': None,
                    'ai_tips': None
                })
        except Exception as e:
            print(f"Error searching for {q}: {e}")

    # Remove duplicates by ID
    unique_ads = {ad['id']: ad for ad in all_ads}.values()
    
    # Sort ONLY if user asked for newest. If relevance, keep API order as much as possible
    if sort == 'newest':
        sorted_ads = sorted(unique_ads, key=lambda x: x['date'], reverse=True)
    else:
        # Keep original order but deduplicated
        sorted_ads = list(unique_ads) 
    
    return jsonify(sorted_ads)
    
@app.route('/api/compare', methods=['POST'])
def compare_ads():
    """Compares selected ads using Gemini."""
    ads = request.json.get('ads', [])
    if not ads:
        return jsonify({"error": "No ads selected"}), 400
    
    recommendation = analyzer.compare_and_recommend(ads)
    return jsonify({"recommendation": recommendation})

@app.route('/api/gem-builder', methods=['POST'])
def gem_builder():
    goal = request.json.get('goal', '')
    if not goal: return jsonify({"error": "Empty goal"}), 400
    instructions = analyzer.build_ai_instructions(goal)
    return jsonify({"instructions": instructions})

@app.route('/api/searches/<name>', methods=['GET', 'DELETE'])
def manage_single_search(name):
    if request.method == 'GET':
        all_s = database.get_active_searches()
        found = next((s for s in all_s if s['name'] == name), None)
        return jsonify(found) if found else (jsonify({"error": "Not found"}), 404)

    if database.delete_search(name):
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 500

if __name__ == '__main__':
    database.initialize_db()
    app.run(debug=True, port=5000)
