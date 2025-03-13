import requests
import json
import logging
import re
import base64
from pfrchecksnils.crome import update_cookies_and_post
from logging_excel.log import log_message_to_excel
from floor.floor import classify_gender
import openpyxl
from openpyxl import Workbook
import os
from unidecode import unidecode

logger = logging.getLogger(__name__)
used_snils = []
snils_results = {}

def decode_base64_to_text(encoded_str: str) -> str:
    """
    Декодирует строку из формата base64 в текст.

    :param encoded_str: Строка в формате base64, которую нужно декодировать.
    :return: Декодированная строка, если декодирование прошло успешно; `None` в случае ошибки.
    """
    try:
        decoded_bytes = base64.b64decode(encoded_str)
        decoded_str = decoded_bytes.decode('utf-8')
        return decoded_str
    except (base64.binascii.Error, UnicodeDecodeError):
        return None


def check_for_whitespace(field):
    """
    Проверяет наличие пробелов в начале или конце строки.

    :param field: Строка для проверки на пробелы.
    :return: `True`, если пробелы обнаружены, иначе `False`.
    """
    parts = field.split()
    if field == ' '.join(parts):
        return False
    else:
        return True

def extract_oid_name(content):
    """
    Извлекает OID и название организации из текста.

    :param content: Текст, из которого нужно извлечь OID и название организации.
    :return: Кортеж из OID и названия организации. Если данные не найдены, возвращает `None` для каждого значения.
    """
    oid_pattern = re.compile(r'<providerOrganization>\s*<id root="([^"]+)"')
    name_pattern = re.compile(r'<providerOrganization>.*?<name>([^<]+)</name>', re.DOTALL)
    
    oid_match = oid_pattern.search(content)
    name_match = name_pattern.search(content)
    
    oid = oid_match.group(1) if oid_match else None
    name = name_match.group(1) if name_match else None
    
    return oid, name


