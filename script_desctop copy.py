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
USE_PROXIES = False  # Использовать прокси (True) или нет (False)
if USE_PROXIES:
    PROXY_LIST = get_proxy_list()
    print(PROXY_LIST)
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
    
    # Список валидных устройств для mobileEmulation
    mobile_devices = [
        "iPhone X",
        "iPhone 8",
        "iPhone 6",
        "Pixel 2",
        "Pixel 2 XL",
        "Galaxy S5",
        "iPad",
        "Nexus 5X"
    ]
    
    # Настройка мобильной эмуляции
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

    driver = None
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
        
        # Устанавливаем размер окна равным эмулируемому устройству
        screen_width = driver.execute_script("return window.innerWidth")
        screen_height = driver.execute_script("return window.innerHeight")
        driver.set_window_size(screen_width, screen_height + 100)  # Добавляем 100 пикселей для панели браузера
        logger.info(f"{Fore.CYAN}Размер окна установлен: {screen_width}x{screen_height + 100}{Style.RESET_ALL}")
        logger.info(f"{Fore.CYAN}Эмулируемый размер: {screen_width}x{screen_height}{Style.RESET_ALL}")
        
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



def read_chapter_mobile(driver, chapter_url, remaining_time):
    try:
        # Задержка перед загрузкой страницы
        initial_delay = random.uniform(1.5, 3.5)
        time.sleep(initial_delay)

        driver.get(chapter_url)
        
        if not check_cloudflare(driver):
            return 0
        
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        reading_time = min(random.uniform(MIN_READING_TIME, MAX_READING_TIME), remaining_time)
        logger.info(f"{Fore.YELLOW}Начато чтение главы на мобильном: {chapter_url}, планируемое время: {reading_time:.1f} сек{Style.RESET_ALL}")

        # Размеры страницы и экрана
        page_height = driver.execute_script("return document.body.scrollHeight")
        screen_height = driver.execute_script("return window.innerHeight")
        screen_width = driver.execute_script("return window.innerWidth")
        current_position = 0
        time_spent = initial_delay

        # Определяем расстояние одного свайпа (10% высоты экрана для большей частоты)
        swipe_distance = int(screen_height * 0.1)  # 10% высоты экрана
        # Рассчитываем количество свайпов, чтобы покрыть всю страницу
        total_swipes_needed = max(1, int(page_height / swipe_distance)) + 1  # +1 для уверенности
        # Распределяем свайпы по времени чтения
        stage_duration = reading_time / total_swipes_needed

        last_action_time = 0
        min_action_interval = 2  # Уменьшаем минимальный интервал для более частых свайпов

        # Находим элемент body
        body_element = driver.find_element(By.TAG_NAME, "body")

        for stage in range(total_swipes_needed):
            if time_spent >= reading_time or current_position >= page_height:
                break

            remaining_stage_time = min(stage_duration, reading_time - time_spent)

            # Случайная пауза перед свайпом
            if random.random() < 0.2 and (time_spent - last_action_time) >= min_action_interval:
                pause = random.uniform(1, 2)  # Уменьшенная пауза
                logger.info(f"{Fore.CYAN}Читатель задумался перед свайпом {stage + 1}, пауза: {pause:.1f} сек{Style.RESET_ALL}")
                time.sleep(pause)
                time_spent += pause
                last_action_time = time_spent

            # Свайп вверх через ActionChains
            swipe_speed = random.uniform(0.2, 0.5)  # Ускоряем свайпы
            swipe_y_distance = swipe_distance

            # Перемещаем курсор в центр элемента body
            actions = ActionChains(driver)
            actions.move_to_element(body_element).perform()

            # Выполняем свайп
            actions.click_and_hold() \
                   .move_by_offset(0, -swipe_y_distance) \
                   .release() \
                   .perform()
            current_position += swipe_distance
            if current_position > page_height:
                current_position = page_height
            time.sleep(swipe_speed)
            time_spent += swipe_speed
            logger.debug(f"Свайп {stage + 1}/{total_swipes_needed}: current_position={current_position}, scrollY={driver.execute_script('return window.scrollY')}")

            # Случайный свайп назад
            if random.random() < 0.15 and (time_spent - last_action_time) >= min_action_interval:
                back_swipe = swipe_distance * random.uniform(0.4, 0.8)
                back_y_distance = int(back_swipe)
                actions = ActionChains(driver)
                actions.move_to_element(body_element).perform()
                actions.click_and_hold() \
                       .move_by_offset(0, back_y_distance) \
                       .release() \
                       .perform()
                current_position -= back_swipe
                if current_position < 0:
                    current_position = 0
                back_time = random.uniform(0.5, 1.0)  # Уменьшенная пауза
                logger.info(f"{Fore.CYAN}Свайп назад на {back_swipe:.0f} пикселей, задержка: {back_time:.1f} сек{Style.RESET_ALL}")
                time.sleep(back_time)
                time_spent += back_time
                last_action_time = time_spent
                logger.debug(f"После свайпа назад: current_position={current_position}, scrollY={driver.execute_script('return window.scrollY')}")

            # Пауза (отвлекся)
            if random.random() < 0.15 and (time_spent - last_action_time) >= min_action_interval:
                pause_time = random.uniform(1, 3)  # Уменьшенная пауза
                logger.info(f"{Fore.CYAN}Пауза (отвлекся), задержка: {pause_time:.1f} сек{Style.RESET_ALL}")
                time.sleep(pause_time)
                time_spent += pause_time
                last_action_time = time_spent

            extra_delay = max(0, remaining_stage_time - (time_spent - (stage * stage_duration)))
            if extra_delay > 0:
                time.sleep(extra_delay)
                time_spent += extra_delay

        final_pause = random.uniform(1.5, 4)
        time.sleep(final_pause)
        time_spent += final_pause
        logger.info(f"{Fore.CYAN}Чтение завершено, финальная пауза: {final_pause:.1f} сек{Style.RESET_ALL}")

        remaining_delay = max(0, reading_time - time_spent)
        if remaining_delay > 4:
            logger.info(f"{Fore.CYAN}Корректировка времени, добавлено: {remaining_delay:.1f} сек{Style.RESET_ALL}")
            time.sleep(remaining_delay)
            time_spent += remaining_delay
        elif remaining_delay > 0:
            logger.info(f"{Fore.CYAN}Минимальная корректировка, добавлено: {remaining_delay:.1f} сек{Style.RESET_ALL}")
            time.sleep(remaining_delay)
            time_spent += remaining_delay

        logger.info(f"{Fore.GREEN}Прочитана глава на мобильном: {chapter_url}, время: {time_spent:.1f} сек{Style.RESET_ALL}")
        return time_spent
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
        reading_time = read_chapter_mobile(driver, chapter_url, session_duration - total_time_spent)
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
            
            reading_time = read_chapter_mobile(driver, chapter_url, remaining_time)
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
    simulate_reading(use_proxies=USE_PROXIES, visual_mode=True)