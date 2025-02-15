
import base64
import itertools
import logging
import os
import random
import re
import requests
import string
import sys
import threading
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementNotInteractableException, NoSuchElementException,
    TimeoutException, WebDriverException, NoAlertPresentException,
    UnexpectedAlertPresentException, StaleElementReferenceException
)


# Global variables
screenshot_counter = 1
should_continue = True

#Directory for logs
logs_directory = 'logs'
os.makedirs(logs_directory, exist_ok=True)
log_file_path = os.path.join(logs_directory, 'logfile.log')
email_used = None
start_url = ''
blacklisted_urls = ["facebook.com", "example.com","linkedin.com","paypal.com"]

# Configure logging
logging.basicConfig(filename=log_file_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
sys.stdout = open(log_file_path, 'a', buffering=1)
sys.stderr = open(log_file_path, 'a', buffering=1)
logging.info("Script started.")

def setup_chrome_options():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-translate")
    chrome_options.add_experimental_option("prefs", {
        "translate_whitelists": {},
        "translate": {"enabled": False},
        "intl.accept_languages": "en-US,en"
    })
    return chrome_options


chrome_driver_path = "/usr/local/bin/chromedriver"
service = Service(executable_path=chrome_driver_path)
chrome_options = setup_chrome_options()

# Handle pop ups and alerts
def handle_alert(driver):
    try:
        # Inject JavaScript to override alert, confirm, and prompt functions
        driver.execute_script("""
            window.alert = function(message) {
                console.log("Alert called with message: " + message);
            };
            window.confirm = function(message) {
                console.log("Confirm called with message: " + message);
                return true;  // Return true to simulate clicking "OK"
            };
            window.prompt = function(message, defaultText) {
                console.log("Prompt called with message: " + message + ", default text: " + defaultText);
                return defaultText;  // Return the default text to simulate entering text and clicking "OK"
            };
        """)
        logging.info("Alert functions overridden to log messages to the console.")
    except Exception as e:
        logging.error(f"Failed to override alert functions: {e}")

# Initialize driver function
def initialize_driver():
    driver = webdriver.Chrome(service=service, options=chrome_options)
    handle_alert(driver)  # Handle alerts immediately after driver initialization
    return driver

driver = initialize_driver()

# Generate random strings and emails for filling forms
def generate_random_string(length=8, names_file='names.txt'): #names.txt contains a dictionary of common names
    with open(names_file, 'r') as file:
        names = [line.strip() for line in file.readlines()]
    random_name = random.choice(names)
    result_string = f"{random_name}"
    return result_string[:length]

def generate_random_email():
    random_number = random.randint(60, 99)
    username = generate_random_string()
    return f"{username}{random_number}@your-email-domain.com" 

# Generate crypto addresses
def generate_btc_address():
    return random.choice(['1', '3']) + ''.join(random.choices(string.digits + string.ascii_letters, k=33))

def generate_eth_address():
    return '0x' + ''.join(random.choices('0123456789abcdef', k=40))

def generate_ltc_address():
    return random.choice(['L', 'M']) + ''.join(random.choices(string.digits + string.ascii_letters, k=33))

def generate_xrp_address():
    return 'r' + ''.join(random.choices(string.digits + string.ascii_letters, k=33))

def generate_xmr_address():
    return '4' + ''.join(random.choices(string.digits + string.ascii_letters, k=94))

def generate_ada_address():
    return 'addr1' + ''.join(random.choices(string.digits + string.ascii_letters, k=58))

# Captcha detection, log error if detected and move to next URL
def has_captcha(html_content, driver):
    if "captcha" in html_content.lower():
        logging.info(f"Captcha detected on {driver.current_url}.")
        recaptcha_elements = driver.find_elements(By.XPATH, "//iframe[contains(@src, 'recaptcha')]") + \
                             driver.find_elements(By.CLASS_NAME, "g-recaptcha")
        if recaptcha_elements:
            logging.info(f"Google reCAPTCHA detected on {driver.current_url}.")
        else:
            logging.info(f"Non-Google captcha detected on {driver.current_url}.")
        return True
    return False

# Predict form values
def predict_values(form):
    predictions = {}
    predicted_password = "Pass@1234"
    predicted_username = generate_random_string()
    predicted_email = f"{predicted_username}{random.randint(60, 99)}@your-email-domain.com"
    input_tags = form.find_elements(By.TAG_NAME, 'input')

    for input_tag in input_tags:
        input_name = input_tag.get_attribute('name')
        input_type = input_tag.get_attribute('type')
        if input_name:
            if "username" in input_name.lower():
                predictions[input_name] = predicted_username
            elif input_type.lower() == "password":
                predictions[input_name] = predicted_password
            elif "email" in input_name.lower():
                predictions[input_name] = predicted_email
            else:
                predictions[input_name] = generate_random_string()
    return predictions

# Fill form
def fill_form(predictions):
    for input_name, prediction in predictions.items():
        input_field = driver.find_element(By.NAME, input_name)
        try:
            if input_field.is_displayed() and input_field.is_enabled():
                input_field.send_keys(prediction)
            else:
                logging.info(f"Element {input_name} is not interactable")
        except ElementNotInteractableException:
            logging.info(f"Element {input_name} is not interactable")

# Handle checkboxes
def handle_checkbox(driver):
    try:
        checkboxes = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'input[type="checkbox"]')))
        for checkbox in checkboxes:
            try:
                if checkbox.is_displayed() and checkbox.is_enabled() and not checkbox.is_selected():
                    checkbox.click()
                    logging.info("Checkbox clicked directly.")
                else:
                    label = driver.find_element(By.XPATH, f"//label[@for='{checkbox.get_attribute('id')}']")
                    if label.is_displayed():
                        label.click()
                        logging.info("Checkbox label clicked.")
            except Exception:
                driver.execute_script("arguments[0].click();", checkbox)
                logging.info("Checkbox clicked using JavaScript.")
    except TimeoutException as e:
        logging.error(f"Timed out waiting for checkboxes: {e}")
    except Exception as e:
        logging.error(f"An error occurred while handling checkboxes: {e}")

