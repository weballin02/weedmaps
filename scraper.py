import os
import sys
import time
import csv
import platform
import subprocess
import streamlit as st

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# === Page Configuration for Enhanced Layout/Design (with mobile in mind) ===
st.set_page_config(
    page_title="Weedmaps Order Scraper 🍃",
    page_icon="🍃",
    layout="centered"  # 'centered' can work better on mobile screens
)

# Add responsive styling for mobile
st.markdown(
    """
    <style>
    /* Set a green theme for headers */
    h1, h2, h3, h4, h5, h6 {
        color: #2E7D32;
    }
    /* Style the buttons with a green background and white text */
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        font-weight: bold;
    }
    /* Padding for a cleaner layout */
    .main > div {
        padding: 1rem;
    }
    /* Responsive font sizes for mobile screens */
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
    /* Links to match theme */
    a {
        color: #2E7D32;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# === Configuration Variables ===
CHROME_DEBUGGER_PORT = 9222
TEST_MODE = False  # Set to False to scrape all orders
CSV_FILE_NAME = 'filtered_orders_data.csv'  # CSV file name to save order data
ALL_ORDERS_URL = 'https://admin.weedmaps.com/orders'

# Session State Variables
if 'driver' not in st.session_state:
    st.session_state.driver = None

def get_app_dir():
    """
    Returns the directory where the script is located.
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def launch_chrome_in_debug_mode(port=CHROME_DEBUGGER_PORT):
    """
    Launch Chrome in remote debugging mode on the specified port.
    For macOS, uses 'open', for Windows and Linux uses direct commands.
    """
    system = platform.system()
    if system == "Darwin":  # macOS
        subprocess.Popen(["open", "-a", "Google Chrome", "--args", f"--remote-debugging-port={port}"])
    elif system == "Windows":  # Windows
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        subprocess.Popen([chrome_path, f"--remote-debugging-port={port}"])
    else:  # Linux
        subprocess.Popen(["google-chrome", f"--remote-debugging-port={port}"])
    time.sleep(3)  # Wait for Chrome to start

def initialize_driver():
    """
    Initialize Selenium WebDriver with debugging options and return the driver instance.
    """
    chrome_options = Options()
    chrome_options.debugger_address = f"localhost:{CHROME_DEBUGGER_PORT}"
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

def save_order_data(order_data, csv_file_name):
    """
    Save order data to a CSV file with specified filename.
    Append if file exists, otherwise write header first.
    """
    app_dir = get_app_dir()
    csv_path = os.path.join(app_dir, csv_file_name)
    file_exists = os.path.isfile(csv_path)

    with open(csv_path, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['Order URL', 'Order Number', 'Customer Name', 'Phone Number', 'Email Address'])
        if not file_exists:
            writer.writeheader()
        writer.writerows(order_data)
    
    st.write(f"Scraped data saved to: {csv_path}")

def scrape_orders(driver):
    """
    Scrape all order data from Weedmaps.
    Steps:
      1. Wait for the page to load and locate all order links.
      2. Extract all order URLs and store them in a list.
      3. Iterate over these URLs to scrape detailed information.
    """
    # Ensure main orders page is fully loaded
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'table__TableRow-sc-xx3up4-13')))

    # Collect all order URLs once
    orders = driver.find_elements(By.XPATH, "//a[@class='order-id-link__IDLink-sc-a7pvg2-0 idfeRm']")
    order_urls = [o.get_attribute('href') for o in orders]

    total_orders = len(order_urls)
    max_orders = 1 if TEST_MODE else total_orders
    order_data = []

    for idx, order_url in enumerate(order_urls[:max_orders]):
        try:
            driver.get(order_url)
            # Wait for order details page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//h4[contains(@class, 'styles__DetailRecipientName')]"))
            )

            # Extract order details
            order_number = driver.find_element(By.XPATH, "//span[contains(@class, 'styles__OrderId')]") \
                                 .text.strip().replace('Order #', '')
            customer_name = driver.find_element(By.XPATH, "//h4[contains(@class, 'styles__DetailRecipientName')]") \
                                  .text.strip()
            phone_number = driver.find_element(
                By.XPATH,
                "//p[contains(text(), 'Phone number')]/following-sibling::div"
            ).text.strip()
            email_address = driver.find_element(
                By.XPATH,
                "//p[contains(text(), 'Email address')]/following-sibling::p"
            ).text.strip()

            # Append data to list
            order_data.append({
                'Order URL': order_url,
                'Order Number': order_number,
                'Customer Name': customer_name,
                'Phone Number': phone_number,
                'Email Address': email_address
            })
        except Exception as e:
            st.error(f"Error processing order #{idx+1}: {e}")
            continue

    # Save all scraped data
    save_order_data(order_data, CSV_FILE_NAME)
    return total_orders, len(order_data)


# === SIDEBAR FOR INSTRUCTIONS & BRANDING ===
with st.sidebar:
    st.markdown("### Empowering Cannabis Operators 🍃")
    with st.expander("Instructions 🍃"):
        st.write("""
        1. Click **Open Chrome** to launch Chrome in debug mode.
        2. Use the opened Chrome window to navigate and filter orders as desired.
        3. Click **Scrape Orders** to begin fetching your order data.
        """)
    st.markdown("Crafted with care for cannabis operators 🌱")

# === MAIN UI ===
st.title("Weedmaps Order Scraper 🍃")

st.subheader("Setup 🛠")
if st.button('Open Chrome'):
    st.write("Opening Chrome... 🍀")
    launch_chrome_in_debug_mode(CHROME_DEBUGGER_PORT)
    try:
        st.session_state.driver = initialize_driver()
        st.session_state.driver.get(ALL_ORDERS_URL)
        st.success("Chrome is ready! Set the date range or filters manually in the opened browser, then click 'Scrape Orders'. ✅")
    except Exception as e:
        st.error(f"Failed to initialize Chrome: {e}")

st.subheader("Scraping 🍀")
if st.button('Scrape Orders'):
    if st.session_state.driver is None:
        st.error("Chrome is not open or driver not initialized.")
    else:
        st.write("Scraping orders... Please wait. ⏳")
        try:
            total_orders, scraped = scrape_orders(st.session_state.driver)
            st.success(f"Scraped {scraped} of {total_orders} orders. 🎉")
        except Exception as e:
            st.error(f"An error occurred: {e}")
        finally:
            if st.session_state.driver:
                st.session_state.driver.quit()
                st.session_state.driver = None
