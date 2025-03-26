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

# Инициализация colorama для цветного вывода в консоли
init()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# URL API для получения данных
API_URL = "https://book.profit-platform.ru/api/v1/"
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
SESSION_DELAY = (5, 10)  # Диапазон задержки между сессиями (в секундах)
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


# Функция для обновления статуса воркера
def update_worker(worker_id, active, busy):
    try:
        url = f"{WORKERS_ENDPOINT}{worker_id}/"
        data = {"busy": busy, "active": active}
        logger.info(f"Обновляем воркер {worker_id}: busy={busy}")
        response = requests.patch(url, json=data, headers=HEADERS, timeout=10)
        response.raise_for_status()
        logger.info(f"{Fore.GREEN}Воркер {worker_id} обновлен: busy={busy}{Style.RESET_ALL}")
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
    api_url = "https://proxy-bunker.com/api2.php"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        proxy_list = response.text.strip().split('\n')
        proxy_list = [f"http://{proxy}" if not proxy.startswith("http") else proxy for proxy in proxy_list]
        additional_proxies = []
        proxy_list.extend(additional_proxies)
        logger.info(f"{Fore.GREEN}Получено {len(proxy_list)} прокси из API и дополнительного списка{Style.RESET_ALL}")
        return proxy_list
    except requests.RequestException as e:
        logger.error(f"{Fore.RED}Ошибка при получении списка прокси: {e}{Style.RESET_ALL}")
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
def setup_driver(use_proxies=USE_PROXIES, visual_mode=VISUAL_MODE, proxy_list=None, retries=0):
    chrome_options = Options()
    user_data_dir = tempfile.mkdtemp(prefix="chrome_profile_")
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
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
        proxy = proxy_list[0]  # Берем первый (и единственный) элемент из списка
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

def read_chapter_mobile(driver, book, chapter_url, remaining_time):
    try:
        initial_delay = random.uniform(1.5, 3.5)
        time.sleep(initial_delay)
        # Убираем driver.get(chapter_url), так как страница уже загружена в simulate_session
        # if not check_cloudflare(driver):  # Эта проверка уже сделана в цикле
        #     return 0
        # WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))  # Это тоже уже сделано
        
        reading_time = min(random.uniform(book["min_reading_time"], book["max_reading_time"]), remaining_time)
        logger.info(f"{Fore.YELLOW}Начато чтение главы: {chapter_url}, планируемое время: {reading_time:.1f} сек{Style.RESET_ALL}")
        page_height = driver.execute_script("return document.body.scrollHeight")
        screen_height = driver.execute_script("return window.innerHeight")
        current_position = 0
        time_spent = initial_delay
        min_swipes = int(reading_time / 2)
        max_swipes = int(reading_time / 1.5)
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
        logger.info(f"{Fore.GREEN}Глава прочитана полностью за {time_spent:.1f} секунд{Style.RESET_ALL}")
        return time_spent
    except Exception as e:
        logger.error(f"{Fore.RED}Ошибка при чтении главы {chapter_url}: {e}{Style.RESET_ALL}")
        return 0

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
    

