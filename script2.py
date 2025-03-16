import time
import random
import requests
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
from colorama import init, Fore, Style
from multiprocessing import Process, Manager, Lock
import threading


init()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
BOOK_URL = "https://author.today/reader/89419"
TOTAL_CHAPTERS = 6
CHAPTER_IDS = [704052, 705009, 707495, 707877, 708134, 709579]
TOTAL_SESSIONS = 3
CHAPTER_DISTRIBUTION = [50, 30, 10, 5, 3, 1]
MIN_READING_TIME = 10  # Для теста
MAX_READING_TIME = 20
MIN_SESSION_TIME = 30
MAX_SESSION_TIME = 60
VISUAL_MODE = False
SESSION_DELAY = (5, 10)
USE_PROXIES = True
MAX_PROXY_RETRIES = 3

if USE_PROXIES:
    PROXY_LIST = get_proxy_list()
    print(PROXY_LIST)
else:
    PROXY_LIST = []

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


def setup_driver(visual_mode=VISUAL_MODE, proxy=None, retries=0):
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
    
    if USE_PROXIES and PROXY_LIST and proxy:
        chrome_options.add_argument(f"--proxy-server={proxy}")
        logger.info(f"{Fore.CYAN}Попытка использовать прокси: {proxy} (попытка {retries + 1}/{MAX_PROXY_RETRIES}){Style.RESET_ALL}")
    else:
        logger.info(f"{Fore.CYAN}Прокси не используются{Style.RESET_ALL}")

    driver = None
    try:
        driver = uc.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        if USE_PROXIES and proxy:
            driver.get(BOOK_URL)
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            logger.info(f"{Fore.GREEN}Прокси {proxy} успешно подключен{Style.RESET_ALL}")
        
        return driver
    except Exception as e:
        if driver:
            driver.quit()
        if USE_PROXIES and proxy and retries < MAX_PROXY_RETRIES - 1:
            logger.warning(f"{Fore.YELLOW}Не удалось подключиться через прокси {proxy}: {e}. Повторная попытка...{Style.RESET_ALL}")
            time.sleep(random.uniform(1, 3))
            return setup_driver(visual_mode, proxy, retries + 1)
        else:
            logger.error(f"{Fore.RED}Не удалось настроить драйвер после {MAX_PROXY_RETRIES} попыток: {e}{Style.RESET_ALL}")
            return None


def check_cloudflare(driver):
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Проверка')]"))
        )
        logger.warning(f"{Fore.YELLOW}Обнаружена проверка Cloudflare. Пытаемся пройти...{Style.RESET_ALL}")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(2, 4))
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(random.uniform(2, 4))
        WebDriverWait(driver, 120).until(
            EC.invisibility_of_element_located((By.XPATH, "//*[contains(text(), 'Проверка')]"))
        )
        logger.info(f"{Fore.GREEN}Проверка Cloudflare успешно пройдена{Style.RESET_ALL}")
        return True
    except TimeoutException:
        if "Проверка" in driver.page_source:
            logger.error(f"{Fore.RED}Не удалось пройти проверку Cloudflare после 120 секунд{Style.RESET_ALL}")
            return False
        logger.info(f"{Fore.GREEN}Проверка Cloudflare не обнаружена или уже пройдена{Style.RESET_ALL}")
        return True
    except NoSuchElementException:
        logger.info(f"{Fore.GREEN}Элемент проверки Cloudflare не найден, продолжаем{Style.RESET_ALL}")
        return True


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
        
        logger.info(f"{Fore.YELLOW}Начато чтение главы: {chapter_url}, время: {reading_time:.1f} сек{Style.RESET_ALL}")
        
        for _ in range(total_scrolls):
            driver.execute_script(f"window.scrollBy(0, {scroll_step});")
            time.sleep(random.uniform(0.5, 1))
            if random.random() < 0.3:
                driver.execute_script(f"window.scrollBy(0, -{scroll_step // 2});")
                time.sleep(random.uniform(0.2, 0.5))
        
        time.sleep(max(0, reading_time - (total_scrolls * 0.5)))
        logger.info(f"{Fore.GREEN}Прочитана глава: {chapter_url}{Style.RESET_ALL}")
        return reading_time
    except Exception as e:
        logger.error(f"{Fore.RED}Ошибка при чтении главы {chapter_url}: {e}{Style.RESET_ALL}")
        return 0



