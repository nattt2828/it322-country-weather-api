import requests
from django.conf import settings


# WMO weather code descriptions (Open-Meteo uses these)
WMO_CODES = {
    0: 'Clear Sky', 1: 'Mainly Clear', 2: 'Partly Cloudy',
    3: 'Overcast', 45: 'Fog', 51: 'Light Drizzle',
    61: 'Slight Rain', 63: 'Moderate Rain', 65: 'Heavy Rain',
    80: 'Rain Showers', 95: 'Thunderstorm',
}


def get_country(name):
    """Call RestCountries API and return cleaned country data."""
    url = f"{settings.RESTCOUNTRIES_URL}/name/{name}"
    params = {'fields': 'name,capital,latlng,population,region,currencies,languages,flags'}
    try:
        r = requests.get(url, params=params, timeout=settings.EXTERNAL_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except requests.exceptions.Timeout:
        raise ConnectionError('RestCountries API timed out.')
    except requests.exceptions.ConnectionError:
        raise ConnectionError('Cannot reach RestCountries API.')
    except requests.exceptions.HTTPError:
        raise ValueError(f"Country '{name}' not found.")

    if not isinstance(data, list) or not data:
        raise ValueError(f"Country '{name}' not found.")

    raw = data[0]
    capital = raw.get('capital', [])
    latlng  = raw.get('latlng', [None, None])

    # Flatten currencies: {"PHP": {"name": "Philippine peso"}} -> "PHP - Philippine peso"
    currencies = [
        f"{code} - {info.get('name', '')}"
        for code, info in raw.get('currencies', {}).items()
    ]

    # Languages: {"fil": "Filipino"} -> ["Filipino"]
    languages = list(raw.get('languages', {}).values())

    return {
        'name':       raw['name']['common'],
        'capital':    capital[0] if capital else None,
        'latitude':   latlng[0] if len(latlng) > 0 else None,
        'longitude':  latlng[1] if len(latlng) > 1 else None,
        'population': raw.get('population'),
        'region':     raw.get('region'),
        'currencies': currencies,
        'languages':  languages,
        'flag_url':   raw.get('flags', {}).get('png'),
    }


def get_weather(lat, lon):
    """Call Open-Meteo API and return current weather data."""
    url = f"{settings.OPEN_METEO_URL}/forecast"
    params = {
        'latitude':   lat,
        'longitude':  lon,
        'current':    'temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code,is_day',
        'wind_speed_unit': 'kmh',
        'timezone':   'auto',
    }
    try:
        r = requests.get(url, params=params, timeout=settings.EXTERNAL_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except requests.exceptions.Timeout:
        raise ConnectionError('Open-Meteo API timed out.')
    except requests.exceptions.ConnectionError:
        raise ConnectionError('Cannot reach Open-Meteo API.')

    current = data.get('current', {})
    code = current.get('weather_code', 0)

    return {
        'temperature_celsius': current.get('temperature_2m'),
        'feels_like_celsius':  current.get('apparent_temperature'),
        'humidity_percent':    current.get('relative_humidity_2m'),
        'wind_speed_kmh':      current.get('wind_speed_10m'),
        'weather_condition':   WMO_CODES.get(code, 'Unknown'),
        'is_day':              bool(current.get('is_day', 1)),
    }
