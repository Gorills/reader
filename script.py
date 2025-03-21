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
BOOK_ID = 325682
BOOK_URL = f"https://author.today/reader/{BOOK_ID}"  # Ссылка на книгу
TOTAL_CHAPTERS = 16  # Количество глав
CHAPTER_IDS = [2974946, 2976373, 2979598, 2981670, 2983586, 2985569, 2987502, 2989643, 2991521, 2993718, 2995380, 2997329, 2999595, 3001372, 3003266, 3005314]  # Список ID глав
TOTAL_SESSIONS = 1  # Количество сессий за один цикл чтения
REPEAT_COUNT = 5000  # Количество раз, которые нужно перезапустить чтение книги
CHAPTER_DISTRIBUTION = [50, 20, 10, 10, 5, 3, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0]  # Вероятности выбора глав (для первой сессии)
FILTER_PERCENTAGE = 0  # Процент сессий с переходом через фильтры
MIN_READING_TIME = 180  # Минимальное время чтения одной главы (в секундах)
MAX_READING_TIME = 240  # Максимальное время чтения одной главы (в секундах)
MIN_SESSION_TIME = 1800  # Минимальное время сессии (30 минут в секундах)
MAX_SESSION_TIME = 2400  # Максимальное время сессии (40 минут в секундах)
MAX_WORKERS_DEFAULT = 1  # Количество параллельных сессий по умолчанию
USE_PROXIES = True  # Использовать прокси (True) или нет (False)
PROXY_LIST = []  # Изначально пустой список прокси, будет обновляться перед каждым циклом
VISUAL_MODE = False  # True - видимый браузер и одна сессия, False - скрытый режим и консоль
SESSION_DELAY = (5, 10)  # Диапазон задержки между сессиями (в секундах)
MAX_PROXY_RETRIES = 3

# Глобальное состояние для отслеживания прочитанных глав в текущем цикле
CURRENT_CYCLE_READ_CHAPTERS = set()  # Множество успешно прочитанных глав в текущем цикле

# Установка MAX_WORKERS в зависимости от VISUAL_MODE
MAX_WORKERS = 1 if VISUAL_MODE else MAX_WORKERS_DEFAULT

# Проверка соответствия количества глав и ID
if len(CHAPTER_IDS) != TOTAL_CHAPTERS:
    raise ValueError("Количество CHAPTER_IDS должно соответствовать TOTAL_CHAPTERS")
if len(CHAPTER_DISTRIBUTION) != TOTAL_CHAPTERS:
    CHAPTER_DISTRIBUTION.extend([0] * (TOTAL_CHAPTERS - len(CHAPTER_DISTRIBUTION)))
    logger.warning("Распределение сессий дополнено нулями до количества глав.")

# Проверка корректности времени
if MIN_READING_TIME >= MAX_READING_TIME:
    raise ValueError("MIN_READING_TIME должен быть меньше MAX_READING_TIME")
if MIN_SESSION_TIME >= MAX_SESSION_TIME:
    raise ValueError("MIN_SESSION_TIME должен быть меньше MAX_SESSION_TIME")
if MIN_SESSION_TIME < MIN_READING_TIME:
    raise ValueError("MIN_SESSION_TIME должен быть больше MIN_READING_TIME")

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
def setup_driver(use_proxies=USE_PROXIES, visual_mode=VISUAL_MODE, retries=0):
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
    proxy = None
    if use_proxies and PROXY_LIST:
        proxy = random.choice(PROXY_LIST)
        chrome_options.add_argument(f'--proxy-server={proxy}')
        print(f"{Fore.CYAN}Попытка использовать прокси: {proxy} (попытка {retries + 1}/{MAX_PROXY_RETRIES}){Style.RESET_ALL}")
    else:
        print(f"{Fore.CYAN}Прокси не используются{Style.RESET_ALL}")
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        screen_width = driver.execute_script("return window.innerWidth")
        screen_height = driver.execute_script("return window.innerHeight")
        driver.set_window_size(screen_width, screen_height + 100)
        logger.info(f"{Fore.CYAN}Размер окна установлен: {screen_width}x{screen_height + 100}{Style.RESET_ALL}")
        if use_proxies:
            driver.get(BOOK_URL)
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            print(f"{Fore.GREEN}Прокси {proxy} успешно подключен{Style.RESET_ALL}")
        logger.info(f"{Fore.CYAN}Выбрано устройство для эмуляции: {mobile_emulation['deviceName']}{Style.RESET_ALL}")
        return driver
    except Exception as e:
        if driver:
            driver.quit()
        if use_proxies and retries < MAX_PROXY_RETRIES - 1:
            logger.warning(f"{Fore.YELLOW}Не удалось подключиться через прокси {proxy}: {e}. Повторная попытка...{Style.RESET_ALL}")
            time.sleep(random.uniform(1, 3))
            return setup_driver(use_proxies, visual_mode, retries + 1)
        else:
            logger.error(f"{Fore.RED}Не удалось настроить драйвер после {MAX_PROXY_RETRIES} попыток: {e}{Style.RESET_ALL}")
            return None
    finally:
        if not visual_mode and os.path.exists(user_data_dir):
            shutil.rmtree(user_data_dir, ignore_errors=True)

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
def navigate_through_filters(driver):
    try:
        book_url = f"https://author.today/work/{BOOK_ID}"
        driver.get(book_url)
        if not check_cloudflare(driver):
            logger.warning(f"{Fore.YELLOW}Обнаружена проблема с Cloudflare на {book_url}{Style.RESET_ALL}")
            return False
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        logger.info(f"{Fore.CYAN}Страница книги {book_url} успешно загружена{Style.RESET_ALL}")
        read_book_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f"//a[contains(@class, 'btn-read-work') and @href='/reader/{BOOK_ID}']"))
        )
        read_book_button.click()
        logger.info(f"{Fore.GREEN}Клик по кнопке 'Читать книгу' выполнен для книги {BOOK_ID}{Style.RESET_ALL}")
        time.sleep(random.uniform(1, 3))
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        logger.info(f"{Fore.GREEN}Переход через фильтры выполнен, загружена страница читалки{Style.RESET_ALL}")
        return True
    except TimeoutException as e:
        logger.error(f"{Fore.RED}Таймаут при переходе через фильтры для книги {BOOK_ID}: {e}{Style.RESET_ALL}")
        return False
    except Exception as e:
        logger.error(f"{Fore.RED}Неизвестная ошибка при выполнении перехода для книги {BOOK_ID}: {e}{Style.RESET_ALL}")
        return False

