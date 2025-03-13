from pymorphy3 import MorphAnalyzer
import logging

logger = logging.getLogger(__name__)

morph = MorphAnalyzer()

def classify_gender(last_name, first_name, patronymic=None):
    """
    Определяет пол по ФИО с использованием библиотеки Pymorphy3.

    Args:
        last_name (str): Фамилия.
        first_name (str): Имя.
        patronymic (str): Отчество (может быть пустым).

    Returns:
        str: '1' для мужского пола, '2' для женского пола, или None, если пол не определен.
    Описание:
        Функция анализирует каждую часть ФИО (фамилию, имя, отчество) с использованием Pymorphy3 для извлечения 
        морфологических признаков, включая пол. Она подсчитывает количество мужских и женских признаков и возвращает пол, 
        основываясь на большинстве.
    """
    genders = {'masc': 0, 'femn': 0, 'neut': 0}

    if patronymic:
        patronymic_parse = morph.parse(patronymic)[0]
        if patronymic_parse.tag.gender:
            genders[patronymic_parse.tag.gender] += 1

    last_name_parse = morph.parse(last_name)[0]
    if last_name_parse.tag.gender:
        genders[last_name_parse.tag.gender] += 1

    first_name_parse = morph.parse(first_name)[0]
    if first_name_parse.tag.gender:
        genders[first_name_parse.tag.gender] += 1

    if genders['masc'] > genders['femn'] and genders['masc'] > genders['neut']:
        logger.debug('Pymorphy3: Мужской пол')
        return '1'
    elif genders['femn'] > genders['masc'] and genders['femn'] > genders['neut']:
        logger.debug('Pymorphy3: Женский пол')
        return '2'
    elif genders['neut'] > 1:
        logger.debug('Pymorphy3: Неопределённый пол')
        return None

    logger.debug('Pymorphy3: Пол не определён')
    return None