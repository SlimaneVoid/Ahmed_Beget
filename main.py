import time
import random
import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import requests
from undetected_chromedriver import Chrome, ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, ElementClickInterceptedException
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
lock = Lock()

def load_moroccan_data(filename):
    with open(filename, 'r') as file:
        lines = file.readlines()
    data = [line.strip().split(', ') for line in lines]
    logging.info(f"Loaded {len(data)} entries from {filename}")
    return data

def fetch_proxies():
    logging.info("Fetching proxies from ProxyScrape API...")
    response = requests.get("https://api.proxyscrape.com/v2/?request=displayproxies&protocol=all&timeout=8000&country=all&ssl=all&anonymity=all")
    proxies = response.text.splitlines()
    logging.info(f"Fetched {len(proxies)} proxies.")
    return proxies

def is_proxy_working(proxy, timeout=10):
    try:
        response = requests.get('https://httpbin.org/ip', proxies={'http': f'http://{proxy}', 'https': f'http://{proxy}'}, timeout=timeout)
        if response.status_code == 200:
            logging.info(f"Proxy {proxy} is working.")
            return proxy
    except requests.RequestException:
        logging.warning(f"Proxy {proxy} failed.")
    return None

@contextmanager
def get_driver(proxy, options):
    driver = Chrome(options=options, driver_executable_path=ChromeDriverManager().install())
    driver.implicitly_wait(60)
    driver.set_page_load_timeout(120)
    driver.set_script_timeout(120)
    try:
        yield driver
    finally:
        pass

def click_element(driver, by, value, retries=3):
    for attempt in range(retries):
        try:
            element = WebDriverWait(driver, 120).until(EC.element_to_be_clickable((by, value)))
            element.click()
            return True
        except ElementClickInterceptedException:
            logging.warning("Element click intercepted; retrying...")
            time.sleep(3)
    logging.error("Failed to click element after retries.")
    return False

def create_driver(proxy, moroccan_entry, retries=3):
    full_name, phone_number, email = moroccan_entry
    logging.info(f"Starting browser for {full_name} with proxy {proxy}")

    options = ChromeOptions()
    options.add_argument(f'--proxy-server={proxy}')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument(f"user-agent={random.choice([  
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
    ])}")

    attempt = 0
    while attempt < retries:
        try:
            with get_driver(proxy, options) as driver:
                logging.info(f"{full_name} - Navigating to the registration page")
                driver.get("https://beget.com/en")
                time.sleep(5)

                if not click_element(driver, By.XPATH, "//button[contains(text(), 'Register')]"):
                    return

                logging.info(f"{full_name} - Register button clicked successfully")
                
                time.sleep(5)
                driver.execute_script("""
                    try {
                        let countryFlagDOM = document.querySelectorAll(".iti__selected-flag")[1];
                        countryFlagDOM.click();
                        let maroc = document.querySelectorAll(".iti__country")[389]; 
                        maroc.click();
                        console.log("Country Set To Morocco")
                    } catch(err) {
                        console.error(err)
                    }
                """)
                time.sleep(4)

                name_input = WebDriverWait(driver, 120).until(EC.presence_of_element_located((By.ID, "personForm-personForm-fullName-field")))
                phone_input = WebDriverWait(driver, 120).until(EC.presence_of_element_located((By.ID, "personForm-personForm-phoneNumber-field")))
                email_input = WebDriverWait(driver, 120).until(EC.presence_of_element_located((By.ID, "personForm-personForm-email-field")))

                for char in full_name:
                    name_input.send_keys(char)
                    time.sleep(random.uniform(0.05, 0.3))

                for char in phone_number:
                    phone_input.send_keys(char)
                    time.sleep(random.uniform(0.05, 0.3))

                for char in email:
                    email_input.send_keys(char)
                    time.sleep(random.uniform(0.05, 0.3))

                if not click_element(driver, By.XPATH, "//span[contains(text(), 'Register')]"):
                    return

                logging.info(f"{full_name} - Form submitted successfully with proxy {proxy}")
                
                input("Press Enter to close the browser manually...")
                driver.quit()
                return

        except (TimeoutException, WebDriverException) as e:
            attempt += 1
            logging.error(f"Attempt {attempt}/{retries} failed for {full_name} with error: {e}")
            if attempt >= retries:
                logging.error(f"Failed to complete for {full_name} after {retries} retries.")
            time.sleep(5)  # Wait before retrying

def main():
    moroccan_data = load_moroccan_data('morrocan_data.txt')
    proxies = fetch_proxies()

    with ThreadPoolExecutor(max_workers=85) as executor:
        working_proxies = list(filter(None, executor.map(lambda p: is_proxy_working(p, timeout=10), proxies)))

    if len(working_proxies) < len(moroccan_data):
        logging.error("Not enough valid proxies available.")
        return

    with ThreadPoolExecutor(max_workers=10) as executor:
        for i, entry in enumerate(moroccan_data):
            proxy = working_proxies[i % len(working_proxies)]
            executor.submit(create_driver, proxy, entry)

if __name__ == "__main__":
    main()
