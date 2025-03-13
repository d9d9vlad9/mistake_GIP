import os
import subprocess
import logging
import openpyxl
from openpyxl import Workbook
from typing import List, Optional, Callable
from logging_excel.log import log_message_to_excel

logger = logging.getLogger(__name__)


def sign_file(file_to_sign: str, properties_file: str, java_path: str, jar_path: str) -> Optional[str]:
    """
    Подписывает указанный XML файл и проверяет успешность подписи.

    :param file_to_sign: Путь к XML файлу, который нужно подписать.
    :param properties_file: Путь к файлу настроек.
    :param java_path: Путь к исполняемому файлу Java.
    :param jar_path: Путь к JAR файлу для подписи.
    :return: Путь к подписанному файлу, если подпись успешна, иначе None.
    """
    try:
        signed_file = file_to_sign.replace(".xml", "-singed.xml")

        command = [
            java_path,
            '-Dfile.encoding=UTF-8',
            f'-DpropsFile={properties_file}',
            '-jar', jar_path,
            'SOAP12', properties_file, file_to_sign, signed_file
        ]

        logger.info(f"Выполняется команда: {' '.join(command)}")

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode == 0 and "Signature valid" in result.stdout:
            logger.info(f"Файл успешно подписан: {signed_file}")
            log_message_to_excel('Подписанные файлы', [(f'{signed_file}', None)])
            return signed_file
        else:
            logger.error(f"Ошибка при подписании файла {file_to_sign}: {result.stderr}")
            logger.error(f"Вывод команды: {result.stdout}")
            log_message_to_excel('Ошибка подписи', [(file_to_sign, result.stderr)])
            return None

    except Exception as e:
        logger.error(f"Исключение при подписании файла {file_to_sign}: {e}")
        return None


def sign_files(config, region_combobox,
    files_to_sign: List[str], 
    properties_file: str, 
    java_path: str, 
    jar_path: str, 
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[str]:
    """
    Подписывает несколько файлов и возвращает список команд curl.
    :param config: Конфигурационный файл с настройками.
    :param region_combobox: Виджет для выбора региона.
    :param files_to_sign: Список путей к XML файлам для подписи.
    :param properties_file: Путь к файлу настроек.
    :param java_path: Путь к исполняемому файлу Java.
    :param jar_path: Путь к JAR файлу для подписи.
    :param progress_callback: Функция обратного вызова для обновления прогресса. 
                               Принимает два аргумента: текущий прогресс и общее количество файлов.
    :return: Список команд curl.
    """
    signed_files = []
    curl_commands = []
    total_files = len(files_to_sign)

    selected_region = region_combobox.get()
    selected_region_config = config["regions"][selected_region]
    address_url_curl = selected_region_config.get("adress_url_curl")
    
    if not address_url_curl:
        logger.error("Не указан адрес URL для curl")
        return False
    
    for index, file in enumerate(files_to_sign, start=1):
        try:
            signed_file = sign_file(file, properties_file, java_path, jar_path)
            if signed_file:
                signed_files.append(signed_file)
                signed_file_name = os.path.basename(signed_file)
                curl_command = (
                    f'curl -X POST -H "Content-Type: text/xml;charset=UTF-8" '
                    f'-H \'SOAPAction: "urn:hl7-org:v3:PRPA_IN201302"\' '
                    f'--data-binary @{signed_file_name} -k {address_url_curl}'
                )
                curl_commands.append(curl_command)
            else:
                logger.error(f"Не удалось подписать файл: {file}")

        except Exception as e:
            logger.error(f"Ошибка при подписи файла {file}: {e}")
    
        if progress_callback:
            progress_callback(index, total_files)
    
    return signed_files, curl_commands

def save_commands_to_file(commands: List[str], filename: str):
    """
    Сохраняет список команд в файл.

    :param commands: Список команд curl.
    :param filename: Имя файла для сохранения команд.
    """
    with open(filename, 'w') as f:
        for command in commands:
            f.write(command + '\n')