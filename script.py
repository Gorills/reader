import re
import time
import random
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from colorama import init, Fore, Style
import requests
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
import tempfile
import os
import shutil
import json
import signal
import sys
from datetime import datetime


# Путь к временному файлу для хранения данных о воркере
WORKER_FILE = "/tmp/worker_data.json"  # Путь в /tmp, чтобы файл удалялся при перезапуске контейнера
PROXY_API_URL = "https://proxy-bunker.com/api2.php"

# Инициализация colorama для цветного вывода в консоли
init()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# URL API для получения данных
API_URL = "https://real-rpg-books.ru/api/v1/"
BOOKS_ENDPOINT = f"{API_URL}books/"
CHAPTERS_ENDPOINT = f"{API_URL}chapters/"
WORKERS_ENDPOINT = f"{API_URL}workers/"

# API-ключ (должен совпадать с тем, что в permissions.py)
API_KEY = "pofUhvArCD!InqR/ihbp10t!4nLDixpV0JKIpSRu3L!tynylcf7soKtZU6c"  # Замените на тот же ключ, что в permissions.py
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}



USE_PROXIES = True  # Использовать прокси (True) или нет (False)
PROXY_LIST = []  # Изначально пустой список прокси, будет обновляться перед каждым циклом
VISUAL_MODE = False  # True - видимый браузер и одна сессия, False - скрытый режим и консоль
SESSION_DELAY = (2, 5)  # Диапазон задержки между сессиями (в секундах)
MAX_PROXY_RETRIES = 3



# Путь к файлу логов сессий
SESSION_LOG_FILE = "/tmp/session_logs.json"

def init_session_log():
    """Инициализирует файл логов сессий, если он не существует."""
    if not os.path.exists(SESSION_LOG_FILE):
        with open(SESSION_LOG_FILE, 'w') as f:
            json.dump([], f)
        logger.info(f"{Fore.GREEN}Создан файл логов сессий: {SESSION_LOG_FILE}{Style.RESET_ALL}")

