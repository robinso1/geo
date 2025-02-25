import os
import shutil
import logging
from typing import Dict, Optional, List
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

from .config import Config

class PhotoProcessor:
    def __init__(self):
        self.config = Config()
        self.config.ensure_directories()
        self._setup_logging()
        
    def _setup_logging(self):
        """Настройка логирования"""
        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler(os.path.join(Config.LOG_DIR, 'photo_processor.log'))
        handler.setFormatter(logging.Formatter(Config.LOG_FORMAT))
        self.logger.addHandler(handler)
        self.logger.setLevel(Config.LOG_LEVEL)
        
    def process_photos(self, photos_data: List[Dict]):
        """Обработка списка фотографий"""
        with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
            list(tqdm(
                executor.map(self.process_single_photo, photos_data),
                total=len(photos_data),
                desc="Обработка фотографий"
            ))
            
    def process_single_photo(self, photo_data: Dict):
        """Обработка одной фотографии"""
        try:
            path = photo_data.get('path')
            if not path or not os.path.exists(path):
                self.logger.error(f"Путь не существует: {path}")
                return
                
            if os.path.isdir(path):
                self._process_directory(path, photo_data)
            else:
                self._process_file(path, photo_data)
                
        except Exception as e:
            self.logger.error(f"Ошибка при обработке {photo_data.get('path')}: {str(e)}")
            
    def _process_directory(self, directory: str, photo_data: Dict):
        """Обработка директории с фотографиями"""
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in Config.SUPPORTED_FORMATS):
                    file_path = os.path.join(root, file)
                    self._process_file(file_path, photo_data)
                    
    def _process_file(self, file_path: str, photo_data: Dict):
        """Обработка отдельного файла"""
        try:
            if Config.CREATE_BACKUP:
                self._create_backup(file_path)
                
            with Image.open(file_path) as img:
                # Добавление GPS данных
                if 'latitude' in photo_data and 'longitude' in photo_data:
                    self._add_gps_info(img, photo_data)
                
                # Добавление других метаданных
                self._add_metadata(img, photo_data)
                
                # Сохранение изменений
                img.save(file_path)
                
            self.logger.info(f"Успешно обработан файл: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке файла {file_path}: {str(e)}")
            
    def _create_backup(self, file_path: str):
        """Создание резервной копии файла"""
        backup_path = f"{file_path}.backup"
        if not os.path.exists(backup_path):
            shutil.copy2(file_path, backup_path)
            
    def _add_gps_info(self, img: Image.Image, photo_data: Dict):
        """Добавление GPS информации в EXIF"""
        # TODO: Реализовать добавление GPS данных
        pass
        
    def _add_metadata(self, img: Image.Image, photo_data: Dict):
        """Добавление дополнительных метаданных"""
        # TODO: Реализовать добавление метаданных
        pass 