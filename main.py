import tkinter as tk
from tkinter import ttk, messagebox
import json
import threading
from samplexml.xml import xml_create
from tpdoc.tpdoc import start_generator_json
from pfrchecksnils.crome import update_cookies_and_post
import logging
import os
from signature.sign import sign_files, save_commands_to_file



logging.basicConfig(filename='main.log', filemode='w', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding="utf-8")
logger = logging.getLogger(__name__)

def load_config():
    """
    Загружает конфигурацию из файла `config.json`.

    :return: Объект конфигурации, загруженный из JSON-файла. В случае ошибки возвращает `None`.
    """
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logging.error(f"Ошибка при загрузке конфигурации: {e}")
        return None
    

def extract_filenames(text):
    """
    Извлекает названия файлов из текста, проверяет их наличие в папке 'work'.

    :param text: Входной текст из `local_uid_text`.
    :return: Кортеж из списка файлов, которые существуют, и списка файлов, которые не существуют.
    """
    lines = text.strip().split('\n')
    filenames = [line.strip() for line in lines if line.strip()]
    work_dir = os.path.join(os.getcwd(), 'work')
    existing_files = []
    missing_files = []

    for filename in filenames:
        file_path = os.path.join(work_dir, filename)
        if os.path.isfile(file_path):
            existing_files.append(file_path)
        else:
            missing_files.append(filename)

    return existing_files, missing_files

