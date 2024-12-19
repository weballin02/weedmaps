import os
import sys
import time
import csv
import platform
import subprocess
import socket
import logging

import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# === Logging Configuration ===
logging.basicConfig(
    filename='scraper.log',
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(message)s'
)

# === Streamlit Page Configuration ===
st.set_page_config(
    page_title="Weedmaps Order Scraper 🍃",
    page_icon="🍃",
    layout="centered"  # 'centered' works better on mobile screens
)

# === Responsive Styling for Mobile ===
st.markdown(
    """
    <style>
    /* Green theme for headers */
    h1, h2, h3, h4, h5, h6 {
        color: #2E7D32;
    }
    /* Green buttons with white text */
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        font-weight: bold;
    }
    /* Padding for cleaner layout */
    .main > div {
        padding: 1rem;
    }
    /* Responsive font sizes for mobile */
    @media (max-width: 600px) {
        h1, h2, h3 {
            font-size: 1.2rem;
        }
        .stButton > button {
            font-size: 0.9rem;
            padding: 0.5rem 1rem;
        }
        .main > div {
            padding: 0.5rem;
        }
    }
    /* Links match the green theme */
    a {
        color: #2E7D32;
    }
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
TEST_MODE = False  # Set to False to scrape all orders
CSV_FILE_NAME = 'filtered_orders_data.csv'  # CSV file name to save order data
ALL_ORDERS_URL = 'https://admin.weedmaps.com/orders'

# === Session State Initialization ===
if 'driver' not in st.session_state:
    st.session_state.driver = None

# === Helper Functions ===
def get_app_dir():
    """
    Returns the directory where the script is located.
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def launch_chrome_in_debug_mode(port=CHROME_DEBUGGER_PORT, chrome_path=None):
    """
    Launch Chrome in remote debugging mode on the specified port.
    For Windows, attempts to find Chrome in common installation paths.
    If not found, uses the provided chrome_path.
    """
    system = platform.system()
    if system != "Windows":
        st.error("This script is optimized for Windows.")
        logging.error("Unsupported OS. This script is optimized for Windows.")
        return False

    chrome_executable = chrome_path

    if not chrome_executable:
        # Attempt to locate Chrome in common installation paths
        common_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
        ]
        for path in common_paths:
            if os.path.exists(path):
                chrome_executable = path
                break

    if not chrome_executable:
        st.sidebar.error("Google Chrome executable not found. Please specify the path below.")
        chrome_executable = st.sidebar.text_input("Chrome Executable Path", value="")
        if not chrome_executable or not os.path.exists(chrome_executable):
            st.error("Invalid Chrome executable path. Please provide a valid path to chrome.exe.")
            logging.error("Invalid Chrome executable path provided by user.")
            return False

    try:
        subprocess.Popen([chrome_executable, f"--remote-debugging-port={port}"])
        logging.info(f"Launched Chrome with remote debugging on port {port}.")
        time.sleep(3)  # Wait for Chrome to start
        return True
    except Exception as e:
        st.error(f"Failed to launch Chrome: {e}")
        logging.error(f"Failed to launch Chrome: {e}", exc_info=True)
        return False