def append_session_log(session_data):
    """Добавляет запись о сессии в файл логов."""
    try:
        init_session_log()
        with open(SESSION_LOG_FILE, 'r+') as f:
            logs = json.load(f)
            logs.append(session_data)
            f.seek(0)
            json.dump(logs, f, indent=2)
        logger.info(f"{Fore.GREEN}Запись о сессии {session_data['session_id']} добавлена в {SESSION_LOG_FILE}{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"{Fore.RED}Ошибка при записи в файл логов: {e}{Style.RESET_ALL}")

def update_session_log(session_id, updates):
    """Обновляет запись о сессии в файле логов."""
    try:
        init_session_log()
        with open(SESSION_LOG_FILE, 'r+') as f:
            logs = json.load(f)
            for log in logs:
                if log['session_id'] == session_id:
                    log.update(updates)
                    break
            f.seek(0)
            f.truncate()
            json.dump(logs, f, indent=2)
        logger.info(f"{Fore.GREEN}Запись о сессии {session_id} обновлена{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"{Fore.RED}Ошибка при обновлении файла логов: {e}{Style.RESET_ALL}")



def check_proxy(proxy, timeout=5, use_selenium_fallback=False):
    """
    Проверяет прокси на доступность сайта real-rpg-books.ru и наличие ссылки с utm_source=realrpg.
    
    Args:
        proxy (str): Прокси в формате http://ip:port
        timeout (int): Таймаут для HTTP-запроса в секундах
        use_selenium_fallback (bool): Использовать Selenium для проверки, если requests не работает
    
    Returns:
        bool: True если прокси рабочий, False если нерабочий
    """
    # Очищаем строку прокси от лишних символов
    proxy = proxy.strip()
    # Проверяем формат прокси с помощью регулярного выражения
    proxy_pattern = r'^(http|https)://[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}:[0-9]{1,5}$'
    if not re.match(proxy_pattern, proxy):
        logger.error(f"{Fore.RED}Прокси {proxy} имеет неверный формат{Style.RESET_ALL}")
        return False

    # Проверка через requests
    try:
        session = requests.Session()
        session.proxies = {"http": proxy, "https": proxy}
        headers = {"User-Agent": random.choice(user_agents)}
        
        logger.info(f"{Fore.CYAN}Проверка прокси {proxy} через requests{Style.RESET_ALL}")
        response = session.get("https://real-rpg-books.ru", headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # Проверяем наличие ссылки с utm_source=realrpg
        if "utm_source=realrpg" in response.text:
            logger.info(f"{Fore.GREEN}Прокси {proxy} рабочий: сайт доступен, ссылка найдена{Style.RESET_ALL}")
            return True
        else:
            logger.warning(f"{Fore.YELLOW}Прокси {proxy} не содержит целевую ссылку{Style.RESET_ALL}")
            return False
            
    except requests.RequestException as e:
        logger.warning(f"{Fore.YELLOW}Прокси {proxy} не прошел проверку через requests: {e}{Style.RESET_ALL}")

        # Если включен fallback на Selenium и это не повторная попытка
        if use_selenium_fallback:
            logger.info(f"{Fore.CYAN}Пробуем проверить прокси {proxy} через Selenium{Style.RESET_ALL}")
            try:
                driver = setup_driver(use_proxies=True, visual_mode=False, proxy_list=[proxy])
                if not driver:
                    logger.error(f"{Fore.RED}Не удалось настроить драйвер для прокси {proxy}{Style.RESET_ALL}")
                    return False
                
                driver.get("https://real-rpg-books.ru/")
                try:
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    if "utm_source=realrpg" in driver.page_source:
                        logger.info(f"{Fore.GREEN}Прокси {proxy} рабочий (Selenium): сайт доступен, ссылка найдена{Style.RESET_ALL}")
                        return True
                    else:
                        logger.warning(f"{Fore.YELLOW}Прокси {proxy} не содержит целевую ссылку (Selenium){Style.RESET_ALL}")
                        return False
                except TimeoutException:
                    logger.error(f"{Fore.RED}Таймаут при загрузке страницы через прокси {proxy} (Selenium){Style.RESET_ALL}")
                    return False
                finally:
                    driver.quit()
            except Exception as e:
                logger.error(f"{Fore.RED}Ошибка при проверке прокси {proxy} через Selenium: {e}{Style.RESET_ALL}")
                return False
        else:
            logger.error(f"{Fore.RED}Прокси {proxy} нерабочий: {e}{Style.RESET_ALL}")
            return False



def get_container_number():
    try:
        container_number = os.getenv('CONTAINER_NUMBER')
        if container_number:
            container_number = int(container_number)
            logger.info(f"{Fore.GREEN}Порядковый номер контейнера: {container_number}{Style.RESET_ALL}")
            return container_number
        else:
            logger.error(f"{Fore.RED}Переменная окружения CONTAINER_NUMBER не найдена, завершаем работу{Style.RESET_ALL}")
            return None
    except ValueError:
        logger.error(f"{Fore.RED}Переменная CONTAINER_NUMBER не является числом: {container_number}{Style.RESET_ALL}")
        return None
    except Exception as e:
        logger.error(f"{Fore.RED}Ошибка при получении номера контейнера: {e}{Style.RESET_ALL}")
        return None
    


# Функция для получения данных о книгах из API
def fetch_books_data():
    try:
        response = requests.get(BOOKS_ENDPOINT, timeout=10)  # GET доступен всем
        response.raise_for_status()
        books = response.json()
        logger.info(f"{Fore.GREEN}Получены данные о {len(books)} книгах из API{Style.RESET_ALL}")
        return books
    except requests.RequestException as e:
        logger.error(f"{Fore.RED}Ошибка при загрузке данных из API: {e}{Style.RESET_ALL}")
        return []



# Функция для получения или создания воркера
def get_or_create_worker(worker_id):
    """
    Запрашивает воркер с указанным worker_id через эндпоинт /assign/.
    
    Args:
        worker_id (int): ID воркера для запроса.
    
    Returns:
        dict or None: Данные воркера, если он доступен, иначе None.
    """
    try:
        # Формируем URL с параметром worker_id
        params = {"worker_id": worker_id}
        response = requests.get(
            f"{WORKERS_ENDPOINT}assign/",
            headers=HEADERS,
            params=params,
            timeout=10
        )
        response.raise_for_status()  # Вызывает исключение для HTTP-ошибок (4xx, 5xx)
        
        worker = response.json()
        
        if worker and "id" in worker:
            logger.info(
                f"{Fore.GREEN}Успешно получен воркер worker_id={worker['worker_id']} "
                f"(ID={worker['id']}) с книгой: {worker['book']}{Style.RESET_ALL}"
            )
            update_worker(worker["id"], active=False, busy=True)
            return worker
        else:
            logger.warning(
                f"{Fore.YELLOW}Сервер не вернул воркера для worker_id={worker_id}{Style.RESET_ALL}"
            )
            return None
            
    except requests.HTTPError as e:
        logger.error(
            f"{Fore.RED}HTTP-ошибка при запросе воркера worker_id={worker_id}: "
            f"{response.status_code} {response.text}{Style.RESET_ALL}"
        )
        return None
    except requests.RequestException as e:
        logger.error(
            f"{Fore.RED}Ошибка при запросе воркера worker_id={worker_id}: {e}{Style.RESET_ALL}"
        )
        return None



# Функция для сохранения данных о воркере в файл
def save_worker_data(worker):
    try:
        with open(WORKER_FILE, 'w') as f:
            json.dump(worker, f)
        logger.info(f"{Fore.GREEN}Данные о воркере сохранены в {WORKER_FILE}{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"{Fore.RED}Ошибка при сохранении данных о воркере: {e}{Style.RESET_ALL}")

# Функция для загрузки данных о воркере из файла
def load_worker_data():
    try:
        if os.path.exists(WORKER_FILE):
            with open(WORKER_FILE, 'r') as f:
                worker = json.load(f)
            logger.info(f"{Fore.GREEN}Данные о воркере загружены из {WORKER_FILE}{Style.RESET_ALL}")
            return worker
        else:
            logger.info(f"{Fore.YELLOW}Файл {WORKER_FILE} не найден{Style.RESET_ALL}")
            return None
    except Exception as e:
        logger.error(f"{Fore.RED}Ошибка при загрузке данных о воркере: {e}{Style.RESET_ALL}")
        return None

# Функция для обновления статуса воркера
def update_worker(worker_id, active, busy):
    try:
        url = f"{WORKERS_ENDPOINT}{worker_id}/"
        data = {"busy": busy, "active": active}
        logger.info(f"Обновляем воркер {worker_id}: active={active}, busy={busy}")
        response = requests.patch(url, json=data, headers=HEADERS, timeout=10)
        response.raise_for_status()
        logger.info(f"{Fore.GREEN}Воркер {worker_id} обновлен: active={active}, busy={busy}{Style.RESET_ALL}")
        return True
    except requests.RequestException as e:
        logger.error(f"{Fore.RED}Ошибка при обновлении воркера {worker_id}: {e}{Style.RESET_ALL}")
        return False


def update_worker_time(worker_id, read_time_delta):
    try:
        url = f"{WORKERS_ENDPOINT}{worker_id}/"
        # Отправляем только новое время чтения, без учета предыдущего
        data = {"read_time": int(read_time_delta)}
        logger.info(f"Отправляем PATCH-запрос на {url} с данными: {data}")
        response = requests.patch(url, json=data, headers=HEADERS, timeout=10)
        response.raise_for_status()
        logger.info(f"{Fore.GREEN}Воркер {worker_id} обновлен: время чтения {read_time_delta}{Style.RESET_ALL}")
        return True
    except requests.RequestException as e:
        logger.error(f"{Fore.RED}Ошибка при обновлении воркера {worker_id}: {e}{Style.RESET_ALL}")
        logger.error(f"Ответ сервера: {e.response.text if e.response else 'Нет ответа'}")
        return False


# Функция для обновления книги
def update_book(book_id, active_workers_delta=None, read_time_delta=None):
    try:
        url = f"{BOOKS_ENDPOINT}{book_id}/"
        data = {}
        if active_workers_delta is not None:
            data["active_workers"] = active_workers_delta
        if read_time_delta is not None:
            # Отправляем только новое время чтения, без учета предыдущего
            data["read_time"] = int(read_time_delta)
        if not data:
            return True
        logger.info(f"Отправляем PATCH-запрос на {url} с данными: {data}")
        response = requests.patch(url, json=data, headers=HEADERS, timeout=10)
        response.raise_for_status()
        logger.info(f"{Fore.GREEN}Книга {book_id} обновлена: {data}{Style.RESET_ALL}")
        return True
    except requests.RequestException as e:
        logger.error(f"{Fore.RED}Ошибка при обновлении книги {book_id}: {e}{Style.RESET_ALL}")
        logger.error(f"Ответ сервера: {e.response.text if e.response else 'Нет ответа'}")
        return False




# Функция для получения данных о книге по ID
def fetch_book_by_id(book_id):
    try:
        url = f"{BOOKS_ENDPOINT}{book_id}/"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"{Fore.RED}Ошибка при получении книги {book_id}: {e}{Style.RESET_ALL}")
        return None

# Функция для обновления главы
def update_chapter(chapter_id, read_time_delta):
    try:
        url = f"{CHAPTERS_ENDPOINT}{chapter_id}/"
        # Отправляем только новое время чтения, без учета предыдущего
        data = {"read_time": int(read_time_delta)}
        logger.info(f"Отправляем PATCH-запрос на {url} с данными: {data}")
        response = requests.patch(url, json=data, headers=HEADERS, timeout=10)
        response.raise_for_status()
        logger.info(f"{Fore.GREEN}Глава {chapter_id} обновлена: время чтения {read_time_delta}{Style.RESET_ALL}")
        return True
    except requests.RequestException as e:
        logger.error(f"{Fore.RED}Ошибка при обновлении главы {chapter_id}: {e}{Style.RESET_ALL}")
        logger.error(f"Ответ сервера: {e.response.text if e.response else 'Нет ответа'}")
        return False
    
    

# Функция для получения данных о главе по ID
def fetch_chapter_by_id(chapter_id):
    try:
        url = f"{CHAPTERS_ENDPOINT}{chapter_id}/"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"{Fore.RED}Ошибка при получении главы {chapter_id}: {e}{Style.RESET_ALL}")
        return None


# Функция для получения списка прокси
def get_proxy_list():
    max_attempts = 5
    attempt = 0
    while attempt < max_attempts:
        try:
            response = requests.get(PROXY_API_URL, timeout=10)
            response.raise_for_status()
            proxy_list = response.text.strip().split('\n')
            proxy_list = [f"http://{proxy}" if not proxy.startswith("http") else proxy for proxy in proxy_list]
            if not proxy_list:
                logger.warning(f"{Fore.YELLOW}Список прокси пуст, повторная попытка через 10 сек (попытка {attempt + 1}/{max_attempts}){Style.RESET_ALL}")
                attempt += 1
                time.sleep(10)
                continue
            logger.info(f"{Fore.GREEN}Получено {len(proxy_list)} прокси{Style.RESET_ALL}")
            return proxy_list
        except requests.RequestException as e:
            logger.error(f"{Fore.RED}Ошибка при получении списка прокси: {e} (попытка {attempt + 1}/{max_attempts}){Style.RESET_ALL}")
            attempt += 1
            time.sleep(10)
    
    logger.error(f"{Fore.RED}Не удалось получить прокси после {max_attempts} попыток{Style.RESET_ALL}")
    return []





# Конфигурация
# Список user-agents для мобильного режима
user_agents = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 12; SM-G998B Build/SP1A.210812.016) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.104 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.5195.136 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Pixel 4a) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.101 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Mobile Safari/537.36"
]