def go_to_next_chapter(driver):
    try:
        next_chapter_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@data-bind=\"click: goToChapter.bind($data, nextChapter())\"]"))
        )
        next_chapter_button.click()
        time.sleep(random.uniform(1, 2))
        logger.info(f"{Fore.GREEN}Переход к следующей главе{Style.RESET_ALL}")
        return True
    except TimeoutException:
        logger.warning(f"{Fore.YELLOW}Кнопка следующей главы не найдена{Style.RESET_ALL}")
        return False



class BrowserManager:
    def __init__(self):
        self.driver = None
        self.lock = Lock()  # Используем multiprocessing.Lock
        
    def setup(self):
        proxy = random.choice(PROXY_LIST) if USE_PROXIES and PROXY_LIST else None
        self.driver = setup_driver(visual_mode=VISUAL_MODE, proxy=proxy)
        if not self.driver:
            raise Exception("Не удалось запустить браузер")
        
    def get_driver(self):
        return self.driver
        
    def close(self):
        if self.driver:
            self.driver.quit()
            
    def acquire(self):
        self.lock.acquire()
        logger.info(f"{Fore.CYAN}Браузер заблокирован для использования{Style.RESET_ALL}")
        
    def release(self):
        self.lock.release()
        logger.info(f"{Fore.CYAN}Браузер освобожден{Style.RESET_ALL}")

def simulate_session(session_id, browser_manager):
    try:
        session_duration = random.uniform(MIN_SESSION_TIME, MAX_SESSION_TIME)
        total_time_spent = 0
        chapters_read = 0
        read_chapters = set()
        
        logger.info(f"{Fore.MAGENTA}Сессия {session_id}: Старт, планируемая длительность: {session_duration:.1f} сек{Style.RESET_ALL}")
        
        browser_manager.acquire()
        driver = browser_manager.get_driver()
        
        try:
            driver.delete_all_cookies()
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            driver.execute_script("window.localStorage.clear();")
            driver.execute_script("window.sessionStorage.clear();")
            logger.info(f"{Fore.CYAN}Сессия {session_id}: Состояние браузера очищено{Style.RESET_ALL}")
            
            driver.get(BOOK_URL)
            if not check_cloudflare(driver):
                logger.error(f"{Fore.RED}Сессия {session_id} прервана из-за Cloudflare{Style.RESET_ALL}")
                return
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            total_time_spent += random.uniform(1, 3)
            logger.info(f"{Fore.CYAN}Сессия {session_id}: Загружена основная страница: {BOOK_URL}{Style.RESET_ALL}")
            
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
                    logger.info(f"{Fore.YELLOW}Сессия {session_id}: Завершение чтения{Style.RESET_ALL}")
                    break
                
                reading_time = read_chapter(driver, chapter_url, remaining_time)
                total_time_spent += reading_time
                chapters_read += 1
                read_chapters.add(current_chapter_index)
            
            logger.info(f"{Fore.MAGENTA}Сессия {session_id} завершена: прочитано {chapters_read} глав, время: {total_time_spent:.1f} сек{Style.RESET_ALL}")
            
        finally:
            browser_manager.release()
            
        delay = random.uniform(*SESSION_DELAY)
        logger.info(f"{Fore.CYAN}Сессия {session_id}: Задержка: {delay:.1f} сек{Style.RESET_ALL}")
        time.sleep(delay)
        
    except Exception as e:
        logger.error(f"{Fore.RED}Сессия {session_id}: Ошибка: {e}{Style.RESET_ALL}")

def simulate_reading():
    logger.info(f"{Fore.BLUE}Запуск имитации чтения книги: {BOOK_URL}{Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}Всего сессий: {TOTAL_SESSIONS}, глав: {TOTAL_CHAPTERS}{Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}Использование прокси: {'Да' if USE_PROXIES else 'Нет'}{Style.RESET_ALL}")
    
    manager = Manager()
    browser_manager = BrowserManager()
    
    try:
        browser_manager.setup()
        
        processes = []
        for session_id in range(TOTAL_SESSIONS):
            p = Process(target=simulate_session, args=(session_id, browser_manager))
            processes.append(p)
            p.start()
        
        for p in processes:
            p.join()
            
    except Exception as e:
        logger.error(f"{Fore.RED}Глобальная ошибка: {e}{Style.RESET_ALL}")
    finally:
        browser_manager.close()
        logger.info(f"{Fore.BLUE}Браузер закрыт{Style.RESET_ALL}")

if __name__ == "__main__":
    simulate_reading()