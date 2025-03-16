import asyncio
import random
import logging
import time
import requests
from colorama import init, Fore, Style
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import stealth_async

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
MAX_RETRIES = 3  # Максимальное количество попыток для загрузки страницы

def get_proxy_list():
    """Получение списка прокси из API"""
    api_url = "https://proxy-bunker.com/api2.php"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        proxy_list = response.text.strip().split('\n')
        proxy_list = [f"http://{proxy}" if not proxy.startswith("http") else proxy for proxy in proxy_list]
        additional_proxies = []  # Дополнительные прокси
        proxy_list.extend(additional_proxies)
        logger.info(f"{Fore.GREEN}Получено {len(proxy_list)} прокси из API и дополнительного списка{Style.RESET_ALL}")
        return proxy_list
    except requests.RequestException as e:
        logger.error(f"{Fore.RED}Ошибка при получении списка прокси: {e}{Style.RESET_ALL}")
        return []

async def test_proxy(proxy, test_url="https://www.google.com", timeout=10000):
    """Тестирование прокси на работоспособность"""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True, proxy={"server": proxy} if proxy else None
            )
            page = await browser.new_page()
            await page.goto(test_url, timeout=timeout, wait_until="domcontentloaded")
            await browser.close()
            return True
    except Exception as e:
        logger.warning(f"{Fore.YELLOW}Прокси {proxy} не работает: {e}{Style.RESET_ALL}")
        return False

async def bypass_cloudflare(page, url, retries=MAX_RETRIES):
    """🔄 Обход Cloudflare с повторными попытками"""
    for attempt in range(retries):
        try:
            logger.info(f"{Fore.CYAN}▶️ Загружаем страницу: {url} (попытка {attempt + 1}/{retries}){Style.RESET_ALL}")
            await page.goto(url, wait_until="networkidle", timeout=30000)  # Увеличиваем таймаут
            await asyncio.sleep(random.uniform(2, 5))  # Задержка для естественности
            return True
        except (PlaywrightTimeoutError, Exception) as e:
            logger.error(f"{Fore.RED}❌ Ошибка при загрузке {url}: {e}{Style.RESET_ALL}")
            if attempt < retries - 1:
                await asyncio.sleep(random.uniform(5, 10))  # Пауза перед повторной попыткой
            else:
                return False
    return False

async def read_chapter(page, chapter_url, remaining_time):
    """📖 Читаем главу (скроллим, задерживаемся)"""
    try:
        if not await bypass_cloudflare(page, chapter_url):
            return 0

        reading_time = min(random.uniform(MIN_READING_TIME, MAX_READING_TIME), remaining_time)
        scrolls = random.randint(10, 20)

        logger.info(f"{Fore.YELLOW}📖 Читаем главу: {chapter_url}, время: {reading_time:.1f} сек{Style.RESET_ALL}")

        for _ in range(scrolls):
            await page.mouse.wheel(0, random.randint(300, 500))
            await asyncio.sleep(random.uniform(1, 3))
            if random.random() < 0.2:
                await asyncio.sleep(random.uniform(2, 5))

        await asyncio.sleep(max(0, reading_time - (scrolls * 2)))
        logger.info(f"{Fore.GREEN}✅ Глава прочитана: {chapter_url}{Style.RESET_ALL}")
        return reading_time
    except Exception as e:
        logger.error(f"{Fore.RED}❌ Ошибка при чтении главы {chapter_url}: {e}{Style.RESET_ALL}")
        return 0

async def simulate_session(session_id, proxy_list):
    """🔄 Имитация пользовательской сессии"""
    try:
        async with async_playwright() as p:
            # Выбираем рабочий прокси
            working_proxy = None
            for proxy in random.sample(proxy_list, min(len(proxy_list), 3)):  # Проверяем до 3 случайных прокси
                if await test_proxy(proxy):
                    working_proxy = proxy
                    break
            
            if not working_proxy and proxy_list:
                logger.warning(f"{Fore.YELLOW}⚠️ Не найдено рабочих прокси, работаем без прокси{Style.RESET_ALL}")
            
            proxy_config = {"server": working_proxy} if working_proxy else None
            if working_proxy:
                logger.info(f"{Fore.CYAN}Используем прокси: {working_proxy} для сессии {session_id}{Style.RESET_ALL}")

            browser = await p.chromium.launch(
                headless=False, args=["--start-maximized"], proxy=proxy_config
            )
            context = await browser.new_context(viewport={"width": 1280, "height": 720})
            page = await context.new_page()
            await stealth_async(page)

            session_time = random.uniform(MIN_SESSION_TIME, MAX_SESSION_TIME)
            remaining_time = session_time

            logger.info(f"{Fore.MAGENTA}🕵️ Начинаем сессию {session_id}, длительность: {session_time:.1f} сек{Style.RESET_ALL}")

            chapter_urls = [f"{BOOK_URL}/{chapter_id}" for chapter_id in CHAPTER_IDS]
            weighted_chapters = random.choices(chapter_urls, weights=CHAPTER_DISTRIBUTION, k=len(chapter_urls))

            for chapter_url in weighted_chapters:
                if remaining_time <= 0:
                    break
                spent_time = await read_chapter(page, chapter_url, remaining_time)
                remaining_time -= spent_time

            logger.info(f"{Fore.BLUE}📌 Сессия {session_id} завершена. Осталось времени: {remaining_time:.1f} сек{Style.RESET_ALL}")
            await browser.close()
    except Exception as e:
        logger.error(f"{Fore.RED}❌ Ошибка в сессии {session_id}: {e}{Style.RESET_ALL}")

async def main():
    """Запускаем несколько сессий"""
    proxy_list = get_proxy_list()
    if not proxy_list:
        logger.warning(f"{Fore.YELLOW}⚠️ Прокси не найдены, работаем без прокси{Style.RESET_ALL}")

    tasks = [simulate_session(i, proxy_list) for i in range(1)]  # Можно увеличить количество сессий
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())