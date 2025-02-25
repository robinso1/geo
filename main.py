import logging
import os
from src import Config, PhotoProcessor, GoogleSheetsClient

def main():
    # Настройка логирования
    logging.basicConfig(
        level=Config.LOG_LEVEL,
        format=Config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(os.path.join(Config.LOG_DIR, 'main.log')),
            logging.StreamHandler()  # Вывод в консоль
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Начало работы программы")
    
    try:
        # Создание необходимых директорий
        Config.ensure_directories()
        
        # Инициализация клиентов
        sheets_client = GoogleSheetsClient()
        photo_processor = PhotoProcessor()
        
        # Получение данных из Google Sheets
        logger.info("Получение данных из Google Sheets")
        photos_data = sheets_client.get_photos_data()
        
        if not photos_data:
            logger.warning("Нет данных для обработки")
            return
            
        logger.info(f"Получено {len(photos_data)} записей для обработки")
        
        # Обработка фотографий
        photo_processor.process_photos(photos_data)
        
        logger.info("Программа успешно завершила работу")
        
    except Exception as e:
        logger.error(f"Произошла ошибка: {str(e)}")
        raise

if __name__ == "__main__":
    main() 