# Настройка драйвера (мобильный режим)
# Исправим setup_driver, чтобы он принимал конкретный прокси
def setup_driver(use_proxies=USE_PROXIES, visual_mode=VISUAL_MODE, proxy_list=None, retries=0, user_data_dir=None):
    chrome_options = Options()
    if user_data_dir:
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    else:
        chrome_options.add_argument(f"--user-data-dir={tempfile.mkdtemp(prefix='chrome_profile_')}")
    mobile_devices = ["iPhone X", "iPhone 8", "iPhone 6", "Pixel 2", "Pixel 2 XL", "Galaxy S5", "iPad", "Nexus 5X"]
    mobile_emulation = {"deviceName": random.choice(mobile_devices)}
    chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
    if not visual_mode:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    user_agent = random.choice(user_agents)
    chrome_options.add_argument(f"user-agent={user_agent}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    if use_proxies and proxy_list:
        proxy = proxy_list[0]
        chrome_options.add_argument(f'--proxy-server={proxy}')
        logger.info(f"{Fore.CYAN}Применяем прокси: {proxy} (попытка {retries + 1}/{MAX_PROXY_RETRIES}){Style.RESET_ALL}")
    else:
        logger.info(f"{Fore.CYAN}Прокси не используются{Style.RESET_ALL}")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        screen_width = driver.execute_script("return window.innerWidth")
        screen_height = driver.execute_script("return window.innerHeight")
        driver.set_window_size(screen_width, screen_height + 100)
        logger.info(f"{Fore.CYAN}Размер окна установлен: {screen_width}x{screen_height + 100}{Style.RESET_ALL}")
        logger.info(f"{Fore.CYAN}Выбрано устройство для эмуляции: {mobile_emulation['deviceName']}{Style.RESET_ALL}")
        return driver
    except Exception as e:
        logger.error(f"{Fore.RED}Ошибка при настройке драйвера: {e}{Style.RESET_ALL}")
        if driver:
            driver.quit()
        return None

# Проверка на Cloudflare
def check_cloudflare(driver):
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Проверка')]"))
        )
        logger.warning(f"{Fore.YELLOW}Обнаружена проверка Cloudflare. Ожидание...{Style.RESET_ALL}")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(1, 3))
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(random.uniform(1, 3))
        WebDriverWait(driver, 120).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        if "Проверка" in driver.page_source:
            logger.error(f"{Fore.RED}Не удалось пройти проверку Cloudflare{Style.RESET_ALL}")
            return False
        return True
    except TimeoutException:
        logger.info(f"{Fore.GREEN}Проверка Cloudflare не обнаружена или успешно пройдена{Style.RESET_ALL}")
        return True

