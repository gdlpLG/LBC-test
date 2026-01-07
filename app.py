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

@app.route('/api/ads')
def get_ads():
    """API endpoint to get all ads."""
    ads = database.get_all_ads()
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
    # We take a maximum of 15 ads per batch to stay safe with token length and single call logic
    batch = ads_to_summarize[:15]
    
    summaries = analyzer.generate_batch_summaries(batch)
    if summaries:
        database.update_summaries_in_batch(summaries)
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
        "is_active": 1
    }
    
    if database.save_search(search_data):
        return jsonify({"status": "success", "search": search_data})
    return jsonify({"status": "error"}), 500

@app.route('/api/searches/<name>', methods=['DELETE'])
def remove_search(name):
    if database.delete_search(name):
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 500

if __name__ == '__main__':
    database.initialize_db()
    app.run(debug=True, port=5000)