def initialize_driver():
    """
    Initialize Selenium WebDriver with debugging options and return the driver instance.
    """
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
    """
    Save order data to a CSV file with the specified filename.
    Append if file exists, otherwise write header first.
    """
    app_dir = get_app_dir()
    csv_path = os.path.join(app_dir, csv_file_name)
    file_exists = os.path.isfile(csv_path)

    try:
        with open(csv_path, mode='a', newline='', encoding='utf-8') as file:
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
    """
    Scrape all order data from Weedmaps.
    Steps:
      1. Wait for the page to load and locate all order links.
      2. Extract all order URLs and store them in a list.
      3. Iterate over these URLs to scrape detailed information.
    """
    try:
        # Ensure main orders page is fully loaded
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'table__TableRow-sc-xx3up4-13'))
        )
        logging.info("Main orders page loaded successfully.")
    except Exception as e:
        logging.error(f"Main orders page failed to load: {e}", exc_info=True)
        st.error(f"Main orders page failed to load: {e}")
        return 0, 0

    try:
        # Collect all order URLs once
        orders = driver.find_elements(By.XPATH, "//a[contains(@class, 'order-id-link__IDLink-sc-a7pvg2-0')]")
        order_urls = [o.get_attribute('href') for o in orders if o.get_attribute('href')]
        total_orders = len(order_urls)
        max_orders = 1 if TEST_MODE else total_orders
        order_data = []

        logging.info(f"Found {total_orders} orders. Preparing to scrape {max_orders} orders.")
    except Exception as e:
        logging.error(f"Failed to collect order URLs: {e}", exc_info=True)
        st.error(f"Failed to collect order URLs: {e}")
        return 0, 0

    for idx, order_url in enumerate(order_urls[:max_orders]):
        try:
            driver.get(order_url)
            logging.info(f"Navigating to order URL: {order_url}")
            # Wait for order details page to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//h4[contains(@class, 'styles__DetailRecipientName')]"))
            )
            logging.info(f"Order details page loaded for URL: {order_url}")

            # Extract order details
            order_number = driver.find_element(By.XPATH, "//span[contains(@class, 'styles__OrderId')]").text.strip().replace('Order #', '')
            customer_name = driver.find_element(By.XPATH, "//h4[contains(@class, 'styles__DetailRecipientName')]").text.strip()
            phone_number = driver.find_element(By.XPATH, "//p[contains(text(), 'Phone number')]/following-sibling::div").text.strip()
            email_address = driver.find_element(By.XPATH, "//p[contains(text(), 'Email address')]/following-sibling::p").text.strip()

            # Append data to list
            order_data.append({
                'Order URL': order_url,
                'Order Number': order_number,
                'Customer Name': customer_name,
                'Phone Number': phone_number,
                'Email Address': email_address
            })
            logging.info(f"Successfully scraped order #{idx+1}: {order_number}")

        except Exception as e:
            st.error(f"Error processing order #{idx+1}: {e}")
            logging.error(f"Error processing order #{idx+1}: {e}", exc_info=True)
            continue

    # Save all scraped data
    save_order_data(order_data, CSV_FILE_NAME)
    return total_orders, len(order_data)

# === Streamlit Sidebar ===
with st.sidebar:
    st.markdown("### Empowering Cannabis Operators 🍃")
    with st.expander("Instructions 🍃"):
        st.write("""
        1. Click **Open Chrome** to launch Chrome in debug mode.
        2. Use the opened Chrome window to navigate and filter orders as desired.
        3. Click **Scrape Orders** to begin fetching your order data.
        """)
    st.markdown("Crafted with care for cannabis operators 🌱")

# === Main Streamlit UI ===
st.title("Weedmaps Order Scraper 🍃")

st.subheader("Setup 🛠")
if st.button('Open Chrome'):
    st.write("Opening Chrome... 🍀")
    success = launch_chrome_in_debug_mode(CHROME_DEBUGGER_PORT)
    if success:
        driver = initialize_driver()
        if driver:
            st.session_state.driver = driver
            driver.get(ALL_ORDERS_URL)
            st.success("Chrome is ready! Set the date range or filters manually in the opened browser, then click 'Scrape Orders'. ✅")
        else:
            st.error("Failed to initialize Selenium WebDriver.")
    else:
        st.error("Failed to launch Chrome.")

st.subheader("Scraping 🍀")
if st.button('Scrape Orders'):
    if st.session_state.driver is None:
        st.error("Chrome is not open or driver not initialized.")
        logging.warning("Scrape Orders clicked but driver is not initialized.")
    else:
        st.write("Scraping orders... Please wait. ⏳")
        try:
            total_orders, scraped = scrape_orders(st.session_state.driver)
            st.success(f"Scraped {scraped} of {total_orders} orders. 🎉")
            logging.info(f"Scraped {scraped} of {total_orders} orders.")
        except Exception as e:
            st.error(f"An error occurred during scraping: {e}")
            logging.error(f"An error occurred during scraping: {e}", exc_info=True)
        finally:
            if st.session_state.driver:
                st.session_state.driver.quit()
                st.session_state.driver = None
                logging.info("Selenium WebDriver closed successfully.")
