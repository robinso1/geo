import os
import shutil
import logging
from typing import Dict, Optional, List
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import piexif
from pathlib import Path
import re

from .config import Config
from .geo_utils import GeoUtils

class PhotoProcessor:
    def __init__(self):
        self.config = Config()
        self.config.ensure_directories()
        self._setup_logging()
        self.geo_utils = GeoUtils()
        self.success_count = 0
        self.error_count = 0
        
    def _setup_logging(self):
        """Настройка логирования"""
        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler(os.path.join(Config.LOG_DIR, 'photo_processor.log'))
        handler.setFormatter(logging.Formatter(Config.LOG_FORMAT))
        self.logger.addHandler(handler)
        self.logger.setLevel(Config.LOG_LEVEL)
        
    def validate_data(self, photo_data: Dict) -> bool:
        """Валидация обязательных полей"""
        # Проверка обязательных полей
        required_fields = ['Путь', 'Широта', 'Долгота']
        for field in required_fields:
            if field not in photo_data or not photo_data[field]:
                self.logger.error(f"Отсутствует обязательное поле: {field}")
                return False
                
        # Валидация координат
        try:
            lat = float(photo_data['Широта'])
            lon = float(photo_data['Долгота'])
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                self.logger.error(f"Некорректные координаты: {lat}, {lon}")
                return False
        except ValueError:
            self.logger.error("Некорректный формат координат")
            return False
            
        # Валидация email если есть
        if 'Email' in photo_data and photo_data['Email']:
            email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            if not email_pattern.match(photo_data['Email']):
                self.logger.warning(f"Некорректный формат email: {photo_data['Email']}")
                
        # Валидация рейтинга если есть
        if 'Рейтинг' in photo_data and photo_data['Рейтинг']:
            try:
                rating = int(photo_data['Рейтинг'])
                if not (0 <= rating <= 5):
                    self.logger.warning(f"Рейтинг вне диапазона 0-5: {rating}")
            except ValueError:
                self.logger.warning(f"Некорректный формат рейтинга: {photo_data['Рейтинг']}")
                
        return True
        
    def process_photos(self, photos_data: List[Dict]):
        """Обработка списка фотографий"""
        self.success_count = 0
        self.error_count = 0
        
        # Фильтруем данные с валидными полями
        valid_photos = [photo for photo in photos_data if self.validate_data(photo)]
        
        if not valid_photos:
            self.logger.error("Нет валидных данных для обработки")
            return
            
        with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
            list(tqdm(
                executor.map(self.process_single_photo, valid_photos),
                total=len(valid_photos),
                desc="Обработка фотографий"
            ))
            
        self.logger.info(f"Обработка завершена. Успешно: {self.success_count}, Ошибок: {self.error_count}")
            
    def process_single_photo(self, photo_data: Dict):
        """Обработка одной фотографии"""
        try:
            path = photo_data.get('Путь')
            if not path:
                self.logger.error("Путь не указан")
                self.error_count += 1
                return
                
            # Преобразуем путь в объект Path для кроссплатформенной совместимости
            # Поддерживаем как абсолютные, так и относительные пути
            path = Path(path)
            
            # Проверяем существование пути
            if not path.exists():
                self.logger.error(f"Путь не существует: {path}")
                self.error_count += 1
                return
                
            # Проверяем права доступа
            try:
                if path.is_file():
                    with open(path, 'rb') as f:
                        pass
                elif path.is_dir():
                    # Проверяем доступ к директории
                    list(path.iterdir())
            except PermissionError:
                self.logger.error(f"Нет прав доступа к пути: {path}")
                self.error_count += 1
                return
                
            # Обрабатываем директорию или файл
            if path.is_dir():
                self._process_directory(path, photo_data)
            else:
                if path.suffix.lower() in ['.jpg', '.jpeg']:
                    self._process_file(path, photo_data)
                else:
                    self.logger.error(f"Неподдерживаемый формат файла: {path}")
                    self.error_count += 1
                
        except Exception as e:
            self.logger.error(f"Ошибка при обработке {photo_data.get('Путь')}: {str(e)}")
            self.error_count += 1
            
    def _process_directory(self, directory: Path, photo_data: Dict):
        """Обработка директории с фотографиями"""
        try:
            # Получаем список всех файлов в директории и поддиректориях
            files = list(directory.rglob("*"))
            photo_files = [f for f in files if f.suffix.lower() in ['.jpg', '.jpeg']]
            
            if not photo_files:
                self.logger.warning(f"В директории {directory} нет поддерживаемых файлов")
                return
                
            self.logger.info(f"Найдено {len(photo_files)} файлов для обработки в директории {directory}")
            
            # Используем tqdm для отображения прогресса
            for file_path in tqdm(photo_files, desc=f"Обработка файлов в {directory.name}"):
                try:
                    self.logger.info(f"Обработка файла из директории: {file_path}")
                    self._process_file(file_path, photo_data)
                except Exception as e:
                    self.logger.error(f"Ошибка при обработке файла {file_path}: {str(e)}")
                    self.error_count += 1
                
        except Exception as e:
            self.logger.error(f"Ошибка при обработке директории {directory}: {str(e)}")
            self.error_count += 1
                    
    def _process_file(self, file_path: Path, photo_data: Dict):
        """Обработка отдельного файла"""
        try:
            # Создаем резервную копию если нужно
            if Config.CREATE_BACKUP:
                self._create_backup(file_path)
                
            # Проверяем наличие координат
            try:
                lat = float(photo_data['Широта'])
                lon = float(photo_data['Долгота'])
                
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    self.logger.error(f"Некорректные координаты для файла {file_path}: {lat}, {lon}")
                    self.error_count += 1
                    return
            except ValueError:
                self.logger.error(f"Некорректный формат координат для файла {file_path}")
                self.error_count += 1
                return
                
            try:
                # Получаем EXIF данные
                exif_dict = piexif.load(str(file_path))
            except Exception as e:
                self.logger.error(f"Ошибка при чтении EXIF данных файла {file_path}: {str(e)}")
                # Создаем пустой EXIF словарь
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
                
            # Убеждаемся, что секция GPS существует
            if 'GPS' not in exif_dict:
                exif_dict['GPS'] = {}
                
            # Конвертируем координаты в формат EXIF
            gps_data, _ = self.geo_utils.convert_coordinates(lat, lon)
            
            # Добавляем GPS данные в EXIF
            for key, value in gps_data.items():
                if key == 'GPSLatitudeRef':
                    exif_dict['GPS'][piexif.GPSIFD.GPSLatitudeRef] = value.encode('utf-8')
                elif key == 'GPSLatitude':
                    exif_dict['GPS'][piexif.GPSIFD.GPSLatitude] = value
                elif key == 'GPSLongitudeRef':
                    exif_dict['GPS'][piexif.GPSIFD.GPSLongitudeRef] = value.encode('utf-8')
                elif key == 'GPSLongitude':
                    exif_dict['GPS'][piexif.GPSIFD.GPSLongitude] = value
                    
            # Добавляем дополнительные метаданные
            self._add_metadata(exif_dict, photo_data)
            
            try:
                # Сохраняем изменения
                exif_bytes = piexif.dump(exif_dict)
                piexif.insert(exif_bytes, str(file_path))
                
                self.logger.info(f"Успешно обработан файл: {file_path}")
                self.success_count += 1
            except Exception as e:
                self.logger.error(f"Ошибка при сохранении EXIF данных в файл {file_path}: {str(e)}")
                self.error_count += 1
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке файла {file_path}: {str(e)}")
            self.error_count += 1
            
    def _create_backup(self, file_path: Path):
        """Создание резервной копии файла"""
        backup_path = file_path.with_suffix(file_path.suffix + '.backup')
        if not backup_path.exists():
            shutil.copy2(file_path, backup_path)
            
    def _add_metadata(self, exif_dict: Dict, photo_data: Dict):
        """Добавление дополнительных метаданных"""
        try:
            # Убеждаемся, что все необходимые секции существуют
            if '0th' not in exif_dict:
                exif_dict['0th'] = {}
            if 'Exif' not in exif_dict:
                exif_dict['Exif'] = {}
                
            # Рейтинг
            if 'Рейтинг' in photo_data and photo_data['Рейтинг']:
                try:
                    rating = int(photo_data['Рейтинг'])
                    if 0 <= rating <= 5:
                        exif_dict['Exif'][piexif.ExifIFD.Rating] = rating
                    else:
                        self.logger.warning(f"Рейтинг вне диапазона 0-5: {rating}")
                except ValueError:
                    self.logger.warning(f"Некорректный формат рейтинга: {photo_data['Рейтинг']}")
                
            # Категории и теги
            tags = []
            if 'Категория' in photo_data and photo_data['Категория']:
                tags.append(photo_data['Категория'])
            if 'Подкатегория' in photo_data and photo_data['Подкатегория']:
                tags.append(photo_data['Подкатегория'])
            if 'Ключевые слова' in photo_data and photo_data['Ключевые слова']:
                tags.extend([tag.strip() for tag in photo_data['Ключевые слова'].split(',')])
            
            if tags:
                try:
                    exif_dict['0th'][piexif.ImageIFD.XPKeywords] = '; '.join(tags).encode('utf-8')
                except Exception as e:
                    self.logger.warning(f"Ошибка при добавлении тегов: {str(e)}")
                
            # Описание
            if 'Описание' in photo_data and photo_data['Описание']:
                try:
                    exif_dict['0th'][piexif.ImageIFD.ImageDescription] = photo_data['Описание'].encode('utf-8')
                except Exception as e:
                    self.logger.warning(f"Ошибка при добавлении описания: {str(e)}")
                
            # Контактная информация
            contact_info = []
            if 'Контакты' in photo_data and photo_data['Контакты']:
                contact_info.append(photo_data['Контакты'])
            if 'Email' in photo_data and photo_data['Email']:
                contact_info.append(f"Email: {photo_data['Email']}")
            if 'URL' in photo_data and photo_data['URL']:
                contact_info.append(f"URL: {photo_data['URL']}")
                
            if contact_info:
                try:
                    exif_dict['0th'][piexif.ImageIFD.Artist] = '\n'.join(contact_info).encode('utf-8')
                except Exception as e:
                    self.logger.warning(f"Ошибка при добавлении контактной информации: {str(e)}")
                
            # Географическая информация
            location_info = []
            if 'Город' in photo_data and photo_data['Город']:
                location_info.append(photo_data['Город'])
            if 'Страна' in photo_data and photo_data['Страна']:
                location_info.append(photo_data['Страна'])
            if 'Индекс' in photo_data and photo_data['Индекс']:
                location_info.append(photo_data['Индекс'])
            if 'Адрес' in photo_data and photo_data['Адрес']:
                location_info.append(photo_data['Адрес'])
                
            if location_info:
                try:
                    exif_dict['0th'][piexif.ImageIFD.DocumentName] = ', '.join(location_info).encode('utf-8')
                except Exception as e:
                    self.logger.warning(f"Ошибка при добавлении географической информации: {str(e)}")
                
            # Подписи
            captions = []
            if 'Подпись' in photo_data and photo_data['Подпись']:
                captions.append(photo_data['Подпись'])
            if 'Текст подписи' in photo_data and photo_data['Текст подписи']:
                captions.append(photo_data['Текст подписи'])
                
            if captions:
                try:
                    exif_dict['0th'][piexif.ImageIFD.XPTitle] = '\n'.join(captions).encode('utf-8')
                except Exception as e:
                    self.logger.warning(f"Ошибка при добавлении подписей: {str(e)}")
                
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении метаданных: {str(e)}") 