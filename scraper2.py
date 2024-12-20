<<<<<<< HEAD

=======
>>>>>>> 57d0a95341ff33fc3f026d6b1127d13ab9232ad0
import os
import sys
import time
import csv
import platform
import subprocess
import socket
import logging
from pathlib import Path
from shutil import which

import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# === Logging Configuration ===
app_dir = Path(__file__).parent
log_path = app_dir / 'scraper.log'

logging.basicConfig(
    filename=str(log_path),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# === Streamlit Page Configuration ===
st.set_page_config(
    page_title="Weedmaps Order Scraper 🍃",
    page_icon="🍃",
    layout="centered"
)

# === Responsive Styling for Mobile ===
st.markdown(
    """
    <style>
    h1, h2, h3, h4, h5, h6 { color: #2E7D32; }
    .stButton > button { background-color: #4CAF50; color: white; }
    a { color: #2E7D32; }
    </style>
    """,
    unsafe_allow_html=True
)

# === Configuration Variables ===
def find_free_port():
    """Finds and returns a free port on the host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

CHROME_DEBUGGER_PORT = find_free_port()
CSV_FILE_NAME = 'filtered_orders_data.csv'
ALL_ORDERS_URL = 'https://admin.weedmaps.com/orders'

# === Session State Initialization ===
if 'driver' not in st.session_state:
    st.session_state.driver = None

# === Helper Functions ===
def get_chrome_path():
    """Attempts to locate Chrome executable on Windows."""
    chrome_path = which('chrome')
    if chrome_path:
        return chrome_path
    
    common_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
    ]
    
    for path in common_paths:
        if Path(path).exists():
            return path
    return None

def launch_chrome_in_debug_mode(port=CHROME_DEBUGGER_PORT):
    """Launch Chrome in debug mode."""
    chrome_path = get_chrome_path()
    if not chrome_path:
        st.error("Google Chrome not found. Please install Chrome and try again.")
        logging.error("Google Chrome executable not found.")
        return False

    try:
        subprocess.Popen([chrome_path, f"--remote-debugging-port={port}"])
        logging.info(f"Launched Chrome with remote debugging on port {port}.")
        time.sleep(3)  # Wait for Chrome to start
        return True
    except Exception as e:
        st.error(f"Failed to launch Chrome: {e}")
        logging.error(f"Failed to launch Chrome: {e}", exc_info=True)
        return False

def initialize_driver():
    """Initialize Selenium WebDriver."""
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", f"localhost:{CHROME_DEBUGGER_PORT}")
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        logging.info("Selenium WebDriver initialized successfully.")
        return driver
    except Exception as e:
        st.error(f"Failed to initialize Selenium WebDriver: {e}")
        logging.error(f"Failed to initialize Selenium WebDriver: {e}", exc_info=True)
        return None

def save_order_data(order_data, csv_file_name):
    """Save scraped order data to CSV."""
    csv_path = app_dir / csv_file_name
    file_exists = csv_path.is_file()

    try:
        with csv_path.open(mode='a', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=['Order URL', 'Order Number', 'Customer Name', 'Phone Number', 'Email Address'])
            if not file_exists:
                writer.writeheader()
            writer.writerows(order_data)
        st.write(f"Scraped data saved to: `{csv_path}`")
        logging.info(f"Scraped data saved to: {csv_path}")
    except Exception as e:
        st.error(f"Failed to save data to CSV: {e}")
        logging.error(f"Failed to save data to CSV: {e}", exc_info=True)

def scrape_orders(driver):
    """Scrape order data from Weedmaps."""
    try:
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, 'table__TableRow-sc-xx3up4-13')))
    except Exception as e:
        st.error(f"Main orders page failed to load: {e}")
        logging.error(f"Main orders page failed to load: {e}", exc_info=True)
        return 0, 0

    try:
        orders = driver.find_elements(By.XPATH, "//a[contains(@class, 'order-id-link__IDLink-sc-a7pvg2-0')]")
        order_urls = [o.get_attribute('href') for o in orders if o.get_attribute('href')]
    except Exception as e:
        st.error(f"Failed to collect order URLs: {e}")
        logging.error(f"Failed to collect order URLs: {e}", exc_info=True)
        return 0, 0

    order_data = []
    for idx, order_url in enumerate(order_urls[:1]):  # For TEST_MODE, scrape only 1 order
        try:
            driver.get(order_url)
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, "//h4[contains(@class, 'styles__DetailRecipientName')]")))

            order_number = driver.find_element(By.XPATH, "//span[contains(@class, 'styles__OrderId')]").text.strip().replace('Order #', '')
            customer_name = driver.find_element(By.XPATH, "//h4[contains(@class, 'styles__DetailRecipientName')]").text.strip()
            phone_number = driver.find_element(By.XPATH, "//p[contains(text(), 'Phone number')]/following-sibling::div").text.strip()
            email_address = driver.find_element(By.XPATH, "//p[contains(text(), 'Email address')]/following-sibling::p").text.strip()

            order_data.append({
                'Order URL': order_url,
                'Order Number': order_number,
                'Customer Name': customer_name,
                'Phone Number': phone_number,
                'Email Address': email_address
            })
            logging.info(f"Successfully scraped order #{idx + 1}: {order_number}")
        except Exception as e:
            st.error(f"Error processing order #{idx + 1}: {e}")
            logging.error(f"Error processing order #{idx + 1}: {e}", exc_info=True)
            continue

    save_order_data(order_data, CSV_FILE_NAME)
    return len(order_urls), len(order_data)

# === Sidebar UI ===
with st.sidebar:
    st.markdown("### Empowering Cannabis Operators 🍃")
    with st.expander("Instructions 🍃"):
        st.write("""
        1. Click **Open Chrome** to launch Chrome in debug mode.
        2. Use the opened Chrome window to navigate and filter orders.
        3. Click **Scrape Orders** to fetch your order data.
        """)
    st.markdown("Crafted with care for cannabis operators 🌱")

# === Main UI ===
st.title("Weedmaps Order Scraper 🍃")

st.subheader("Setup 🛠")
if st.button('Open Chrome'):
    if launch_chrome_in_debug_mode():
        driver = initialize_driver()
        if driver:
            st.session_state.driver = driver
            driver.get(ALL_ORDERS_URL)

st.subheader("Scraping 🍀")
if st.button('Scrape Orders'):
    if st.session_state.driver:
        scrape_orders(st.session_state.driver)