# Имитация перехода через фильтры
def navigate_through_filters(driver, book):
    try:
        book_id = book["book_id"]
        book_url = f"https://author.today/work/{book_id}"
        driver.get(book_url)
        if not check_cloudflare(driver):
            logger.warning(f"{Fore.YELLOW}Обнаружена проблема с Cloudflare на {book_url}{Style.RESET_ALL}")
            return False
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        logger.info(f"{Fore.CYAN}Страница книги {book_url} успешно загружена{Style.RESET_ALL}")
        read_book_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f"//a[contains(@class, 'btn-read-work') and @href='/reader/{book_id}']"))
        )
        read_book_button.click()
        logger.info(f"{Fore.GREEN}Клик по кнопке 'Читать книгу' выполнен для книги {book_id}{Style.RESET_ALL}")
        time.sleep(random.uniform(1, 3))
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        logger.info(f"{Fore.GREEN}Переход через фильтры выполнен, загружена страница читалки{Style.RESET_ALL}")
        return True
    except TimeoutException as e:
        logger.error(f"{Fore.RED}Таймаут при переходе через фильтры для книги {book_id}: {e}{Style.RESET_ALL}")
        return False
    except Exception as e:
        logger.error(f"{Fore.RED}Неизвестная ошибка при выполнении перехода для книги {book_id}: {e}{Style.RESET_ALL}")
        return False




def read_chapter_mobile(driver, book, read_all, target_book_url, chapter_url, remaining_time, worker_id, apply_read_short=False):
    try:
        initial_delay = random.uniform(1.5, 3.5)
        # time.sleep(initial_delay)
        
        # Находим главу
        chapter = next((ch for ch in book["chapters"] if f"{target_book_url}/{ch['chapter_id']}" == chapter_url), None)
        if not chapter or "chapter_length" not in chapter:
            logger.error(f"{Fore.RED}Глава {chapter_url} не найдена или отсутствует chapter_length{Style.RESET_ALL}")
            return 0, False
        
        chapter_length = chapter["chapter_length"]
        reading_speed = random.uniform(40, 60)
        calculated_reading_time = chapter_length / reading_speed

        is_fully_read = True
        if read_all:
            reading_time = min(calculated_reading_time * random.uniform(0.9, 1.1), remaining_time)
            if apply_read_short:
                # Новая логика: время 90с +/- 15%
                reading_time = random.uniform(90 * 0.85, 90 * 1.15)

            logger.info(f"{Fore.YELLOW}Чтение главы {chapter_url} полностью (read_all=True, apply_read_short = {apply_read_short}): {reading_time:.1f} сек{Style.RESET_ALL}")

        else:
            if random.random() < 0.7:
                reading_time = min(calculated_reading_time * random.uniform(0.1, 0.3), remaining_time)
                is_fully_read = False
                logger.info(f"{Fore.YELLOW}Частичное чтение главы {chapter_url}: {reading_time:.1f} сек{Style.RESET_ALL}")
            else:
                reading_time = min(calculated_reading_time * random.uniform(0.9, 1.1), remaining_time)
        
        logger.info(f"{Fore.YELLOW}Начато чтение главы: {chapter_url}, объем: {chapter_length} символов, скорость: {reading_speed:.1f} сим/сек, планируемое время: {reading_time:.1f} сек{Style.RESET_ALL}")
        
        page_height = driver.execute_script("return document.body.scrollHeight")
        screen_height = driver.execute_script("return window.innerHeight")
        current_position = 0
        time_spent = initial_delay
        min_swipes = max(1, int(reading_time / 2))
        max_swipes = max(1, int(reading_time / 1.5))
        total_swipes_needed = random.randint(min_swipes, max_swipes)
        swipe_distance = max(80, page_height // total_swipes_needed)
        stage_duration = reading_time / total_swipes_needed
        body_element = driver.find_element(By.TAG_NAME, "body")
        actions = ActionChains(driver)
        
        # Интервал отправки времени чтения (10 секунд)
        report_interval = random.uniform(10, 30)
        last_report_time = time_spent
        final_time = 0
        
        for stage in range(total_swipes_needed):
            if time_spent >= reading_time:
                break
            if random.random() < 0.3:
                pause = random.uniform(0.5, 1.5)
                logger.info(f"{Fore.CYAN}Пауза перед свайпом {stage + 1}: {pause:.1f} сек{Style.RESET_ALL}")
                time.sleep(pause)
                time_spent += pause
            
            # Проверяем, прошло ли 10 секунд с последней отправки
            if time_spent - last_report_time >= report_interval:
                read_time_delta = time_spent - last_report_time
                logger.info(f"{Fore.CYAN}Отправка промежуточного времени чтения: {read_time_delta:.1f} сек для книги {book['id']} и главы {chapter['id']}{Style.RESET_ALL}")
                final_time += read_time_delta
                last_report_time = time_spent

            
            actions.move_to_element(body_element).click_and_hold().move_by_offset(0, -swipe_distance).release().perform()
            current_position += swipe_distance
            time.sleep(stage_duration)
            time_spent += stage_duration

        final_read_time = time_spent - last_report_time
        final_time += final_read_time
        if final_read_time > 0:
            logger.info(f"{Fore.CYAN}Отправка финального времени чтения: {final_read_time:.1f} сек{Style.RESET_ALL}")
            update_chapter(chapter["id"], read_time_delta=final_time)
            update_worker_time(worker_id, final_time)
        
        
        logger.info(f"{Fore.GREEN}Глава прочитана за {time_spent:.1f} секунд{' (частично)' if not is_fully_read else ''}{Style.RESET_ALL}")
        return time_spent, is_fully_read
    except Exception as e:
        logger.error(f"{Fore.RED}Ошибка при чтении главы {chapter_url}: {e}{Style.RESET_ALL}")
        return 0, False
    



# Переход к следующей главе через кнопку
def go_to_next_chapter(driver):
    try:
        next_chapter_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@data-bind=\"click: goToChapter.bind($data, nextChapter())\"]"))
        )
        next_chapter_button.click()
        time.sleep(random.uniform(1, 2))
        logger.info(f"{Fore.GREEN}Переход к следующей главе выполнен{Style.RESET_ALL}")
        return True
    except TimeoutException as e:
        logger.warning(f"{Fore.YELLOW}Кнопка следующей главы не найдена: {e}{Style.RESET_ALL}")
        return False
    

