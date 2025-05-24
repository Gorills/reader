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
def get_or_create_worker():
    
    try:
        response = requests.get(f"{WORKERS_ENDPOINT}assign/", headers=HEADERS, timeout=10)
        response.raise_for_status()
        worker = response.json()
        
        if worker and "id" in worker:
            logger.info(f"{Fore.GREEN}Успешно зарезервирован воркер {worker['id']} с книгой: {worker['book']}{Style.RESET_ALL}")
            return worker
        else:
            logger.warning(f"{Fore.YELLOW}Сервер не вернул свободного воркера{Style.RESET_ALL}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"{Fore.RED}Ошибка при запросе воркера через /assign/: {e}{Style.RESET_ALL}")
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

# Функция для обновления книги
def update_book(book_id, active_workers_delta=None, read_time_delta=None):
    try:
        url = f"{BOOKS_ENDPOINT}{book_id}/"
        current_book = fetch_book_by_id(book_id)
        if not current_book:
            return False
        data = {}
        if active_workers_delta is not None:
            data["active_workers"] = active_workers_delta
        if read_time_delta is not None:
            current_read_time = float(current_book["read_time"])
            # Округляем до целого числа
            data["read_time"] = int(current_read_time + read_time_delta)
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
        current_chapter = fetch_chapter_by_id(chapter_id)
        if current_chapter:
            current_read_time = float(current_chapter["read_time"])
            # Округляем до целого числа
            data = {"read_time": int(current_read_time + read_time_delta)}
            logger.info(f"Отправляем PATCH-запрос на {url} с данными: {data}")
            response = requests.patch(url, json=data, headers=HEADERS, timeout=10)
            response.raise_for_status()
            logger.info(f"{Fore.GREEN}Глава {chapter_id} обновлена: время чтения +{read_time_delta}{Style.RESET_ALL}")
            return True
        return False
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



def read_chapter_mobile(driver, book, target_book_url, chapter_url, remaining_time):
    try:
        initial_delay = random.uniform(1.5, 3.5)
        time.sleep(initial_delay)
        
        # Находим главу
        chapter = next((ch for ch in book["chapters"] if f"{target_book_url}/{ch['chapter_id']}" == chapter_url), None)
        if not chapter or "chapter_length" not in chapter:
            logger.error(f"{Fore.RED}Глава {chapter_url} не найдена или отсутствует chapter_length{Style.RESET_ALL}")
            return 0, False
        
        chapter_length = chapter["chapter_length"]
        reading_speed = random.uniform(40, 60)
        calculated_reading_time = chapter_length / reading_speed
        
        # Вероятность частичного чтения (30% шанс не дочитать главу полностью)
        is_fully_read = True
        if random.random() < 0.3:
            reading_time = min(calculated_reading_time * random.uniform(0.1, 0.5), remaining_time)
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
        
        for stage in range(total_swipes_needed):
            if time_spent >= reading_time:
                break
            if random.random() < 0.3:
                pause = random.uniform(0.5, 1.5)
                logger.info(f"{Fore.CYAN}Пауза перед свайпом {stage + 1}: {pause:.1f} сек{Style.RESET_ALL}")
                time.sleep(pause)
                time_spent += pause
            actions.move_to_element(body_element).click_and_hold().move_by_offset(0, -swipe_distance).release().perform()
            current_position += swipe_distance
            time.sleep(stage_duration)
            time_spent += stage_duration
        
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
    



def simulate_session(book, session_id, worker_id, proxy_list, use_proxies=USE_PROXIES, visual_mode=VISUAL_MODE):
    if not book["active"] or book["workers"] <= book["active_workers"]:
        logger.info(f"{Fore.YELLOW}Книга {book['name']} не активна или нет свободных слотов{Style.RESET_ALL}")
        return False

    use_filters = random.randint(1, 100) <= book["page_percentage"]
    session_duration = random.uniform(book["min_session_time"], book["max_session_time"])
    target_book_url = f"https://author.today/reader/{book['book_id']}"
    chapters = [ch for ch in book["chapters"] if ch["active"]]
    if not chapters:
        logger.warning(f"{Fore.YELLOW}Нет активных глав для книги {book['name']}{Style.RESET_ALL}")
        return False

    driver = None
    user_data_dir = None
    current_proxy = None
    try:
        if use_proxies and proxy_list:
            current_proxy = random.choice(proxy_list)
            logger.info(f"{Fore.CYAN}Используем прокси для сессии: {current_proxy}{Style.RESET_ALL}")
        user_data_dir = tempfile.mkdtemp(prefix="chrome_profile_")
        driver = setup_driver(use_proxies=use_proxies, visual_mode=visual_mode, proxy_list=[current_proxy] if current_proxy else [], user_data_dir=user_data_dir)
        if not driver:
            logger.error(f"{Fore.RED}Сессия {session_id} не запущена из-за проблем с драйвером{Style.RESET_ALL}")
            return False

        total_time_spent = 0
        chapters_read_in_session = 0
        
        logger.info(f"{Fore.MAGENTA}Старт сессии {session_id}, планируемая длительность: {session_duration:.1f} сек{Style.RESET_ALL}")
        
        # Заходим на real-rpg-books.ru
        driver.get("https://real-rpg-books.ru/")
        if not check_cloudflare(driver):
            logger.error(f"{Fore.RED}Не удалось пройти Cloudflare на real-rpg-books.ru{Style.RESET_ALL}")
            return False
        
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        logger.info(f"{Fore.CYAN}Страница real-rpg-books.ru загружена{Style.RESET_ALL}")

        # Время на сайте
        stay_time = random.uniform(10, 20)
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
                    logger.error(f"{Fore.RED}Ссылка для книги {book['book_id']} не найдена{Style.RESET_ALL}")
                    return False
                time.sleep(random.uniform(2, 5))
        
        total_time_spent += stay_time
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        if not check_cloudflare(driver):
            logger.error(f"{Fore.RED}Не удалось пройти Cloudflare на странице читалки{Style.RESET_ALL}")
            return False
        
        if handle_age_verification(driver):
            total_time_spent += random.uniform(1, 3)

        # Всегда начинаем с первой главы
        current_chapter_index = 0
        
        while total_time_spent < session_duration:
            remaining_time = session_duration - total_time_spent
            if remaining_time < book["min_reading_time"]:
                break

            chapter = chapters[current_chapter_index]
            chapter_url = f"{target_book_url}/{chapter['chapter_id']}"
            driver.get(chapter_url)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            logger.info(f"{Fore.CYAN}Загружена страница главы: {chapter_url}{Style.RESET_ALL}")

            reading_time, is_fully_read = read_chapter_mobile(driver, book, target_book_url, chapter_url, remaining_time)
            
            if reading_time == 0:
                logger.warning(f"{Fore.YELLOW}Ошибка чтения главы {chapter_url}, завершаем сессию для перезапуска с новым прокси{Style.RESET_ALL}")
                return False  # Завершаем сессию для перезапуска с новым прокси

            total_time_spent += reading_time
            chapters_read_in_session += 1
            chapter["read_time"] += reading_time
            book["read_time"] = int(float(book["read_time"]) + int(reading_time))
            
            update_book(book["id"], read_time_delta=reading_time)
            update_chapter(chapter["id"], read_time_delta=reading_time)
            
            logger.info(f"{Fore.GREEN}Глава {chapter['chapter_id']} прочитана за {reading_time:.1f} сек{' (частично)' if not is_fully_read else ''}{Style.RESET_ALL}")
            
            # Вероятность не перейти ко второй главе (80%)
            if chapters_read_in_session == 1 and random.random() < 0.80:
                logger.info(f"{Fore.YELLOW}Пользователь завершил сессию после первой главы{Style.RESET_ALL}")
                return True

            # Если глава прочитана частично, завершаем сессию без перехода к следующей
            if not is_fully_read:
                logger.info(f"{Fore.YELLOW}Глава {chapter['chapter_id']} прочитана частично, завершаем сессию{Style.RESET_ALL}")
                return True

            # Вероятность завершения сессии после текущей главы (10–15%)
            dropout_chance = random.uniform(0.20, 0.30)
            if random.random() < dropout_chance:
                logger.info(f"{Fore.YELLOW}Пользователь завершил сессию после главы {chapter['chapter_id']}{Style.RESET_ALL}")
                return True

            # Переход к следующей главе
            next_chapter_index = current_chapter_index + 1
            if next_chapter_index >= len(chapters):
                logger.info(f"{Fore.YELLOW}Достигнут конец книги, завершаем сессию{Style.RESET_ALL}")
                return True
            if go_to_next_chapter(driver):
                current_chapter_index = next_chapter_index
                total_time_spent += random.uniform(1, 2)
            else:
                logger.info(f"{Fore.YELLOW}Не удалось перейти к следующей главе, завершаем сессию{Style.RESET_ALL}")
                return True

        logger.info(f"{Fore.MAGENTA}Сессия {session_id} завершена: прочитано {chapters_read_in_session} глав{Style.RESET_ALL}")
        return True
    
    except Exception as e:
        logger.error(f"{Fore.RED}Ошибка в сессии {session_id}: {e}{Style.RESET_ALL}")
        return False
    finally:
        if driver is not None:
            driver.quit()
        if user_data_dir and os.path.exists(user_data_dir):
            shutil.rmtree(user_data_dir)
            logger.info(f"{Fore.CYAN}Временная директория {user_data_dir} удалена{Style.RESET_ALL}")
        delay = random.uniform(*SESSION_DELAY)
        logger.info(f"{Fore.CYAN}Задержка перед следующей сессией: {delay:.1f} сек{Style.RESET_ALL}")
        time.sleep(delay)



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

    worker = None
    worker_id = None

    signal.signal(signal.SIGTERM, lambda signum, frame: handle_shutdown(signum, frame, worker_id))
    signal.signal(signal.SIGINT, lambda signum, frame: handle_shutdown(signum, frame, worker_id))

    while True:
        # Получаем список прокси
        proxy_list = get_proxy_list()
        if not proxy_list:
            logger.error(f"{Fore.RED}Не удалось получить прокси, повтор через 60 сек{Style.RESET_ALL}")
            time.sleep(60)
            continue

        if not worker:
            delay = random.uniform(1, 15)
            logger.info(f"{Fore.CYAN}Задержка перед началом работы воркера: {delay:.1f} сек{Style.RESET_ALL}")
            time.sleep(delay)
            worker = load_worker_data()
            if worker and "id" in worker and "book" in worker:
                worker_id = worker["id"]
                logger.info(f"{Fore.GREEN}Используем сохраненного воркера {worker_id}{Style.RESET_ALL}")
            else:
                logger.info(f"{Fore.CYAN}Попытка получить нового воркера{Style.RESET_ALL}")
                worker = get_or_create_worker()
                if not worker:
                    logger.error(f"{Fore.RED}Не удалось получить воркера, повтор через 10 сек{Style.RESET_ALL}")
                    time.sleep(10)
                    continue
                worker_id = worker["id"]
                save_worker_data(worker)
                logger.info(f"{Fore.GREEN}Воркер {worker_id} запущен с книгой: {worker['book']}{Style.RESET_ALL}")

        try:
            response = requests.get(f"{WORKERS_ENDPOINT}{worker_id}/", timeout=10)
            response.raise_for_status()
            worker = response.json()
            save_worker_data(worker)
        except requests.RequestException as e:
            logger.error(f"{Fore.RED}Ошибка при обновлении данных воркера {worker_id}: {e}{Style.RESET_ALL}")
            worker = None
            if os.path.exists(WORKER_FILE):
                os.remove(WORKER_FILE)
                logger.info(f"{Fore.GREEN}Файл {WORKER_FILE} удален из-за ошибки API{Style.RESET_ALL}")
            time.sleep(60)
            continue

        book_id = worker["book"]
        if not book_id:
            logger.info(f"{Fore.YELLOW}У воркера {worker_id} нет книги, ждем 60 сек{Style.RESET_ALL}")
            time.sleep(60)
            continue

        available_book = fetch_book_by_id(worker['book_id'])
        if not available_book or not available_book["active"]:
            logger.warning(f"{Fore.YELLOW}Книга {book_id} не найдена или не активна, ждем 60 сек{Style.RESET_ALL}")
            time.sleep(60)
            continue

        logger.info(f"{Fore.BLUE}Обрабатываем книгу: {available_book['name']} (ID: {available_book['book_id']}) с воркером {worker_id}{Style.RESET_ALL}")

        # Случайная задержка перед новой сессией
        delay = random.uniform(5, 40)
        logger.info(f"{Fore.CYAN}Задержка перед новой сессией: {delay:.1f} сек{Style.RESET_ALL}")
        time.sleep(delay)

        # Проверяем, что прокси все еще доступны
        proxy_list = get_proxy_list()
        if not proxy_list:
            logger.error(f"{Fore.RED}Не удалось получить прокси, повтор через 60 сек{Style.RESET_ALL}")
            time.sleep(60)
            continue

        success = simulate_session(available_book, 1, worker_id, proxy_list, use_proxies=True, visual_mode=visual_mode)

        if not success:
            logger.warning(f"{Fore.YELLOW}Сессия завершилась с ошибкой, обновляем прокси и пробуем снова{Style.RESET_ALL}")
            proxy_list = get_proxy_list()
            if not proxy_list:
                logger.error(f"{Fore.RED}Не удалось получить прокси, ждем 60 сек{Style.RESET_ALL}")
                time.sleep(60)
                continue
            time.sleep(random.uniform(5, 15))

if __name__ == "__main__":
    simulate_reading(use_proxies=USE_PROXIES, visual_mode=VISUAL_MODE)