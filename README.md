# mistake_GIP
mistake_GIP — это набор утилит на Python для обработки данных и выполнения различных задач. Проект включает модули для проверки СНИЛС в рамках требований Пенсионного фонда РФ, обработки XML-документов, ведения логов в формате Excel, работы с цифровой подписью и генерации технической документации.

## Структура проекта

- **floor/**  
  Модуль для работы с данными, связанными с обработкой пола пациента.

- **logging_excel/**  
  Утилиты для ведения логов и экспорта данных в Excel.

- **pfrchecksnils/**  
  Скрипты для проверки корректности СНИЛС по стандартам Пенсионного фонда РФ.

- **samplexml/**  
  Примеры XML-документов для тестирования работы модулей, связанных с обработкой XML.

- **signature/**  
  Модуль для создания и проверки цифровой подписи.

- **tp/**  
  Компоненты, связанные с обработкой данных.

- **tpdoc/**  
  Модуль для работы с документацией и шаблонами технических предложений.

- **main.py**  
  Основной скрипт, служащий точкой входа в приложение.

- **config.json**  
  Файл конфигурации, содержащий настройки для работы проекта.

- **requirements.txt**  
  Список зависимостей, необходимых для запуска проекта.

## Установка

1. **Клонируйте репозиторий:**

   ```bash
   git clone https://github.com/d9d9vlad9/mistake_GIP.git
   ```

2. **Перейдите в каталог проекта:**

   ```bash
   cd mistake_GIP
   ```

3. **Установите зависимости с помощью pip:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Запустите проект:**

   ```bash
   python main.py
   ```
Примечание: Перед запуском убедитесь, что файл config.json настроен в соответствии с вашими требованиями.