# Ensure driver function with enhanced error handling
def ensure_driver(driver):
    try:
        current_url = driver.current_url
    except (WebDriverException, Exception) as e:
        logging.info(f"WebDriver not responding, reinitializing due to error: {e}")
        try:
            logging.info("Quitting driver now")
            driver.quit()
        except Exception as inner_e:
            logging.error(f"Failed to quit the driver: {inner_e}")
        driver = initialize_driver()
    return driver

# Handle dropdowns
def handle_dropdowns(form, driver):
    select_elements = form.find_elements(By.TAG_NAME, 'select')
    for select_element in select_elements:
        try:
            select = Select(select_element)
            options = select.options
            if options:
                random_option = random.choice(options)
                select.select_by_value(random_option.get_attribute("value"))
        except WebDriverException:
            try:
                if options:
                    random_value = random.choice(options).get_attribute("value")
                    driver.execute_script("arguments[0].value = arguments[1];", select_element, random_value)
            except WebDriverException as e:
                logging.error(f"Failed to select dropdown option using JavaScript: {e}")

# Submit form
def click_and_submit(driver, button, button_type):
    try:
        driver.execute_script("arguments[0].click();", button)
        time.sleep(3)
        current_url = driver.current_url
        if current_url != start_url:
            logging.info(f"Form submitted - Redirected to: {current_url}")
            return True
    except (ElementNotInteractableException, TimeoutException):
        button.send_keys(Keys.RETURN)
    return False

def submit_form(driver, selectors):
    for selector, selector_type in selectors:
        try:
            submit_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((selector_type, selector)))
            if click_and_submit(driver, submit_button, selector_type):
                return True
        except TimeoutException:
            logging.info(f"Timed out waiting for the submit button to be clickable: {selector}")
    try:
        any_button = driver.find_element(By.TAG_NAME, 'button')
        any_button.click()
        return True
    except NoSuchElementException:
        logging.info("No buttons found on the page.")
    return False

# Check if the URL is blacklisted
def is_blacklisted(url):
    for blacklisted_url in blacklisted_urls:
        if blacklisted_url in url:
            return True
    return False

