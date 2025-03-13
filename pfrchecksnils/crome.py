import requests
from PIL import Image, ImageTk
from io import BytesIO
import logging
import pickle
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any

logger = logging.getLogger(__name__)

def captcha(session, root, timeout=30000):
    """
    Создает окно для ввода капчи и проверяет введенную капчу.

    :param session: Объект сессии `requests.Session` для выполнения HTTP-запросов.
    :param root: Корневое окно Tkinter, используемое для создания окна капчи.
    :param timeout: Время (в миллисекундах) до автоматического закрытия окна капчи.
    :return: `True`, если капча была успешно пройдена, иначе `False`.
    """
    captcha_url = 'https://es.pfrf.ru/api/captcha/img'
    check_url = 'https://es.pfrf.ru/checkSnils'

    def create_captcha_window():
        response = session.get(captcha_url)
        if response.status_code == 200:
            image = Image.open(BytesIO(response.content))
            img = ImageTk.PhotoImage(image)
            
            captcha_window = tk.Toplevel(root)
            captcha_window.title("Введите капчу")
            captcha_window.geometry("300x200")
            captcha_window.resizable(False, False)

            style = ttk.Style()
            style.configure('TLabel', font=("Arial", 12))
            style.configure('TButton', padding=10, relief="flat", background="#abb1bf", foreground="#000", font=("Arial", 11), borderwidth=0)
            style.configure('TEntry', font=("Arial", 12))
            
            frame = ttk.Frame(captcha_window, padding="5")
            frame.pack(fill=tk.BOTH, expand=True)

            label = ttk.Label(frame, image=img)
            label.image = img
            label.pack(pady=(0, 10))

            entry = ttk.Entry(frame)
            entry.pack(pady=(0, 5), fill=tk.X) 

            def submit_captcha():
                captcha_response = entry.get()
                if not captcha_response:
                    messagebox.showwarning("Ошибка", "Пожалуйста, введите капчу.")
                    return

                captcha_data = {'captcha-response': captcha_response}
                captcha_check = session.post(check_url, data=captcha_data)
                
                if captcha_check.status_code == 200:
                    if 'Проверка пользователя' in captcha_check.text:
                        logger.info("Требуется дополнительная проверка.")
                        messagebox.showinfo("Проверка", "Требуется дополнительная проверка.")
                        captcha_window.destroy()
                        captcha_window.result = False
                    else:
                        logger.info("Проверка пользователя пройдена.")
                        captcha_window.result = True  
                        captcha_window.destroy()
                else:
                    logger.info("Ошибка при проверке капчи.")
                    messagebox.showerror("Ошибка", "Ошибка при проверке капчи.")
                    captcha_window.result = False 
                    captcha_window.destroy()

            submit_button = ttk.Button(frame, text="Отправить", command=submit_captcha)
            submit_button.pack(pady=(0), fill=tk.X)

            captcha_window.after(timeout, lambda: close_captcha_window(captcha_window))

            captcha_window.protocol("WM_DELETE_WINDOW", lambda: close_captcha_window(captcha_window))

            captcha_window.grab_set()
            root.wait_window(captcha_window)

            return captcha_window.result
        else:
            logger.info("Не удалось получить изображение капчи.")
            messagebox.showerror("Ошибка", "Не удалось получить изображение капчи.")
            return False

    def close_captcha_window(captcha_window):
        logger.info("Окно капчи закрыто вручную или по тайм-ауту.")
        captcha_window.result = False
        captcha_window.destroy()

    while True:
        result = create_captcha_window()
        if result:
            return session

def save_session(session, filename):
    """
    Сохраняет объект сессии в файл с использованием `pickle`.

    :param session: Объект сессии `requests.Session`, который нужно сохранить.
    :param filename: Имя файла, в который будет сохранена сессия.
    """
    with open(filename, 'wb') as f:
        pickle.dump(session, f)

def load_session(filename):
    """
    Загружает объект сессии из файла с использованием `pickle`.

    :param filename: Имя файла, из которого будет загружена сессия.
    :return: Объект сессии `requests.Session`, загруженный из файла.
    """
    with open(filename, 'rb') as f:
        return pickle.load(f)

def check_user(root):
    """
    Проверяет пользователя, загружает сессию или создает новую, если требуется.

    :param root: Корневое окно Tkinter, используемое для отображения окна капчи.
    :return: Объект сессии `requests.Session` после проверки пользователя и прохождения капчи.
    """
    try:
        session = load_session('session.pkl')
        logger.info('Сессия загружена')
    except (FileNotFoundError, EOFError):
        logger.info("Сессия не найдена. Создаем новую.")
        session = requests.Session()

    check_url = 'https://es.pfrf.ru/checkSnils'
    check_response = session.get(check_url)
    
    if 'Проверка пользователя' in check_response.text:
        logger.info("Необходима проверка пользователя.")
        session = captcha(session, root)
        if session:
            save_session(session, 'session.pkl')
        else:
            logger.info("Не удалось пройти капчу. Сессия не сохранена.")
    else:
        logger.info("Проверка пользователя не требуется. Продолжаем.")
    
    return session

def update_cookies_and_post(snils_data: Dict[str, Any], root) -> bool:
    """
    Отправляет данные для проверки СНИЛС и обновляет куки.

    :param snils_data: Словарь с данными для проверки, содержащий ключи "surname", "name", "patrName", "birthDate", "snils".
    :param root: Корневое окно Tkinter, используемое для создания окна капчи.
    :return: ФИО пользователя, если проверка успешна, иначе `False`.
    """
    session = check_user(root)

    check_ss = 'https://es.pfrf.ru/api/service_checkSnils'

    payload = {
        "userData[nameLast]": snils_data["surname"],
        "userData[nameFirst]": snils_data["name"],
        "userData[patronymic]": snils_data["patrName"],
        "userData[birthDate]": snils_data["birthDate"],
        "userData[snils]": snils_data["snils"],
        "simpleCheck": True
    }

    check_response = session.post(url=check_ss, data=payload)


    if check_response.status_code == 200 and check_response.json().get("error") == 9107:
        logger.info("Антиспам проверка не пройдена.")
    elif check_response.status_code == 200 and check_response.json().get("error") == 5624:
        logger.info("СНИЛС задан некорректно.")
    elif check_response.status_code == 200 and check_response.json().get("data", {}).get("isValid"):
        logger.info("Пользователь прошел проверку. ФИО: %s", check_response.json().get("data", {}).get("personFIO"))
        return check_response.json().get("data", {}).get("personFIO")
    else: 
        logger.error("Ошибка запроса или неверные данные.")
        return False