def main():
    """
    Основная функция приложения, которая инициализирует графический интерфейс, загружает конфигурацию,
    и обрабатывает действия пользователя для загрузки, проверки и подписания документов.
    """
    logger.info("Запуск основной функции main()")

    config = load_config()
    if config is None:
        logging.error("Конфигурация не была загружена. Программа завершает работу.")
        return

    root = tk.Tk()
    root.title("ГИП правка")
    root.geometry("770x450")
    root.resizable(False, False)

    style = ttk.Style()
    style.configure('TButton', padding=10, relief="flat", background="#abb1bf", foreground="#000", font=("Arial", 11), borderwidth=0)
    style.configure('TProgressbar', thickness=20, troughcolor="#f0f0f0", background="#4CAF50")

    frame = ttk.Frame(root, padding="20")
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame, text="Выберите регион:", font=("Arial", 12)).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
    region_combobox = ttk.Combobox(frame, state="readonly", font=("Arial", 12))
    region_combobox['values'] = list(config["regions"].keys())
    region_combobox.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
    region_combobox.current(0)

    ttk.Label(frame, text="Local UID(s) и другое:", font=("Arial", 12)).grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
    local_uid_text = tk.Text(frame, height=15, width=60, font=("Arial", 12))
    local_uid_text.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)

    progress_var = tk.IntVar()
    progress_bar = ttk.Progressbar(frame, variable=progress_var, maximum=100)
    progress_bar.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=13)

    selected_region_config = config["regions"][region_combobox.get()]

    def on_region_change(event):
        nonlocal selected_region_config
        selected_region_config = config["regions"][region_combobox.get()]

    region_combobox.bind("<<ComboboxSelected>>", on_region_change)

    def update_progress_bar(current, total):
        """
        Обновляет индикатор прогресса.

        :param current: Текущее значение прогресса.
        :param total: Общее количество задач.
        """
        progress_var.set(current)
        progress_bar.update()

    def upload_completed(successful, total):
        """
        Отображает сообщение о завершении загрузки документов.

        :param successful: Количество успешно загруженных документов.
        :param total: Общее количество документов.
        """
        if successful == total:
            messagebox.showinfo("Завершено", f"Все документы ({successful}/{total}) успешно выгружены.")
        else:
            messagebox.showwarning("Завершено", f"Не все документы были выгружены ({successful}/{total}).")
        
        progress_var.set(0)
        progress_bar.update()

    def upload_button_action():
        """
        Обрабатывает нажатие кнопки 'Upload': запускает процесс загрузки документов в отдельном потоке.
        """
        logger.info("Кнопка 'Upload' нажата")
        try:
            progress_var.set(0)
            total_uids = len(local_uid_text.get("1.0", "end-1c").strip().split('\n'))
            progress_bar['maximum'] = total_uids
            
            def run_upload():
                successful_uploads = start_generator_json(config, region_combobox, local_uid_text, update_progress_bar)
                upload_completed(successful_uploads, total_uids)
            
            thread = threading.Thread(target=run_upload)
            thread.start()
            
        except Exception as e:
            logger.error(f"Ошибка при выгрузке документов: {e}")

    def check_completed(successful, total):
        """
        Отображает сообщение о завершении проверки XML-файлов.

        :param successful: Список успешно созданных файлов.
        :param total: Общее количество файлов.
        """
        if len(successful) == 0:
            messagebox.showinfo("Завершено", f"Все XML-файлы ({total - len(successful)}/{total}) успешно созданы.")
        else:
            messagebox.showwarning("Завершено", f"Не все XML-файлы были успешно созданы ({total - len(successful)}/{total}).")
        progress_var.set(0)
        progress_bar.update()

    def check_button_action():
        """
        Обрабатывает нажатие кнопки 'Check': запускает процесс проверки XML-файлов в отдельном потоке.
        """
        logger.info("Кнопка 'Check' нажата")
        try:
            uids = local_uid_text.get("1.0", "end-1c").strip().split('\n')
            total_uids = len(uids)
            progress_bar['maximum'] = total_uids

            def update_progress(current, total):
                progress_var.set(current)
                progress_bar.update()

            def run_check():
                mpi_mismatch_errors = True

                user_choice = messagebox.askyesno(
                "Подтверждение", 
                "Хотите включить проверку на наличие ошибок PATIENT_MPI_MISMATCH в данных пациента? "
                "Если такая ошибка не найдена, файл не пройдет валидацию."
                )
                if user_choice is not None:
                    mpi_mismatch_errors = user_choice
                logger.info(f"Проверка на ошибки PATIENT_MPI_MISMATCH установлена в статус: {'Выполняется' if mpi_mismatch_errors else "Невыполняется"}")

                successful_creations = xml_create(config, region_combobox, local_uid_text, root=root, progress_callback=update_progress, mpi_mismatch_errors=mpi_mismatch_errors)

                check_completed(successful_creations, total_uids)

            thread = threading.Thread(target=run_check)
            thread.start()

        except Exception as e:
            logger.error(f"Ошибка при создании XML: {e}")

    def sign_button_action():
        """
        Обрабатывает нажатие кнопки 'Sign': запускает процесс подписания файлов в отдельном потоке
        и отображает прогресс в интерфейсе.
        """
        logger.info("Кнопка 'Sign' нажата")
        try:
            text = local_uid_text.get("1.0", "end-1c")

            existing_files, missing_files = extract_filenames(text)

            if missing_files:
                missing_files_str = '\n'.join(missing_files)
                logger.error(f"Файлы не найдены: {missing_files_str}")
                messagebox.showerror("Ошибка", f"Следующие файлы не найдены:\n{missing_files_str}")
                
            if existing_files:
                def update_progress(current: int, total: int):
                    """
                    Обновляет прогрессбар с текущим значением прогресса.

                    :param current: Текущее значение прогресса.
                    :param total: Общее количество задач.
                    """
                    progress_var.set(current)
                    progress_bar.update()

                def run_sign():
                    java_path = "C:\\Java\\jdk1.8.0_181\\bin\\java.exe"
                    jar_path = "C:\\Distr\\XMLSign_20200115\\xmlfile-sign-1.7.0.jar"
                    properties_file = selected_region_config["properties"]

                    signed_files, curl_commands = sign_files(config, region_combobox, existing_files, properties_file, java_path, jar_path, update_progress)
                    save_commands_to_file(curl_commands, 'curl_commands.txt')

                    if signed_files:
                        messagebox.showinfo("Завершено", f"Подписано файлов: {len(signed_files)} из {len(existing_files) + len(missing_files)}\nКоманды curl сохранены в файл: curl_commands.txt")
                    else:
                        messagebox.showwarning("Ошибка", "Подпись файлов не удалась.")


                    progress_var.set(0)
                    progress_bar.update()


                progress_var.set(0)
                progress_bar['maximum'] = len(existing_files)
                    
                thread = threading.Thread(target=run_sign)
                thread.start()

        except Exception as e:
            logger.error(f"Ошибка при подписании файлов: {e}")
            messagebox.showerror("Ошибка", f"Ошибка при подписании файлов: {e}")


    buttons_frame = ttk.Frame(frame)
    buttons_frame.grid(row=3, column=0, columnspan=2, pady=10)

    upload_button = ttk.Button(buttons_frame, text="Выгрузить", command=upload_button_action)
    upload_button.pack(side=tk.LEFT, padx=(50, 50))

    check_button = ttk.Button(buttons_frame, text="Проверить", command=check_button_action)
    check_button.pack(side=tk.LEFT, padx=(50, 50))

    sign_button = ttk.Button(buttons_frame, text="Подписать", command=sign_button_action)
    sign_button.pack(side=tk.LEFT, padx=(50, 50))

    root.mainloop()

if __name__ == "__main__":
    main()
    logger.info("Программа завершена")