# Fill sign-up form
def fill_sign_up_form(driver, start_url):
    global should_continue, email_used
    driver = ensure_driver(driver)
    base_domain = get_base_domain(start_url)
    visited_urls = set()
    urls_to_check = [start_url]
    form_filled = False

    while urls_to_check and should_continue:
        current_url = urls_to_check.pop(0)
        if current_url in visited_urls or is_blacklisted(current_url):
            continue
        visited_urls.add(current_url)
        try:
            if has_two_or_more_password_fields(driver, current_url) and not form_filled and should_continue:
                driver = ensure_driver(driver)
                driver.get(current_url)
                html_content = driver.page_source
                if has_captcha(html_content, driver):
                    return False

                wait = WebDriverWait(driver, 5)
                try:
                    form = wait.until(EC.presence_of_element_located((By.TAG_NAME, 'form')))
                    if form and should_continue:
                        predictions = predict_values(form)
                        fill_form(predictions)
                        time.sleep(1)

                        if not should_continue:
                            return False

                        handle_dropdowns(form, driver)
                        time.sleep(1)

                        if not should_continue:
                            return False

                        handle_checkbox(driver)

                        selectors = [
                            ('input[type="submit"]', By.CSS_SELECTOR),
                            ('button[type="submit"]', By.CSS_SELECTOR),
                            ('button[type="button"]', By.CSS_SELECTOR),
                            ('input[name="submit"]', By.NAME)
                        ]

                        if submit_form(driver, selectors):
                            email_used = predictions.get("email")
                            form_filled = True
                            logging.info(f"Form submission successful. Signed up using {email_used}")
                            api_key = "YOUR_API_KEY"
                            email_checked = check_mailinator_inbox_and_click_links(api_key, driver, 10)
                            if email_checked:
                                logging.info("Successfully interacted with new email.")
                            else:
                                logging.info("No new email to interact with within 10 seconds.")

                            login_url = find_login_url_with_single_password_field(driver, current_url)
                            if login_url:
                                login_and_take_screenshot(driver, login_url, "PASSWORD", email_used)
                            else:
                                logging.info("Could not find a login URL to proceed with login.")
                                return False
                            break

                        else:
                            logging.info("Form submission unsuccessful.")
                    else:
                        logging.info("No form found on the page.")
                except Exception as e:
                    logging.error(f"An error occurred: {str(e)}")

            if not form_filled:
                for link in driver.find_elements(By.CSS_SELECTOR, 'a[href]'):
                    absolute_link = urljoin(current_url, link.get_attribute('href'))
                    if get_base_domain(absolute_link) == base_domain and not is_blacklisted(absolute_link):
                        if absolute_link not in visited_urls and absolute_link not in urls_to_check and should_continue:
                            urls_to_check.append(absolute_link)
        except TimeoutException:
            logging.info(f"Sign-up unsuccessful for {current_url}. Website not reachable")
    if not form_filled:
        logging.info("No page with two or more password fields found.")
    return form_filled

# Check for multiple password fields
def has_two_or_more_password_fields(driver, url):
    if url.startswith('javascript:'):
        return None
    keywords = ['joinus', 'register', 'signup','createaccount', 'newuser', 'registration'] #Keywords to detect signup pages in DOM
    if any(keyword in url.lower() for keyword in keywords):
        logging.info(f"Registration URL is {url}")
        return url
    try:
        driver.get(url)
        password_inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="password"]')
        if len(password_inputs) >= 2:
            return url
    except Exception as e:
        logging.error(f"An error occurred while fetching {url}: {str(e)}")

# Process URLs from a list
def fill_sign_up_urls_in_list(urls_file_path, last_processed_file_path):
    last_processed_url = get_last_processed_url(last_processed_file_path)
    start_processing = last_processed_url is None

    with open(urls_file_path, 'r') as file:
        for line in file:
            url = line.strip()
            if start_processing:
                try:
                    email_used = fill_sign_up_form_with_timeout(driver, url)
                    if email_used:
                        logging.info(f"Success: {url} ")
                    else:
                        logging.info(f"Timeout or failure: {url}")
                    save_last_processed_url(last_processed_file_path, url)
                except Exception as e:
                    logging.error(f"An error occurred while processing {url}: {e}")
                    break
            if url == last_processed_url:
                start_processing = True

