import os
import sys
import time
import csv
import platform
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# === Configuration Variables ===
CHROME_DEBUGGER_PORT = 9222
TEST_MODE = True  # Limit to 1 order in test mode
CSV_FILE_NAME = 'filtered_orders_data.csv'  # CSV file name to save order data
ALL_ORDERS_URL = 'https://admin.weedmaps.com/orders'


def get_app_dir():
    """
    Returns the directory where the executable or script is located.
    If running as a PyInstaller one-file executable, returns the directory of the executable.
    If running as a normal script, returns the script's directory.
    """
    if hasattr(sys, '_MEIPASS'):
        # Running in PyInstaller one-file mode
        return os.path.dirname(sys.executable)
    else:
        # Running as a normal script
        return os.path.dirname(os.path.abspath(__file__))


def launch_chrome_in_debug_mode(port=CHROME_DEBUGGER_PORT):
    """
    Launches Google Chrome in remote debugging mode.
    """
    system = platform.system()
    if system == "Windows":  # Windows
        # Adjust the path if Chrome is not in the default location
        chrome_path = r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        subprocess.Popen([
            chrome_path,
            f"--remote-debugging-port={port}"
        ])
    elif system == "Darwin":  # macOS
        subprocess.Popen([
            "open",
            "-a", "Google Chrome",
            "--args",
            f"--remote-debugging-port={port}"
        ])
    else:  # Linux or other systems
        subprocess.Popen([
            "google-chrome",
            f"--remote-debugging-port={port}"
        ])
    # Give Chrome time to launch
    time.sleep(3)


def initialize_driver():
    """Initialize Selenium WebDriver with debugging options."""
    chrome_options = Options()
    chrome_options.debugger_address = f"localhost:{CHROME_DEBUGGER_PORT}"
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver


def save_order_data(order_data, csv_file_name):
    """
    Saves or appends order data to a CSV file.
    If the CSV file does not exist, it creates it with headers.
    If it exists, it appends new rows.
    """
    app_dir = get_app_dir()
    csv_path = os.path.join(app_dir, csv_file_name)

    file_exists = os.path.isfile(csv_path)
    with open(csv_path, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['Order URL', 'Order Number', 'Customer Name', 'Phone Number', 'Email Address'])
        if not file_exists:
            writer.writeheader()
        writer.writerows(order_data)

    print(f"\nScraped data appended to {csv_path}")


def scrape_orders(driver):
    """Scrape the orders based on the currently filtered page."""
    # Wait for filtered results to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'table__TableRow-sc-xx3up4-13'))
    )

    orders = driver.find_elements(By.XPATH, "//a[@class='order-id-link__IDLink-sc-a7pvg2-0 idfeRm']")
    total_orders = len(orders)

    max_orders = 1 if TEST_MODE else total_orders
    order_data = []

    for idx, order in enumerate(orders[:max_orders], start=1):
        try:
            order_url = order.get_attribute('href')
            driver.get(order_url)

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//h4[contains(@class, 'styles__DetailRecipientName')]"))
            )

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

            if idx < max_orders:
                driver.get(ALL_ORDERS_URL)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'table__TableRow-sc-xx3up4-13'))
                )

        except Exception as e:
            print(f"Error processing order #{idx}: {e}")
            continue

    save_order_data(order_data, CSV_FILE_NAME)
    return total_orders, len(order_data)


class App:
    def __init__(self, master):
        self.master = master
        master.title("Simple Order Scraper")
        master.geometry("400x300")

        self.instructions_label = ttk.Label(
            master,
            text=(
                "Welcome! This tool will scrape order data.\n\n"
                "1. Click 'Open Chrome' to start Chrome in special mode.\n"
                "2. The website will appear in Chrome.\n"
                "3. Set the desired date range manually in Chrome.\n"
                "4. Return here and click 'Scrape Orders'."
            ),
            wraplength=380
        )
        self.instructions_label.pack(pady=10)

        self.open_chrome_button = ttk.Button(master, text="Open Chrome", command=self.open_chrome)
        self.open_chrome_button.pack(pady=10)

        self.scrape_button = ttk.Button(master, text="Scrape Orders", command=self.scrape)
        self.scrape_button.config(state="disabled")
        self.scrape_button.pack(pady=10)

        self.status_label = ttk.Label(master, text="", foreground="blue")
        self.status_label.pack(pady=10)

        self.driver = None

    def open_chrome(self):
        launch_chrome_in_debug_mode()
        try:
            self.driver = initialize_driver()
            self.driver.get(ALL_ORDERS_URL)
            self.scrape_button.config(state="normal")
            self.open_chrome_button.config(state="disabled")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open Chrome properly: {e}")

    def scrape(self):
        try:
            total_orders, scraped = scrape_orders(self.driver)
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during scraping: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
