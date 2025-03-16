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

# Инициализация colorama для цветного вывода в консоли
init()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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


# Конфигурация
BOOK_URL = "https://author.today/reader/89419"  # Ссылка на книгу
TOTAL_CHAPTERS = 6  # Количество глав
CHAPTER_IDS = [704052, 705009, 707495, 707877, 708134, 709579]  # Список ID глав
TOTAL_SESSIONS = 1  # Общее количество сессий
CHAPTER_DISTRIBUTION = [50, 30, 10, 5, 3, 1]  # Вероятности выбора глав
FILTER_PERCENTAGE = 0  # Процент сессий с переходом через фильтры
MIN_READING_TIME = 120  # Минимальное время чтения одной главы (в секундах)
MAX_READING_TIME = 240  # Максимальное время чтения одной главы (в секундах)
MIN_SESSION_TIME = 1200  # Минимальное время сессии (5 минут в секундах)
MAX_SESSION_TIME = 2400  # Максимальное время сессии (40 минут в секундах)
MAX_WORKERS_DEFAULT = 1  # Количество параллельных сессий по умолчанию
USE_PROXIES = True  # Использовать прокси (True) или нет (False)
if USE_PROXIES:
    PROXY_LIST = get_proxy_list()
    print(PROXY_LIST)
    # PROXY_LIST = ["http://185.158.114.14:26935"]
else:
    PROXY_LIST = []

VISUAL_MODE = False  # True - видимый браузер и одна сессия, False - скрытый режим и консоль
SESSION_DELAY = (5, 10)  # Диапазон задержки между сессиями (в секундах)
MAX_PROXY_RETRIES = 3


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



# Настройка драйвера с использованием undetected-chromedriver
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
    proxy = None
    
    if use_proxies and PROXY_LIST:
        proxy = random.choice(PROXY_LIST)
        chrome_options.add_argument(f'--proxy-server={proxy}')
        print(f"{Fore.CYAN}Попытка использовать прокси: {proxy} (попытка {retries + 1}/{MAX_PROXY_RETRIES}){Style.RESET_ALL}")
    else:
        print(f"{Fore.CYAN}Прокси не используются{Style.RESET_ALL}")

    try:
        driver = uc.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        if use_proxies:
            driver.get(BOOK_URL)
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            print(f"{Fore.GREEN}Прокси {proxy} успешно подключен{Style.RESET_ALL}")
        
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



# Проверка на Cloudflare
def check_cloudflare(driver):
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Проверка')]"))
        )
        logger.warning(f"{Fore.YELLOW}Обнаружена проверка Cloudflare. Ожидание...{Style.RESET_ALL}")
        # Имитация прокрутки для прохождения проверки
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


# Имитация чтения главы с прокруткой (без движения мыши)
def read_chapter(driver, chapter_url, remaining_time):
    try:
        # Случайная задержка перед загрузкой страницы (имитация ожидания)
        time.sleep(random.uniform(2, 5))
        driver.get(chapter_url)
        
        # Проверка на Cloudflare
        if not check_cloudflare(driver):
            return 0
        
        # Ожидаем, пока страница не будет полностью загружена
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # Определяем время чтения (ограничиваем оставшимся временем)
        reading_time = min(random.uniform(MIN_READING_TIME, MAX_READING_TIME), remaining_time)
        total_scrolls = random.randint(5, 15)  # Количество прокруток
        scroll_step = int(driver.execute_script("return document.body.scrollHeight") / total_scrolls)

        # Логируем начало чтения
        logger.info(f"{Fore.YELLOW}Начато чтение главы: {chapter_url}, планируемое время: {reading_time:.1f} сек{Style.RESET_ALL}")
        
        for _ in range(total_scrolls):
            # Прокрутка вниз с случайной задержкой
            driver.execute_script(f"window.scrollBy(0, {scroll_step});")
            time.sleep(random.uniform(1, 3))  # Пауза между прокрутками вниз (случайная)

            # С вероятностью 30% прокручиваем немного вверх (имитация внимания)
            if random.random() < 0.3:  
                driver.execute_script(f"window.scrollBy(0, -{scroll_step // 2});")  # Прокрутка вверх на половину шага
                time.sleep(random.uniform(0.5, 1))  # Пауза после прокрутки вверх

            # Иногда делаем паузу для видимого "читательского" поведения
            if random.random() < 0.2:  # 20% шанс сделать паузу
                time.sleep(random.uniform(1, 3))  # Делать паузу на 1-3 секунды

        # Дополнительная задержка для имитации чтения
        time.sleep(max(0, reading_time - (total_scrolls * 2)))  # Учитываем время на прокрутки

        # Логируем завершение чтения
        logger.info(f"{Fore.GREEN}Прочитана глава: {chapter_url}, время: {reading_time:.1f} сек{Style.RESET_ALL}")
        return reading_time
    except TimeoutException as e:
        logger.error(f"{Fore.RED}Ошибка при загрузке главы {chapter_url}: {e}{Style.RESET_ALL}")
        return 0



# Переход к следующей главе через кнопку
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
def simulate_session(session_id, use_proxies=USE_PROXIES, visual_mode=VISUAL_MODE):
    use_filters = random.randint(1, 100) <= FILTER_PERCENTAGE
    session_duration = random.uniform(MIN_SESSION_TIME, MAX_SESSION_TIME)
    driver = setup_driver(use_proxies=use_proxies, visual_mode=visual_mode)
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
            navigation_time = random.uniform(1, 5)
            total_time_spent += navigation_time
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
                # current_chapter_index = random.choices(available_chapters, weights=[CHAPTER_DISTRIBUTION[i] for i in available_chapters], k=1)[0]
                # chapter_url = f"{BOOK_URL}/{CHAPTER_IDS[current_chapter_index]}"
                # driver.get(chapter_url)
                # transition_time = random.uniform(1, 2)
                # total_time_spent += transition_time
                # logger.info(f"{Fore.CYAN}Переход к случайной главе: {chapter_url}{Style.RESET_ALL}")
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
        delay = random.uniform(*SESSION_DELAY)
        logger.info(f"{Fore.CYAN}Задержка перед следующей сессией: {delay:.1f} сек{Style.RESET_ALL}")
        time.sleep(delay)
        

# Основная функция
def simulate_reading(use_proxies=USE_PROXIES, visual_mode=VISUAL_MODE):
    logger.info(f"{Fore.BLUE}Запуск имитации чтения книги: {BOOK_URL}{Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}Всего сессий: {TOTAL_SESSIONS}, глав: {TOTAL_CHAPTERS}, через фильтры: {FILTER_PERCENTAGE}%{Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}Вероятности выбора глав: {CHAPTER_DISTRIBUTION}{Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}ID глав: {CHAPTER_IDS}{Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}Время чтения одной главы: от {MIN_READING_TIME} до {MAX_READING_TIME} сек{Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}Длительность сессий: от {MIN_SESSION_TIME} до {MAX_SESSION_TIME} сек{Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}Использование прокси: {'Да' if use_proxies else 'Нет'}{Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}Визуальный режим: {'Включен' if visual_mode else 'Выключен'} (MAX_WORKERS: {MAX_WORKERS}){Style.RESET_ALL}")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(simulate_session, i, use_proxies, visual_mode) for i in range(TOTAL_SESSIONS)]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logger.error(f"{Fore.RED}Ошибка в потоке: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    simulate_reading(use_proxies=USE_PROXIES, visual_mode=False)