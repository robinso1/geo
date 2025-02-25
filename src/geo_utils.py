import os
import json
import logging
from typing import Dict, Optional, Tuple
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time

from .config import Config

class GeoUtils:
    def __init__(self):
        self.config = Config()
        self._setup_logging()
        self.geocoder = Nominatim(user_agent=Config.NOMINATIM_USER_AGENT)
        self._load_cache()
        
    def _setup_logging(self):
        """Настройка логирования"""
        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler(os.path.join(Config.LOG_DIR, 'geo_utils.log'))
        handler.setFormatter(logging.Formatter(Config.LOG_FORMAT))
        self.logger.addHandler(handler)
        self.logger.setLevel(Config.LOG_LEVEL)
        
    def _load_cache(self):
        """Загрузка кэша геоданных"""
        self.cache_file = os.path.join(Config.CACHE_DIR, 'geo_cache.json')
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            else:
                self.cache = {}
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке кэша: {str(e)}")
            self.cache = {}
            
    def _save_cache(self):
        """Сохранение кэша геоданных"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении кэша: {str(e)}")
            
    def get_location_info(self, lat: float, lon: float) -> Optional[Dict]:
        """Получение информации о местоположении по координатам"""
        cache_key = f"{lat},{lon}"
        
        # Проверяем кэш
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        # Делаем запрос к геокодеру с повторными попытками
        for attempt in range(Config.MAX_RETRIES):
            try:
                location = self.geocoder.reverse((lat, lon))
                if location:
                    result = {
                        'address': location.address,
                        'raw': location.raw,
                        'city': location.raw.get('address', {}).get('city'),
                        'country': location.raw.get('address', {}).get('country'),
                        'postcode': location.raw.get('address', {}).get('postcode'),
                    }
                    
                    # Сохраняем в кэш
                    self.cache[cache_key] = result
                    self._save_cache()
                    
                    return result
                    
            except GeocoderTimedOut:
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)
                continue
            except Exception as e:
                self.logger.error(f"Ошибка при получении геоданных для {lat},{lon}: {str(e)}")
                break
                
        return None
        
    def convert_coordinates(self, lat: float, lon: float) -> Tuple[Dict, Dict]:
        """Конвертация координат в формат для EXIF"""
        def decimal_to_dms(decimal):
            degrees = int(decimal)
            minutes = int((decimal - degrees) * 60)
            seconds = ((decimal - degrees) * 60 - minutes) * 60
            return (degrees, 1), (minutes, 1), (int(seconds * 100), 100)
            
        lat_ref = 'N' if lat >= 0 else 'S'
        lon_ref = 'E' if lon >= 0 else 'W'
        
        lat_dms = decimal_to_dms(abs(lat))
        lon_dms = decimal_to_dms(abs(lon))
        
        return {
            'GPSLatitudeRef': lat_ref,
            'GPSLatitude': lat_dms,
            'GPSLongitudeRef': lon_ref,
            'GPSLongitude': lon_dms
        }, {
            'latitude': abs(lat),
            'longitude': abs(lon),
            'latitude_ref': lat_ref,
            'longitude_ref': lon_ref
        } 