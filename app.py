import os
import json
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from functools import wraps
import database
import analyzer
import searcher.search_providers as multi_search
import notifiers.discord_bot as disc_bot
import threading
import time
import random
from datetime import datetime, timedelta
from nlp import parse_sentence
from utils import get_coordinates

app = Flask(__name__)

# decorator to check if user is logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({"error": "Non authentifié"}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user_id():
    return session.get('user_id', 1) # Default to 1 for back-compat or background tasks


# Config
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'lbc-finder-super-secret-persistent-key')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form if request.form else request.json
        user = database.authenticate_user(data.get('username'), data.get('password'))
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            if request.is_json:
                return jsonify({"status": "success"})
            return redirect(url_for('index'))
        if request.is_json:
            return jsonify({"error": "Identifiants invalides"}), 401
        return "Identifiants invalides", 401
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form if request.form else request.json
        res = database.create_user(data.get('username'), data.get('password'))
        if res == -1:
            return jsonify({"error": "Utilisateur déjà existant"}), 400
        if res:
            return jsonify({"status": "success", "message": "Compte créé !"})
        return jsonify({"error": "Erreur lors de la création"}), 500
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """Main page of the dashboard."""
    return render_template('index.html', username=session.get('username'))


@app.route('/api/metadata')
def get_metadata():
    """Returns categories, regions and departments for the UI."""
    import lbc
    categories = [{"name": c.name.replace('_', ' ').capitalize(), "id": c.name} for c in lbc.Category]

    regions = [{"name": r.name.replace('_', ' ').capitalize(), "id": r.name} for r in lbc.Region]
    departments = [{"name": d.name.replace('_', ' ').capitalize(), "id": d.name} for d in lbc.Department]
    return jsonify({
        "categories": categories,
        "regions": regions,
        "departments": departments
    })

@app.route('/api/ads')
@login_required
def get_ads():
    """API endpoint to get ads, optionally filtered by search name."""
    user_id = get_current_user_id()
    search_name = request.args.get('search_name')
    ads = database.get_all_ads(user_id=user_id)
    
    if search_name:
        ads = [a for a in ads if a.get('search_name') == search_name]
        
    # Sort by date descending
    ads.sort(key=lambda x: x.get('date') or '', reverse=True)
    return jsonify(ads)


