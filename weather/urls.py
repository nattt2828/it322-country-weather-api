from django.urls import path
from .views import CountryWeatherView

urlpatterns = [
    path('country-weather-summary/', CountryWeatherView.as_view(),
         name='country-weather-summary'),
]