def simulate_session(book, session_id, worker_id, proxy_list, current_cycle_read_chapters, use_proxies=USE_PROXIES, visual_mode=VISUAL_MODE):
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
    current_proxy = None
    try:
        if use_proxies and proxy_list:
            current_proxy = random.choice(proxy_list)
            logger.info(f"{Fore.CYAN}Используем прокси для сессии: {current_proxy}{Style.RESET_ALL}")
        driver = setup_driver(use_proxies=use_proxies, visual_mode=visual_mode, proxy_list=[current_proxy] if current_proxy else [])
        if not driver:
            logger.error(f"{Fore.RED}Сессия {session_id} не запущена из-за проблем с драйвером{Style.RESET_ALL}")
            return False

        total_time_spent = 0
        chapters_read_in_session = 0
        
        logger.info(f"{Fore.MAGENTA}Старт сессии {session_id}, планируемая длительность: {session_duration:.1f} сек{Style.RESET_ALL}")
        logger.info(f"{Fore.CYAN}Прочитано глав в текущем цикле: {len(current_cycle_read_chapters)} из {len(chapters)}{Style.RESET_ALL}")
        
        # Заходим на real-rpg-books.ru
        driver.get("https://real-rpg-books.ru/")
        if not check_cloudflare(driver):
            logger.error(f"{Fore.RED}Не удалось пройти Cloudflare на real-rpg-books.ru{Style.RESET_ALL}")
            return False
        
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        logger.info(f"{Fore.CYAN}Страница real-rpg-books.ru загружена{Style.RESET_ALL}")

        # Ищем ссылку с нужным book_id
        target_link_xpath = f"//a[contains(@href, 'https://author.today/reader/{book['book_id']}')]"
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                # Прокручиваем страницу вниз, чтобы подгрузился контент
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(1, 2))  # Даём время на подгрузку
                
                # Пробуем найти элемент через XPath
                book_link = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, target_link_xpath))
                )
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", book_link)
                time.sleep(random.uniform(0.5, 1.5))
                
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, target_link_xpath))
                )

                location = book_link.location
                logger.info(f"Позиция ссылки: x={location['x']}, y={location['y']}")
                
                # Пробуем обычный клик
                try:
                    book_link.click()
                    logger.info(f"{Fore.GREEN}Обычный клик по ссылке для книги {book['book_id']} выполнен (попытка {attempt + 1}){Style.RESET_ALL}")
                    break
                except Exception as e:
                    logger.warning(f"{Fore.YELLOW}Обычный клик не сработал: {e}, пробуем JavaScript-клик{Style.RESET_ALL}")
                    driver.execute_script("arguments[0].click();", book_link)
                    logger.info(f"{Fore.GREEN}JavaScript-клик по ссылке для книги {book['book_id']} выполнен (попытка {attempt + 1}){Style.RESET_ALL}")
                    break
                
            except TimeoutException:
                logger.warning(f"{Fore.YELLOW}Попытка {attempt + 1}/{max_attempts}: Ссылка для книги {book['book_id']} не найдена или не кликабельна{Style.RESET_ALL}")
                
                if attempt == max_attempts - 1:
                    logger.error(f"{Fore.RED}Ссылка для книги {book['book_id']} не найдена после {max_attempts} попыток{Style.RESET_ALL}")
                    return False
                time.sleep(random.uniform(2, 5))  # Ждём перед следующей попыткой
        
        total_time_spent += random.uniform(1, 3)

        # Ждем загрузки страницы читалки
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        if not check_cloudflare(driver):
            logger.error(f"{Fore.RED}Не удалось пройти Cloudflare на странице читалки{Style.RESET_ALL}")
            return False
        
        if handle_age_verification(driver):
            total_time_spent += random.uniform(1, 3)

        # Если все главы прочитаны, сбрасываем цикл и меняем прокси
        unread_chapters = [i for i in range(len(chapters)) if i not in current_cycle_read_chapters]
        if not unread_chapters:
            logger.info(f"{Fore.GREEN}Все главы книги {book['name']} прочитаны, начинаем цикл заново с новым прокси{Style.RESET_ALL}")
            current_cycle_read_chapters.clear()
            unread_chapters = list(range(len(chapters)))
            if use_proxies and proxy_list:
                driver.quit()
                current_proxy = random.choice(proxy_list)
                logger.info(f"{Fore.CYAN}Переключаемся на новый прокси: {current_proxy}{Style.RESET_ALL}")
                driver = setup_driver(use_proxies=use_proxies, visual_mode=visual_mode, proxy_list=[current_proxy] if current_proxy else [])
                if not driver:
                    logger.error(f"{Fore.RED}Не удалось перезапустить драйвер с новым прокси{Style.RESET_ALL}")
                    return False
                driver.get(target_book_url)
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # Выбираем стартовую главу
        if not current_cycle_read_chapters:
            chapter_weights = [ch["chapter_distribution"] for ch in chapters]
            current_chapter_index = random.choices(range(len(chapters)), weights=chapter_weights, k=1)[0]
        else:
            current_chapter_index = min(unread_chapters)

        while total_time_spent < session_duration:
            remaining_time = session_duration - total_time_spent
            if remaining_time < book["min_reading_time"]:
                break

            chapter = chapters[current_chapter_index]
            chapter_url = f"{target_book_url}/{chapter['chapter_id']}"
            driver.get(chapter_url)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            logger.info(f"{Fore.CYAN}Загружена страница главы: {chapter_url}{Style.RESET_ALL}")

            reading_time = read_chapter_mobile(driver, book, chapter_url, remaining_time)
            
            if reading_time > 0:
                total_time_spent += reading_time
                chapters_read_in_session += 1
                current_cycle_read_chapters.add(current_chapter_index)
                chapter["read_time"] += reading_time
                book["read_time"] = int(float(book["read_time"]) + int(reading_time))
                
                update_book(book["id"], read_time_delta=reading_time)
                update_chapter(chapter["id"], read_time_delta=reading_time)
                
                logger.info(f"{Fore.GREEN}Глава {chapter['chapter_id']} прочитана за {reading_time:.1f} сек{Style.RESET_ALL}")
                
                unread_chapters = [i for i in range(len(chapters)) if i not in current_cycle_read_chapters]
                if not unread_chapters:
                    logger.info(f"{Fore.GREEN}Все главы прочитаны в этой сессии, начинаем цикл заново с новым прокси{Style.RESET_ALL}")
                    current_cycle_read_chapters.clear()
                    unread_chapters = list(range(len(chapters)))
                    if use_proxies and proxy_list:
                        driver.quit()
                        current_proxy = random.choice(proxy_list)
                        logger.info(f"{Fore.CYAN}Переключаемся на новый прокси: {current_proxy}{Style.RESET_ALL}")
                        driver = setup_driver(use_proxies=use_proxies, visual_mode=visual_mode, proxy_list=[current_proxy] if current_proxy else [])
                        if not driver:
                            logger.error(f"{Fore.RED}Не удалось перезапустить драйвер с новым прокси{Style.RESET_ALL}")
                            return False
                        driver.get(target_book_url)
                        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

                next_chapter_index = current_chapter_index + 1
                if next_chapter_index >= len(chapters):
                    next_chapter_index = 0
                if go_to_next_chapter(driver):
                    current_chapter_index = next_chapter_index
                    total_time_spent += random.uniform(1, 2)
                else:
                    logger.info(f"{Fore.YELLOW}Нет следующей главы для чтения, переходим к первой{Style.RESET_ALL}")
                    current_chapter_index = 0
                    driver.get(f"{target_book_url}/{chapters[0]['chapter_id']}")
                    total_time_spent += random.uniform(1, 3)
            else:
                logger.warning(f"{Fore.YELLOW}Глава {chapter['chapter_id']} не была прочитана из-за ошибки{Style.RESET_ALL}")
                break

        logger.info(f"{Fore.MAGENTA}Сессия {session_id} завершена: прочитано {chapters_read_in_session} глав, всего в цикле {len(current_cycle_read_chapters)}/{len(chapters)}{Style.RESET_ALL}")
        return True
    
    except Exception as e:
        logger.error(f"{Fore.RED}Ошибка в сессии {session_id}: {e}{Style.RESET_ALL}")
        return False
    finally:
        if driver is not None:
            driver.quit()
        delay = random.uniform(*SESSION_DELAY)
        logger.info(f"{Fore.CYAN}Задержка перед следующей сессией: {delay:.1f} сек{Style.RESET_ALL}")
        time.sleep(delay)




