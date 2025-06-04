import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import json
import os
import urllib.parse
import requests
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

def info(msg):
    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} {msg}")

def success(msg):
    print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {msg}")

def error(msg):
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {msg}")

def save_to_data_file(xsrf_token, gmailnator_session):
    """Save the XSRF token and gmailnator_session to data.txt"""
    with open('data.txt', 'w') as f:
        f.write(f"XSRF-TOKEN: {xsrf_token}\n")
        f.write(f"gmailnator_session: {gmailnator_session}\n")
    info("Tokens saved to data.txt")

def load_from_data_file():
    """Load the XSRF token and gmailnator_session from data.txt if it exists"""
    if not os.path.exists('data.txt'):
        return None, None

    xsrf_token = None
    gmailnator_session = None

    with open('data.txt', 'r') as f:
        for line in f:
            if line.startswith('XSRF-TOKEN:'):
                xsrf_token = line.split('XSRF-TOKEN:')[1].strip()
            elif line.startswith('gmailnator_session:'):
                gmailnator_session = line.split('gmailnator_session:')[1].strip()

    return xsrf_token, gmailnator_session

def generate_email():
    """Generate a temporary email using EmailNator with undetected-chromedriver"""
    options = uc.ChromeOptions()
    options.headless = True
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-notifications')
   # options.add_argument('--start-maximized')
    
    # Set a common user agent
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
    options.add_argument(f'user-agent={user_agent}')
    
    # Add some human-like behavior
    options.add_argument('--disable-web-security')
    options.add_argument('--allow-running-insecure-content')
    
    driver = None
    try:
        # Initialize the undetected Chrome driver with version check
        driver = uc.Chrome(
            options=options,
            version_main=136  # Force using ChromeDriver for version 136
        )
        driver.set_page_load_timeout(60)
        
        # First, visit the main page
        info("Loading EmailNator homepage...")
        driver.get('https://www.emailnator.com/')
        
        # Wait for the page to load completely
        time.sleep(random.uniform(3, 7))
        
        # Debug: Print page title and URL
        info(f"Current URL: {driver.current_url}")
        info(f"Page title: {driver.title}")
        
        # Check if we got redirected
        if "emailnator.com" not in driver.current_url:
            error(f"Unexpected redirect to: {driver.current_url}")
            raise Exception("Page was redirected unexpectedly")
            
        # More flexible check for the page content
        if "emailnator" not in driver.page_source.lower() and "temporary disposable" not in driver.page_source.lower():
            error("Page content doesn't match expected content")
            # Save page source for debugging
            with open('page_source.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            error("Page source saved to page_source.html")
            raise Exception("Failed to load EmailNator homepage - content validation failed")
        
        # Get cookies and extract XSRF token
        cookies = driver.get_cookies()
        cookie_dict = {c['name']: c['value'] for c in cookies}
        
        # Extract XSRF token from cookies - it might be URL-encoded
        xsrf_token = cookie_dict.get('XSRF-TOKEN', '')
        if '%3D' in xsrf_token:
            xsrf_token = urllib.parse.unquote(xsrf_token)
        
        # Prepare the request headers with the correct XSRF token
        headers = {
            'authority': 'www.emailnator.com',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://www.emailnator.com',
            'referer': 'https://www.emailnator.com/',
            'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not-A.Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': user_agent,
            'x-requested-with': 'XMLHttpRequest',
            'x-xsrf-token': xsrf_token  # Use the properly formatted token
        }
        
        # Generate email
        info("Generating email...")
        data = json.dumps({"email": ["dotGmail"]})
        
        # Create a new session and set cookies
        session = requests.Session()
        for cookie in cookies:
            # Make sure to set the correct domain and path for the cookies
            session.cookies.set(
                cookie['name'],
                cookie['value'],
                domain='.emailnator.com',
                path='/'
            )
        
        # Add headers to the session
        session.headers.update(headers)
        
        # Make the request
        response = session.post(
            'https://www.emailnator.com/generate-email',
            headers=headers,
            data=data,
            timeout=30
        )
        
        if response.status_code >= 400:
            error(f"Failed to generate email: {response.status_code} {response.text}")
            raise Exception(f"Failed to generate email: {response.status_code}")
        
        email_data = response.json()
        if not email_data or 'email' not in email_data or not email_data['email']:
            error("No email returned in response")
            error(f"Response: {email_data}")
            raise Exception("No email returned in response")
        
        email = email_data['email'][0]
        info(f"Generated email: {email}")
        
        # Get updated cookies
        updated_cookies = driver.get_cookies()
        xsrf_token = next((c['value'] for c in updated_cookies if c['name'] == 'XSRF-TOKEN'), '')
        gmailnator_session = next((c['value'] for c in updated_cookies if c['name'] == 'gmailnator_session'), '')
        
        if '%3D' in xsrf_token:
            xsrf_token = urllib.parse.unquote(xsrf_token)
        
        save_to_data_file(xsrf_token, gmailnator_session)
        
        return email, xsrf_token, gmailnator_session
        
    except Exception as e:
        error(f"Error in generate_email: {str(e)}")
        # Take a screenshot for debugging
        if driver:
            screenshot_path = os.path.join(os.getcwd(), 'error_screenshot.png')
            driver.save_screenshot(screenshot_path)
            info(f"Screenshot saved to: {screenshot_path}")
        raise
        
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def main():
    print("""
 ###### #    #   ##   # #      #    #   ##   #####  ####  #####  
 #      ##  ##  #  #  # #      ##   #  #  #    #   #    # #    # 
 #####  # ## # #    # # #      # #  # #    #   #   #    # #    # 
 #      #    # ###### # #      #  # # ######   #   #    # #####  
 #      #    # #    # # #      #   ## #    #   #   #    # #   #  
 ###### #    # #    # # ###### #    # #    #   #    ####  #    #                                                  
    """)
    
    try:
        info("Starting email generation...")
        email, xsrf_token, gmailnator_session = generate_email()
        success(f"Successfully generated email: {email}")
        success(f"XSRF Token: {xsrf_token[:20]}...")
        success(f"Session: {gmailnator_session[:20]}...")
        
    except Exception as e:
        error(f"Error in main: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    main()