def read_chapter_mobile(driver, chapter_url, remaining_time):
    try:
        initial_delay = random.uniform(1.5, 3.5)
        time.sleep(initial_delay)
        driver.get(chapter_url)
        if not check_cloudflare(driver):
            return 0
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        reading_time = min(random.uniform(MIN_READING_TIME, MAX_READING_TIME), remaining_time)
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
        resource_count = driver.execute_script('return performance.getEntriesByType("resource").length')
        logger.info(f"Количество сетевых запросов: {resource_count}")

        for stage in range(total_swipes_needed):
            if time_spent >= reading_time:
                break
            if random.random() < 0.3:
                pause = random.uniform(0.5, 1.5)
                # logger.info(f"{Fore.CYAN}Пауза перед свайпом {stage + 1}: {pause:.1f} сек{Style.RESET_ALL}")
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

# Одна сессия чтения с учётом непрочитанных глав в текущем цикле
def simulate_session(session_id, use_proxies=USE_PROXIES, visual_mode=VISUAL_MODE):
    global CURRENT_CYCLE_READ_CHAPTERS
    use_filters = random.randint(1, 100) <= FILTER_PERCENTAGE
    session_duration = random.uniform(MIN_SESSION_TIME, MAX_SESSION_TIME)
    driver = setup_driver(use_proxies=use_proxies, visual_mode=visual_mode)
    if not driver:
        logger.error(f"{Fore.RED}Сессия {session_id} не запущена из-за проблем с драйвером{Style.RESET_ALL}")
        return
    
    total_time_spent = 0
    chapters_read_in_session = 0
    
    try:
        logger.info(f"{Fore.MAGENTA}Старт сессии {session_id}, планируемая длительность: {session_duration:.1f} сек{Style.RESET_ALL}")
        logger.info(f"{Fore.CYAN}Прочитано глав в текущем цикле: {len(CURRENT_CYCLE_READ_CHAPTERS)} из {TOTAL_CHAPTERS}{Style.RESET_ALL}")
        
        # Если используем фильтры, идём через страницу книги
        if use_filters:
            if not navigate_through_filters(driver):
                return
            total_time_spent += random.uniform(1, 5)
        
        # Определяем стартовую главу
        if not CURRENT_CYCLE_READ_CHAPTERS:  # Если ещё ничего не прочитано
            current_chapter_index = random.choices(range(TOTAL_CHAPTERS), weights=CHAPTER_DISTRIBUTION, k=1)[0]
        else:  # Начинаем с первой непрочитанной главы
            current_chapter_index = min([i for i in range(TOTAL_CHAPTERS) if i not in CURRENT_CYCLE_READ_CHAPTERS])
        
        # Читаем текущую главу
        while total_time_spent < session_duration and len(CURRENT_CYCLE_READ_CHAPTERS) < TOTAL_CHAPTERS:
            remaining_time = session_duration - total_time_spent
            if remaining_time < MIN_READING_TIME:
                break
            
            chapter_url = f"{BOOK_URL}/{CHAPTER_IDS[current_chapter_index]}"
            if not use_filters:  # Если не использовали фильтры, загружаем главу напрямую
                driver.get(chapter_url)
                if not check_cloudflare(driver):
                    return
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                total_time_spent += random.uniform(1, 3)
                logger.info(f"{Fore.CYAN}Загружена страница главы: {chapter_url}{Style.RESET_ALL}")
            
            reading_time = read_chapter_mobile(driver, chapter_url, remaining_time)
            
            if reading_time > 0:  # Глава прочитана успешно
                total_time_spent += reading_time
                chapters_read_in_session += 1
                CURRENT_CYCLE_READ_CHAPTERS.add(current_chapter_index)
                logger.info(f"{Fore.GREEN}Глава {CHAPTER_IDS[current_chapter_index]} прочитана{Style.RESET_ALL}")
                
                # Переход к следующей главе только после успешного чтения
                next_chapter_index = current_chapter_index + 1
                if next_chapter_index >= TOTAL_CHAPTERS:
                    break
                if go_to_next_chapter(driver):
                    current_chapter_index = next_chapter_index
                    total_time_spent += random.uniform(1, 2)
                else:
                    logger.info(f"{Fore.YELLOW}Нет следующей главы для чтения{Style.RESET_ALL}")
                    break
            else:
                logger.warning(f"{Fore.YELLOW}Глава {CHAPTER_IDS[current_chapter_index]} не была прочитана из-за ошибки{Style.RESET_ALL}")
                break  # Прерываем, чтобы следующая сессия начала с этой же главы
        
        logger.info(f"{Fore.MAGENTA}Сессия {session_id} завершена: прочитано {chapters_read_in_session} глав, всего в цикле {len(CURRENT_CYCLE_READ_CHAPTERS)}/{TOTAL_CHAPTERS}{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"{Fore.RED}Ошибка в сессии {session_id}: {e}{Style.RESET_ALL}")
    finally:
        if driver:
            driver.quit()
        delay = random.uniform(*SESSION_DELAY)
        logger.info(f"{Fore.CYAN}Задержка перед следующей сессией: {delay:.1f} сек{Style.RESET_ALL}")
        time.sleep(delay)



# Основная функция с повторением и обновлением прокси
def simulate_reading(use_proxies=USE_PROXIES, visual_mode=VISUAL_MODE):
    global CURRENT_CYCLE_READ_CHAPTERS
    logger.info(f"{Fore.BLUE}Запуск имитации чтения книги: {BOOK_URL}{Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}Всего сессий за цикл: {TOTAL_SESSIONS}, глав: {TOTAL_CHAPTERS}, через фильтры: {FILTER_PERCENTAGE}%{Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}Вероятности выбора глав: {CHAPTER_DISTRIBUTION}{Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}ID глав: {CHAPTER_IDS}{Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}Время чтения одной главы: от {MIN_READING_TIME} до {MAX_READING_TIME} сек{Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}Длительность сессий: от {MIN_SESSION_TIME} до {MAX_SESSION_TIME} сек{Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}Использование прокси: {'Да' if use_proxies else 'Нет'}{Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}Визуальный режим: {'Включен' if visual_mode else 'Выключен'} (MAX_WORKERS: {MAX_WORKERS}){Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}Количество повторений: {REPEAT_COUNT}{Style.RESET_ALL}")

    for repeat in range(REPEAT_COUNT + 1):
        if use_proxies:
            global PROXY_LIST
            PROXY_LIST = get_proxy_list()
            if not PROXY_LIST:
                logger.warning(f"{Fore.YELLOW}Список прокси пуст, продолжаем без прокси для цикла {repeat + 1}{Style.RESET_ALL}")
                use_proxies = False
            else:
                logger.info(f"{Fore.CYAN}Список прокси обновлён перед циклом {repeat + 1}: {len(PROXY_LIST)} прокси доступно{Style.RESET_ALL}")
        else:
            logger.info(f"{Fore.CYAN}Прокси не используются для цикла {repeat + 1}{Style.RESET_ALL}")

        logger.info(f"{Fore.MAGENTA}Цикл чтения {repeat + 1} из {REPEAT_COUNT + 1}{Style.RESET_ALL}")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(simulate_session, i + (repeat * TOTAL_SESSIONS), use_proxies, visual_mode) for i in range(TOTAL_SESSIONS)]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"{Fore.RED}Ошибка в потоке: {e}{Style.RESET_ALL}")
        
        if len(CURRENT_CYCLE_READ_CHAPTERS) == TOTAL_CHAPTERS:
            logger.info(f"{Fore.GREEN}Книга прочитана полностью в цикле {repeat + 1}{Style.RESET_ALL}")
            CURRENT_CYCLE_READ_CHAPTERS = set()  # Сбрасываем только после полного прочтения
        else:
            logger.warning(f"{Fore.YELLOW}Книга не прочитана полностью в цикле {repeat + 1} ({len(CURRENT_CYCLE_READ_CHAPTERS)}/{TOTAL_CHAPTERS}){Style.RESET_ALL}")
        
        if repeat < REPEAT_COUNT:
            logger.info(f"{Fore.CYAN}Перезапуск цикла чтения...{Style.RESET_ALL}")
            time.sleep(random.uniform(10, 20))
    
    logger.info(f"{Fore.BLUE}Чтение книги завершено после {REPEAT_COUNT + 1} циклов{Style.RESET_ALL}")




if __name__ == "__main__":
    simulate_reading(use_proxies=USE_PROXIES, visual_mode=False)