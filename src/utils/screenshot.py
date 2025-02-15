import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class SeleniumScreenshot:
    def __init__(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument('--remote-debugging-pipe')
        chrome_options.add_argument("--window-size=1024,768")
        chrome_options.binary_location = r'/home/ubuntu/cryptoscams/datacollection/testing/chrome-unpacked/chrome-linux64/chrome'
        self.options = chrome_options

    def take_screenshot(self, url, curr_date, path, SYSNO):
        for attempt in range(2):
            if self.screenshot_retrier(url, curr_date, path, SYSNO):
                return True
        time.sleep(0.5)
        return False

    def screenshot_retrier(self, url, curr_date,  path, SYSNO):
        service = Service(executable_path=r'/usr/bin/chromedriver')
        browser = None
        try:
            service.start()
            browser = webdriver.Chrome(options=self.options, service=service)
            browser.set_page_load_timeout(20)
            browser.get("http://" + url)
            WebDriverWait(browser, 20).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            browser.execute_script("window.scrollTo(0, 0);")
            S = lambda X: browser.execute_script('return document.body.parentNode.scroll' + X)
            browser.set_window_size(S('Width'), S('Height'))
            browser.find_element(By.TAG_NAME, 'body').screenshot(path + '/full_page.png')
            return True
        except Exception as e:
            return False
        finally:
            if browser:
                browser.quit()
            service.stop()