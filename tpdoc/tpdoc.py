import requests
import json
import os
from urllib.parse import urlparse
import time
import logging
import openpyxl
from openpyxl import Workbook
from logging_excel.log import log_message_to_excel
logger = logging.getLogger(__name__)



def send_get_request(url):
    """
    Отправляет GET-запрос по указанному URL и возвращает ответ в формате JSON.

    :param url: URL-адрес для отправки запроса.
    :return: Ответ в формате JSON, если запрос выполнен успешно; `None` в случае ошибки.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        log_message_to_excel('json', [(generate_filename(url).replace('.json', ''), 'Успешное создание')])
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при подключении к {url}: {e}")
        log_message_to_excel('json', [(generate_filename(url).replace('.json', ''), 'Ошибка создания')])
        return None

def save_to_json(data, filename):
    """
    Сохраняет данные в JSON-файл в папке 'data'.

    :param data: Данные, которые нужно сохранить в файл.
    :param filename: Имя файла для сохранения данных.
    """
    data_directory = os.path.join(os.getcwd(), 'data')

    if not os.path.exists(data_directory):
        os.makedirs(data_directory)

    file_path = os.path.join(data_directory, filename)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def generate_filename(url):
    """
    Генерирует имя файла на основе URL.

    :param url: URL, на основе которого будет сгенерировано имя файла.
    :return: Имя файла в формате 'имя.json'.
    """
    parsed_url = urlparse(url)
    path = parsed_url.path.strip('/')
    filename = path if path else 'index'
    filename = filename.split('/')[-1] + '.json'
    return filename

def start_generator_json(config, region_combobox, local_uid_text, progress_callback=None):
    """
    Генерирует JSON-файлы для локальных UID на основе конфигурации и сохраняет их на диск.

    :param config: Конфигурационный словарь, содержащий информацию о регионах и API-эндпоинтах.
    :param region_combobox: Виджет выбора региона, который предоставляет выбранный регион.
    :param local_uid_text: Виджет текста, содержащий локальные UID, по одному на строку.
    :param progress_callback: Необязательная функция обратного вызова для отслеживания прогресса.
    :return: Количество успешно обработанных и сохраненных JSON-файлов.
    """
    selected_region = region_combobox.get()
    selected_region_config = config["regions"][selected_region]
    base_url = selected_region_config.get("api_endpoint")
    local_uids = local_uid_text.get("1.0", "end-1c").strip().split('\n')
    total_urls = len(local_uids)

    successful_uploads = 0

    for index, local_uid in enumerate(local_uids, start=1):
        if local_uid.strip():
            url = os.path.join(base_url, local_uid.strip())
            json_data = send_get_request(url)
            if json_data:
                filename = generate_filename(url)
                save_to_json(json_data, filename)
                successful_uploads += 1
                logger.info(f"Данные local_uid: {local_uid} сохранены в {filename}. Обработка {index} из {total_urls}")
                
                if progress_callback:
                    progress_callback(index, total_urls)
                    
                time.sleep(1)

    return successful_uploads