def handle_age_verification(driver):
    try:
        # Проверяем наличие кнопки "Да, мне есть 18"
        age_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@data-bind='click: setAdultCookie' and contains(text(), 'Да, мне есть 18')]"))
        )
        logger.info(f"{Fore.CYAN}Обнаружена кнопка подтверждения возраста{Style.RESET_ALL}")
        age_button.click()
        logger.info(f"{Fore.GREEN}Кнопка 'Да, мне есть 18' нажата{Style.RESET_ALL}")
        # Ждём, пока страница обновится после нажатия (если требуется)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        return True
    except TimeoutException:
        logger.info(f"{Fore.GREEN}Кнопка подтверждения возраста не обнаружена, продолжаем без нажатия{Style.RESET_ALL}")
        return False
    except Exception as e:
        logger.error(f"{Fore.RED}Ошибка при обработке кнопки возраста: {e}{Style.RESET_ALL}")
        return False
    


def simulate_session(session_id, worker_id, proxy_list, use_proxies=USE_PROXIES, visual_mode=VISUAL_MODE):
    # Инициализируем запись о сессии
    session_data = {
        "session_id": session_id,
        "worker_id": worker_id,
        "start_time": datetime.utcnow().isoformat(),
        "planned_duration": None,
        "end_time": None,
        "status": "running",
        "error_message": None,
        "chapters_read": 0,
        "total_time_spent": 0
    }
    append_session_log(session_data)

    # Получаем данные воркера
    try:
        response = requests.get(f"{WORKERS_ENDPOINT}{worker_id}/", headers=HEADERS, timeout=10)
        response.raise_for_status()
        worker = response.json()
        logger.info(f"{Fore.GREEN}Данные воркера {worker_id} обновлены перед сессией {session_id}{Style.RESET_ALL}")
    except requests.RequestException as e:
        error_message = f"Ошибка при обновлении данных воркера: {e}"
        logger.error(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
        update_session_log(session_id, {
            "end_time": datetime.utcnow().isoformat(),
            "status": "error",
            "error_message": error_message
        })
        return False

    # Проверяем, назначена ли книга воркеру
    book_id = worker.get("book_id")
    if not book_id:
        error_message = f"У воркера {worker_id} нет назначенной книги"
        logger.warning(f"{Fore.YELLOW}{error_message}{Style.RESET_ALL}")
        update_session_log(session_id, {
            "end_time": datetime.utcnow().isoformat(),
            "status": "error",
            "error_message": error_message
        })
        return False

    # Загружаем актуальные данные о книге
    book = fetch_book_by_id(book_id)
    if not book or "chapters" not in book or not book["active"]:
        error_message = f"Книга {book_id} не найдена, не активна или не содержит глав"
        logger.warning(f"{Fore.YELLOW}{error_message}{Style.RESET_ALL}")
        update_session_log(session_id, {
            "end_time": datetime.utcnow().isoformat(),
            "status": "error",
            "error_message": error_message
        })
        return False

    # ----> НАЧАЛО ИЗМЕНЕНИЙ <----
    read_all = worker.get("read_all", False)
    read_short = worker.get("read_short", False)
    logger.info(f"{Fore.BLUE}Сессия {session_id}: Обрабатываем книгу {book['name']} (ID: {book['book_id']}), read_all={read_all}, read_short={read_short}{Style.RESET_ALL}")
    # ----> КОНЕЦ ИЗМЕНЕНИЙ <----

    if not book["active"]:
        error_message = f"Книга {book['name']} не активна"
        logger.info(f"{Fore.YELLOW}{error_message}{Style.RESET_ALL}")
        update_session_log(session_id, {
            "end_time": datetime.utcnow().isoformat(),
            "status": "error",
            "error_message": error_message
        })
        return False

    use_filters = random.randint(1, 100) <= book["page_percentage"]
    target_book_url = f"https://author.today/reader/{book['book_id']}"
    chapters = [ch for ch in book["chapters"] if ch["active"]]
    if not chapters:
        error_message = f"Нет активных глав для книги {book['name']}"
        logger.warning(f"{Fore.YELLOW}{error_message}{Style.RESET_ALL}")
        update_session_log(session_id, {
            "end_time": datetime.utcnow().isoformat(),
            "status": "error",
            "error_message": error_message
        })
        return False

    # Логируем количество активных глав
    logger.info(f"{Fore.CYAN}Количество активных глав в книге {book['book_id']}: {len(chapters)}{Style.RESET_ALL}")

    # Рассчитываем общее время сессии
    reading_speed = random.uniform(40, 60)
    total_session_time = sum(ch["chapter_length"] / reading_speed * random.uniform(0.9, 1.1) for ch in chapters if "chapter_length" in ch and ch["chapter_length"] > 0)
    if len(chapters) > 1:
        total_session_time += (len(chapters) - 1) * random.uniform(1, 2)
    logger.info(f"{Fore.MAGENTA}Сессия {session_id}: Рассчитанное время сессии: {total_session_time:.1f} сек (скорость чтения: {reading_speed:.1f} сим/сек){Style.RESET_ALL}")

    # Обновляем планируемую длительность в логе
    session_data["planned_duration"] = total_session_time
    update_session_log(session_id, {"planned_duration": total_session_time})

    driver = None
    user_data_dir = None
    proxy_retries = 0

    while proxy_retries < MAX_PROXY_RETRIES:
        # Выбираем прокси
        current_proxy = random.choice(proxy_list) if proxy_list else None
        logger.info(f"{Fore.CYAN}Проверка прокси: {current_proxy} (попытка {proxy_retries + 1}/{MAX_PROXY_RETRIES}){Style.RESET_ALL}")

        # Проверяем текущий прокси
        if use_proxies and current_proxy and not check_proxy(current_proxy):
            logger.warning(f"{Fore.YELLOW}Прокси {current_proxy} нерабочий, пробуем новый{Style.RESET_ALL}")
            proxy_retries += 1
            proxy_list = get_proxy_list() if proxy_retries < MAX_PROXY_RETRIES else []
            if not proxy_list:
                error_message = "Не удалось получить новый список прокси"
                logger.error(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
                update_session_log(session_id, {
                    "end_time": datetime.utcnow().isoformat(),
                    "status": "error",
                    "error_message": error_message
                })
                return False
            continue

        try:
            user_data_dir = tempfile.mkdtemp(prefix="chrome_profile_")
            driver = setup_driver(use_proxies=use_proxies, visual_mode=visual_mode, proxy_list=[current_proxy] if current_proxy else [], user_data_dir=user_data_dir)
            if not driver:
                raise Exception("Не удалось настроить драйвер")

            total_time_spent = 0
            chapters_read_in_session = 0

            logger.info(f"{Fore.MAGENTA}Старт сессии {session_id}, планируемая длительность: {total_session_time:.1f} сек{Style.RESET_ALL}")

            # Заходим на real-rpg-books.ru
            driver.get("https://real-rpg-books.ru/")
            if not check_cloudflare(driver):
                raise Exception("Не удалось пройти Cloudflare на real-rpg-books.ru")

            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            logger.info(f"{Fore.CYAN}Страница real-rpg-books.ru загружена{Style.RESET_ALL}")

            # Время на сайте
            stay_time = random.uniform(3, 5)
            logger.info(f"{Fore.CYAN}Планируемое время на сайте real-rpg-books.ru: {stay_time:.1f} сек{Style.RESET_ALL}")
            page_height = driver.execute_script("return document.body.scrollHeight")
            start_time = time.time()
            while time.time() - start_time < stay_time - 2:
                scroll_distance = random.randint(200, 500)
                direction = random.choice([-1, 1])
                driver.execute_script(f"window.scrollBy(0, {scroll_distance * direction});")
                time.sleep(random.uniform(0.5, 2))

            # Переход по ссылке
            target_link_xpath = f"//a[contains(@href, 'https://author.today/reader/{book['book_id']}/?utm_source=realrpg&utm_medium=referral&utm_campaign=book_link')]"
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    book_link = WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, target_link_xpath))
                    )
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", book_link)
                    time.sleep(random.uniform(0.5, 1.5))
                    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, target_link_xpath)))
                    try:
                        book_link.click()
                        logger.info(f"{Fore.GREEN}Обычный клик по ссылке для книги {book['book_id']} выполнен{Style.RESET_ALL}")
                        break
                    except Exception as e:
                        logger.warning(f"{Fore.YELLOW}Обычный клик не сработал: {e}, пробуем JavaScript-клик{Style.RESET_ALL}")
                        driver.execute_script("arguments[0].click();", book_link)
                        logger.info(f"{Fore.GREEN}JavaScript-клик по ссылке для книги {book['book_id']} выполнен{Style.RESET_ALL}")
                        break
                except TimeoutException:
                    logger.warning(f"{Fore.YELLOW}Попытка {attempt + 1}/{max_attempts}: Ссылка не найдена{Style.RESET_ALL}")
                    if attempt == max_attempts - 1:
                        raise Exception(f"Ссылка для книги {book['book_id']} не найдена")

            total_time_spent += stay_time
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            if not check_cloudflare(driver):
                raise Exception("Не удалось пройти Cloudflare на странице читалки")

            if handle_age_verification(driver):
                total_time_spent += random.uniform(1, 3)

            # Всегда начинаем с первой главы
            current_chapter_index = 0

            while current_chapter_index < len(chapters):
                chapter = chapters[current_chapter_index]
                chapter_url = f"{target_book_url}/{chapter['chapter_id']}"

                # Проверяем корректность chapter_length
                if "chapter_length" not in chapter or chapter["chapter_length"] <= 0:
                    error_message = f"Глава {chapter['chapter_id']} не содержит корректное значение chapter_length"
                    logger.error(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
                    update_session_log(session_id, {
                        "end_time": datetime.utcnow().isoformat(),
                        "status": "error",
                        "error_message": error_message
                    })
                    return False

                # ----> НАЧАЛО ИЗМЕНЕНИЙ <----
                # Определяем, применяется ли read_short к ЭТОЙ главе
                apply_read_short = read_short and current_chapter_index == 0
                # ----> КОНЕЦ ИЗМЕНЕНИЙ <----

                driver.get(chapter_url)
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                logger.info(f"{Fore.CYAN}Загружена страница главы: {chapter_url}{Style.RESET_ALL}")

                # ----> НАЧАЛО ИЗМЕНЕНИЙ <----
                # Читаем главу
                reading_time, is_fully_read = read_chapter_mobile(
                    driver, 
                    book, 
                    read_all, 
                    target_book_url, 
                    chapter_url, 
                    float('inf'), 
                    worker_id,
                    apply_read_short  # <-- Передаем новый флаг
                )
                # ----> КОНЕЦ ИЗМЕНЕНИЙ <----

                if reading_time == 0:
                    logger.warning(f"{Fore.YELLOW}Ошибка чтения главы {chapter_url}, пробуем новый прокси{Style.RESET_ALL}")
                    proxy_retries += 1
                    driver.quit()
                    proxy_list = get_proxy_list() if proxy_retries < MAX_PROXY_RETRIES else []
                    if not proxy_list:
                        error_message = "Не удалось получить новый список прокси"
                        logger.error(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
                        update_session_log(session_id, {
                            "end_time": datetime.utcnow().isoformat(),
                            "status": "error",
                            "error_message": error_message
                        })
                        return False
                    current_proxy = random.choice(proxy_list)
                    continue

                total_time_spent += reading_time
                chapters_read_in_session += 1
                chapter["read_time"] += reading_time
                book["read_time"] = int(float(book["read_time"]) + int(reading_time))

                logger.info(f"{Fore.GREEN}Глава {chapter['chapter_id']} прочитана за {reading_time:.1f} сек{' (частично)' if not is_fully_read else ''}{Style.RESET_ALL}")

                # ----> НАЧАЛО ИЗМЕНЕНИЙ <----
                # Если read_short, выходим ПОСЛЕ первой главы
                if apply_read_short:
                    logger.info(f"{Fore.YELLOW}read_short активен. Завершаем сессию после первой главы.{Style.RESET_ALL}")
                    update_session_log(session_id, {
                        "end_time": datetime.utcnow().isoformat(),
                        "status": "completed",
                        "chapters_read": chapters_read_in_session,
                        "total_time_spent": total_time_spent
                    })
                    return True # Завершаем сессию
                # ----> КОНЕЦ ИЗМЕНЕНИЙ <----


                # Если read_all = False, применяем вероятности завершения
                if not read_all:
                    # Вероятность не перейти ко второй главе (80%)
                    if chapters_read_in_session == 1 and random.random() < 0.80:
                        logger.info(f"{Fore.YELLOW}Пользователь завершил сессию после первой главы{Style.RESET_ALL}")
                        update_session_log(session_id, {
                            "end_time": datetime.utcnow().isoformat(),
                            "status": "completed",
                            "chapters_read": chapters_read_in_session,
                            "total_time_spent": total_time_spent
                        })
                        return True

                    # Если глава прочитана частично, завершаем сессию
                    if not is_fully_read:
                        logger.info(f"{Fore.YELLOW}Глава {chapter['chapter_id']} прочитана частично, завершаем сессию{Style.RESET_ALL}")
                        update_session_log(session_id, {
                            "end_time": datetime.utcnow().isoformat(),
                            "status": "completed",
                            "chapters_read": chapters_read_in_session,
                            "total_time_spent": total_time_spent
                        })
                        return True

                    # Вероятность завершения сессии после текущей главы (20–30%)
                    dropout_chance = random.uniform(0.20, 0.30)
                    if random.random() < dropout_chance:
                        logger.info(f"{Fore.YELLOW}Пользователь завершил сессию после главы {chapter['chapter_id']}{Style.RESET_ALL}")
                        update_session_log(session_id, {
                            "end_time": datetime.utcnow().isoformat(),
                            "status": "completed",
                            "chapters_read": chapters_read_in_session,
                            "total_time_spent": total_time_spent
                        })
                        return True

                # Переход к следующей главе
                next_chapter_index = current_chapter_index + 1
                if next_chapter_index >= len(chapters):
                    logger.info(f"{Fore.YELLOW}Достигнут конец книги, завершаем сессию{Style.RESET_ALL}")
                    update_session_log(session_id, {
                        "end_time": datetime.utcnow().isoformat(),
                        "status": "completed",
                        "chapters_read": chapters_read_in_session,
                        "total_time_spent": total_time_spent
                    })
                    return True
                if go_to_next_chapter(driver):
                    current_chapter_index = next_chapter_index
                    total_time_spent += random.uniform(1, 2)
                else:
                    logger.info(f"{Fore.YELLOW}Не удалось перейти к следующей главе, завершаем сессию{Style.RESET_ALL}")
                    update_session_log(session_id, {
                        "end_time": datetime.utcnow().isoformat(),
                        "status": "completed",
                        "chapters_read": chapters_read_in_session,
                        "total_time_spent": total_time_spent
                    })
                    return True

            logger.info(f"{Fore.MAGENTA}Сессия {session_id} завершена: прочитано {chapters_read_in_session} глав за {total_time_spent:.1f} сек{Style.RESET_ALL}")
            update_session_log(session_id, {
                "end_time": datetime.utcnow().isoformat(),
                "status": "completed",
                "chapters_read": chapters_read_in_session,
                "total_time_spent": total_time_spent
            })
            return True

        except Exception as e:
            logger.warning(f"{Fore.YELLOW}Ошибка с прокси {current_proxy}: {e}. Пробуем новый прокси (попытка {proxy_retries + 1}/{MAX_PROXY_RETRIES}){Style.RESET_ALL}")
            proxy_retries += 1
            if driver:
                driver.quit()
            if user_data_dir and os.path.exists(user_data_dir):
                try:
                    shutil.rmtree(user_data_dir)
                    logger.info(f"{Fore.CYAN}Временная директория {user_data_dir} удалена{Style.RESET_ALL}")
                except Exception as e:
                    logger.error(f"{Fore.RED}Ошибка при удалении {user_data_dir}: {e}{Style.RESET_ALL}")
            proxy_list = get_proxy_list() if proxy_retries < MAX_PROXY_RETRIES else []
            if not proxy_list:
                error_message = "Не удалось получить новый список прокси"
                logger.error(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
                update_session_log(session_id, {
                    "end_time": datetime.utcnow().isoformat(),
                    "status": "error",
                    "error_message": error_message
                })
                return False
            continue

        finally:
            if driver is not None:
                driver.quit()
            if user_data_dir and os.path.exists(user_data_dir):
                try:
                    shutil.rmtree(user_data_dir)
                    logger.info(f"{Fore.CYAN}Временная директория {user_data_dir} удалена{Style.RESET_ALL}")
                except Exception as e:
                    logger.error(f"{Fore.RED}Ошибка при удалении {user_data_dir}: {e}{Style.RESET_ALL}")

    error_message = f"Достигнуто максимальное количество попыток с прокси ({MAX_PROXY_RETRIES})"
    logger.error(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
    update_session_log(session_id, {
        "end_time": datetime.utcnow().isoformat(),
        "status": "error",
        "error_message": error_message
    })
    return False


# Функция для обработки остановки контейнера
def handle_shutdown(signum, frame, worker_id):
    logger.info(f"{Fore.YELLOW}Получен сигнал {signum}, останавливаем воркера {worker_id}{Style.RESET_ALL}")
    if worker_id:
        # Отправляем статус воркера в API: active=False, busy=False
        update_worker(worker_id, active=False, busy=False)
        logger.info(f"{Fore.GREEN}Статус воркера {worker_id} обновлен перед остановкой{Style.RESET_ALL}")
    # Удаляем файл с данными воркера, чтобы при следующем запуске запросить нового
    if os.path.exists(WORKER_FILE):
        os.remove(WORKER_FILE)
        logger.info(f"{Fore.GREEN}Файл {WORKER_FILE} удален{Style.RESET_ALL}")
    sys.exit(0)




def simulate_reading(use_proxies=USE_PROXIES, visual_mode=VISUAL_MODE):
    logger.info(f"{Fore.BLUE}Запуск имитации чтения{Style.RESET_ALL}")

    # Прокси обязательны
    if not use_proxies:
        logger.error(f"{Fore.RED}Прокси обязательны для работы скрипта{Style.RESET_ALL}")
        return

    container_number = get_container_number()
    if not container_number:
        logger.error(f"{Fore.RED}Не удалось определить номер контейнера, завершаем работу{Style.RESET_ALL}")
        return
    
    worker = get_or_create_worker(get_container_number())
    worker_id = worker["id"]

    signal.signal(signal.SIGTERM, lambda signum, frame: handle_shutdown(signum, frame, worker_id))
    signal.signal(signal.SIGINT, lambda signum, frame: handle_shutdown(signum, frame, worker_id))

    session_counter = 1  # Счетчик для уникальных ID сессий

    while True:
        # Получаем список прокси
        proxy_list = get_proxy_list()
        if not proxy_list:
            logger.error(f"{Fore.RED}Не удалось получить прокси, повтор через 60 сек{Style.RESET_ALL}")
            time.sleep(60)
            continue
        
        # Запускаем сессию с воркером
        success = simulate_session(session_counter, worker_id, proxy_list, use_proxies=True, visual_mode=visual_mode)

        if not success:
            logger.warning(f"{Fore.YELLOW}Сессия {session_counter} завершилась с ошибкой, обновляем прокси и пробуем снова{Style.RESET_ALL}")
            proxy_list = get_proxy_list()
            if not proxy_list:
                logger.error(f"{Fore.RED}Не удалось получить прокси, ждем 60 сек{Style.RESET_ALL}")
                time.sleep(60)
                continue
            time.sleep(random.uniform(5, 15))
        
        session_counter += 1  # Увеличиваем счетчик для следующей сессии



if __name__ == "__main__":
    simulate_reading(use_proxies=USE_PROXIES, visual_mode=VISUAL_MODE)