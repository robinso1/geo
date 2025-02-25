import os
import logging
from typing import List, Dict
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.oauth2 import service_account

from .config import Config

class GoogleSheetsClient:
    # Области доступа для Google Sheets API
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    
    def __init__(self):
        self.config = Config()
        self._setup_logging()
        self.service = self._get_sheets_service()
        
    def _setup_logging(self):
        """Настройка логирования"""
        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler(os.path.join(Config.LOG_DIR, 'google_sheets.log'))
        handler.setFormatter(logging.Formatter(Config.LOG_FORMAT))
        self.logger.addHandler(handler)
        self.logger.setLevel(Config.LOG_LEVEL)
        
    def _get_sheets_service(self):
        """Получение сервиса для работы с Google Sheets"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                Config.GOOGLE_SHEETS_CREDENTIALS,
                scopes=self.SCOPES
            )
            return build('sheets', 'v4', credentials=credentials)
        except Exception as e:
            self.logger.error(f"Ошибка при инициализации Google Sheets API: {str(e)}")
            raise
            
    def get_photos_data(self) -> List[Dict]:
        """Получение данных о фотографиях из таблицы"""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=Config.SPREADSHEET_ID,
                range='A2:Z'  # Начинаем со второй строки, предполагая что первая - заголовки
            ).execute()
            
            values = result.get('values', [])
            if not values:
                self.logger.warning("Данные в таблице не найдены")
                return []
                
            # Получаем заголовки
            headers_result = self.service.spreadsheets().values().get(
                spreadsheetId=Config.SPREADSHEET_ID,
                range='A1:Z1'
            ).execute()
            
            headers = headers_result.get('values', [[]])[0]
            
            # Преобразуем данные в список словарей
            photos_data = []
            for row in values:
                # Дополняем строку пустыми значениями, если она короче заголовков
                row_extended = row + [''] * (len(headers) - len(row))
                photo_data = dict(zip(headers, row_extended))
                
                # Проверяем обязательные поля
                required_fields = ['Путь', 'Широта', 'Долгота']
                missing_fields = [field for field in required_fields if field not in photo_data or not photo_data[field]]
                
                if missing_fields:
                    self.logger.warning(f"Пропущена строка с отсутствующими полями {', '.join(missing_fields)}: {photo_data}")
                    continue
                    
                photos_data.append(photo_data)
                
            self.logger.info(f"Получено {len(photos_data)} записей из таблицы")
            return photos_data
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении данных из таблицы: {str(e)}")
            return [] 