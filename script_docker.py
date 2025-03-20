import time
import random
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import argparse
import logging
from colorama import init, Fore, Style
import requests

# Инициализация colorama для цветного вывода в консоли
init()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Список User-Agent
user_agents = [
    # 📌 Google Chrome (Windows, macOS, Linux, Android, iOS)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Ubuntu 22.04; x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    
    # 📌 Mozilla Firefox (Windows, macOS, Linux, Android)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.3; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Linux; Ubuntu 22.04; x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
   

    # 📌 Microsoft Edge (Windows, macOS, Android)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36 EdgA/122.0.0.0",

    # 📌 Safari (macOS, iOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/537.36 (KHTML, like Gecko) Version/17.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/537.36",
    "Mozilla/5.0 (iPad; CPU OS 17_3 like Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/537.36",

    # 📌 Opera (Windows, macOS, Android)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/95.0.0.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/95.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/95.0.0.0",
    "Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36 OPR/95.0.0.0",

    # 📌 Samsung Internet (2025)
    "Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36 SamsungBrowser/24.0",

    # 📌 Brave (на основе Chrome, Windows, macOS, Linux, Android)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Brave/1.62.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Brave/1.62.0",
    "Mozilla/5.0 (Linux; Ubuntu 22.04; x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Brave/1.62.0",
    "Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36 Brave/1.62.0",

    # 📌 Vivaldi (Windows, macOS, Linux)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Vivaldi/6.4.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Vivaldi/6.4.0",
    "Mozilla/5.0 (Linux; Ubuntu 22.04; x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Vivaldi/6.4.0"
]

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

# Парсер аргументов
parser = argparse.ArgumentParser(description="Имитация чтения книги на author.today")
parser.add_argument("--session-id", type=int, required=True, help="ID сессии")
parser.add_argument("--use-proxies", action="store_true", help="Использовать прокси")
parser.add_argument("--proxy", type=str, help="Специфический прокси (например, http://user:pass@host:port)")
parser.add_argument("--visual-mode", action="store_true", help="Включить визуальный режим")
parser.add_argument("--book-url", type=str, default="https://author.today/reader/89419", help="URL книги")
parser.add_argument("--chapter-ids", nargs="+", type=int, default=[704052, 705009, 707495, 707877, 708134, 709579], help="Список ID глав")
parser.add_argument("--chapter-distribution", nargs="+", type=int, default=[50, 30, 10, 5, 3, 1], help="Вероятности выбора глав")
parser.add_argument("--min-reading-time", type=int, default=120, help="Минимальное время чтения (сек)")
parser.add_argument("--max-reading-time", type=int, default=240, help="Максимальное время чтения (сек)")
parser.add_argument("--min-session-time", type=int, default=1200, help="Минимальное время сессии (сек)")
parser.add_argument("--max-session-time", type=int, default=2400, help="Максимальное время сессии (сек)")
parser.add_argument("--filter-percentage", type=int, default=0, help="Процент сессий с фильтрами (%)")
args = parser.parse_args()

# Конфигурация из аргументов
SESSION_ID = args.session_id
USE_PROXIES = args.use_proxies
PROXY = args.proxy if args.proxy else (random.choice(get_proxy_list()) if USE_PROXIES and get_proxy_list() else None)
VISUAL_MODE = args.visual_mode
BOOK_URL = args.book_url
CHAPTER_IDS = args.chapter_ids
CHAPTER_DISTRIBUTION = args.chapter_distribution
MIN_READING_TIME = args.min_reading_time
MAX_READING_TIME = args.max_reading_time
MIN_SESSION_TIME = args.min_session_time
MAX_SESSION_TIME = args.max_session_time
FILTER_PERCENTAGE = args.filter_percentage
TOTAL_CHAPTERS = len(CHAPTER_IDS)

