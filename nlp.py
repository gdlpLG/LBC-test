'''
Natural Language Processing module to parse user sentences.
'''
import re
from typing import Dict, Any, Optional, Tuple

def parse_price(text: str) -> Tuple[Optional[int], Optional[int]]:
    """Extracts min and max price from text using regular expressions."""
    price_min, price_max = None, None

    # Case 1: "entre 100 et 200 euros", "de 100k a 200k"
    match = re.search(r"(?:entre|de)\s+(\d+[\s']?\d*)\s*(k)?(?:euros|€)?\s*(?:et|à)\s+(\d+[\s']?\d*)\s*(k)?(?:euros|€)?", text, re.IGNORECASE)
    if match:
        price_min = int(match.group(1).replace("'", "").replace(" ", ""))
        if match.group(2) and 'k' in match.group(2).lower(): price_min *= 1000
        
        price_max = int(match.group(3).replace("'", "").replace(" ", ""))
        if match.group(4) and 'k' in match.group(4).lower(): price_max *= 1000
        return price_min, price_max

    # Case 2: "moins de 300000 euros", "budget max 300k"
    match = re.search(r"(?:moins de|budget max(?:imum)? de?|jusqu'à|pas plus de)\s+(\d+[\s']?\d*)\s*(k)?(?:euros|€)?", text, re.IGNORECASE)
    if match:
        price_max = int(match.group(1).replace("'", "").replace(" ", ""))
        if match.group(2) and 'k' in match.group(2).lower(): price_max *= 1000
        return None, price_max

    # Case 3: "plus de 100 euros", "à partir de 100k"
    match = re.search(r"(?:plus de|à partir de|minimum de?|min de)\s+(\d+[\s']?\d*)\s*(k)?(?:euros|€)?", text, re.IGNORECASE)
    if match:
        price_min = int(match.group(1).replace("'", "").replace(" ", ""))
        if match.group(2) and 'k' in match.group(2).lower(): price_min *= 1000
        return price_min, None

    return price_min, price_max

def parse_location(text: str) -> Optional[str]:
    """Extracts location from text (e.g., 'à Bordeaux', 'sur Paris', 'dans le secteur de Lyon')."""
    # Expanded list of indicators and support for lowercase city names
    match = re.search(r"\s(?:à|sur|vers|près de|dans la ville de|dans|secteur|proche|aux alentours de)\s+([a-zA-Z\xC0-\xFF][a-zA-Z\s\xC0-\xFF'-]+?)(?:,|$|\s+pour|\s+avec|\s+budget|\s+moins|\+|plus)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip().capitalize()
    return None

def parse_radius(text: str) -> int:
    """Extracts radius in km from text (e.g., '+20km', 'rayon de 10'). Defaults to 10."""
    match = re.search(r"(?:\+|rayon de|à|autour de)?\s*(\d+)\s*(?:km|kilomètres)", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 10 # Default LBC radius

def clean_search_text(text: str, location: Optional[str]) -> str:
    """Removes location, price and radius phrases to get the core search query."""
    core_text = text
    if location:
        core_text = re.sub(r"\s(?:à|sur|vers|près de|dans la ville de|dans|secteur|proche|aux alentours de)\s+" + re.escape(location), "", core_text, flags=re.IGNORECASE)
    
    # Remove radius phrases
    core_text = re.sub(r"(?:\+|rayon de)?\s*\d+\s*(?:km|kilomètres)", "", core_text, flags=re.IGNORECASE)
    
    # Remove all price-related phrases
    core_text = re.sub(r"(entre|de|moins de|budget max(?:imum)? de?|jusqu'à|pas plus de|à partir de|minimum de?|min de)\s+(\d+[\s']?\d*)\s*(k)?(?:euros|€)?(?:\s*(et|à)\s*\d+[\s']?\d*\s*(k)?(?:euros|€)?)?", "", core_text, flags=re.IGNORECASE)
    
    # Remove common conversational filler words
    core_text = re.sub(r"je cherche|je recherche|cherche|je voudrais|j'aimerais trouver|trouve-moi|un|une|des", "", core_text, flags=re.IGNORECASE)
    
    # Remove punctuation and extra spaces
    core_text = re.sub(r"[.,;:!?-]", " ", core_text)
    return ' '.join(core_text.split()).strip()

def parse_sentence(user_input: str) -> Dict[str, Any]:
    """
    Parses a natural language sentence to extract structured search criteria.
    """
    price_min, price_max = parse_price(user_input)
    location = parse_location(user_input)
    radius = parse_radius(user_input)
    search_text = clean_search_text(user_input, location)

    return {
        "text": search_text,
        "location": location,
        "radius": radius,
        "price_min": price_min,
        "price_max": price_max
    }
