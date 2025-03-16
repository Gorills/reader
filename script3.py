import time
import random
import requests
import logging
from colorama import init, Fore, Style
from multiprocessing import Process
from fake_useragent import UserAgent
import cloudscraper

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
        logger.info(f"{Fore.GREEN}Получено {len(proxy_list)} прокси: {proxy_list}{Style.RESET_ALL}")
        return proxy_list
    except requests.RequestException as e:
        logger.error(f"{Fore.RED}Ошибка при получении списка прокси: {e}{Style.RESET_ALL}")
        return []

# Конфигурация
BOOK_URL = "https://author.today/reader/89419"
TOTAL_CHAPTERS = 6
CHAPTER_IDS = [704052, 705009, 707495, 707877, 708134, 709579]
TOTAL_SESSIONS = 1
CHAPTER_DISTRIBUTION = [50, 30, 10, 5, 3, 1]
MIN_READING_TIME = 240
MAX_READING_TIME = 360
MIN_SESSION_TIME = 360
MAX_SESSION_TIME = 2400
SESSION_DELAY = (5, 10)
USE_PROXIES = False

if USE_PROXIES:
    PROXY_LIST = get_proxy_list()
    if not PROXY_LIST:
        logger.warning(f"{Fore.YELLOW}Нет доступных прокси, продолжаем без них{Style.RESET_ALL}")
        USE_PROXIES = False
else:
    PROXY_LIST = []

ua = UserAgent()

def bypass_cloudflare(session, url, proxy=None):
    """Попытка обхода защиты Cloudflare с использованием cloudscraper"""
    headers = {
        'User-Agent': ua.random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://author.today/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    proxies = {"http": proxy, "https": proxy} if proxy else None
    
    try:
        logger.info(f"{Fore.CYAN}Попытка загрузки {url} с прокси {proxy}{Style.RESET_ALL}")
        response = session.get(url, headers=headers, proxies=proxies, timeout=15, allow_redirects=True)
        
        if response.status_code == 200:
            logger.info(f"{Fore.GREEN}Загружена страница: {url}{Style.RESET_ALL}")
            return True
        else:
            logger.error(f"{Fore.RED}Не удалось загрузить {url}. Код ответа: {response.status_code}{Style.RESET_ALL}")
            return False
    
    except requests.RequestException as e:
        logger.error(f"{Fore.RED}Ошибка при загрузке {url}: {e}{Style.RESET_ALL}")
        return False

def read_chapter(session, chapter_url, remaining_time, proxy=None):
    """Имитация чтения главы"""
    try:
        time.sleep(random.uniform(1, 3))
        if not bypass_cloudflare(session, chapter_url, proxy):
            return 0
        
        reading_time = min(random.uniform(MIN_READING_TIME, MAX_READING_TIME), remaining_time)
        total_scrolls = random.randint(5, 15)
        
        logger.info(f"{Fore.YELLOW}Начато чтение главы: {chapter_url}, время: {reading_time:.1f} сек{Style.RESET_ALL}")
        
        for _ in range(total_scrolls):
            time.sleep(random.uniform(0.5, 1))
            if random.random() < 0.3:
                time.sleep(random.uniform(0.2, 0.5))
        
        time.sleep(max(0, reading_time - (total_scrolls * 0.5)))
        logger.info(f"{Fore.GREEN}Прочитана глава: {chapter_url}{Style.RESET_ALL}")
        return reading_time
    except Exception as e:
        logger.error(f"{Fore.RED}Ошибка при чтении главы {chapter_url}: {e}{Style.RESET_ALL}")
        return 0

def simulate_session(session_id):
    """Имитация сессии чтения"""
    try:
        session_duration = random.uniform(MIN_SESSION_TIME, MAX_SESSION_TIME)
        total_time_spent = 0
        chapters_read = 0
        read_chapters = set()
        
        logger.info(f"{Fore.MAGENTA}Сессия {session_id}: Старт, планируемая длительность: {session_duration:.1f} сек{Style.RESET_ALL}")
        
        session = cloudscraper.create_scraper()
        proxy = None
        if USE_PROXIES and PROXY_LIST:
            proxy = random.choice(PROXY_LIST)
            logger.info(f"{Fore.CYAN}Сессия {session_id}: Используется прокси {proxy}{Style.RESET_ALL}")
        
        if not bypass_cloudflare(session, BOOK_URL, proxy):
            logger.error(f"{Fore.RED}Сессия {session_id} прервана на начальной загрузке{Style.RESET_ALL}")
            return
        total_time_spent += random.uniform(1, 3)
        
        current_chapter_index = random.choices(range(TOTAL_CHAPTERS), weights=CHAPTER_DISTRIBUTION, k=1)[0]
        chapter_url = f"{BOOK_URL}/{CHAPTER_IDS[current_chapter_index]}"
        reading_time = read_chapter(session, chapter_url, session_duration - total_time_spent, proxy)
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
            if next_chapter_index in available_chapters and random.random() < 0.8:
                current_chapter_index = next_chapter_index
                chapter_url = f"{BOOK_URL}/{CHAPTER_IDS[current_chapter_index]}"
                transition_time = random.uniform(1, 2)
                total_time_spent += transition_time
                logger.info(f"{Fore.GREEN}Сессия {session_id}: Переход к следующей главе{Style.RESET_ALL}")
            else:
                logger.info(f"{Fore.YELLOW}Сессия {session_id}: Завершение чтения{Style.RESET_ALL}")
                break
            
            reading_time = read_chapter(session, chapter_url, remaining_time, proxy)
            total_time_spent += reading_time
            chapters_read += 1
            read_chapters.add(current_chapter_index)
        
        logger.info(f"{Fore.MAGENTA}Сессия {session_id} завершена: прочитано {chapters_read} глав, время: {total_time_spent:.1f} сек{Style.RESET_ALL}")
        
        delay = random.uniform(*SESSION_DELAY)
        logger.info(f"{Fore.CYAN}Сессия {session_id}: Задержка: {delay:.1f} сек{Style.RESET_ALL}")
        time.sleep(delay)
        
    except Exception as e:
        logger.error(f"{Fore.RED}Сессия {session_id}: Ошибка: {e}{Style.RESET_ALL}")

def simulate_reading():
    """Запуск имитации чтения"""
    logger.info(f"{Fore.BLUE}Запуск имитации чтения книги: {BOOK_URL}{Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}Всего сессий: {TOTAL_SESSIONS}, глав: {TOTAL_CHAPTERS}{Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}Использование прокси: {'Да' if USE_PROXIES else 'Нет'}{Style.RESET_ALL}")
    
    processes = []
    
    try:
        for session_id in range(TOTAL_SESSIONS):
            p = Process(target=simulate_session, args=(session_id,))
            processes.append(p)
            p.start()
        
        for p in processes:
            p.join()
            
    except Exception as e:
        logger.error(f"{Fore.RED}Глобальная ошибка: {e}{Style.RESET_ALL}")
    finally:
        logger.info(f"{Fore.BLUE}Имитация чтения завершена{Style.RESET_ALL}")

if __name__ == "__main__":
    simulate_reading()