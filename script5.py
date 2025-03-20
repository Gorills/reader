import requests
from requests_html import HTMLSession
import random
import time
import logging
from colorama import init, Fore, Style
from multiprocessing import Pool
import os

init()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 📌 Конфигурация
BOOK_URL = "https://author.today/reader/89419"
CHAPTER_IDS = [704052, 705009, 707495, 707877, 708134, 709579]
CHAPTER_DISTRIBUTION = [50, 30, 10, 5, 3, 1]

# ⏳ Временные интервалы
MIN_READING_TIME = 240
MAX_READING_TIME = 360
MIN_SESSION_TIME = 360
MAX_SESSION_TIME = 2400
SESSION_DELAY = (5, 10)
NUM_SESSIONS = 5  # Количество одновременных сессий

def get_proxy_list():
    """Получение списка прокси из API"""
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

def test_proxy(proxy, test_url="https://www.google.com"):
    """Тестирование прокси на работоспособность"""
    session = HTMLSession()
    try:
        response = session.get(test_url, proxies={"http": proxy, "https": proxy}, timeout=10)
        response.html.render()  # Выполнение JavaScript
        logger.info(f"{Fore.GREEN}Прокси {proxy} работает корректно{Style.RESET_ALL}")
        return True
    except Exception as e:
        logger.warning(f"{Fore.YELLOW}Прокси {proxy} не работает: {e}{Style.RESET_ALL}")
        return False

def read_chapter(chapter_url, session, remaining_time):
    """Читаем главу (имитация чтения)"""
    try:
        response = session.get(chapter_url, timeout=10)
        response.html.render()  # Выполнение JavaScript
        content = response.html.find("#reader > div.reader-content.hidden-print", first=True)
        if not content:
            logger.error(f"{Fore.RED}❌ Контент главы не найден на {chapter_url}{Style.RESET_ALL}")
            return 0

        reading_time = min(random.uniform(MIN_READING_TIME, MAX_READING_TIME), remaining_time)
        logger.info(f"{Fore.YELLOW}📖 Читаем главу: {chapter_url}, время: {reading_time:.1f} сек{Style.RESET_ALL}")
        time.sleep(reading_time)
        logger.info(f"{Fore.GREEN}✅ Глава прочитана: {chapter_url}{Style.RESET_ALL}")
        return reading_time
    except Exception as e:
        logger.error(f"{Fore.RED}❌ Ошибка при чтении главы {chapter_url}: {e}{Style.RESET_ALL}")
        return 0

def simulate_session(session_id):
    """Имитация пользовательской сессии"""
    try:
        proxy_list = get_proxy_list()
        working_proxy = None
        session = HTMLSession()

        for proxy in random.sample(proxy_list, min(len(proxy_list), 5)):
            if test_proxy(proxy):
                working_proxy = proxy
                session.proxies = {"http": working_proxy, "https": working_proxy}
                break

        if not working_proxy and proxy_list:
            logger.warning(f"{Fore.YELLOW}⚠️ Не найдено рабочих прокси, работаем без прокси{Style.RESET_ALL}")
        if working_proxy:
            logger.info(f"{Fore.CYAN}Используем прокси: {working_proxy} для сессии {session_id}{Style.RESET_ALL}")

        session_time = random.uniform(MIN_SESSION_TIME, MAX_SESSION_TIME)
        remaining_time = session_time

        logger.info(f"{Fore.MAGENTA}🕵️ Начинаем сессию {session_id}, длительность: {session_time:.1f} сек{Style.RESET_ALL}")

        chapter_urls = [f"{BOOK_URL}/{chapter_id}" for chapter_id in CHAPTER_IDS]
        weighted_chapters = random.choices(chapter_urls, weights=CHAPTER_DISTRIBUTION, k=len(chapter_urls))

        for chapter_url in weighted_chapters:
            if remaining_time <= 0:
                break
            spent_time = read_chapter(chapter_url, session, remaining_time)
            remaining_time -= spent_time

        logger.info(f"{Fore.BLUE}📌 Сессия {session_id} завершена. Осталось времени: {remaining_time:.1f} сек{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"{Fore.RED}❌ Ошибка в сессии {session_id}: {e}{Style.RESET_ALL}")

def main():
    """Запускаем несколько сессий через multiprocessing"""
    with Pool(processes=NUM_SESSIONS) as pool:
        pool.map(simulate_session, range(NUM_SESSIONS))

if __name__ == "__main__":
    main()