import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

class Config:
    # Google Sheets настройки
    GOOGLE_SHEETS_CREDENTIALS = os.getenv('GOOGLE_SHEETS_CREDENTIALS', 'credentials.json')
    SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
    
    # Настройки геокодирования
    NOMINATIM_USER_AGENT = os.getenv('NOMINATIM_USER_AGENT', 'GeoPhotoTagger/1.0')
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', '1'))
    
    # Пути к директориям
    LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cache')
    
    # Настройки логирования
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Настройки обработки фото
    SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.JPG', '.JPEG']
    CREATE_BACKUP = os.getenv('CREATE_BACKUP', 'True').lower() == 'true'
    
    # Настройки многопоточности
    MAX_WORKERS = int(os.getenv('MAX_WORKERS', '4'))

    @classmethod
    def ensure_directories(cls):
        """Создание необходимых директорий"""
        os.makedirs(cls.LOG_DIR, exist_ok=True)
        os.makedirs(cls.CACHE_DIR, exist_ok=True) 