def check_patient_data(json_filename, root, mpi_mismatch_errors):
    """
    Проверяет данные пациента в JSON-файле и возвращает результат проверки.

    Функция открывает JSON-файл, проверяет наличие ошибок в данных пациента, включая проверку на
    наличие ошибки `PATIENT_MPI_MISMATCH` в случае, если этот параметр активирован. Результаты
    проверок логируются и записываются в Excel.

    :param json_filename: Имя JSON-файла (local_uid), содержащего данные пациента.
    :param root: Корневое окно Tkinter, используемое для создания окна капчи.
    :param mpi_mismatch_errors: Логическое значение, указывающее, нужно ли учитывать ошибки 
                                `PATIENT_MPI_MISMATCH` при валидации данных пациента.
    :return: Словарь с результатами проверки, если все проверки пройдены успешно; `None` в противном случае.
    """
    logger.info("Запущена функция check_patient_data")
    try:
        local_uid = os.path.splitext(os.path.basename(json_filename))[0]
        try:
            with open(json_filename, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except FileNotFoundError:
            logger.error(f"Файл '{json_filename}' не найден.")
            log_message_to_excel('Все документы', [(local_uid, 'Файл не найден')])
            log_message_to_excel('Отсутсвует', [(local_uid, 'Файл не найден')])
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка при декодировании JSON в файле '{json_filename}': {str(e)}")
            log_message_to_excel('Все документы', [(local_uid, 'Ошибка при декодировании JSON')])
            log_message_to_excel('Отсутсвует', [(local_uid, 'Файл не найден')])
            return None
        
    
        global used_snils, snils_results
        new_snils = data['patient']['snils']

        if new_snils in used_snils:
            original_result = snils_results.get(new_snils)
            if original_result:
                sheet_name, original_message = original_result
                duplicate_message = f"Найден дубликат по номеру СНИЛС. Сообщение оригинала: {original_message}"
                log_message_to_excel(sheet_name, [(local_uid, duplicate_message)])
                log_message_to_excel('Все документы', [(local_uid, duplicate_message)])
                logger.error(duplicate_message)
            else:
                duplicate_message = "Найден дубликат по номеру СНИЛС. Сообщение оригинала: Результат оригинала неизвестен"
                log_message_to_excel('Все документы', [(local_uid, duplicate_message)])
                logger.error(duplicate_message)
            return None
        else:
            used_snils.append(new_snils)

        if mpi_mismatch_errors:
            mpi_mismatch_errors_list = [error for error in data.get('errors', []) if error['code'] == 'PATIENT_MPI_MISMATCH' and ('Имя пациента' in error['message'] or 'Дата рождения' in error['message'] or 'снилс' in error['message'].lower()) or 'Пол пациента' in error['message']]

            if not mpi_mismatch_errors_list:
                result_message = "Соответствующих ошибок PATIENT_MPI_MISMATCH c именем пациента или датой рождения или снилс или полом не обнаружено."
                logger.info(result_message)
                log_message_to_excel('PATIENT_MPI_MISMATCH нет', [(local_uid, result_message)])
                log_message_to_excel('Все документы', [(local_uid, result_message)])
                snils_results[new_snils] = ('PATIENT_MPI_MISMATCH нет', result_message)
                return None 

        if check_for_whitespace(data['patient']['name']) or check_for_whitespace(data['patient']['surname']):
            result_message = "Одно из полей имени или фамилии содержит пробел в начале или в конце."
            logger.error(result_message)
            log_message_to_excel('Пробелы в ФИО', [(local_uid, result_message)])
            log_message_to_excel('Все документы', [(local_uid, result_message)])
            snils_results[new_snils] = ('Пробелы в ФИО', result_message)
            return None

        if 'patrName' in data['patient']:
            if check_for_whitespace(data['patient']['patrName']):
                result_message = "Поле отчества содержит пробел в начале или в конце."
                logger.error(result_message)
                log_message_to_excel('Пробелы в ФИО', [(local_uid, result_message)])
                log_message_to_excel('Все документы', [(local_uid, result_message)])
                snils_results[new_snils] = ('Пробелы в ФИО', result_message)
                return None
        else:
            logger.info("Отчество отсутствует.")

        gender_error = any(error['code'] == 'PATIENT_MPI_MISMATCH' and 'Пол пациента' in error['message'] for error in data.get('errors', []))
        if gender_error:
            logger.debug(f"Пол пациента в метаданных {data['patient']['surname']} {data['patient']['name']} {data['patient'].get('patrName', '')}: {'Муж' if data['patient']['gender']['code']=='1' else 'Жен'}")
            if not data['patient']['gender']['code'] == classify_gender(data['patient']['surname'], data['patient']['name'], data['patient'].get('patrName', '')):
                result_message = "Пол пациента не соответствует требуемому. Смотрите логи."
                logger.error(result_message)
                log_message_to_excel('Пол пациента', [(local_uid, result_message)])
                log_message_to_excel('Все документы', [(local_uid, result_message)])
                snils_results[new_snils] = ('Пол пациента', result_message)
                return None

        if 'organization' not in data or 'code' not in data['organization'] or 'displayName' not in data['organization']:
            logger.error("Отсутствует код организации или отображаемое имя организации в spring-cloud-gateway начинаю проверять тело документа.")
            
            docContent = data['docContent']['data']
            decode_docContent = decode_base64_to_text(docContent)
            organization_code, organization_displayName = extract_oid_name(decode_docContent)
            
            
            if organization_code is None or organization_displayName is None:
                result_message = "Код организации или отображаемое имя организации в теле документа отсутствуют."
                logger.error(result_message)
                log_message_to_excel('Ошибка нет организации', [(local_uid, result_message)])
                log_message_to_excel('Все документы', [(local_uid, result_message)])
                snils_results[new_snils] = ('Ошибка нет организации', result_message)
                return None
            else:
                logger.info("Код организации и отображаемое имя организации в теле документа найдены.")

        else:
            logger.info("Код организации и отображаемое имя организации в spring-cloud-gateway найдены.")
            organization_code = data['organization']['code']
            organization_displayName = data['organization']['displayName']
        

        birth_date = data['patient']['birthDate']
        reversed_birth_date = '.'.join(birth_date.split('-')[::-1]) 



        patient_data = {
            "surname": data['patient']['surname'],
            "name": data['patient']['name'],
            "patrName": data['patient'].get('patrName', ''),
            "birthDate": reversed_birth_date,
            "snils": data['patient']['snils']
        }

        
        if json_pfr_data:= update_cookies_and_post(patient_data, root):
            if json_pfr_data.get('patronymic') == None or json_pfr_data.get('patronymic').lower() == data['patient'].get('patrName').lower():
                result = {
                        "birthDate": data['patient']['birthDate'],
                        "gender": data['patient']['gender']['code'],
                        "localId": data['patient']['localId'],
                        "name": data['patient']['name'], 
                        "patrName": data['patient'].get('patrName', ''),
                        "snils": data['patient']['snils'],
                        "surname": data['patient']['surname'],
                        "organizationCode": organization_code,
                        "organizationDisplayName": organization_displayName
                    }
                patr_name = result.get('patrName', "")
                first_char = patr_name[0] if patr_name else ""
                xml_filename = unidecode(result.get('surname', f'{local_uid}') + result.get('name', "")[0] + first_char, 'ru').replace(" ", '-').replace("'", "") + ".xml"

                if gender_error:
                    xml_filename += " (Ошибка пола пациента)"
                
                log_message_to_excel('Созданные файлы', [(xml_filename, None)])
                log_message_to_excel('Созданные файлы и их дубли', [(local_uid, f"Отправлен на формирование XML {xml_filename}")])
                log_message_to_excel('Все документы', [(local_uid, f"Отправлен на формирование XML {xml_filename}")])
                snils_results[new_snils] = ('Созданные файлы и их дубли', xml_filename)
                return result
            else:
                result_message = "Отчество на ПФР и поле отчества из spring-cloud-gateway не совпадают."
                logger.error(result_message)
                log_message_to_excel('Ошибки ПФР', [(local_uid, result_message)])
                log_message_to_excel('Все документы', [(local_uid, result_message)])
                snils_results[new_snils] = ('Ошибки ПФР', result_message)
                return None

        result_message = "Пациент не прошел проверку на пфр либо запрос к cheksnils пфр не удался."
        logger.error(result_message)
        log_message_to_excel('Ошибки ПФР', [(local_uid, result_message)])
        log_message_to_excel('Все документы', [(local_uid, result_message)])
        snils_results[new_snils] = ('Ошибки ПФР', result_message)
        return None

    except Exception as e:
        logger.error(f"Ошибка при проверке данных: {e}")