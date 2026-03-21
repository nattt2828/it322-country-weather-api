from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .services import get_country, get_weather


class CountryWeatherView(APIView):
    """
    GET /api/v1/country-weather-summary/
    Merges RestCountries + Open-Meteo into one unified response.
    """

    @swagger_auto_schema(
        operation_summary='Get unified country + weather data',
        manual_parameters=[
            openapi.Parameter(
                'country', openapi.IN_QUERY,
                description='Country name (e.g. Philippines, Japan)',
                type=openapi.TYPE_STRING, required=True
            )
        ],
        responses={
            200: openapi.Response('Success', examples={'application/json': {
                'country': 'Philippines', 'capital': 'Manila',
                'temperature_celsius': 31.4, 'weather_condition': 'Partly Cloudy',
                'humidity_percent': 78, 'is_day': True,
            }}),
            400: openapi.Response('Bad Request'),
            404: openapi.Response('Country not found'),
            502: openapi.Response('External API failure'),
        }
    )
    def get(self, request):
        # 1. Validate input
        country_name = request.query_params.get('country', '').strip()
        if not country_name:
            return Response(
                {'error': True, 'status_code': 400,
                 'message': "The 'country' query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if len(country_name) < 2:
            return Response(
                {'error': True, 'status_code': 400,
                 'message': "Country name must be at least 2 characters."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Fetch country data (API 1)
        try:
            country = get_country(country_name)
        except ValueError as e:
            return Response(
                {'error': True, 'status_code': 404, 'message': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except ConnectionError as e:
            return Response(
                {'error': True, 'status_code': 502, 'message': str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )

        # 3. Fetch weather data (API 2) using country's coordinates
        lat = country.get('latitude')
        lon = country.get('longitude')
        if lat is None or lon is None:
            return Response(
                {'error': True, 'status_code': 404,
                 'message': f"No coordinates found for '{country_name}'."},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            weather = get_weather(lat, lon)
        except ConnectionError as e:
            return Response(
                {'error': True, 'status_code': 502, 'message': str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )

        # 4. Transform + merge both API responses into one clean payload
        # (lat/lon are intentionally excluded from the response)
        result = {
            'country':             country['name'],
            'capital':             country['capital'],
            'population':          country['population'],
            'region':              country['region'],
            'currencies':          country['currencies'],
            'languages':           country['languages'],
            'flag_url':            country['flag_url'],
            'temperature_celsius': weather['temperature_celsius'],
            'feels_like_celsius':  weather['feels_like_celsius'],
            'humidity_percent':    weather['humidity_percent'],
            'wind_speed_kmh':      weather['wind_speed_kmh'],
            'weather_condition':   weather['weather_condition'],
            'is_day':              weather['is_day'],
            'sources': [
                'https://restcountries.com/v3.1',
                'https://api.open-meteo.com/v1',
            ],
        }
        return Response(result, status=status.HTTP_200_OK)