# Check for single password field
def has_single_password_field(driver, url):
    if url.startswith('javascript:'):
        return None
    login_keywords = [
        'login', 'signin', 'log-in', 'sign-in', 'auth', 'authenticate',
        'account', 'user', 'useraccount', 'user-account', 'myaccount', 'userlogin', 'enter' #Keywords to detect login pages in DOM
    ]
    if any(keyword in url.lower() for keyword in login_keywords):
        logging.info(f"The login URLs are {url}")
        return url
    try:
        driver.get(url)
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        password_inputs = soup.find_all('input', {'type': 'password'})
        if len(password_inputs) == 1:
            return url
    except Exception as e:
        logging.error(f"An error occurred while fetching {url}: {str(e)}")
    return None

# Get base domain from URL
def get_base_domain(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc

# Login and take screenshot
def login_and_take_screenshot(driver, login_url, predicted_password, email_used):
    base_domain = get_base_domain(login_url)
    try:
        driver.get(login_url)
        logging.info(f"Navigating to URL: {login_url}")
        original_window = driver.current_window_handle
        initial_url = driver.current_url

        try:
            username_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="username"],input[type="email"],input[type="text"]')))
            input_type = username_input.get_attribute('type')
            if input_type == "text":
                modified_email = re.sub(r'\d+', '', email_used).replace("@your-email-domain.com", "")
                username_input.send_keys(modified_email)
            else:
                username_input.send_keys(email_used)
        except TimeoutException:
            logging.error("Timeout occurred while trying to find the username/email input field.")

        password_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]')))
        password_input.send_keys(predicted_password)

        try:
            submit_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit'],input[type='submit']")))
            submit_button.click()
        except TimeoutException:
            submit_button = driver.find_element(By.CSS_SELECTOR, "form button, form input[type='button']")
            driver.execute_script("arguments[0].click();", submit_button)

        WebDriverWait(driver, 10).until(EC.url_changes(initial_url))
        logging.info("URL changed, indicating a potential successful login.")

        directory_name = login_url.replace('://', '_').replace('/', '_')
        os.makedirs(directory_name, exist_ok=True)
        processed_links = set()

        links = driver.find_elements(By.TAG_NAME, 'a')
        process_links(driver, links, processed_links, base_domain, directory_name, original_window, max_links=25)
    except NoSuchElementException as e:
        logging.error(f"Element not found during login process: {e}")
    except TimeoutException as e:
        logging.error("Timeout occurred, login might have failed or the URL did not change.")
    except Exception as e:
        logging.error(f"Unexpected error during login and page capturing: {e}")
    finally:
        if original_window in driver.window_handles:
            driver.switch_to.window(original_window)

#Validate links to avoid clicking on logout/signout buttons
def validate_link(href, processed_links, base_domain):
    return href is not None and href not in processed_links and "logout" not in href.lower() and "signout" not in href.lower() and get_base_domain(href) == base_domain

