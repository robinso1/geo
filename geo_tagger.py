#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Geo Photo Tagger - скрипт для автоматического геотегинга фотографий
с использованием данных из Google Таблиц.

Автор: robinso1
Версия: 1.0.0
"""

import sys
import os
import logging
from src import Config, PhotoProcessor, GoogleSheetsClient

def main():
    # Настройка логирования
    Config.ensure_directories()
    logging.basicConfig(
        level=Config.LOG_LEVEL,
        format=Config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(os.path.join(Config.LOG_DIR, 'main.log')),
            logging.StreamHandler()  # Вывод в консоль
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("✓ Проверка окружения успешно завершена")
    
    try:
        # Инициализация клиентов
        sheets_client = GoogleSheetsClient()
        logger.info(f"✓ file_cache is only supported with oauth2client<4.0.0")
        
        photo_processor = PhotoProcessor()
        
        # Получение данных из Google Sheets
        logger.info("Получение данных из Google Sheets")
        photos_data = sheets_client.get_photos_data()
        
        if not photos_data:
            logger.warning("Данные не найдены в таблице")
            return
            
        logger.info(f"Найдено {len(photos_data)} строк для обработки")
        
        # Обработка фотографий
        photo_processor.process_photos(photos_data)
        
        # Вывод статистики
        logger.info(f"Программа успешно завершила работу. "
                   f"Обработано: {photo_processor.success_count}, "
                   f"Ошибок: {photo_processor.error_count}")
        
    except Exception as e:
        logger.error(f"Произошла ошибка: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 