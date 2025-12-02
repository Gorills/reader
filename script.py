import re
import time
import random
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import logging
from colorama import init, Fore, Style
import requests
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
import tempfile
import os
import shutil
import json
import signal
import sys
from datetime import datetime


# Путь к временному файлу для хранения данных о воркере
WORKER_FILE = "/tmp/worker_data.json"  # Путь в /tmp, чтобы файл удалялся при перезапуске контейнера
PROXY_API_URL = "https://proxy-bunker.com/api2.php"

# Инициализация colorama для цветного вывода в консоли
init()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# URL API для получения данных
API_URL = "https://real-rpg-books.ru/api/v1/"
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
VISUAL_MODE = True  # True - видимый браузер и одна сессия, False - скрытый режим и консоль
SESSION_DELAY = (2, 5)  # Диапазон задержки между сессиями (в секундах)
MAX_PROXY_RETRIES = 3

# Константы для оптимизации работы с прокси
PROXY_CHECK_TIMEOUT = 5  # Таймаут проверки прокси в секундах
PROXY_POOL_SIZE = 10  # Размер пула рабочих прокси
PROXY_CHECK_WORKERS = 3  # Количество потоков для параллельной проверки прокси
PROXY_CACHE_TTL = 300  # Время жизни кэша проверки прокси (5 минут)
PROXY_LIST_CACHE_TTL = 60  # Время жизни кэша списка прокси (1 минута)
USE_COOKIES = False  # Использовать явное сохранение cookies (False - cookies сохраняются автоматически через driver)

# Константы для симуляции чтения
READING_SPEED_MIN = 40  # Минимальная скорость чтения (символов в секунду)
READING_SPEED_MAX = 60  # Максимальная скорость чтения (символов в секунду)
PARTIAL_READ_PROBABILITY = 0.7  # Вероятность частичного чтения (70%)
PARTIAL_READ_RATIO_MIN = 0.1  # Минимальный процент прочтения при частичном чтении
PARTIAL_READ_RATIO_MAX = 0.3  # Максимальный процент прочтения при частичном чтении
FULL_READ_RATIO_MIN = 0.9  # Минимальный процент прочтения при полном чтении
FULL_READ_RATIO_MAX = 1.1  # Максимальный процент прочтения при полном чтении
READ_SHORT_TIME_BASE = 90  # Базовое время чтения при read_short (секунды)
READ_SHORT_TIME_VARIATION = 0.15  # Вариация времени read_short (+/-15%)

# Константы для сессии
DROPOUT_AFTER_FIRST_CHAPTER = 0.80  # Вероятность завершения после первой главы (80%)
DROPOUT_PER_CHAPTER_MIN = 0.20  # Минимальная вероятность завершения после каждой главы
DROPOUT_PER_CHAPTER_MAX = 0.30  # Максимальная вероятность завершения после каждой главы
PAUSE_BEFORE_SWIPE_PROBABILITY = 0.3  # Вероятность паузы перед свайпом (30%)
PAUSE_MIN = 0.5  # Минимальная длительность паузы (секунды)
PAUSE_MAX = 1.5  # Максимальная длительность паузы (секунды)
REPORT_INTERVAL_MIN = 10  # Минимальный интервал отправки времени чтения (секунды)
REPORT_INTERVAL_MAX = 30  # Максимальный интервал отправки времени чтения (секунды)

# Константы для навигации и Cloudflare
CLOUDFLARE_WAIT_TIMEOUT = 10  # Таймаут ожидания проверки Cloudflare (секунды)
CLOUDFLARE_MAX_WAIT = 120  # Максимальное время ожидания прохождения Cloudflare (секунды)
PAGE_LOAD_TIMEOUT = 10  # Таймаут загрузки страницы (секунды)
ELEMENT_WAIT_TIMEOUT = 10  # Таймаут ожидания элемента (секунды)
SCROLL_DELAY_MIN = 0.5  # Минимальная задержка между скроллами (секунды)
SCROLL_DELAY_MAX = 2.0  # Максимальная задержка между скроллами (секунды)
STAY_ON_SITE_MIN = 3  # Минимальное время на сайте (секунды)
STAY_ON_SITE_MAX = 5  # Максимальное время на сайте (секунды)

# Константы для улучшенного чтения
READING_SCROLL_BACK_PROBABILITY = 0.15  # Вероятность возврата назад при чтении (15%)
READING_DEEP_PAUSE_PROBABILITY = 0.25  # Вероятность глубокой паузы для "осмысления" (25%)
READING_DEEP_PAUSE_MIN = 2.0  # Минимальная длительность глубокой паузы (секунды)
READING_DEEP_PAUSE_MAX = 5.0  # Максимальная длительность глубокой паузы (секунды)
READING_SCROLL_BACK_DISTANCE_MIN = 0.1  # Минимальная часть экрана для возврата (10%)
READING_SCROLL_BACK_DISTANCE_MAX = 0.4  # Максимальная часть экрана для возврата (40%)
READING_MICRO_PAUSE_PROBABILITY = 0.4  # Вероятность микропаузы (40%)
READING_MICRO_PAUSE_MIN = 0.3  # Минимальная микропауза (секунды)
READING_MICRO_PAUSE_MAX = 1.0  # Максимальная микропауза (секунды)



# Путь к файлу логов сессий
SESSION_LOG_FILE = "/tmp/session_logs.json"

def init_session_log():
    """Инициализирует файл логов сессий, если он не существует."""
    if not os.path.exists(SESSION_LOG_FILE):
        with open(SESSION_LOG_FILE, 'w') as f:
            json.dump([], f)
        logger.info(f"{Fore.GREEN}Создан файл логов сессий: {SESSION_LOG_FILE}{Style.RESET_ALL}")

