import requests
from typing import Optional, Tuple

def get_coordinates(city_name: str) -> Optional[Tuple[float, float, str]]:
    """
    Get (latitude, longitude, zip_code) for a city name using the Govt API.
    Returns None if not found.
    """
    try:
        url = f"https://api-adresse.data.gouv.fr/search/?q={city_name}&type=municipality&limit=1"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['features']:
                feature = data['features'][0]
                lng, lat = feature['geometry']['coordinates']
                zip_code = feature['properties']['postcode']
                return lat, lng, zip_code
    except Exception as e:
        print(f"Error resolving coordinates for {city_name}: {e}")
    return None