def process_link(driver, href, directory_name, original_window):
    driver.execute_script("window.open(arguments[0]);", href)
    driver.switch_to.window(driver.window_handles[-1])
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
    time.sleep(3)

    html_content = driver.page_source
    html_file_path = os.path.join(directory_name, f"page_{href.replace('://', '_').replace('/', '_').replace('?', '_')}.html")
    with open(html_file_path, 'w', encoding='utf-8') as file:
        file.write(html_content)

    result = driver.execute_cdp_cmd("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True})
    screenshot_data = base64.b64decode(result['data'])
    screenshot_path = os.path.join(directory_name, f"screenshot_{href.replace('://', '_').replace('/', '_').replace('?', '_')}.png")
    with open(screenshot_path, 'wb') as file:
        file.write(screenshot_data)

    logging.info(f"Captured and saved data for {href}")
    driver.close()
    driver.switch_to.window(original_window)

def process_links(driver, links, processed_links, base_domain, directory_name, original_window, max_links=25):
    if len(processed_links) >= max_links:
        logging.info(f"Reached maximum link processing threshold of {max_links}. Stopping further processing.")
        return

    deposit_page_counter = 0

    for link in links:
        href = link.get_attribute('href')
        if validate_link(href, processed_links, base_domain):
            try:
                if re.search(r'\bdeposits?\b', href.lower()) and deposit_page_counter < 5: # condition true if either deposit or deposits in url and within limit
                    process_deposit_page(driver, href, directory_name, original_window)
                    deposit_page_counter += 1
                else:
                    process_link(driver, href, directory_name, original_window)
                processed_links.add(href)

                second_layer_links = driver.find_elements(By.TAG_NAME, 'a')
                for second_link in second_layer_links:
                    second_href = second_link.get_attribute('href')
                    if validate_link(second_href, processed_links, base_domain) and len(processed_links) < max_links:
                        if re.search(r'\bdeposits?\b', second_href.lower()) and deposit_page_counter < 5:
                            process_deposit_page(driver, second_href, directory_name, original_window)
                            deposit_page_counter += 1
                        else:
                            process_link(driver, second_href, directory_name, original_window)
                        processed_links.add(second_href)
                    if len(processed_links) >= max_links:
                        logging.info("Reached max links limit during second-layer processing.")
                        break
            except UnexpectedAlertPresentException as e:
                alert = driver.switch_to.alert
                logging.warning(f"Unexpected alert present while processing {href}: {alert.text}")
                alert.accept()
                logging.info(f"Accepted unexpected alert for {href}. Moving to next link.")
            except Exception as e:
                logging.error(f"Failed to process {href}: {e}")
            finally:
                if original_window not in driver.window_handles:
                    logging.error("Original window has been closed.")
                else:
                    driver.switch_to.window(original_window)

def process_deposit_page(driver, href, directory_name, original_window):
    def safe_find_elements(by, value, retries=3, delay=1):
        """Safely find elements and handle StaleElementReferenceException."""
        for attempt in range(retries):
            try:
                elements = driver.find_elements(by, value)
                if elements is not None:
                    return [el for el in elements if el is not None]  # Filter out None elements
                else:
                    return []  # Return empty list if no elements are found
            except StaleElementReferenceException:
                if attempt < retries - 1:
                    time.sleep(delay)  
                else:
                    raise

    def safe_click_element(element, retries=3, delay=1):
        """Safely click an element and handle StaleElementReferenceException."""
        for attempt in range(retries):
            try:
                if element is not None:  # Check if element is not None
                    driver.execute_script("arguments[0].scrollIntoView(true);", element)  # Scroll to the element
                    time.sleep(0.5)  # Small delay to ensure the element is in view
                    element.click()
                return
            except StaleElementReferenceException:
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    raise

    def disable_google_translate_bar():
        """Disable the Google Translate bar if it appears."""
        try:
            driver.execute_script("""
                var element = document.querySelector('#google_translate_element');
                if (element) {
                    element.style.display = 'none';
                }
                var translateBar = document.querySelector('.goog-te-banner-frame');
                if (translateBar) {
                    translateBar.style.display = 'none';
                }
                var body = document.querySelector('body');
                if (body) {
                    body.classList.remove('translated-rtl');
                }
            """)
        except Exception as e:
            logging.error(f"Failed to disable Google Translate bar: {e}")

    def clear_input_fields(input_elements, select_elements, text_fields):
        """Clear the values in input fields (radio buttons, checkboxes, text fields, and dropdowns)."""
        for input_element in input_elements:
            try:
                if input_element.get_attribute('type') in ['radio', 'checkbox']:
                    input_element.click()  # Toggle the state of radio buttons and checkboxes
            except Exception as e:
                logging.error(f"Failed to clear input element: {e}")

        for text_field in text_fields:
            try:
                text_field.clear()
            except Exception as e:
                logging.error(f"Failed to clear text field: {e}")

        for select_element in select_elements:
            try:
                select = Select(select_element)
                select.deselect_all()
            except Exception as e:
                logging.error(f"Failed to clear dropdown: {e}")

    def set_radio_option(input_elements, radio_option):
        """Set the value of a radio button option."""
        for input_element in input_elements:
            try:
                if input_element.get_attribute('type') == 'radio' and input_element.get_attribute('value') == radio_option:
                    safe_click_element(input_element)
                    break
            except Exception as e:
                logging.error(f"Failed to set radio option: {e}")

    def set_dropdown_options(select_elements, dropdown_options, dropdown_values):
        """Set the values of dropdown options."""
        for select_element, options in zip(select_elements, dropdown_values):
            try:
                select = Select(select_element)
                for option in options:
                    select.select_by_value(option)
            except Exception as e:
                logging.error(f"Failed to set dropdown option: {e}")

    def set_text_field_values(text_fields, text_field_value):
        """Set the values of text fields."""
        for text_field in text_fields:
            try:
                text_field.send_keys(text_field_value)
            except Exception as e:
                logging.error(f"Failed to set text field value: {e}")

    def find_submit_button(driver):
        """Find and return the submit button element."""
        possible_selectors = ["input[type='submit']", "button[type='submit']", "input[type='button']", "button[type='button']"]
        for selector in possible_selectors:
            submit_buttons = safe_find_elements(By.CSS_SELECTOR, selector)
            if submit_buttons:
                return submit_buttons[0]
        return None

    def capture_html_and_screenshot(driver, directory_name, href, counter):
        """Capture the HTML content and screenshot of the current page."""
        html_content = driver.page_source

        # Create unique file name based on the combination values for captured web pages
        html_file_path = os.path.join(directory_name, f"deposit_page_{href.replace('://', '_').replace('/', '_').replace('?', '_')}_{counter}.html")

        with open(html_file_path, 'w', encoding='utf-8') as file:
            file.write(html_content)

        result = driver.execute_cdp_cmd("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True})
        screenshot_data = base64.b64decode(result['data'])
        screenshot_path = os.path.join(directory_name, f"deposit_screenshot_{counter}.png")
        with open(screenshot_path, 'wb') as file:
            file.write(screenshot_data)

        logging.info(f"Captured and saved data for deposit page {href} with counter: {counter}")

    driver.execute_script("window.open(arguments[0]);", href)
    driver.switch_to.window(driver.window_handles[-1])
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
    time.sleep(3)

    try:
        # Disable Google Translate bar if it appears
        disable_google_translate_bar()

        # Find input elements
        select_elements = safe_find_elements(By.TAG_NAME, 'select')
        input_elements = safe_find_elements(By.CSS_SELECTOR, 'input[type="checkbox"], input[type="radio"]')
        text_fields = safe_find_elements(By.CSS_SELECTOR, 'input[type="text"], input[type="number"]')

        # Store input options in separate lists/dictionaries
        radio_options = [element.get_attribute('value') for element in input_elements if element.get_attribute('type') == 'radio']
        dropdown_options = {select.get_attribute('name'): [option.get_attribute('value') for option in select.find_elements(By.TAG_NAME, 'option')] for select in select_elements}
        text_fields_values = ['1000']  # or any other desired values
        counter = 1

        # Generate all possible combinations of input options
        all_combinations = itertools.product(radio_options, dropdown_options.values(), text_fields_values)

        # Iterate over each combination
        for radio_option, dropdown_values, text_field_value in all_combinations:
            # Clear existing values
            clear_input_fields(input_elements, select_elements, text_fields)

            # Set values for the current combination
            set_radio_option(input_elements, radio_option)
            set_dropdown_options(select_elements, dropdown_options, dropdown_values)
            set_text_field_values(text_fields, text_field_value)

            # Find and click the submit button
            submit_button = find_submit_button(driver)
            if submit_button:
                safe_click_element(submit_button)

            # Wait for the resulting page to load
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            time.sleep(3)

            # Capture HTML and screenshot
            capture_html_and_screenshot(driver, directory_name, href, counter)
            counter += 1

            # Navigate back to the original deposit page
            driver.get(href)

    except UnexpectedAlertPresentException as e:
        alert = driver.switch_to.alert
        logging.warning(f"Unexpected alert present while processing deposit page {href}: {alert.text}")
        alert.accept()
        logging.info(f"Accepted unexpected alert for deposit page {href}. Moving to next link.")
    except Exception as e:
        logging.error(f"Failed to process deposit page {href}: {e}")
    finally:
        driver.close()
        driver.switch_to.window(original_window)

# Sign-up form with timeout
def fill_sign_up_form_with_timeout(driver, url, timeout_seconds=300):
    global should_continue, form_filled
    should_continue = True
    form_filled = False

    def target():
        global form_filled
        form_filled = fill_sign_up_form(driver, url)

    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout_seconds)
    if thread.is_alive():
        logging.warning(f"Timeout exceeded for {url}")
        should_continue = False
        thread.join()
        return False
    return email_used if form_filled else None

# Find login URL with a single password field
def find_login_url_with_single_password_field(driver, start_url):
    visited_urls = set()
    urls_to_check = [start_url]
    login_url = None

    while urls_to_check:
        current_url = urls_to_check.pop(0)
        if current_url in visited_urls or is_blacklisted(current_url):
            continue
        visited_urls.add(current_url)
        try:
            driver.get(current_url)
            login_url = has_single_password_field(driver, current_url)
            if login_url:
                logging.info(f"URL with a single password field in a form: {login_url}")
                return login_url
            links = driver.find_elements(By.TAG_NAME, 'a')
            for link in links:
                absolute_link = urljoin(current_url, link.get_attribute('href'))
                if absolute_link not in visited_urls and absolute_link not in urls_to_check and not is_blacklisted(absolute_link):
                    urls_to_check.append(absolute_link)
        except Exception as e:
            logging.error(f"An error occurred while crawling {current_url}: {str(e)}")
    logging.info("No page with a single password field found.")
    return None

# Save and retrieve last processed URL
def save_last_processed_url(file_path, last_url):
    with open(file_path, 'w') as file:
        file.write(last_url)

def get_last_processed_url(file_path):
    try:
        with open(file_path, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        return None

# Check Mailinator inbox and click links. Mailinator is used as an email service to click on email confirmation links after signup
def check_mailinator_inbox_and_click_links(api_key, driver, time_threshold_seconds=10):
    endpoint = "https://api.mailinator.com/api/v2/domains/private/inboxes"
    params = {"token": api_key}
    email_interacted = False

    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        inboxes = response.json().get('inboxes', [])

        for inbox in inboxes:
            inbox_endpoint = f"{endpoint}/{inbox}/messages"
            inbox_response = requests.get(inbox_endpoint, params=params)
            inbox_response.raise_for_status()
            emails = inbox_response.json().get('msgs', [])

            for email in emails:
                email_time = datetime.fromtimestamp(email['time'])
                if datetime.now() - email_time < timedelta(seconds=time_threshold_seconds):
                    email_id = email['id']
                    email_content_endpoint = f"{inbox_endpoint}/{email_id}"
                    email_content_response = requests.get(email_content_endpoint, params=params)
                    email_content = email_content_response.json().get('data', {}).get('parts', [])[0].get('body', '')

                    links = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', email_content)
                    for link in links:
                        driver.get(link)
                        logging.info(f"Clicked link in email: {link}")
                        email_interacted = True

        return email_interacted
    except requests.RequestException as e:
        logging.error(f"Error checking Mailinator inbox: {e}")
        return False

# Main function
def main():
    global driver
    driver = initialize_driver()
    handle_alert(driver)  # Handle initial alerts right after the driver is initialized
    try:
        list_of_urls_file = 'urls.txt' #List of URLs to run the crawler through
        last_processed_file_path = 'crawled_urls.txt' #Contains the last crawled URL to keep track
        fill_sign_up_urls_in_list(list_of_urls_file, last_processed_file_path)

        login_url = find_login_url_with_single_password_field(driver, start_url)
        if login_url:
            driver.get(login_url)
            handle_alert(driver)  # Handle any alerts that may appear when navigating to the login page
            predicted_password = 'PASSWORD' #Password for logging in the the account created
            if login_and_take_screenshot(driver, login_url, predicted_password, email_used):
                logging.info("Login and screenshot successful.")
            else:
                logging.error("Login failed or screenshot not taken.")
        else:
            logging.info("No page with a single password field found.")
    except Exception as e:
        logging.error(f"An error occurred in the main loop: {e}")
        driver = ensure_driver(driver)  # Ensures the driver is responsive and handles re-initialization if needed
    finally:
        logging.info("Quitting Driver")
        driver.quit()

if __name__ == "__main__":
    main()