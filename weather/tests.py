from unittest.mock import patch, MagicMock
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

URL = '/api/v1/country-weather-summary/'

MOCK_COUNTRY = {
    'name': 'Philippines', 'capital': 'Manila',
    'latitude': 13.0, 'longitude': 122.0,
    'population': 109000000, 'region': 'Asia',
    'currencies': ['PHP - Philippine peso'],
    'languages': ['Filipino', 'English'],
    'flag_url': 'https://flagcdn.com/w320/ph.png',
}

MOCK_WEATHER = {
    'temperature_celsius': 31.4, 'feels_like_celsius': 37.0,
    'humidity_percent': 78, 'wind_speed_kmh': 14.0,
    'weather_condition': 'Partly Cloudy', 'is_day': True,
}


class CountryWeatherTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    # --- Happy path ---
    @patch('weather.views.get_weather', return_value=MOCK_WEATHER)
    @patch('weather.views.get_country', return_value=MOCK_COUNTRY)
    def test_200_success(self, mc, mw):
        r = self.client.get(URL, {'country': 'Philippines'})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['country'], 'Philippines')
        self.assertEqual(r.data['capital'], 'Manila')
        self.assertEqual(r.data['temperature_celsius'], 31.4)
        self.assertEqual(r.data['weather_condition'], 'Partly Cloudy')
        self.assertIn('sources', r.data)

    # --- 400 errors ---
    def test_400_missing_country(self):
        r = self.client.get(URL)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(r.data['error'])

    def test_400_single_char(self):
        r = self.client.get(URL, {'country': 'X'})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    # --- 404 errors ---
    @patch('weather.views.get_country', side_effect=ValueError("Country 'Narnia' not found."))
    def test_404_unknown_country(self, mc):
        r = self.client.get(URL, {'country': 'Narnia'})
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('not found', r.data['message'].lower())

    # --- 502 errors ---
    @patch('weather.views.get_country', side_effect=ConnectionError('API timed out.'))
    def test_502_country_api_fail(self, mc):
        r = self.client.get(URL, {'country': 'Philippines'})
        self.assertEqual(r.status_code, status.HTTP_502_BAD_GATEWAY)

    @patch('weather.views.get_weather', side_effect=ConnectionError('API timed out.'))
    @patch('weather.views.get_country', return_value=MOCK_COUNTRY)
    def test_502_weather_api_fail(self, mc, mw):
        r = self.client.get(URL, {'country': 'Philippines'})
        self.assertEqual(r.status_code, status.HTTP_502_BAD_GATEWAY)

    # --- Response structure ---
    @patch('weather.views.get_weather', return_value=MOCK_WEATHER)
    @patch('weather.views.get_country', return_value=MOCK_COUNTRY)
    def test_no_lat_lon_in_response(self, mc, mw):
        r = self.client.get(URL, {'country': 'Philippines'})
        self.assertNotIn('latitude', r.data)
        self.assertNotIn('longitude', r.data)