# Проверка соответствия
if len(CHAPTER_IDS) != len(CHAPTER_DISTRIBUTION):
    logger.error(f"{Fore.RED}Количество CHAPTER_IDS ({len(CHAPTER_IDS)}) не соответствует CHAPTER_DISTRIBUTION ({len(CHAPTER_DISTRIBUTION)}){Style.RESET_ALL}")
    exit(1)

# Настройка драйвера
def setup_driver(use_proxies=USE_PROXIES, visual_mode=VISUAL_MODE, retries=0):
    chrome_options = uc.ChromeOptions()
    if not visual_mode:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    user_agent = random.choice(user_agents)
    chrome_options.add_argument(f"user-agent={user_agent}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-automation")

    driver = None
    proxy = PROXY if use_proxies else None
    
    if use_proxies and proxy:
        chrome_options.add_argument(f'--proxy-server={proxy}')
        logger.info(f"{Fore.CYAN}Попытка использовать прокси: {proxy} (попытка {retries + 1}/3){Style.RESET_ALL}")
    else:
        logger.info(f"{Fore.CYAN}Прокси не используются{Style.RESET_ALL}")

    try:
        driver = uc.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        if use_proxies and proxy:
            driver.get(BOOK_URL)
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            logger.info(f"{Fore.GREEN}Прокси {proxy} успешно подключен{Style.RESET_ALL}")
        
        return driver
    except Exception as e:
        if driver:
            driver.quit()
        if use_proxies and retries < 2:  # Максимум 3 попытки
            logger.warning(f"{Fore.YELLOW}Не удалось подключиться через прокси {proxy}: {e}. Повторная попытка...{Style.RESET_ALL}")
            time.sleep(random.uniform(1, 3))
            return setup_driver(use_proxies, visual_mode, retries + 1)
        else:
            logger.error(f"{Fore.RED}Не удалось настроить драйвер после 3 попыток: {e}{Style.RESET_ALL}")
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
        
        WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        if "Проверка" in driver.page_source:
            logger.error(f"{Fore.RED}Не удалось пройти проверку Cloudflare{Style.RESET_ALL}")
            return False
        return True
    except TimeoutException:
        logger.info(f"{Fore.GREEN}Проверка Cloudflare не обнаружена или успешно пройдена{Style.RESET_ALL}")
        return True

# Имитация перехода через фильтры
def navigate_through_filters(driver):
    try:
        driver.get("https://author.today/works")
        if not check_cloudflare(driver):
            return False
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        filter_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Фэнтези')]"))
        )
        filter_button.click()
        time.sleep(random.uniform(1, 3))
        book_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@href='/reader/89419']"))
        )
        book_link.click()
        logger.info(f"{Fore.GREEN}Переход через фильтры выполнен{Style.RESET_ALL}")
    except TimeoutException as e:
        logger.error(f"{Fore.RED}Ошибка при переходе через фильтры: {e}{Style.RESET_ALL}")
        return False
    return True

# Имитация чтения главы
def read_chapter(driver, chapter_url, remaining_time):
    try:
        time.sleep(random.uniform(2, 5))
        driver.get(chapter_url)
        
        if not check_cloudflare(driver):
            return 0
        
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        reading_time = min(random.uniform(MIN_READING_TIME, MAX_READING_TIME), remaining_time)
        total_scrolls = random.randint(5, 15)
        scroll_step = int(driver.execute_script("return document.body.scrollHeight") / total_scrolls)

        logger.info(f"{Fore.YELLOW}Начато чтение главы: {chapter_url}, планируемое время: {reading_time:.1f} сек{Style.RESET_ALL}")
        
        for _ in range(total_scrolls):
            driver.execute_script(f"window.scrollBy(0, {scroll_step});")
            time.sleep(random.uniform(1, 3))
            if random.random() < 0.3:
                driver.execute_script(f"window.scrollBy(0, -{scroll_step // 2});")
                time.sleep(random.uniform(0.5, 1))
            if random.random() < 0.2:
                time.sleep(random.uniform(1, 3))

        time.sleep(max(0, reading_time - (total_scrolls * 2)))

        logger.info(f"{Fore.GREEN}Прочитана глава: {chapter_url}, время: {reading_time:.1f} сек{Style.RESET_ALL}")
        return reading_time
    except TimeoutException as e:
        logger.error(f"{Fore.RED}Ошибка при загрузке главы {chapter_url}: {e}{Style.RESET_ALL}")
        return 0