def simulate_reading(use_proxies=USE_PROXIES, visual_mode=VISUAL_MODE):
    current_cycle_read_chapters = set()
    logger.info(f"{Fore.BLUE}Запуск имитации чтения{Style.RESET_ALL}")

    delay = random.uniform(1, 40)  # От 1 до 3 минут (60–180 секунд)
    logger.info(f"{Fore.CYAN}Задержка перед созданием воркера: {delay:.1f} сек{Style.RESET_ALL}")
    time.sleep(delay)

    # Получаем воркера один раз при старте
    worker = get_or_create_worker()
    if not worker:
        logger.error(f"{Fore.RED}Не удалось получить воркера. Завершение.{Style.RESET_ALL}")
        return

    worker_id = worker["id"]
    logger.info(f"{Fore.GREEN}Воркер {worker_id} запущен с книгой: {worker['book']}{Style.RESET_ALL}")

    # Загружаем список прокси один раз и передаем его в сессии
    proxy_list = get_proxy_list() if use_proxies else []
    if use_proxies and not proxy_list:
        logger.warning(f"{Fore.YELLOW}Список прокси пуст, продолжаем без прокси{Style.RESET_ALL}")
        use_proxies = False

    # Флаг для отслеживания завершения цикла
    previous_cycle_completed = True

    while True:
        # Получаем актуальные данные воркера
        try:
            response = requests.get(f"{WORKERS_ENDPOINT}{worker_id}/", timeout=10)
            response.raise_for_status()
            worker = response.json()
        except requests.RequestException as e:
            logger.error(f"{Fore.RED}Ошибка при обновлении данных воркера {worker_id}: {e}{Style.RESET_ALL}")
            time.sleep(60)  # Ждем перед повторной попыткой
            continue

        book_id = worker["book"]
        if not book_id:
            logger.info(f"{Fore.YELLOW}У воркера {worker_id} нет привязанной книги, ждем 60 сек{Style.RESET_ALL}")
            time.sleep(60)
            continue

        # Получаем данные книги по ID из поля book
        available_book = fetch_book_by_id(worker['book_id'])
        if not available_book or not available_book["active"]:
            logger.warning(f"{Fore.YELLOW}Книга {book_id} не найдена или не активна, ждем 60 сек{Style.RESET_ALL}")
            time.sleep(60)
            continue

       
        logger.info(f"{Fore.BLUE}Обрабатываем книгу: {available_book['name']} (ID: {available_book['book_id']}) с воркером {worker_id}{Style.RESET_ALL}")

        # Добавляем случайную задержку перед новым чтением, если предыдущий цикл завершен
        if previous_cycle_completed and not current_cycle_read_chapters:
            delay = random.uniform(60, 180)  # От 1 до 3 минут (60–180 секунд)
            logger.info(f"{Fore.CYAN}Задержка перед новым чтением книги: {delay:.1f} сек{Style.RESET_ALL}")
            time.sleep(delay)

        success = simulate_session(available_book, 1, worker_id, proxy_list, current_cycle_read_chapters, use_proxies, visual_mode)


        # Проверяем, завершился ли цикл полностью
        if success and len(current_cycle_read_chapters) == len(available_book["chapters"]):
            previous_cycle_completed = True
        else:
            previous_cycle_completed = False

        if not success:
            logger.warning(f"{Fore.YELLOW}Сессия завершилась с ошибкой, ждем перед следующей попыткой{Style.RESET_ALL}")
            time.sleep(random.uniform(5, 15))

        # Цикл продолжается бесконечно, воркер продолжает проверять book





if __name__ == "__main__":

    # print(fetch_books_data())
    simulate_reading(use_proxies=USE_PROXIES, visual_mode=VISUAL_MODE)