def append_session_log(session_data):
    """Добавляет запись о сессии в файл логов."""
    try:
        init_session_log()
        with open(SESSION_LOG_FILE, 'r+') as f:
            logs = json.load(f)
            logs.append(session_data)
            f.seek(0)
            json.dump(logs, f, indent=2)
        logger.info(f"{Fore.GREEN}Запись о сессии {session_data['session_id']} добавлена в {SESSION_LOG_FILE}{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"{Fore.RED}Ошибка при записи в файл логов: {e}{Style.RESET_ALL}")

def update_session_log(session_id, updates):
    """Обновляет запись о сессии в файле логов."""
    try:
        init_session_log()
        with open(SESSION_LOG_FILE, 'r+') as f:
            logs = json.load(f)
            for log in logs:
                if log['session_id'] == session_id:
                    log.update(updates)
                    break
            f.seek(0)
            f.truncate()
            json.dump(logs, f, indent=2)
        logger.info(f"{Fore.GREEN}Запись о сессии {session_id} обновлена{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"{Fore.RED}Ошибка при обновлении файла логов: {e}{Style.RESET_ALL}")



def check_proxy(proxy, timeout=PROXY_CHECK_TIMEOUT, verbose=False):
    """
    Проверяет прокси на доступность сайта real-rpg-books.ru и наличие ссылки с utm_source=realrpg.
    Оптимизированная версия без Selenium fallback для быстрой проверки.
    
    Args:
        proxy (str): Прокси в формате http://ip:port
        timeout (int): Таймаут для HTTP-запроса в секундах
        verbose (bool): Выводить подробное логирование
    
    Returns:
        bool: True если прокси рабочий, False если нерабочий
    """
    # Очищаем строку прокси от лишних символов
    proxy = proxy.strip()
    # Проверяем формат прокси с помощью регулярного выражения
    proxy_pattern = r'^(http|https)://[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}:[0-9]{1,5}$'
    if not re.match(proxy_pattern, proxy):
        if verbose:
            logger.debug(f"{Fore.YELLOW}Прокси {proxy} имеет неверный формат{Style.RESET_ALL}")
        return False

    # Проверка через requests (без Selenium для ускорения)
    try:
        session = requests.Session()
        session.proxies = {"http": proxy, "https": proxy}
        headers = {"User-Agent": random.choice(user_agents)}
        
        if verbose:
            logger.debug(f"{Fore.CYAN}Проверка прокси {proxy}...{Style.RESET_ALL}")
        
        response = session.get("https://real-rpg-books.ru", headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # Проверяем наличие ссылки с utm_source=realrpg
        if "utm_source=realrpg" in response.text:
            if verbose:
                logger.info(f"{Fore.GREEN}Прокси {proxy} рабочий: сайт доступен, ссылка найдена{Style.RESET_ALL}")
            return True
        else:
            if verbose:
                logger.debug(f"{Fore.YELLOW}Прокси {proxy} доступен, но ссылка utm_source=realrpg не найдена{Style.RESET_ALL}")
            # Прокси работает, но ссылки нет - все равно считаем рабочим
            # (ссылка может появиться позже или быть динамической)
            return True  # Изменено: принимаем прокси, если сайт доступен
            
    except requests.exceptions.Timeout:
        if verbose:
            logger.debug(f"{Fore.YELLOW}Прокси {proxy} таймаут{Style.RESET_ALL}")
        return False
    except requests.exceptions.ProxyError as e:
        if verbose:
            logger.debug(f"{Fore.YELLOW}Прокси {proxy} ошибка подключения: {e}{Style.RESET_ALL}")
        return False
    except requests.RequestException as e:
        if verbose:
            logger.debug(f"{Fore.YELLOW}Прокси {proxy} ошибка запроса: {type(e).__name__}{Style.RESET_ALL}")
        return False


class ProxyPool:
    """
    Класс для управления пулом проверенных прокси.
    Оптимизирует работу с прокси, минимизируя количество проверок.
    """
    def __init__(self, max_size=PROXY_POOL_SIZE, check_workers=PROXY_CHECK_WORKERS, cache_ttl=PROXY_CACHE_TTL):
        self.working_proxies = []  # Пул рабочих прокси
        self.checked_proxies = {}  # Кэш проверенных {proxy: (is_working, timestamp)}
        self.max_size = max_size
        self.check_workers = check_workers
        self.cache_ttl = cache_ttl
        self.proxy_list_cache = []
        self.proxy_list_cache_time = 0
        self.lock = None  # Будет использоваться threading.Lock если понадобится
        
    def _get_proxy_list_cached(self):
        """Получает список прокси с кэшированием"""
        current_time = time.time()
        if (current_time - self.proxy_list_cache_time) < PROXY_LIST_CACHE_TTL and self.proxy_list_cache:
            return self.proxy_list_cache.copy()
        
        # Обновляем кэш
        proxy_list = get_proxy_list()
        if proxy_list:
            self.proxy_list_cache = proxy_list
            self.proxy_list_cache_time = current_time
        return proxy_list
    
    def _check_proxies_batch(self, proxy_list):
        """
        Проверяет прокси параллельно с ограничением количества потоков.
        
        Args:
            proxy_list: Список прокси для проверки
            
        Returns:
            list: Список рабочих прокси
        """
        if not proxy_list:
            return []
        
        working = []
        checked_count = 0
        total_to_check = len(proxy_list)
        
        logger.info(f"{Fore.CYAN}Начинаем проверку {total_to_check} прокси (потоков: {self.check_workers}){Style.RESET_ALL}")
        
        # Используем ThreadPoolExecutor для параллельной проверки
        with ThreadPoolExecutor(max_workers=self.check_workers) as executor:
            # Создаем задачи на проверку
            futures = {executor.submit(check_proxy, proxy, PROXY_CHECK_TIMEOUT, verbose=False): proxy for proxy in proxy_list}
            
            # Обрабатываем результаты по мере готовности
            for future in as_completed(futures):
                proxy = futures[future]
                checked_count += 1
                try:
                    is_working = future.result()
                    # Обновляем кэш
                    self.checked_proxies[proxy] = (is_working, time.time())
                    
                    if is_working:
                        working.append(proxy)
                        logger.info(f"{Fore.GREEN}✓ Прокси {proxy} рабочий ({len(working)}/{checked_count}){Style.RESET_ALL}")
                    else:
                        logger.debug(f"{Fore.YELLOW}✗ Прокси {proxy} нерабочий{Style.RESET_ALL}")
                except Exception as e:
                    logger.warning(f"{Fore.YELLOW}Ошибка проверки {proxy}: {type(e).__name__}: {e}{Style.RESET_ALL}")
                    self.checked_proxies[proxy] = (False, time.time())
                
                # Показываем прогресс каждые 10 проверок
                if checked_count % 10 == 0:
                    logger.info(f"{Fore.CYAN}Прогресс проверки: {checked_count}/{total_to_check}, найдено рабочих: {len(working)}{Style.RESET_ALL}")
        
        logger.info(f"{Fore.GREEN}Проверка завершена: {len(working)}/{total_to_check} прокси рабочих{Style.RESET_ALL}")
        return working
    
    def _refresh_pool(self):
        """Обновляет пул рабочих прокси из кэша и новых проверок"""
        current_time = time.time()
        
        # Очищаем устаревшие записи из кэша
        self.checked_proxies = {
            proxy: (status, timestamp)
            for proxy, (status, timestamp) in self.checked_proxies.items()
            if (current_time - timestamp) < self.cache_ttl
        }
        
        # Добавляем рабочие прокси из кэша в пул
        cached_working = [
            proxy for proxy, (is_working, _) in self.checked_proxies.items()
            if is_working and proxy not in self.working_proxies
        ]
        self.working_proxies.extend(cached_working[:self.max_size - len(self.working_proxies)])
        
        # Если пул не полный, проверяем новые прокси
        if len(self.working_proxies) < self.max_size:
            proxy_list = self._get_proxy_list_cached()
            if not proxy_list:
                return False
            
            # Фильтруем уже проверенные
            unchecked = [
                proxy for proxy in proxy_list
                if proxy not in self.checked_proxies
            ]
            
            if unchecked:
                # Проверяем больше прокси, чтобы найти достаточно рабочих
                needed = self.max_size - len(self.working_proxies)
                # Увеличиваем количество для проверки (в 5 раз больше для надежности)
                to_check = unchecked[:needed * 5]  # Проверяем в 5 раз больше для надежности
                
                logger.info(f"{Fore.CYAN}Нужно рабочих прокси: {needed}, проверяем: {len(to_check)}{Style.RESET_ALL}")
                new_working = self._check_proxies_batch(to_check)
                
                if new_working:
                    self.working_proxies.extend(new_working[:needed])
                    logger.info(
                        f"{Fore.GREEN}Пул прокси обновлен: {len(self.working_proxies)}/{self.max_size} рабочих{Style.RESET_ALL}"
                    )
                else:
                    logger.warning(f"{Fore.YELLOW}Не найдено рабочих прокси из {len(to_check)} проверенных{Style.RESET_ALL}")
            else:
                logger.warning(f"{Fore.YELLOW}Нет непроверенных прокси для проверки{Style.RESET_ALL}")
        
        return len(self.working_proxies) > 0
    
    def get_working_proxy(self):
        """
        Возвращает рабочий прокси из пула. Автоматически обновляет пул при необходимости.
        
        Returns:
            str|None: Рабочий прокси или None если не удалось получить
        """
        # Удаляем прокси из пула, чтобы не использовать повторно сразу
        if self.working_proxies:
            return self.working_proxies.pop(0)
        
        # Если пул пуст, пытаемся обновить
        if self._refresh_pool():
            if self.working_proxies:
                return self.working_proxies.pop(0)
        
        return None
    
    def invalidate_proxy(self, proxy):
        """Помечает прокси как нерабочий и удаляет из пула"""
        if proxy in self.working_proxies:
            self.working_proxies.remove(proxy)
        
        # Обновляем кэш
        self.checked_proxies[proxy] = (False, time.time())
        logger.debug(f"{Fore.YELLOW}Прокси {proxy} помечен как нерабочий{Style.RESET_ALL}")
    
    def ensure_pool_size(self):
        """Обеспечивает минимальный размер пула рабочих прокси"""
        if len(self.working_proxies) < self.max_size // 2:
            self._refresh_pool()



class APIClient:
    """
    Класс для централизованной работы с API.
    Группирует все API запросы для улучшения читаемости и поддержки.
    """
    def __init__(self, api_url=API_URL, api_key=API_KEY):
        self.api_url = api_url
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        self.timeout = 10
    
    def get_books(self):
        """Получает список всех книг"""
        try:
            response = requests.get(f"{self.api_url}books/", timeout=self.timeout)
            response.raise_for_status()
            books = response.json()
            logger.info(f"{Fore.GREEN}Получены данные о {len(books)} книгах из API{Style.RESET_ALL}")
            return books
        except requests.RequestException as e:
            logger.error(f"{Fore.RED}Ошибка при загрузке данных из API: {e}{Style.RESET_ALL}")
            return []
    
    def get_book(self, book_id):
        """Получает данные о книге по ID"""
        try:
            url = f"{self.api_url}books/{book_id}/"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"{Fore.RED}Ошибка при получении книги {book_id}: {e}{Style.RESET_ALL}")
            return None
    
    def update_book(self, book_id, active_workers_delta=None, read_time_delta=None):
        """Обновляет данные книги"""
        try:
            url = f"{self.api_url}books/{book_id}/"
            data = {}
            if active_workers_delta is not None:
                data["active_workers"] = active_workers_delta
            if read_time_delta is not None:
                data["read_time"] = int(read_time_delta)
            if not data:
                return True
            logger.info(f"Отправляем PATCH-запрос на {url} с данными: {data}")
            response = requests.patch(url, json=data, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            logger.info(f"{Fore.GREEN}Книга {book_id} обновлена: {data}{Style.RESET_ALL}")
            return True
        except requests.RequestException as e:
            logger.error(f"{Fore.RED}Ошибка при обновлении книги {book_id}: {e}{Style.RESET_ALL}")
            logger.error(f"Ответ сервера: {e.response.text if hasattr(e, 'response') and e.response else 'Нет ответа'}")
            return False
    
    def get_chapter(self, chapter_id):
        """Получает данные о главе по ID"""
        try:
            url = f"{self.api_url}chapters/{chapter_id}/"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"{Fore.RED}Ошибка при получении главы {chapter_id}: {e}{Style.RESET_ALL}")
            return None
    
    def update_chapter(self, chapter_id, read_time_delta):
        """Обновляет время чтения главы"""
        try:
            url = f"{self.api_url}chapters/{chapter_id}/"
            data = {"read_time": int(read_time_delta)}
            logger.info(f"Отправляем PATCH-запрос на {url} с данными: {data}")
            response = requests.patch(url, json=data, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            logger.info(f"{Fore.GREEN}Глава {chapter_id} обновлена: время чтения {read_time_delta}{Style.RESET_ALL}")
            return True
        except requests.RequestException as e:
            logger.error(f"{Fore.RED}Ошибка при обновлении главы {chapter_id}: {e}{Style.RESET_ALL}")
            logger.error(f"Ответ сервера: {e.response.text if hasattr(e, 'response') and e.response else 'Нет ответа'}")
            return False
    
    def get_worker(self, worker_id):
        """Получает данные воркера по ID"""
        try:
            url = f"{self.api_url}workers/{worker_id}/"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"{Fore.RED}Ошибка при получении воркера {worker_id}: {e}{Style.RESET_ALL}")
            return None
    
    def get_or_create_worker(self, worker_id):
        """Запрашивает воркер с указанным worker_id через эндпоинт /assign/"""
        try:
            params = {"worker_id": worker_id}
            response = requests.get(
                f"{self.api_url}workers/assign/",
                headers=self.headers,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            worker = response.json()
            
            if worker and "id" in worker:
                logger.info(
                    f"{Fore.GREEN}Успешно получен воркер worker_id={worker['worker_id']} "
                    f"(ID={worker['id']}) с книгой: {worker['book']}{Style.RESET_ALL}"
                )
                self.update_worker(worker["id"], active=False, busy=True)
                return worker
            else:
                logger.warning(
                    f"{Fore.YELLOW}Сервер не вернул воркера для worker_id={worker_id}{Style.RESET_ALL}"
                )
                return None
                
        except requests.HTTPError as e:
            logger.error(
                f"{Fore.RED}HTTP-ошибка при запросе воркера worker_id={worker_id}: "
                f"{response.status_code} {response.text}{Style.RESET_ALL}"
            )
            return None
        except requests.RequestException as e:
            logger.error(
                f"{Fore.RED}Ошибка при запросе воркера worker_id={worker_id}: {e}{Style.RESET_ALL}"
            )
            return None
    
    def update_worker(self, worker_id, active=None, busy=None, read_time=None):
        """Обновляет статус воркера"""
        try:
            url = f"{self.api_url}workers/{worker_id}/"
            data = {}
            if active is not None:
                data["active"] = active
            if busy is not None:
                data["busy"] = busy
            if read_time is not None:
                data["read_time"] = int(read_time)
            
            logger.info(f"Обновляем воркер {worker_id}: {data}")
            response = requests.patch(url, json=data, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            logger.info(f"{Fore.GREEN}Воркер {worker_id} обновлен: {data}{Style.RESET_ALL}")
            return True
        except requests.RequestException as e:
            logger.error(f"{Fore.RED}Ошибка при обновлении воркера {worker_id}: {e}{Style.RESET_ALL}")
            return False


# Создаем глобальный экземпляр API клиента
api_client = APIClient()


def get_container_number():
    try:
        container_number = os.getenv('CONTAINER_NUMBER')
        if container_number:
            container_number = int(container_number)
            logger.info(f"{Fore.GREEN}Порядковый номер контейнера: {container_number}{Style.RESET_ALL}")
            return container_number
        else:
            logger.error(f"{Fore.RED}Переменная окружения CONTAINER_NUMBER не найдена, завершаем работу{Style.RESET_ALL}")
            return None
    except ValueError:
        logger.error(f"{Fore.RED}Переменная CONTAINER_NUMBER не является числом: {container_number}{Style.RESET_ALL}")
        return None
    except Exception as e:
        logger.error(f"{Fore.RED}Ошибка при получении номера контейнера: {e}{Style.RESET_ALL}")
        return None
    


# Обертки для обратной совместимости (используют новый APIClient)
def fetch_books_data():
    """Получает список всех книг (обратная совместимость)"""
    return api_client.get_books()


def get_or_create_worker(worker_id):
    """Получает или создает воркера (обратная совместимость)"""
    return api_client.get_or_create_worker(worker_id)



# Функция для сохранения данных о воркере в файл
def save_worker_data(worker):
    try:
        with open(WORKER_FILE, 'w') as f:
            json.dump(worker, f)
        logger.info(f"{Fore.GREEN}Данные о воркере сохранены в {WORKER_FILE}{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"{Fore.RED}Ошибка при сохранении данных о воркере: {e}{Style.RESET_ALL}")

# Функция для загрузки данных о воркере из файла
def load_worker_data():
    try:
        if os.path.exists(WORKER_FILE):
            with open(WORKER_FILE, 'r') as f:
                worker = json.load(f)
            logger.info(f"{Fore.GREEN}Данные о воркере загружены из {WORKER_FILE}{Style.RESET_ALL}")
            return worker
        else:
            logger.info(f"{Fore.YELLOW}Файл {WORKER_FILE} не найден{Style.RESET_ALL}")
            return None
    except Exception as e:
        logger.error(f"{Fore.RED}Ошибка при загрузке данных о воркере: {e}{Style.RESET_ALL}")
        return None

# Обертки для обратной совместимости
def update_worker(worker_id, active=None, busy=None):
    """Обновляет статус воркера (обратная совместимость)"""
    return api_client.update_worker(worker_id, active=active, busy=busy)


def update_worker_time(worker_id, read_time_delta):
    """Обновляет время чтения воркера (обратная совместимость)"""
    return api_client.update_worker(worker_id, read_time=read_time_delta)


def update_book(book_id, active_workers_delta=None, read_time_delta=None):
    """Обновляет данные книги (обратная совместимость)"""
    return api_client.update_book(book_id, active_workers_delta=active_workers_delta, read_time_delta=read_time_delta)


def fetch_book_by_id(book_id):
    """Получает данные о книге по ID (обратная совместимость)"""
    return api_client.get_book(book_id)


def update_chapter(chapter_id, read_time_delta):
    """Обновляет время чтения главы (обратная совместимость)"""
    return api_client.update_chapter(chapter_id, read_time_delta)


def fetch_chapter_by_id(chapter_id):
    """Получает данные о главе по ID (обратная совместимость)"""
    return api_client.get_chapter(chapter_id)


# Функция для получения списка прокси
def get_proxy_list():
    max_attempts = 5
    attempt = 0
    while attempt < max_attempts:
        try:
            response = requests.get(PROXY_API_URL, timeout=10)
            response.raise_for_status()
            proxy_list = response.text.strip().split('\n')
            proxy_list = [f"http://{proxy}" if not proxy.startswith("http") else proxy for proxy in proxy_list]
            if not proxy_list:
                logger.warning(f"{Fore.YELLOW}Список прокси пуст, повторная попытка через 10 сек (попытка {attempt + 1}/{max_attempts}){Style.RESET_ALL}")
                attempt += 1
                time.sleep(10)
                continue
            logger.info(f"{Fore.GREEN}Получено {len(proxy_list)} прокси{Style.RESET_ALL}")
            return proxy_list
        except requests.RequestException as e:
            logger.error(f"{Fore.RED}Ошибка при получении списка прокси: {e} (попытка {attempt + 1}/{max_attempts}){Style.RESET_ALL}")
            attempt += 1
            time.sleep(10)
    
    logger.error(f"{Fore.RED}Не удалось получить прокси после {max_attempts} попыток{Style.RESET_ALL}")
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
def setup_driver(use_proxies=USE_PROXIES, visual_mode=VISUAL_MODE, proxy_list=None, retries=0, user_data_dir=None):
    chrome_options = Options()
    if user_data_dir:
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    else:
        chrome_options.add_argument(f"--user-data-dir={tempfile.mkdtemp(prefix='chrome_profile_')}")
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
        proxy = proxy_list[0]
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
        return None

# Проверка на Cloudflare
def save_cookies(driver, domain):
    """
    Сохраняет cookies для указанного домена.
    
    Args:
        driver: WebDriver экземпляр
        domain: Домен для сохранения cookies (например, 'real-rpg-books.ru')
    
    Returns:
        dict: Словарь cookies или None в случае ошибки
    """
    try:
        cookies = driver.get_cookies()
        # Фильтруем cookies для указанного домена
        domain_cookies = {}
        for cookie in cookies:
            cookie_domain = cookie.get('domain', '')
            if domain in cookie_domain or cookie_domain in domain:
                domain_cookies[cookie['name']] = cookie
        logger.info(f"{Fore.CYAN}Сохранено {len(domain_cookies)} cookies для домена {domain}{Style.RESET_ALL}")
        return domain_cookies
    except Exception as e:
        logger.warning(f"{Fore.YELLOW}Ошибка при сохранении cookies для {domain}: {e}{Style.RESET_ALL}")
        return None


def restore_cookies(driver, cookies, domain):
    """
    Восстанавливает cookies для указанного домена.
    
    Args:
        driver: WebDriver экземпляр
        cookies: Словарь cookies для восстановления
        domain: Домен для восстановления cookies
    
    Returns:
        bool: True если успешно, False в случае ошибки
    """
    if not cookies:
        return False
    
    try:
        # Сначала переходим на домен, чтобы установить cookies
        driver.get(f"https://{domain}/")
        time.sleep(1)  # Небольшая задержка для загрузки
        
        restored_count = 0
        for cookie_name, cookie_data in cookies.items():
            try:
                # Удаляем 'domain' если он содержит точку в начале (для Selenium)
                cookie_to_set = cookie_data.copy()
                if 'domain' in cookie_to_set and cookie_to_set['domain'].startswith('.'):
                    cookie_to_set['domain'] = cookie_to_set['domain'][1:]
                driver.add_cookie(cookie_to_set)
                restored_count += 1
            except Exception as e:
                logger.debug(f"Не удалось восстановить cookie {cookie_name}: {e}")
        
        logger.info(f"{Fore.GREEN}Восстановлено {restored_count}/{len(cookies)} cookies для домена {domain}{Style.RESET_ALL}")
        return restored_count > 0
    except Exception as e:
        logger.warning(f"{Fore.YELLOW}Ошибка при восстановлении cookies для {domain}: {e}{Style.RESET_ALL}")
        return False


def ensure_cookies_persistence(driver):
    """
    Обеспечивает сохранение cookies между переходами.
    Использует один и тот же driver и user-data-dir для сохранения cookies.
    
    Args:
        driver: WebDriver экземпляр
    
    Returns:
        bool: True если все в порядке
    """
    try:
        # Проверяем, что cookies сохраняются
        current_cookies = driver.get_cookies()
        logger.debug(f"{Fore.CYAN}Текущее количество cookies: {len(current_cookies)}{Style.RESET_ALL}")
        return True
    except Exception as e:
        logger.warning(f"{Fore.YELLOW}Ошибка при проверке cookies: {e}{Style.RESET_ALL}")
        return False


def check_cloudflare(driver):
    try:
        WebDriverWait(driver, CLOUDFLARE_WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Проверка')]"))
        )
        logger.warning(f"{Fore.YELLOW}Обнаружена проверка Cloudflare. Ожидание...{Style.RESET_ALL}")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(PAUSE_MIN, PAUSE_MAX * 2))  # Чуть больше для Cloudflare
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(random.uniform(PAUSE_MIN, PAUSE_MAX * 2))
        WebDriverWait(driver, CLOUDFLARE_MAX_WAIT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
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
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        logger.info(f"{Fore.CYAN}Страница книги {book_url} успешно загружена{Style.RESET_ALL}")
        read_book_button = WebDriverWait(driver, ELEMENT_WAIT_TIMEOUT).until(
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


def read_chapter_mobile(driver, book, read_all, target_book_url, chapter_url, remaining_time, worker_id, apply_read_short=False):
    try:
        initial_delay = random.uniform(1.5, 3.5)
        # time.sleep(initial_delay)
        
        # Находим главу
        chapter = next((ch for ch in book["chapters"] if f"{target_book_url}/{ch['chapter_id']}" == chapter_url), None)
        if not chapter or "chapter_length" not in chapter:
            logger.error(f"{Fore.RED}Глава {chapter_url} не найдена или отсутствует chapter_length{Style.RESET_ALL}")
            return 0, False
        
        chapter_length = chapter["chapter_length"]
        reading_speed = random.uniform(READING_SPEED_MIN, READING_SPEED_MAX)
        calculated_reading_time = chapter_length / reading_speed

        # ----> НАЧАЛО ИЗМЕНЕНИЙ (Ваша логика + 1 строка) <----

        is_fully_read = True # По умолчанию
        
        # 1. Сначала определяем БАЗОВОЕ время и статус (по read_all или вероятности)
        if read_all:
            reading_time = calculated_reading_time * random.uniform(FULL_READ_RATIO_MIN, FULL_READ_RATIO_MAX)
            # is_fully_read уже True
            logger.info(f"{Fore.YELLOW}Базовая логика: Чтение главы {chapter_url} полностью (read_all=True): {reading_time:.1f} сек{Style.RESET_ALL}")

        else:
            # Стандартная логика
            if random.random() < PARTIAL_READ_PROBABILITY:
                reading_time = calculated_reading_time * random.uniform(PARTIAL_READ_RATIO_MIN, PARTIAL_READ_RATIO_MAX)
                is_fully_read = False
                logger.info(f"{Fore.YELLOW}Базовая логика: Частичное чтение главы {chapter_url}: {reading_time:.1f} сек{Style.RESET_ALL}")
            else:
                reading_time = calculated_reading_time * random.uniform(FULL_READ_RATIO_MIN, FULL_READ_RATIO_MAX)
                # is_fully_read уже True
                logger.info(f"{Fore.YELLOW}Базовая логика: Полное (вероятностное) чтение главы {chapter_url}: {reading_time:.1f} сек{Style.RESET_ALL}")

        # 2. Теперь ПЕРЕОПРЕДЕЛЯЕМ, если apply_read_short=True (Независимо от read_all)
        if apply_read_short:
            # Новая логика: время с вариацией
            reading_time = random.uniform(
                READ_SHORT_TIME_BASE * (1 - READ_SHORT_TIME_VARIATION),
                READ_SHORT_TIME_BASE * (1 + READ_SHORT_TIME_VARIATION)
            )
            # И ОБЯЗАТЕЛЬНО меняем статус на "частично"
            is_fully_read = False 
            logger.info(f"{Fore.MAGENTA}ПЕРЕОПРЕДЕЛЕНИЕ: apply_read_short=True. Время: {reading_time:.1f} сек, Статус: Частично (False){Style.RESET_ALL}")
        
        # 3. Применяем общий лимит (на всякий случай)
        reading_time = min(reading_time, remaining_time)
        
        # ----> КОНЕЦ ИЗМЕНЕНИЙ <----
        
        logger.info(f"{Fore.YELLOW}Начато чтение главы: {chapter_url}, объем: {chapter_length} символов, скорость: {reading_speed:.1f} сим/сек, планируемое время: {reading_time:.1f} сек{Style.RESET_ALL}")
        
        page_height = driver.execute_script("return document.body.scrollHeight")
        screen_height = driver.execute_script("return window.innerHeight")
        current_position = 0
        time_spent = initial_delay
        min_swipes = max(1, int(reading_time / 2))
        max_swipes = max(1, int(reading_time / 1.5))
        total_swipes_needed = random.randint(min_swipes, max_swipes)
        swipe_distance = max(80, page_height // total_swipes_needed)
        stage_duration = reading_time / total_swipes_needed
        body_element = driver.find_element(By.TAG_NAME, "body")
        actions = ActionChains(driver)
        
        # Интервал отправки времени чтения
        report_interval = random.uniform(REPORT_INTERVAL_MIN, REPORT_INTERVAL_MAX)
        last_report_time = time_spent
        final_time = 0
        
        for stage in range(total_swipes_needed):
            if time_spent >= reading_time:
                break
            
            # Глубокая пауза для "осмысления" (как реальный читатель)
            if random.random() < READING_DEEP_PAUSE_PROBABILITY:
                deep_pause = random.uniform(READING_DEEP_PAUSE_MIN, READING_DEEP_PAUSE_MAX)
                logger.info(f"{Fore.CYAN}Глубокая пауза для осмысления: {deep_pause:.1f} сек{Style.RESET_ALL}")
                time.sleep(deep_pause)
                time_spent += deep_pause
            
            # Обычная пауза перед свайпом
            if random.random() < PAUSE_BEFORE_SWIPE_PROBABILITY:
                pause = random.uniform(PAUSE_MIN, PAUSE_MAX)
                logger.debug(f"{Fore.CYAN}Пауза перед свайпом {stage + 1}: {pause:.1f} сек{Style.RESET_ALL}")
                time.sleep(pause)
                time_spent += pause
            
            # Иногда возвращаемся назад (как реальный читатель перечитывает)
            if stage > 0 and random.random() < READING_SCROLL_BACK_PROBABILITY:
                back_distance = int(screen_height * random.uniform(
                    READING_SCROLL_BACK_DISTANCE_MIN,
                    READING_SCROLL_BACK_DISTANCE_MAX
                ))
                logger.info(f"{Fore.CYAN}Возврат назад на {back_distance}px (перечитывание){Style.RESET_ALL}")
                actions.move_to_element(body_element).click_and_hold().move_by_offset(0, back_distance).release().perform()
                time.sleep(random.uniform(PAUSE_MIN * 0.5, PAUSE_MAX * 0.5))
                time_spent += random.uniform(PAUSE_MIN * 0.5, PAUSE_MAX * 0.5)
            
            # Проверяем, прошло ли достаточно времени с последней отправки
            if time_spent - last_report_time >= report_interval:
                read_time_delta = time_spent - last_report_time
                logger.info(f"{Fore.CYAN}Отправка промежуточного времени чтения: {read_time_delta:.1f} сек для книги {book['id']} и главы {chapter['id']}{Style.RESET_ALL}")
                final_time += read_time_delta
                last_report_time = time_spent
            
            # Выполняем свайп вверх (чтение)
            actions.move_to_element(body_element).click_and_hold().move_by_offset(0, -swipe_distance).release().perform()
            current_position += swipe_distance
            
            # Микропауза после свайпа (более естественное чтение)
            if random.random() < READING_MICRO_PAUSE_PROBABILITY:
                micro_pause = random.uniform(READING_MICRO_PAUSE_MIN, READING_MICRO_PAUSE_MAX)
                time.sleep(micro_pause)
                time_spent += micro_pause
            
            time.sleep(stage_duration)
            time_spent += stage_duration

        final_read_time = time_spent - last_report_time
        final_time += final_read_time
        if final_read_time > 0:
            logger.info(f"{Fore.CYAN}Отправка финального времени чтения: {final_read_time:.1f} сек{Style.RESET_ALL}")
            update_chapter(chapter["id"], read_time_delta=final_time)
            update_worker_time(worker_id, final_time)
        
        
        logger.info(f"{Fore.GREEN}Глава прочитана за {time_spent:.1f} секунд{' (частично)' if not is_fully_read else ''}{Style.RESET_ALL}")
        return time_spent, is_fully_read
    except Exception as e:
        logger.error(f"{Fore.RED}Ошибка при чтении главы {chapter_url}: {e}{Style.RESET_ALL}")
        return 0, False



# Переход к следующей главе через кнопку
def go_to_next_chapter(driver):
    try:
        next_chapter_button = WebDriverWait(driver, ELEMENT_WAIT_TIMEOUT).until(
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
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        return True
    except TimeoutException:
        logger.info(f"{Fore.GREEN}Кнопка подтверждения возраста не обнаружена, продолжаем без нажатия{Style.RESET_ALL}")
        return False
    except Exception as e:
        logger.error(f"{Fore.RED}Ошибка при обработке кнопки возраста: {e}{Style.RESET_ALL}")
        return False
    


def simulate_session(session_id, worker_id, proxy_pool=None, use_proxies=USE_PROXIES, visual_mode=VISUAL_MODE):
    # Инициализируем запись о сессии
    session_data = {
        "session_id": session_id,
        "worker_id": worker_id,
        "start_time": datetime.utcnow().isoformat(),
        "planned_duration": None,
        "end_time": None,
        "status": "running",
        "error_message": None,
        "chapters_read": 0,
        "total_time_spent": 0
    }
    append_session_log(session_data)

    # Получаем данные воркера
    try:
        worker = api_client.get_worker(worker_id)
        if not worker:
            error_message = f"Не удалось получить данные воркера {worker_id}"
            logger.error(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
            update_session_log(session_id, {
                "end_time": datetime.utcnow().isoformat(),
                "status": "error",
                "error_message": error_message
            })
            return False
        logger.info(f"{Fore.GREEN}Данные воркера {worker_id} обновлены перед сессией {session_id}{Style.RESET_ALL}")
    except Exception as e:
        error_message = f"Ошибка при обновлении данных воркера: {e}"
        logger.error(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
        update_session_log(session_id, {
            "end_time": datetime.utcnow().isoformat(),
            "status": "error",
            "error_message": error_message
        })
        return False

    # Проверяем, назначена ли книга воркеру
    book_id = worker.get("book_id")
    if not book_id:
        error_message = f"У воркера {worker_id} нет назначенной книги"
        logger.warning(f"{Fore.YELLOW}{error_message}{Style.RESET_ALL}")
        update_session_log(session_id, {
            "end_time": datetime.utcnow().isoformat(),
            "status": "error",
            "error_message": error_message
        })
        return False

    # Загружаем актуальные данные о книге
    book = api_client.get_book(book_id)
    if not book or "chapters" not in book or not book["active"]:
        error_message = f"Книга {book_id} не найдена, не активна или не содержит глав"
        logger.warning(f"{Fore.YELLOW}{error_message}{Style.RESET_ALL}")
        update_session_log(session_id, {
            "end_time": datetime.utcnow().isoformat(),
            "status": "error",
            "error_message": error_message
        })
        return False

    # ----> НАЧАЛО ИЗМЕНЕНИЙ <----
    read_all = worker.get("read_all", False)
    read_short = worker.get("read_short", False)
    logger.info(f"{Fore.BLUE}Сессия {session_id}: Обрабатываем книгу {book['name']} (ID: {book['book_id']}), read_all={read_all}, read_short={read_short}{Style.RESET_ALL}")
    # ----> КОНЕЦ ИЗМЕНЕНИЙ <----

    if not book["active"]:
        error_message = f"Книга {book['name']} не активна"
        logger.info(f"{Fore.YELLOW}{error_message}{Style.RESET_ALL}")
        update_session_log(session_id, {
            "end_time": datetime.utcnow().isoformat(),
            "status": "error",
            "error_message": error_message
        })
        return False

    use_filters = random.randint(1, 100) <= book["page_percentage"]
    target_book_url = f"https://author.today/reader/{book['book_id']}"
    chapters = [ch for ch in book["chapters"] if ch["active"]]
    if not chapters:
        error_message = f"Нет активных глав для книги {book['name']}"
        logger.warning(f"{Fore.YELLOW}{error_message}{Style.RESET_ALL}")
        update_session_log(session_id, {
            "end_time": datetime.utcnow().isoformat(),
            "status": "error",
            "error_message": error_message
        })
        return False

    # Логируем количество активных глав
    logger.info(f"{Fore.CYAN}Количество активных глав в книге {book['book_id']}: {len(chapters)}{Style.RESET_ALL}")

    # Рассчитываем общее время сессии
    reading_speed = random.uniform(READING_SPEED_MIN, READING_SPEED_MAX)
    total_session_time = sum(
        ch["chapter_length"] / reading_speed * random.uniform(FULL_READ_RATIO_MIN, FULL_READ_RATIO_MAX)
        for ch in chapters if "chapter_length" in ch and ch["chapter_length"] > 0
    )
    if len(chapters) > 1:
        total_session_time += (len(chapters) - 1) * random.uniform(1, 2)
    logger.info(f"{Fore.MAGENTA}Сессия {session_id}: Рассчитанное время сессии: {total_session_time:.1f} сек (скорость чтения: {reading_speed:.1f} сим/сек){Style.RESET_ALL}")

    # Обновляем планируемую длительность в логе
    session_data["planned_duration"] = total_session_time
    update_session_log(session_id, {"planned_duration": total_session_time})

    driver = None
    user_data_dir = None
    proxy_retries = 0

    while proxy_retries < MAX_PROXY_RETRIES:
        # Получаем рабочий прокси из пула (без проверки, так как он уже проверен)
        if use_proxies and proxy_pool:
            current_proxy = proxy_pool.get_working_proxy()
            if not current_proxy:
                logger.warning(f"{Fore.YELLOW}Не удалось получить рабочий прокси из пула (попытка {proxy_retries + 1}/{MAX_PROXY_RETRIES}){Style.RESET_ALL}")
                proxy_retries += 1
                # Пытаемся обновить пул
                if proxy_retries < MAX_PROXY_RETRIES:
                    proxy_pool.ensure_pool_size()
                    time.sleep(2)  # Небольшая задержка перед следующей попыткой
                else:
                    error_message = "Не удалось получить рабочий прокси из пула после всех попыток"
                    logger.error(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
                    update_session_log(session_id, {
                        "end_time": datetime.utcnow().isoformat(),
                        "status": "error",
                        "error_message": error_message
                    })
                    return False
                continue
            logger.info(f"{Fore.CYAN}Используется прокси из пула: {current_proxy} (попытка {proxy_retries + 1}/{MAX_PROXY_RETRIES}){Style.RESET_ALL}")
        else:
            current_proxy = None

        try:
            user_data_dir = tempfile.mkdtemp(prefix="chrome_profile_")
            logger.info(f"{Fore.CYAN}Создание драйвера с прокси {current_proxy if current_proxy else 'без прокси'}...{Style.RESET_ALL}")
            driver = setup_driver(use_proxies=use_proxies, visual_mode=visual_mode, proxy_list=[current_proxy] if current_proxy else [], user_data_dir=user_data_dir)
            if not driver:
                # Если драйвер не создан, помечаем прокси как нерабочий для Chrome
                if current_proxy and proxy_pool:
                    logger.warning(f"{Fore.YELLOW}Прокси {current_proxy} не работает для Chrome, помечаем как нерабочий{Style.RESET_ALL}")
                    proxy_pool.invalidate_proxy(current_proxy)
                raise Exception("Не удалось настроить драйвер")

            total_time_spent = 0
            chapters_read_in_session = 0

            logger.info(f"{Fore.MAGENTA}Старт сессии {session_id}, планируемая длительность: {total_session_time:.1f} сек{Style.RESET_ALL}")

            # Заходим на real-rpg-books.ru
            driver.get("https://real-rpg-books.ru/")
            if not check_cloudflare(driver):
                raise Exception("Не удалось пройти Cloudflare на real-rpg-books.ru")

            WebDriverWait(driver, PAGE_LOAD_TIMEOUT * 2).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            logger.info(f"{Fore.CYAN}Страница real-rpg-books.ru загружена{Style.RESET_ALL}")

            # Сохраняем cookies с сайта прокладки для передачи на читалку (опционально)
            source_cookies = None
            if USE_COOKIES:
                source_cookies = save_cookies(driver, "real-rpg-books.ru")
                ensure_cookies_persistence(driver)
            else:
                # Cookies сохраняются автоматически через один driver
                logger.debug(f"{Fore.CYAN}Cookies сохраняются автоматически через driver{Style.RESET_ALL}")

            # Время на сайте
            stay_time = random.uniform(STAY_ON_SITE_MIN, STAY_ON_SITE_MAX)
            logger.info(f"{Fore.CYAN}Планируемое время на сайте real-rpg-books.ru: {stay_time:.1f} сек{Style.RESET_ALL}")
            page_height = driver.execute_script("return document.body.scrollHeight")
            start_time = time.time()
            while time.time() - start_time < stay_time - 2:
                scroll_distance = random.randint(200, 500)
                direction = random.choice([-1, 1])
                driver.execute_script(f"window.scrollBy(0, {scroll_distance * direction});")
                time.sleep(random.uniform(SCROLL_DELAY_MIN, SCROLL_DELAY_MAX))

            # Переход по ссылке
            target_link_xpath = f"//a[contains(@href, 'https://author.today/reader/{book['book_id']}/?utm_source=realrpg&utm_medium=referral&utm_campaign=book_link')]"
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    book_link = WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, target_link_xpath))
                    )
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", book_link)
                    time.sleep(random.uniform(0.5, 1.5))
                    WebDriverWait(driver, ELEMENT_WAIT_TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, target_link_xpath)))
                    try:
                        book_link.click()
                        logger.info(f"{Fore.GREEN}Обычный клик по ссылке для книги {book['book_id']} выполнен{Style.RESET_ALL}")
                        break
                    except Exception as e:
                        logger.warning(f"{Fore.YELLOW}Обычный клик не сработал: {e}, пробуем JavaScript-клик{Style.RESET_ALL}")
                        driver.execute_script("arguments[0].click();", book_link)
                        logger.info(f"{Fore.GREEN}JavaScript-клик по ссылке для книги {book['book_id']} выполнен{Style.RESET_ALL}")
                        break
                except TimeoutException:
                    logger.warning(f"{Fore.YELLOW}Попытка {attempt + 1}/{max_attempts}: Ссылка не найдена{Style.RESET_ALL}")
                    if attempt == max_attempts - 1:
                        raise Exception(f"Ссылка для книги {book['book_id']} не найдена")

            total_time_spent += stay_time
            
            # После перехода на author.today, cookies должны автоматически сохраниться
            # через один и тот же driver, но проверяем их наличие
            WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Проверяем сохранение cookies после перехода (опционально)
            if USE_COOKIES and source_cookies:
                logger.info(f"{Fore.CYAN}Проверяем сохранение cookies после перехода на author.today{Style.RESET_ALL}")
                ensure_cookies_persistence(driver)
                # Cookies сохраняются автоматически через один driver,
                # но можем попытаться восстановить релевантные, если нужно
                # restore_cookies(driver, source_cookies, "author.today")  # Если нужно явно восстановить
            else:
                # Cookies сохраняются автоматически через один driver
                logger.debug(f"{Fore.CYAN}Cookies сохраняются автоматически через driver{Style.RESET_ALL}")
            
            if not check_cloudflare(driver):
                raise Exception("Не удалось пройти Cloudflare на странице читалки")

            if handle_age_verification(driver):
                total_time_spent += random.uniform(PAUSE_MIN, PAUSE_MAX * 2)

            # Всегда начинаем с первой главы
            current_chapter_index = 0

            while current_chapter_index < len(chapters):
                chapter = chapters[current_chapter_index]
                chapter_url = f"{target_book_url}/{chapter['chapter_id']}"

                # Проверяем корректность chapter_length
                if "chapter_length" not in chapter or chapter["chapter_length"] <= 0:
                    error_message = f"Глава {chapter['chapter_id']} не содержит корректное значение chapter_length"
                    logger.error(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
                    update_session_log(session_id, {
                        "end_time": datetime.utcnow().isoformat(),
                        "status": "error",
                        "error_message": error_message
                    })
                    return False

                # ----> НАЧАЛО ИЗМЕНЕНИЙ <----
                # Определяем, применяется ли read_short к ЭТОЙ главе
                apply_read_short = read_short and current_chapter_index == 0
                # ----> КОНЕЦ ИЗМЕНЕНИЙ <----

                driver.get(chapter_url)
                WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                logger.info(f"{Fore.CYAN}Загружена страница главы: {chapter_url}{Style.RESET_ALL}")

                # ----> НАЧАЛО ИЗМЕНЕНИЙ <----
                # Читаем главу
                reading_time, is_fully_read = read_chapter_mobile(
                    driver, 
                    book, 
                    read_all, 
                    target_book_url, 
                    chapter_url, 
                    float('inf'), 
                    worker_id,
                    apply_read_short  # <-- Передаем новый флаг
                )
                # ----> КОНЕЦ ИЗМЕНЕНИЙ <----

                if reading_time == 0:
                    logger.warning(f"{Fore.YELLOW}Ошибка чтения главы {chapter_url}, пробуем новый прокси{Style.RESET_ALL}")
                    proxy_retries += 1
                    if driver:
                        driver.quit()
                    if current_proxy and proxy_pool:
                        proxy_pool.invalidate_proxy(current_proxy)
                    if proxy_retries >= MAX_PROXY_RETRIES:
                        error_message = "Достигнуто максимальное количество попыток с прокси"
                        logger.error(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
                        update_session_log(session_id, {
                            "end_time": datetime.utcnow().isoformat(),
                            "status": "error",
                            "error_message": error_message
                        })
                        return False
                    # Пытаемся получить новый прокси из пула
                    if proxy_pool:
                        proxy_pool.ensure_pool_size()
                    continue

                total_time_spent += reading_time
                chapters_read_in_session += 1
                chapter["read_time"] += reading_time
                book["read_time"] = int(float(book["read_time"]) + int(reading_time))

                logger.info(f"{Fore.GREEN}Глава {chapter['chapter_id']} прочитана за {reading_time:.1f} сек{' (частично)' if not is_fully_read else ''}{Style.RESET_ALL}")

                # ----> НАЧАЛО ИЗМЕНЕНИЙ <----
                # Если read_short, выходим ПОСЛЕ первой главы
                if apply_read_short:
                    logger.info(f"{Fore.YELLOW}read_short активен. Завершаем сессию после первой главы.{Style.RESET_ALL}")
                    update_session_log(session_id, {
                        "end_time": datetime.utcnow().isoformat(),
                        "status": "completed",
                        "chapters_read": chapters_read_in_session,
                        "total_time_spent": total_time_spent
                    })
                    return True # Завершаем сессию
                # ----> КОНЕЦ ИЗМЕНЕНИЙ <----


                # Если read_all = False, применяем вероятности завершения
                if not read_all:
                    # Вероятность не перейти ко второй главе
                    if chapters_read_in_session == 1 and random.random() < DROPOUT_AFTER_FIRST_CHAPTER:
                        logger.info(f"{Fore.YELLOW}Пользователь завершил сессию после первой главы{Style.RESET_ALL}")
                        update_session_log(session_id, {
                            "end_time": datetime.utcnow().isoformat(),
                            "status": "completed",
                            "chapters_read": chapters_read_in_session,
                            "total_time_spent": total_time_spent
                        })
                        return True

                    # Если глава прочитана частично, завершаем сессию
                    if not is_fully_read:
                        logger.info(f"{Fore.YELLOW}Глава {chapter['chapter_id']} прочитана частично, завершаем сессию{Style.RESET_ALL}")
                        update_session_log(session_id, {
                            "end_time": datetime.utcnow().isoformat(),
                            "status": "completed",
                            "chapters_read": chapters_read_in_session,
                            "total_time_spent": total_time_spent
                        })
                        return True

                    # Вероятность завершения сессии после текущей главы
                    dropout_chance = random.uniform(DROPOUT_PER_CHAPTER_MIN, DROPOUT_PER_CHAPTER_MAX)
                    if random.random() < dropout_chance:
                        logger.info(f"{Fore.YELLOW}Пользователь завершил сессию после главы {chapter['chapter_id']}{Style.RESET_ALL}")
                        update_session_log(session_id, {
                            "end_time": datetime.utcnow().isoformat(),
                            "status": "completed",
                            "chapters_read": chapters_read_in_session,
                            "total_time_spent": total_time_spent
                        })
                        return True

                # Переход к следующей главе
                next_chapter_index = current_chapter_index + 1
                if next_chapter_index >= len(chapters):
                    logger.info(f"{Fore.YELLOW}Достигнут конец книги, завершаем сессию{Style.RESET_ALL}")
                    update_session_log(session_id, {
                        "end_time": datetime.utcnow().isoformat(),
                        "status": "completed",
                        "chapters_read": chapters_read_in_session,
                        "total_time_spent": total_time_spent
                    })
                    return True
                if go_to_next_chapter(driver):
                    current_chapter_index = next_chapter_index
                    total_time_spent += random.uniform(1, 2)
                else:
                    logger.info(f"{Fore.YELLOW}Не удалось перейти к следующей главе, завершаем сессию{Style.RESET_ALL}")
                    update_session_log(session_id, {
                        "end_time": datetime.utcnow().isoformat(),
                        "status": "completed",
                        "chapters_read": chapters_read_in_session,
                        "total_time_spent": total_time_spent
                    })
                    return True

            logger.info(f"{Fore.MAGENTA}Сессия {session_id} завершена: прочитано {chapters_read_in_session} глав за {total_time_spent:.1f} сек{Style.RESET_ALL}")
            update_session_log(session_id, {
                "end_time": datetime.utcnow().isoformat(),
                "status": "completed",
                "chapters_read": chapters_read_in_session,
                "total_time_spent": total_time_spent
            })
            return True

        except Exception as e:
            logger.warning(f"{Fore.YELLOW}Ошибка с прокси {current_proxy}: {e}. Пробуем новый прокси (попытка {proxy_retries + 1}/{MAX_PROXY_RETRIES}){Style.RESET_ALL}")
            proxy_retries += 1
            if driver:
                driver.quit()
            if current_proxy and proxy_pool:
                proxy_pool.invalidate_proxy(current_proxy)
            if user_data_dir and os.path.exists(user_data_dir):
                try:
                    shutil.rmtree(user_data_dir)
                    logger.info(f"{Fore.CYAN}Временная директория {user_data_dir} удалена{Style.RESET_ALL}")
                except Exception as e:
                    logger.error(f"{Fore.RED}Ошибка при удалении {user_data_dir}: {e}{Style.RESET_ALL}")
            if proxy_retries >= MAX_PROXY_RETRIES:
                error_message = "Достигнуто максимальное количество попыток с прокси"
                logger.error(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
                update_session_log(session_id, {
                    "end_time": datetime.utcnow().isoformat(),
                    "status": "error",
                    "error_message": error_message
                })
                return False
            # Пытаемся получить новый прокси из пула
            if proxy_pool:
                proxy_pool.ensure_pool_size()
            continue

        finally:
            if driver is not None:
                driver.quit()
            if user_data_dir and os.path.exists(user_data_dir):
                try:
                    shutil.rmtree(user_data_dir)
                    logger.info(f"{Fore.CYAN}Временная директория {user_data_dir} удалена{Style.RESET_ALL}")
                except Exception as e:
                    logger.error(f"{Fore.RED}Ошибка при удалении {user_data_dir}: {e}{Style.RESET_ALL}")

    error_message = f"Достигнуто максимальное количество попыток с прокси ({MAX_PROXY_RETRIES})"
    logger.error(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
    update_session_log(session_id, {
        "end_time": datetime.utcnow().isoformat(),
        "status": "error",
        "error_message": error_message
    })
    return False


# Функция для обработки остановки контейнера
def handle_shutdown(signum, frame, worker_id):
    logger.info(f"{Fore.YELLOW}Получен сигнал {signum}, останавливаем воркера {worker_id}{Style.RESET_ALL}")
    if worker_id:
        # Отправляем статус воркера в API: active=False, busy=False
        update_worker(worker_id, active=False, busy=False)
        logger.info(f"{Fore.GREEN}Статус воркера {worker_id} обновлен перед остановкой{Style.RESET_ALL}")
    # Удаляем файл с данными воркера, чтобы при следующем запуске запросить нового
    if os.path.exists(WORKER_FILE):
        os.remove(WORKER_FILE)
        logger.info(f"{Fore.GREEN}Файл {WORKER_FILE} удален{Style.RESET_ALL}")
    sys.exit(0)




def simulate_reading(use_proxies=USE_PROXIES, visual_mode=VISUAL_MODE):
    logger.info(f"{Fore.BLUE}Запуск имитации чтения{Style.RESET_ALL}")

    # Прокси обязательны
    if not use_proxies:
        logger.error(f"{Fore.RED}Прокси обязательны для работы скрипта{Style.RESET_ALL}")
        return

    container_number = get_container_number()
    if not container_number:
        logger.error(f"{Fore.RED}Не удалось определить номер контейнера, завершаем работу{Style.RESET_ALL}")
        return
    
    worker = get_or_create_worker(get_container_number())
    worker_id = worker["id"]

    signal.signal(signal.SIGTERM, lambda signum, frame: handle_shutdown(signum, frame, worker_id))
    signal.signal(signal.SIGINT, lambda signum, frame: handle_shutdown(signum, frame, worker_id))

    session_counter = 1  # Счетчик для уникальных ID сессий
    
    # Создаем пул прокси для оптимизации работы
    proxy_pool = None
    if use_proxies:
        logger.info(f"{Fore.CYAN}Инициализация пула прокси (макс. размер: {PROXY_POOL_SIZE}, потоков проверки: {PROXY_CHECK_WORKERS}){Style.RESET_ALL}")
        proxy_pool = ProxyPool(max_size=PROXY_POOL_SIZE, check_workers=PROXY_CHECK_WORKERS, cache_ttl=PROXY_CACHE_TTL)
        # Предварительно заполняем пул
        if not proxy_pool._refresh_pool():
            logger.warning(f"{Fore.YELLOW}Не удалось заполнить пул прокси при старте{Style.RESET_ALL}")

    while True:
        # Обеспечиваем наличие рабочих прокси в пуле
        if use_proxies and proxy_pool:
            proxy_pool.ensure_pool_size()
        
        # Запускаем сессию с воркером и пулом прокси
        success = simulate_session(session_counter, worker_id, proxy_pool=proxy_pool, use_proxies=use_proxies, visual_mode=visual_mode)

        if not success:
            logger.warning(f"{Fore.YELLOW}Сессия {session_counter} завершилась с ошибкой, обновляем пул прокси и пробуем снова{Style.RESET_ALL}")
            if use_proxies and proxy_pool:
                proxy_pool.ensure_pool_size()
            time.sleep(random.uniform(5, 15))
        
        session_counter += 1  # Увеличиваем счетчик для следующей сессии



if __name__ == "__main__":
    simulate_reading(use_proxies=USE_PROXIES, visual_mode=VISUAL_MODE)