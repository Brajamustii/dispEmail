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
import cloudscraper
from colorama import init, Fore, Style
from seleniumbase import Driver

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
    """Generate a temporary email using EmailNator with SeleniumBase"""
    driver = None
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            # Initialize the SeleniumBase driver with undetected-chromedriver
            driver = Driver(
                uc=True,                    # Use undetected-chromedriver
                headless=True,             # Keep visible for debugging
                agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
                incognito=True,             # Use incognito mode
                disable_csp=True,           # Disable Content Security Policy
                block_images=True,          # Block images for faster loading
                do_not_track=True,          # Enable Do Not Track
                no_sandbox=True            # Bypass OS security model
            )
            
            # Set page load timeout
            driver.set_page_load_timeout(60)
            
            # Load EmailNator homepage
            info(f"Attempt {attempt + 1}/{max_retries}: Loading EmailNator...")
            driver.get('https://www.emailnator.com/')
            
            # Wait for the page to load completely
            time.sleep(random.uniform(5, 10))
            
            # Debug: Print page title and URL
            info(f"Current URL: {driver.current_url}")
            info(f"Page title: {driver.title}")
            
            # Get cookies and extract XSRF token
            cookies = driver.get_cookies()
            cookie_dict = {c['name']: c['value'] for c in cookies}
            
            # Extract XSRF token from cookies
            xsrf_token = cookie_dict.get('XSRF-TOKEN', '')
            if '%3D' in xsrf_token:
                xsrf_token = urllib.parse.unquote(xsrf_token)
            
            if not xsrf_token:
                error("XSRF token not found in cookies")
                raise Exception("Failed to get XSRF token")
            
            # Set up request headers
            headers = {
                'authority': 'www.emailnator.com',
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': 'application/json',
                'origin': 'https://www.emailnator.com',
                'referer': 'https://www.emailnator.com/',
                'user-agent': driver.execute_script("return navigator.userAgent;"),
                'x-requested-with': 'XMLHttpRequest',
                'x-xsrf-token': xsrf_token
            }
            
            # Make the API request
            info("Generating email...")
            data = {"email": ["dotGmail"]}
            
            # Use Selenium to make the request
            api_url = 'https://www.emailnator.com/generate-email'
            script = f"""
            var xhr = new XMLHttpRequest();
            xhr.open('POST', '{api_url}', false);
            {''.join([f"xhr.setRequestHeader('{k}', '{v}');" for k, v in headers.items()])}
            xhr.send(JSON.stringify({json.dumps(data)}));
            return {{
                status: xhr.status,
                responseText: xhr.responseText
            }};
            """
            
            result = driver.execute_script(script)
            
            if result['status'] >= 400:
                error(f"Failed to generate email: {result['status']} {result['responseText']}")
                raise Exception(f"Failed to generate email: {result['status']}")
            
            email_data = json.loads(result['responseText'])
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
            error(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                raise
            info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    raise Exception("All attempts to generate email failed")

def main():
    print("""
 ###### #    #   ##   # #      #    #   ##   #####  ####  #####  
 #      ##  ##  #  #  # #      ##   #  #  #    #   #    # #    # 
 #####  # ## # #    # # #      # #  # #    #   #   #    # #    # 
 #      #    # ###### # #      #  # # ######   #   #    # #####  
 #      #    # #    # # #      #   ## #    #   #   #    # #   #  
 ###### #    # #    # # ###### #    # #    #   #    ####  #    #  
 AUTO GET COOKIE BY @AIRDROPFAMILYIDN
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