@app.route('/api/feedback', methods=['POST'])
@login_required
def submit_feedback():
    try:
        user_id = get_current_user_id()
        data = request.json
        if database.add_feedback(user_id, data.get('type'), data.get('message')):
            return jsonify({"status": "success"})
        return jsonify({"status": "error"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/analyze', methods=['POST'])
@login_required
def trigger_analysis():
    """Trigger AI summary generation for ads. Supports specific ad IDs and custom prompts."""
    try:
        user_id = get_current_user_id()
        data = request.get_json(silent=True) or {}
        ad_ids = data.get('ad_ids')
        ads_data = data.get('ads_data') # New: List of full ad objects
        custom_context = data.get('custom_prompt')
        
        # Upsert ads if provided (Live Search case)
        if ads_data:
            print(f"📥 Received {len(ads_data)} ads to upsert/analyze.")
            upserted_ids = []
            for ad in ads_data:
                # Ensure essential fields
                if not ad.get('id'): continue
                
                # Sanitize/Prepare for DB
                db_ad = {
                    'id': str(ad.get('id')),
                    'title': ad.get('title'),
                    'price': ad.get('price'),
                    'location': ad.get('location'),
                    'date': ad.get('date'),
                    'url': ad.get('url'),
                    'description': ad.get('description'),
                    'image_url': ad.get('image_url'),
                    'is_pro': 1 if ad.get('is_pro') else 0,
                    'lat': ad.get('lat'),
                    'lng': ad.get('lng'),
                    'category': ad.get('category'),
                    'search_name': ad.get('search_name') or 'Live Search', # Default if missing
                    'source': 'lbc' # Default
                }
                
                # Use database.add_ad (it handles INSERT OR UPDATE)
                database.add_ad(db_ad, user_id=user_id)
                upserted_ids.append(db_ad['id'])
            
            # If no manual IDs were requested but we upserted data, use these IDs
            if not ad_ids:
                ad_ids = upserted_ids

        
        # Determine strict list of ads to analyze
        if ad_ids:
            ads_to_summarize = database.get_ads_by_ids(ad_ids, user_id=user_id)
        else:
            ads_to_summarize = database.get_ads_without_summary(user_id=user_id)
            
        if not ads_to_summarize:
            return jsonify({"status": "no_ads", "message": "Aucune annonce à analyser (DB vide ?)."})
        
        # User specific API Key
        user_data = database.get_user_by_id(user_id) or {}
        user_api_key = user_data.get('google_api_key')
        
        # Background task function
        def run_background_analysis(ads_list, u_id, u_api_key, c_context):
            with app.app_context():
                import analyzer
                
                # Group ads by search_name
                from collections import defaultdict
                grouped_ads = defaultdict(list)
                for ad in ads_list:
                    grouped_ads[ad['search_name']].append(ad)
                
                all_searches = database.get_active_searches(user_id=u_id)
                total_summaries = 0
                
                processed_count = 0
                max_batch = 40
            
            for search_name, ads in grouped_ads.items():
                if processed_count >= max_batch: break
                
                batch = ads[:max_batch - processed_count]
                processed_count += len(batch)
                
                # Use custom context if provided, else defaults
                search_info = next((s for s in all_searches if s['name'] == search_name), {})
                context = c_context
                if not context:
                    context = search_info.get('ai_context')
                if not context or not context.strip():
                    query = search_info.get('query_text', 'Recherche générale')
                    context = f"L'utilisateur recherche : {query}. Analyse la pertinence par rapport à ce produit."
                
                print(f"--- Analyse background pour [{search_name}] ---")
                
                summaries = analyzer.generate_batch_summaries(batch, user_context=context, api_key=u_api_key)
                if summaries:
                    processed = []
                    for s in summaries:
                        processed.append({
                            "id": s.get("id"),
                            "ai_summary": s.get("ai_summary"),
                            "ai_score": s.get("ai_score", 5.0),
                            "ai_tips": s.get("ai_tips", "")
                        })
                    database.update_summaries_in_batch(processed, user_id=u_id)
                    total_summaries += len(processed)

                    # Discord Notifications
                    webhook = search_info.get('discord_webhook') or (user_data.get('discord_webhook') if user_data else None) or database.get_setting('discord_webhook')
                    if webhook:
                        notifier = disc_bot.DiscordNotifier(webhook)
                        for p in processed:
                            if p.get('ai_score', 0) >= 8:
                                full_ad = next((ad for ad in batch if ad['id'] == p['id']), None)
                                if full_ad:
                                    full_ad.update(p)
                                    notifier.send_ad_notification(full_ad, is_pepite=True)
            
            print(f"--- Fin analyse background ({total_summaries} items) ---")

        # Start thread
        thread = threading.Thread(target=run_background_analysis, args=(ads_to_summarize, user_id, user_api_key, custom_context))
        thread.daemon = True
        thread.start()

        return jsonify({
            "status": "started", 
            "message": "Analyse lancée en arrière-plan.",
            "count_prediction": len(ads_to_summarize)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/clear-analysis', methods=['POST'])
@login_required
def clear_analysis():
    """Removes AI summaries and scores from ads."""
    user_id = get_current_user_id()
    data = request.json
    search_name = data.get('search_name')
    ad_ids = data.get('ad_ids')
    
    if database.clear_ad_analyses(user_id=user_id, search_name=search_name, ad_ids=ad_ids):
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 500


@app.route('/api/ai-status')
def get_ai_status():
    """Returns the current background status of the AI analyzer."""
    return jsonify(analyzer.get_ai_status())

@app.route('/api/stop-analysis', methods=['POST'])
@login_required
def stop_analysis_route():
    analyzer.stop_analysis()
    return jsonify({"status": "success", "message": "Arrêt demandé."})

@app.route('/api/stats')
@login_required
def get_stats():
    """Get basic statistics for the dashboard."""
    user_id = get_current_user_id()
    all_ads = database.get_all_ads(user_id=user_id)
    without_summary = len(database.get_ads_without_summary(user_id=user_id))
    
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

@app.route('/api/ai-market-analysis')
def ai_market_analysis():
    query = request.args.get('query', '')
    if not query: return jsonify({"error": "Query required"}), 400
    
    # Get relevant ads from DB
    all_ads = database.get_all_ads()
    relevant_ads = [a for a in all_ads if query.lower() in a['title'].lower()]
    
    analysis = analyzer.get_ai_market_analysis(query, relevant_ads)
    return jsonify({"analysis": analysis})


# --- Search Management Routes ---
@app.route('/api/searches', methods=['GET', 'POST'])
@login_required
def manage_searches():
    user_id = get_current_user_id()
    if request.method == 'GET':
        try:
            results = database.get_active_searches(user_id=user_id)
            return jsonify(results)
        except Exception as e:
            print(f"[API Error] GET /api/searches failed: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
    
    if request.method == 'POST':
        try:
            data = request.get_json(silent=True) or {}
            sentence = data.get('sentence', '')
            if not sentence:
                return jsonify({"error": "Description de la veille requise"}), 400
            
            criteria = parse_sentence(sentence)
            
            # Resolve coordinates if city is present
            lat, lng, zip_code = None, None, None
            if criteria.get('location'):
                result = get_coordinates(criteria['location'])
                if result:
                    lat, lng, zip_code = result
            
            # Resolve coordinates for all cities in multi-location list
            raw_locations = data.get('locations', [])
            processed_locations = []
            for loc in raw_locations:
                if loc.get('type') == 'city' and (not loc.get('lat') or not loc.get('lng')):
                    coords = get_coordinates(loc.get('value'))
                    if coords:
                        loc['lat'], loc['lng'], loc['zip_code'] = coords
                processed_locations.append(loc)

            # FETCH GLOBAL DEFAULTS
            def_mode = database.get_setting('default_refresh_mode', 'manual')
            def_interval = int(database.get_setting('default_refresh_interval', 60))
            def_platforms = database.get_setting('default_platforms', '{"lbc":true,"ebay":false,"vinted":false}')
            def_context = database.get_setting('default_ai_context', '')

            # Ensure numeric interval from request or default
            interval = def_interval
            try:
                interval_str = data.get('refresh_interval')
                if interval_str:
                    interval = int(interval_str)
            except:
                pass

            # Use provided queries array if available, otherwise fallback to parsed text
            keywords_list = data.get('queries', [])
            if keywords_list:
                query_text = ", ".join(keywords_list)
            else:
                query_text = criteria['text']

            search_data = {
                "name": data.get('name') or f"Veille: {query_text} ({criteria['location'] or 'FR'})",
                "query_text": query_text,
                "city": criteria['location'],
                "radius": criteria.get('radius', 10),
                "lat": lat,
                "lng": lng,
                "zip_code": zip_code,
                "locations": json.dumps(processed_locations),
                "price_min": criteria.get('price_min'),
                "price_max": criteria.get('price_max'),
                "category": None,
                "last_run": None,
                "is_active": 1,
                "ai_context": data.get('ai_context') or def_context,
                "refresh_mode": data.get('refresh_mode') or def_mode,
                "refresh_interval": interval,
                "platforms": json.dumps(data.get('platforms')) if data.get('platforms') else def_platforms,
                "last_viewed": None
            }
            
            if database.save_search(search_data, user_id=user_id):
                # Save initial ads
                initial_ads = data.get('initial_ads', [])
                if initial_ads:
                    for ad in initial_ads:
                        ad['search_name'] = search_data['name']
                        database.add_ad(ad, user_id=user_id)
                return jsonify({"status": "success", "search": search_data})
            
            return jsonify({"status": "error", "message": "Erreur base de données lors de la sauvegarde"}), 500

            
        except Exception as e:
            print(f"[API Error] manage_searches POST failed: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"error": "Méthode non autorisée"}), 405

@app.route('/api/searches/stats')
@login_required
def get_watch_stats():
    """Returns global stats for all watches."""
    user_id = get_current_user_id()
    return jsonify(database.get_global_watch_stats(user_id=user_id))

@app.route('/api/searches/<path:name>/viewed', methods=['POST'])
@login_required
def mark_watch_viewed(name):
    """Marks a watch as viewed to reset new ad counters."""
    user_id = get_current_user_id()
    if database.update_last_viewed(name, user_id=user_id):
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 500

@app.route('/api/searches/<path:name>', methods=['PUT'])
@login_required
def update_search(name):
    """Update settings for a specific search."""
    user_id = get_current_user_id()
    data = request.json
    if 'platforms' in data:
        data['platforms'] = json.dumps(data['platforms'])
    
    if database.update_search_settings(name, data, user_id=user_id):
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 500


# --- Global Settings Routes ---
@app.route('/api/settings', methods=['GET', 'POST'])
@login_required
def manage_settings():
    user_id = get_current_user_id()
    user_data = database.get_user_by_id(user_id)
    
    if request.method == 'GET':
        return jsonify({
            "discord_webhook": user_data.get('discord_webhook', '') if user_data else '',
            "google_api_key": user_data.get('google_api_key', '') if user_data else '',
            "default_ai_context": database.get_setting('default_ai_context', 'Analyse générale de la qualité et du prix.'),
            "default_refresh_mode": database.get_setting('default_refresh_mode', 'manual'),
            "default_refresh_interval": int(database.get_setting('default_refresh_interval', 60)),
            "default_platforms": json.loads(database.get_setting('default_platforms', '{"lbc":true,"ebay":false,"vinted":false}'))
        })
    
    data = request.json
    
    # Update user specific settings
    user_updates = {}
    if 'discord_webhook' in data: user_updates['discord_webhook'] = data['discord_webhook']
    if 'google_api_key' in data: user_updates['google_api_key'] = data['google_api_key']
    if user_updates:
        database.update_user_settings(user_id, user_updates)
            
    # Keep some defaults global or per user? Let's say these stay global for now or just ignored
    return jsonify({"status": "success"})


@app.route('/api/settings/test-discord', methods=['POST'])
def test_discord():
    webhook = request.json.get('discord_webhook')
    if not webhook: return jsonify({"error": "Webhook requis"}), 400
    
    notifier = disc_bot.DiscordNotifier(webhook)
    if notifier.test_notification():
        return jsonify({"status": "success"})
    return jsonify({"error": "Échec de l'envoi"}), 500

@app.route('/api/quick-search', methods=['POST'])
@login_required
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
    
    # New multi-location support
    raw_locations = data.get('locations', []) # List of {type: 'city', value: 'Paris', radius: 10} etc.
    
    from utils import get_coordinates
    
    for loc in raw_locations:
        loc_type = loc.get('type')
        loc_val = loc.get('value')
        if not loc_val: continue
        
        if loc_type == 'city':
            res = get_coordinates(loc_val)
            if res:
                lat, lng, zip_code = res
                locations.append(lbc.City(lat=lat, lng=lng, city=loc_val, radius=int(loc.get('radius', 10))*1000))
        elif loc_type == 'department':
            try:
                locations.append(getattr(lbc.Department, loc_val))
            except AttributeError:
                pass
        elif loc_type == 'region':
            try:
                locations.append(getattr(lbc.Region, loc_val))
            except AttributeError:
                pass
            
    # Fallback/Backward compatibility
    if not locations:
        if data.get('city'):
            res = get_coordinates(data['city'])
            if res:
                lat, lng, zip_code = res
                locations.append(lbc.City(lat=lat, lng=lng, city=data['city'], radius=int(data.get('radius', 10))*1000))
        elif data.get('department'):
            try:
                locations.append(getattr(lbc.Department, data['department']))
            except AttributeError:
                pass
        elif data.get('region'):
            try:
                locations.append(getattr(lbc.Region, data['region']))
            except AttributeError:
                pass

    client = lbc.Client()
    all_ads = []
    
    lbc_sort = lbc.Sort.NEWEST if sort == 'newest' else lbc.Sort.RELEVANCE
    lbc_category = getattr(lbc.Category, category) if category and category != '0' else lbc.Category.TOUTES_CATEGORIES
    
    lbc_owner = lbc.OwnerType.ALL
    if owner_type == 'private': lbc_owner = lbc.OwnerType.PRIVATE
    elif owner_type == 'pro': lbc_owner = lbc.OwnerType.PRO

    # Execute all searches
    is_deep = data.get('deep_search', 0) == 1
    
    for q in queries:
        if not q: continue
        try:
            pages_to_fetch = 3 if is_deep else 1
            
            for page in range(1, pages_to_fetch + 1):
                # Small delay for stealth mode to avoid rate limiting
                if page > 1:
                    time.sleep(random.randint(2, 5))
                
                res = client.search(
                    text=q,
                    locations=locations if locations else None,
                    category=lbc_category,
                    price=(price_min, price_max),
                    shippable=delivery,
                    owner_type=lbc_owner,
                    limit=50,
                    sort=lbc_sort,
                    page=page
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

    # Multi-platform search logic
    platforms = data.get('platforms', {'lbc': True})
    query_text = (queries[0] if queries else data.get('query', ''))
    
    # Execute eBay/Vinted if requested
    other_ads = multi_search.get_multi_platform_results(query_text, platforms)
    for ad in other_ads:
        all_ads.append(ad)

    # Remove duplicates by ID
    unique_ads = {ad['id']: ad for ad in all_ads}.values()
    
    # Sort ONLY if user asked for newest. If relevance, keep API order as much as possible
    if sort == 'newest':
        sorted_ads = sorted(unique_ads, key=lambda x: x.get('date') or '', reverse=True)
    else:
        # Keep original order but deduplicated
        sorted_ads = list(unique_ads) 
    
    return jsonify(sorted_ads[:200]) # Retourne un peu plus car multi-plateformes
    
@app.route('/api/compare', methods=['POST'])
@login_required
def compare_ads():
    """Compares selected ads using Gemini."""
    user_id = get_current_user_id()
    user_data = database.get_user_by_id(user_id) or {}
    api_key = user_data.get('google_api_key')

    ads = request.json.get('ads', [])
    if not ads:
        return jsonify({"error": "No ads selected"}), 400
    
    recommendation = analyzer.generate_comparison(ads, api_key=api_key)
    return jsonify({"recommendation": recommendation})

@app.route('/api/gem-builder', methods=['POST'])
@login_required
def gem_builder():
    user_id = get_current_user_id()
    user_data = database.get_user_by_id(user_id) or {}
    api_key = user_data.get('google_api_key')

    goal = request.json.get('goal', '')
    if not goal: return jsonify({"error": "Empty goal"}), 400
    instructions = analyzer.refine_search_query(goal, api_key=api_key)
    return jsonify({"instructions": instructions})


@app.route('/api/scam-detector', methods=['POST'])
@login_required
def scam_detector():
    """Endpoint to check an ad for potential scam risk."""
    user_id = get_current_user_id()
    user_data = database.get_user_by_id(user_id) or {}
    api_key = user_data.get('google_api_key')

    data = request.json
    ad_id = data.get('ad_id')
    
    if ad_id:
        ads = database.get_ads_by_ids([ad_id], user_id=user_id)
        if ads:
            result = analyzer.detect_scam(ads[0], api_key=api_key)
            return jsonify(result)
            
    return jsonify({"error": "Ad not found"}), 404



@app.route('/api/ads/move-to-watch', methods=['POST'])
@login_required
def move_ads_to_watch():
    """Moves selected ads to another watch (or new one)."""
    user_id = get_current_user_id()
    data = request.json
    ad_ids = data.get('ad_ids', [])
    target_watch = data.get('target_watch')
    
    if not ad_ids or not target_watch:
        return jsonify({"error": "Missing data"}), 400
    
    success = database.move_ads_to_search(ad_ids, target_watch, user_id)
    if success:
        return jsonify({"status": "success", "message": f"Moved {len(ad_ids)} ads to {target_watch}"})
    return jsonify({"error": "Database error"}), 500


@app.route('/api/searches/<path:name>', methods=['GET', 'DELETE'])
@login_required
def manage_single_search(name):
    user_id = get_current_user_id()
    if request.method == 'GET':
        all_s = database.get_active_searches(user_id=user_id)
        found = next((s for s in all_s if s['name'] == name), None)
        return jsonify(found) if found else (jsonify({"error": "Not found"}), 404)

    if database.delete_search(name, user_id=user_id):
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 500


@app.route('/api/negotiate', methods=['POST'])
@login_required
def trigger_negotiation():
    """Generates a negotiation draft for an ad."""
    user_id = get_current_user_id()
    user_data = database.get_user_by_id(user_id) or {}
    api_key = user_data.get('google_api_key')

    data = request.json
    ad_id = data.get('ad_id')
    if not ad_id: return jsonify({"error": "ID required"}), 400
    
    ad = database.get_ads_by_ids([ad_id], user_id=user_id)
    if not ad: return jsonify({"error": "Ad not found"}), 404
    
    draft = analyzer.generate_negotiation_draft(ad[0], api_key=api_key)
    return jsonify({"draft": draft})

@app.route('/api/chat', methods=['POST'])
@login_required
def trigger_chat():
    """AI Chat dedicated to discussion about an ad or search."""
    user_id = get_current_user_id()
    user_data = database.get_user_by_id(user_id) or {}
    api_key = user_data.get('google_api_key')

    data = request.json
    message = data.get('message', '')
    ad_id = data.get('ad_id')
    history = data.get('history', [])
    
    ad_data = None
    if ad_id:
        ads = database.get_ads_by_ids([ad_id], user_id=user_id)
        if ads: ad_data = ads[0]
        
    response = analyzer.get_chat_response(message, ad_data, history, api_key=api_key)
    return jsonify({"response": response})

@app.route('/api/ads/manual', methods=['POST'])
@login_required
def add_manual_ad():
    """Add a manual ad using its URL with advanced JSON state extraction."""
    user_id = get_current_user_id()
    data = request.json
    url = data.get('url', '').strip()
    search_name = data.get('search_name', 'Ajout Manuel')
    
    if not url: return jsonify({"error": "URL required"}), 400
    
    import requests
    from bs4 import BeautifulSoup
    import re
    import json
    from datetime import datetime
    
    try:
        # Robust ID extraction
        id_match = re.search(r'/(\d+)(?:\.htm|/|$|\?)', url)
        if not id_match:
            return jsonify({"error": "Impossible d'extraire l'ID de l'annonce."}), 400
        ad_id = id_match.group(1)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        
        ad_title = "Annonce Leboncoin"
        ad_price = 0
        ad_image = None
        ad_description = "Pas de description."
        ad_location = "France"
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                # STAGE 1: Try application/ld+json (Highly reliable for SEO)
                soup = BeautifulSoup(resp.text, 'html.parser')
                ld_scripts = soup.find_all('script', type='application/ld+json')
                for script in ld_scripts:
                    try:
                        ld_data = json.loads(script.string)
                        # LD+JSON can be a list or a single object
                        items = ld_data if isinstance(ld_data, list) else [ld_data]
                        for item in items:
                                if item.get('@type') == 'Product':
                                    ad_title = item.get('name', ad_title)
                                    images = item.get('image')
                                    if images:
                                        ad_image = images[0] if isinstance(images, list) else images
                                    offers = item.get('offers')
                                    if offers:
                                        price = offers.get('price') if isinstance(offers, dict) else offers[0].get('price') if isinstance(offers, list) else 0
                                        ad_price = float(price) if price else ad_price
                                    ad_description = item.get('description', ad_description)
                                    
                                    # Try extracting location from LD+JSON
                                    loc = item.get('location') or item.get('address')
                                    if isinstance(loc, dict):
                                        if '@type' in loc and loc['@type'] == 'Place':
                                            addr = loc.get('address', {})
                                            city = addr.get('addressLocality')
                                            zipcode = addr.get('postalCode')
                                            if city:
                                                ad_location = f"{city} ({zipcode})" if zipcode else city
                    except: continue

                # STAGE 2: Try window.__REDUX_STATE__ (Internal Data)
                if ad_location == "France": # Only try Redux if location not found yet
                    match = re.search(r'window\.__REDUX_STATE__\s*=\s*({.*?});', resp.text, re.DOTALL)
                    if match:
                        try:
                            state = json.loads(match.group(1))
                            
                            if ad_id in ["3075046375", "3126232591"]:
                                print(f"DEBUG REDUX: Keys in State: {state.keys()}")
                                print(f"DEBUG REDUX: adview keys: {state.get('adview', {}).keys()}")
                            
                            # Try multiple paths for ad data
                            ad_data = state.get('adview', {}).get('adData', {}) or \
                                      state.get('ad', {}).get('adData', {}) or \
                                      state.get('adview', {}).get('data', {})
                            
                            if ad_data:
                                if ad_title == "Annonce Leboncoin":
                                    ad_title = ad_data.get('subject', ad_title)
                                if ad_price == 0:
                                    ad_price = ad_data.get('price', [0])[0] if isinstance(ad_data.get('price'), list) else ad_data.get('price', 0)
                                if ad_description == "Pas de description.":
                                    ad_description = ad_data.get('body', ad_description)
                                
                                # Precise location from Redux
                                loc = ad_data.get('location', {})
                                city = loc.get('city_label') or loc.get('city')
                                zipcode = loc.get('zipcode') or loc.get('zip_code')
                                if city:
                                    ad_location = f"{city} ({zipcode})" if zipcode else city
                                
                                # coordinates
                                lat = loc.get('lat')
                                lng = loc.get('lng')

                                images = ad_data.get('images', {}).get('urls', [])
                                if images and not ad_image: ad_image = images[0]

                        except: pass
                
                # STAGE 3: Fallback Regex for Location if still generic (executed only if needed)
                if ad_location == "France" or not ad_location:
                    for tag in soup.find_all(['h2', 'p', 'div', 'span']):
                        txt = tag.get_text(" ", strip=True) # Join with space to avoid glued words
                        # Regex for City Zipcode (e.g., "Paris 75001" or "Zone 09209")
                        # We allow "Zone" now as it appears in valid LBC ads.
                        match = re.search(r'([A-Za-zÀ-ÖØ-öø-ÿ\-\s]+)\s+(\d{5})', txt)
                        
                        # Avoid huge texts, looking for short location strings
                        if match and len(txt) < 60:
                             candidates_city = match.group(1).strip()
                             # Filter out common false positives like "depuis le" or "livraison" if they match accidentaly
                             if "livraison" in candidates_city.lower(): continue
                             
                             ad_location = f"{candidates_city} ({match.group(2)})"
                             break


                # STAGE 3: Mega Fallback (Meta Tags & Regex)
                # Image
                if not ad_image:
                    for meta_prop in ['og:image', 'twitter:image', 'image']:
                        m = soup.find('meta', property=meta_prop) or soup.find('meta', attrs={"name": meta_prop})
                        if m: 
                            ad_image = m.get('content')
                            break
                
                # Location (Refined Search)
                if ad_location == "France":
                    # 1. Search in breadcrumbs (Very reliable)
                    breadcrumbs = soup.find_all(attrs={"data-qa-id": re.compile(r'breadcrumb', re.I)})
                    for bc in reversed(breadcrumbs):
                        text = bc.get_text().strip()
                        if re.search(r'\d{5}', text):
                            ad_location = text
                            break
                    
                    # 2. Search in specific LBC location markers
                    if ad_location == "France":
                        loc_tag = soup.find(attrs={"data-qa-id": re.compile(r'location|city|adview_location', re.I)}) or \
                                  soup.find(class_=re.compile(r'location', re.I))
                        if loc_tag:
                            cand = loc_tag.get_text().strip()
                            if cand and len(cand) < 100:
                                ad_location = cand
                    
                    # 3. Regex Fallback (Stricter: 5 digits zip code)
                    if ad_location == "France" or "92100" in ad_location:
                        # Regex for "City (ZipCode)" or "City ZipCode"
                        # We exclude common brands and technical terms
                        excluded = ['prix', 'date', 'offre', 'vendeur', 'annonce', 'toutes', 'peerless', 'focal', 'cabasse', 'denon', 'sony', 'philips', 'samsung', 'rel', 'haut', 'parleur']
                        
                        # Try searching in title/desc first
                        search_space = (soup.title.string if soup.title else '') + " "
                        meta_desc = soup.find('meta', attrs={'name': 'description'})
                        if meta_desc: search_space += meta_desc.get('content', '') + " "
                        search_space += resp.text[:15000] # Search first 15k chars

                        loc_matches = re.finditer(r'([A-ZÀ-Ÿ][a-zà-ÿ\s\-]{3,})\s?\(?(\d{5})\)?', search_space)
                        for match in loc_matches:
                            cityName = match.group(1).strip()
                            zipCode = match.group(2)
                            if cityName.lower() not in excluded and zipCode not in ['92100', '75000']:
                                ad_location = f"{cityName} ({zipCode})"
                                break

                        
                        # Last ditch: any 5 digit code that's not LBC HQ
                        if ad_location == "France" or "92100" in ad_location:
                            codes = re.findall(r'(\d{5})', search_space)
                            for c in codes:
                                if c not in ['92100', '75000']:
                                    # Look for a word before it
                                    surround = re.search(r'([A-ZÀ-Ÿ][a-zà-ÿ\s\-]{3,})\s?\(?' + c + r'\)?', search_space)
                                    if surround and surround.group(1).strip().lower() not in excluded:
                                        ad_location = f"{surround.group(1).strip()} ({c})"
                                        break
                                    else:
                                        ad_location = f"Zone {c}"
                                        break

                # Price fallback regex if still 0

                if ad_price == 0:
                    price_match = re.search(r'(\d+[\s]?\d*)\s*€', resp.text)
                    if price_match:
                        ad_price = float(price_match.group(1).replace(' ', '').replace('\xa0', ''))

        except Exception as scrap_e:
            print(f"[Manual Add] Advanced extraction failed: {scrap_e}")

        ad = {
            "id": ad_id,

            "title": ad_title,
            "url": url,
            "price": ad_price,
            "image_url": ad_image,
            "description": ad_description,
            "location": ad_location,
            "search_name": search_name,
            "is_pro": 0,
            "date": datetime.now().isoformat(),
            "source": "MANUAL",
            "is_hidden": 0
        }
        
        # Force add even if exists to update info? OR keep as is
        # Overwrite=True in database.add_ad would be better
        success, _, _ = database.add_ad(ad, user_id=user_id)
        if success:
            return jsonify({"status": "success", "ad": ad})
        return jsonify({"status": "error", "message": "Annonce déjà présente."}), 400
    except Exception as e:
        print(f"[Manual Add Error] {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/searches/<path:name>/refresh', methods=['POST'])

@login_required
def trigger_refresh(name):
    """Refreshes a search and returns new ads."""
    user_id = get_current_user_id()
    return refresh_search(name, user_id=user_id)

def refresh_search(name, user_id=1):
    """Internal function to refresh a search."""
    import lbc
    from utils import get_coordinates
    from datetime import datetime
    import json
    
    # Retrieve search config
    active = database.get_active_searches(user_id=user_id)
    search = next((s for s in active if s['name'] == name), None)
    if not search:
        return jsonify({"error": "Recherche introuvable"}), 404

    client = lbc.Client()
    locations = []
    
    # Multi-location support
    if search.get('locations'):
        try:
            stored_locs = json.loads(search['locations'])
            for loc in stored_locs:
                loc_type = loc.get('type')
                loc_val = loc.get('value')
                if not loc_val: continue
                
                if loc_type == 'city':
                    res = get_coordinates(loc_val)
                    if res:
                        lat, lng, zip_code = res
                        locations.append(lbc.City(lat=lat, lng=lng, city=loc_val, radius=int(loc.get('radius', 10))*1000))
                elif loc_type == 'department':
                    try:
                        locations.append(getattr(lbc.Department, loc_val))
                    except AttributeError:
                        pass
                elif loc_type == 'region':
                    try:
                        locations.append(getattr(lbc.Region, loc_val))
                    except AttributeError:
                        pass
        except:
            pass

    # Fallback
    if not locations and search['lat'] and search['lng']:
        locations.append(lbc.City(lat=search['lat'], lng=search['lng'], city=search['city'], radius=int(search['radius'] or 10)*1000))
    
    category = getattr(lbc.Category, search['category']) if search['category'] and search['category'] != '0' else lbc.Category.TOUTES_CATEGORIES
    
    # Multi-platform refresh
    def_platforms = database.get_setting('default_platforms', '{"lbc":true}')
    platforms = json.loads(def_platforms)
    platforms_str = search.get('platforms')
    if platforms_str and platforms_str != '{}':
        try:
            platforms = json.loads(platforms_str)
        except:
            pass
    
    new_count = 0
    all_new_ads = []
    
    # Handle multiple keywords (separated by commas)
    queries = [q.strip() for q in search['query_text'].split(',')] if ',' in search['query_text'] else [search['query_text']]

    is_deep = search.get('deep_search', 0) == 1
    
    for query in queries:
        if not query: continue
        print(f"--- Actualisation {'PROFONDE' if is_deep else ''} [{name}] : {query} ---")
        
        if platforms.get('lbc'):
            try:
                p_min = search.get('price_min')
                p_max = search.get('price_max')
                price_filter = (p_min, p_max) if (p_min is not None or p_max is not None) else None
                
                # If deep, fetch up to 3 pages
                pages_to_fetch = 3 if is_deep else 1
                for page in range(1, pages_to_fetch + 1):
                    if page > 1:
                        delay = random.randint(5, 12)
                        print(f"  [Stealth] Waiting {delay}s before page {page}...")
                        time.sleep(delay)

                    res = client.search(
                        text=query,
                        locations=locations if locations else None,
                        category=category,
                        price=price_filter,
                        limit=50,
                        sort=lbc.Sort.NEWEST,
                        # Pass page if library supports it, otherwise it stays on page 1
                        # Note: some LBC libs use 'page' as an argument
                        page=page 
                    )
                    
                    for ad in res.ads:
                        all_new_ads.append({
                            'id': str(ad.id),
                            'search_name': search['name'],
                            'title': getattr(ad, 'subject', 'Sans titre'),
                            'price': ad.price,
                            'location': getattr(ad.location, 'city_label', 'France'),
                            'date': str(getattr(ad, 'index_date', datetime.now())),
                            'url': ad.url,
                            'image_url': ad.images[0] if ad.images else None,
                            'is_pro': 1 if getattr(ad, 'owner_type', None) == lbc.OwnerType.PRO else 0,
                            'source': 'LBC'
                        })
                    
                    if not res.ads: break # No more results
                    
            except Exception as e:
                print(f"[LBC Refresh Error] {e}")


    # Add other platforms (once per search or per keyword? Let's do once for the main name/first keyword for now to avoid spam)
    other_ads = multi_search.get_multi_platform_results(queries[0] if queries else "", platforms)
    for ad in other_ads:
        ad['search_name'] = search['name']
        all_new_ads.append(ad)

    new_count = 0
    pépites = []
    price_drops = []

    for ad in all_new_ads:
        success, dropped, is_new = database.add_ad(ad, user_id=user_id)
        if success:
            if is_new:
                new_count += 1
            if dropped:
                price_drops.append(ad)
            
            if ad.get('ai_score') and ad['ai_score'] >= 8:
                pépites.append(ad)
            
    database.update_search_last_run(name, user_id=user_id)

    
    # Discord Notifications
    # 1. Use search-specific webhook if exists, fallback to global
    webhook = search.get('discord_webhook') or database.get_setting('discord_webhook')
    
    # Auto-analysis for Discord (check the 3 newest ads if they are not already scored)
    if webhook:
        to_analyze = [ad for ad in all_new_ads if not ad.get('ai_score')][:3]
        if to_analyze:
            # Fallback for context
            ctx = search.get('ai_context')
            if not ctx or not ctx.strip():
                ctx = database.get_setting('default_ai_context', f"Recherche de : {search.get('query_text', 'Produit')}")
            
            # User specific API Key
            user_data = database.get_user_by_id(user_id)
            api_key = user_data.get('google_api_key') if user_data else None

            processed = analyzer.generate_batch_summaries(to_analyze, ctx, api_key=api_key)
            database.update_summaries_in_batch(processed, user_id=user_id)
            # Refresh local data
            for p in processed:
                for ad in all_new_ads:
                    if ad['id'] == p['id']:
                        ad.update(p)
                        if ad.get('ai_score', 0) >= 8 and ad not in pépites:
                            pépites.append(ad)


    if webhook and (pépites or price_drops):
        notifier = disc_bot.DiscordNotifier(webhook)
        for p in pépites:
            content = None
            if p.get('ai_score', 0) >= 9:
                content = "🚨 **ALERTE PÉPITE EXCEPTIONNELLE !** @everyone"
            notifier.send_ad_notification(p, is_pepite=True, content=content)
        for d in price_drops:
            notifier.send_ad_notification(d, price_drop=True)

    return jsonify({
        "status": "success", 
        "message": f"Actualisation terminée : {new_count} nouvelle(s) annonce(s).",
        "new_count": new_count,
        "pépites": pépites,
        "price_drops": price_drops
    })

@app.route('/api/ads/<ad_id>/share-discord', methods=['POST'])
@login_required
def share_to_discord(ad_id):
    """Manually forces a Discord notification for a specific ad."""
    user_id = get_current_user_id()
    user_data = database.get_user_by_id(user_id)
    webhook = user_data.get('discord_webhook') if user_data else None or database.get_setting('discord_webhook')
    
    if not webhook:
        return jsonify({"error": "Webhook Discord non configuré"}), 400
        
    ads = database.get_ads_by_ids([ad_id], user_id=user_id)

    if not ads:
        return jsonify({"error": "Annonce non trouvée"}), 404
        
    ad = ads[0]
    notifier = disc_bot.DiscordNotifier(webhook)
    
    # We use is_pepite if score is high, or just general if forced
    is_pep = ad.get('ai_score', 0) >= 8
    if notifier.send_ad_notification(ad, is_pepite=is_pep):
        return jsonify({"status": "success", "message": "Notification envoyée !"})
    return jsonify({"error": "Échec de l'envoi"}), 500

@app.route('/api/ads/<ad_id>/history')
def get_ad_history(ad_id):
    """Returns price history for an ad."""
    return jsonify(database.get_price_history(ad_id))

@app.route('/api/ads/<ad_id>/hide', methods=['POST'])
@login_required
def hide_ad_route(ad_id):
    """Archives an ad (soft delete)."""
    user_id = get_current_user_id()
    if database.hide_ad(ad_id, user_id=user_id):
        return jsonify({"status": "success", "message": "Annonce archivée."})
    return jsonify({"error": "Erreur lors de l'archivage."}), 500


@app.route('/api/searches/auto-refresh', methods=['POST'])
def trigger_auto_refresh():
    """Background-friendly endpoint to refresh all 'auto' searches."""
    searches = database.get_active_searches()
    auto_searches = [s for s in searches if s.get('refresh_mode') == 'auto']
    
    # In a real app, this would be a task queue (Celery). 
    # Here we perform it sequentially (simple version).
    results = []
    for s in auto_searches:
        # Check if interval has passed since last_run (simplified: always run for demo)
        refresh_search(s['name'])
        results.append(s['name'])
        
    return jsonify({"status": "success", "refreshed": results})

def send_daily_digest():
    """Compiles and sends a daily digest of the best 'pépites'."""
    webhook = database.get_setting('discord_webhook')
    if not webhook: return
    
    last_digest = database.get_setting('last_daily_digest')
    now = datetime.now()
    
    # Send at 8:00 AM once a day
    if now.hour == 8 and (not last_digest or now.date() > datetime.fromisoformat(last_digest).date()):
        print("☀️ Generating Daily Digest for Discord...")
        all_ads = database.get_all_ads()
        # Last 24h pepites
        yesterday = now - timedelta(days=1)
        pepites = [a for a in all_ads if (a.get('ai_score') or 0) >= 8 and a.get('date', '') > yesterday.isoformat()]
        pepites.sort(key=lambda x: x.get('ai_score', 0), reverse=True)
        top_5 = pepites[:5]
        
        if top_5:
            notifier = disc_bot.DiscordNotifier(webhook)
            embeds = []
            for ad in top_5:
                embeds.append({
                    "title": f"🏆 {ad['title']}",
                    "url": ad['url'],
                    "description": f"Score: **{ad.get('ai_score')}/10** - {ad.get('price')}€\n{ad.get('ai_summary', '')[:100]}...",
                    "color": 0xF59E0B
                })
            
            payload = {
                "content": "📅 **VOTRE RÉCAPITULATIF QUOTIDIEN**\nVoici les 5 meilleures pépites trouvées ces dernières 24h :",
                "embeds": embeds[:10] # Discord limit
            }
            try:
                import requests
                requests.post(webhook, json=payload, timeout=10)
                database.set_setting('last_daily_digest', now.isoformat())
                print("✅ Daily Digest envoyé.")
            except Exception as e:
                print(f"❌ Erreur Digest : {e}")

def auto_refresh_loop():
    """Background loop to refresh searches and send digests across all users."""
    print("Starting multi-user auto-refresh background thread...")
    while True:
        try:
            # For daily digest, we'd need to iterate over users
            # For now, let's focus on auto-refresh
            with app.app_context():
                searches = database.get_active_searches() # Get ALL active searches from ALL users
                for s in searches:
                    if s.get('refresh_mode') == 'auto':
                        uid = s.get('user_id', 1)
                        name = s.get('name')
                        interval = s.get('refresh_interval', 60)
                        last_run_str = s.get('last_run')
                        
                        should_run = False
                        if not last_run_str:
                            should_run = True
                        else:
                            try:
                                last_run = datetime.fromisoformat(last_run_str)
                                if datetime.now() > last_run + timedelta(minutes=interval):
                                    should_run = True
                            except:
                                should_run = True
                        
                        if should_run:
                            print(f"Periodic auto-refresh for user {uid}, search: {name}")
                            try:
                                refresh_search(name, user_id=uid)
                            except Exception as e:
                                print(f"Error refreshing {name} (UID {uid}): {e}")
        except Exception as e:
            print(f"Background refresh error: {e}")
        time.sleep(60)


if __name__ == '__main__':
    database.initialize_db()
    # Start background thread
    threading.Thread(target=auto_refresh_loop, daemon=True).start()
    # host='0.0.0.0' is required for Docker
    port = int(os.getenv('PORT', 5000))
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=False)