# Переход к следующей главе
def go_to_next_chapter(driver):
    try:
        next_chapter_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@data-bind=\"click: goToChapter.bind($data, nextChapter())\"]"))
        )
        next_chapter_button.click()
        time.sleep(random.uniform(1, 2))
        logger.info(f"{Fore.GREEN}Переход к следующей главе выполнен через кнопку{Style.RESET_ALL}")
        return True
    except TimeoutException as e:
        logger.warning(f"{Fore.YELLOW}Кнопка следующей главы не найдена: {e}{Style.RESET_ALL}")
        return False

# Одна сессия чтения
def simulate_session(session_id):
    use_filters = random.randint(1, 100) <= FILTER_PERCENTAGE
    session_duration = random.uniform(MIN_SESSION_TIME, MAX_SESSION_TIME)
    driver = setup_driver(use_proxies=USE_PROXIES, visual_mode=VISUAL_MODE)
    if not driver:
        logger.error(f"{Fore.RED}Сессия {session_id} не запущена из-за проблем с драйвером{Style.RESET_ALL}")
        return
    
    total_time_spent = 0
    chapters_read = 0
    read_chapters = set()
    current_chapter_index = None
    
    try:
        logger.info(f"{Fore.MAGENTA}Старт сессии {session_id}, планируемая длительность: {session_duration:.1f} сек{Style.RESET_ALL}")
        
        if use_filters:
            if not navigate_through_filters(driver):
                return
            total_time_spent += random.uniform(1, 5)
        else:
            driver.get(BOOK_URL)
            if not check_cloudflare(driver):
                return
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            total_time_spent += random.uniform(1, 3)
            logger.info(f"{Fore.CYAN}Загружена основная страница: {BOOK_URL}{Style.RESET_ALL}")
        
        current_chapter_index = random.choices(range(TOTAL_CHAPTERS), weights=CHAPTER_DISTRIBUTION, k=1)[0]
        chapter_url = f"{BOOK_URL}/{CHAPTER_IDS[current_chapter_index]}"
        reading_time = read_chapter(driver, chapter_url, session_duration - total_time_spent)
        total_time_spent += reading_time
        chapters_read += 1
        read_chapters.add(current_chapter_index)
        
        while total_time_spent < session_duration and chapters_read < TOTAL_CHAPTERS:
            remaining_time = session_duration - total_time_spent
            if remaining_time < MIN_READING_TIME:
                break
            
            available_chapters = [i for i in range(TOTAL_CHAPTERS) if i not in read_chapters]
            if not available_chapters:
                break
            
            next_chapter_index = current_chapter_index + 1 if current_chapter_index < TOTAL_CHAPTERS - 1 else None
            if next_chapter_index in available_chapters and go_to_next_chapter(driver):
                current_chapter_index = next_chapter_index
                chapter_url = driver.current_url
                transition_time = random.uniform(1, 2)
                total_time_spent += transition_time
            else:
                logger.info(f"{Fore.YELLOW}Завершение чтения{Style.RESET_ALL}")
                break
            
            reading_time = read_chapter(driver, chapter_url, remaining_time)
            total_time_spent += reading_time
            chapters_read += 1
            read_chapters.add(current_chapter_index)
        
        logger.info(f"{Fore.MAGENTA}Сессия {session_id} завершена: прочитано {chapters_read} глав, время: {total_time_spent:.1f} сек (план: {session_duration:.1f} сек){Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"{Fore.RED}Ошибка в сессии {session_id}: {e}{Style.RESET_ALL}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    simulate_session(SESSION_ID)