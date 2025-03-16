import asyncio
import random
import logging
import time
from colorama import init, Fore, Style
from playwright.async_api import async_playwright
from playwright_stealth import stealth

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

async def bypass_cloudflare(page, url):
    """🔄 Обход Cloudflare через Playwright + Stealth"""
    try:
        logger.info(f"{Fore.CYAN}▶️ Загружаем страницу: {url}{Style.RESET_ALL}")
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(random.uniform(2, 5))  # ⏳ Задержка для естественности
        return True
    except Exception as e:
        logger.error(f"{Fore.RED}❌ Ошибка при загрузке {url}: {e}{Style.RESET_ALL}")
        return False

async def read_chapter(page, chapter_url, remaining_time):
    """📖 Читаем главу (скроллим, задерживаемся)"""
    try:
        if not await bypass_cloudflare(page, chapter_url):
            return 0

        reading_time = min(random.uniform(MIN_READING_TIME, MAX_READING_TIME), remaining_time)
        scrolls = random.randint(10, 20)  # Количество скроллов за сессию

        logger.info(f"{Fore.YELLOW}📖 Читаем главу: {chapter_url}, время: {reading_time:.1f} сек{Style.RESET_ALL}")

        for _ in range(scrolls):
            await page.mouse.wheel(0, random.randint(300, 500))  # 📜 Скроллим вниз
            await asyncio.sleep(random.uniform(1, 3))  # ⏳ Задержка

            if random.random() < 0.2:  # Иногда делаем паузу
                await asyncio.sleep(random.uniform(2, 5))

        await asyncio.sleep(max(0, reading_time - (scrolls * 2)))  # Финальная задержка
        logger.info(f"{Fore.GREEN}✅ Глава прочитана: {chapter_url}{Style.RESET_ALL}")
        return reading_time
    except Exception as e:
        logger.error(f"{Fore.RED}❌ Ошибка при чтении главы {chapter_url}: {e}{Style.RESET_ALL}")
        return 0

async def simulate_session(session_id):
    """🔄 Имитация пользовательской сессии"""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--start-maximized"])  # Запуск в нормальном режиме
            context = await browser.new_context(viewport={"width": 1280, "height": 720})  # Размер окна браузера
            page = await context.new_page()
            await stealth(page)  # Активация Stealth Mode

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
    tasks = [simulate_session(i) for i in range(1)]  # Запуск 1 сессии (можно увеличить)
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
