import cloudscraper
import json
import time
import urllib.parse
import os
import random
from colorama import init, Fore, Style

init(autoreset=True)

def info(msg):
    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} {msg}")

def success(msg):
    print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {msg}")

def warning(msg):
    print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} {msg}")

def error(msg):
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {msg}")

def retry_on_error(func):
    """Decorator to retry a function on error with exponential backoff"""
    def wrapper(*args, **kwargs):
        max_retries = 5
        retry_delay = 1  

        for attempt in range(1, max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:

                if "status code: 5" in str(e) or "500" in str(e) or "502" in str(e) or "503" in str(e) or "504" in str(e):
                    if attempt < max_retries:

                        jitter = random.uniform(0, 0.5)
                        wait_time = retry_delay + jitter

                        warning(f"Attempt {attempt} failed: {str(e)[:100]}...")
                        info(f"Retrying in {wait_time:.2f} seconds... ({attempt}/{max_retries})")

                        time.sleep(wait_time)

                        retry_delay *= 2
                    else:
                        error(f"Max retries ({max_retries}) exceeded. Last error: {str(e)}")
                        raise
                else:

                    raise
    return wrapper

def save_to_data_file(xsrf_token, gmailnator_session):
    """Save the XSRF token and gmailnator_session to data.txt"""
    with open('data.txt', 'w') as f:
        f.write(f"XSRF-TOKEN: {xsrf_token}\n")
        f.write(f"gmailnator_session: {gmailnator_session}\n")
    info("Cookies saved to data.txt")

def load_from_data_file():
    """Load the XSRF token and gmailnator_session from data.txt if it exists"""
    if not os.path.exists('data.txt'):
        return None, None

    xsrf_token = None
    gmailnator_session = None

    with open('data.txt', 'r') as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith('XSRF-TOKEN:'):
                xsrf_token = line.split('XSRF-TOKEN:')[1].strip()
            elif line.startswith('gmailnator_session:'):
                gmailnator_session = line.split('gmailnator_session:')[1].strip()

    return xsrf_token, gmailnator_session

@retry_on_error
def generate_email():

    scraper = cloudscraper.create_scraper(browser={
        'browser': 'chrome',
        'platform': 'darwin',
        'mobile': False
    })

    info("Getting fresh cookies...")
    main_response = scraper.get('https://www.emailnator.com/')

    if main_response.status_code != 200:
        error(f"Failed to access main site: {main_response.status_code}")
        raise Exception(f"Failed to access main site: {main_response.status_code}")

    cookies = scraper.cookies.get_dict()
    xsrf_token = cookies.get('XSRF-TOKEN', '')
    gmailnator_session = cookies.get('gmailnator_session', '')

    if '%3D' in xsrf_token:
        xsrf_token = urllib.parse.unquote(xsrf_token)

    url = 'https://www.emailnator.com/generate-email'

    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        'content-type': 'application/json',
        'dnt': '1',
        'origin': 'https://www.emailnator.com',
        'priority': 'u=1, i',
        'referer': 'https://www.emailnator.com/',
        'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
        'x-xsrf-token': xsrf_token
    }

    data = json.dumps({"email": ["plusGmail", "dotGmail", "googleMail"]})

    response = scraper.post(url, headers=headers, data=data)

    if response.status_code >= 400:
        error_msg = f"Failed to generate email: {response.status_code} {response.text}"
        error(error_msg)
        raise Exception(error_msg)

    cookies = scraper.cookies.get_dict()

    xsrf_token = cookies.get('XSRF-TOKEN', '')
    if '%3D' in xsrf_token:
        xsrf_token = urllib.parse.unquote(xsrf_token)

    gmailnator_session = cookies.get('gmailnator_session', '')

    email = response.json().get('email', [None])[0]
    if not email:
        error("No email returned!")
        raise Exception("No email returned!")

    save_to_data_file(xsrf_token, gmailnator_session)

    return email, xsrf_token, gmailnator_session

@retry_on_error
def get_inbox(email, xsrf_token, gmailnator_session):

    scraper = cloudscraper.create_scraper(browser={
        'browser': 'chrome',
        'platform': 'darwin',
        'mobile': False
    })

    cookies = {
        'XSRF-TOKEN': xsrf_token,
        'gmailnator_session': gmailnator_session
    }

    for key, value in cookies.items():
        scraper.cookies.set(key, value)

    info("Refreshing inbox cookies...")
    inbox_page = scraper.get('https://www.emailnator.com/inbox')

    if inbox_page.status_code != 200:
        error(f"Failed to access inbox page: {inbox_page.status_code}")
        raise Exception(f"Failed to access inbox page: {inbox_page.status_code}")

    updated_cookies = scraper.cookies.get_dict()
    updated_xsrf_token = updated_cookies.get('XSRF-TOKEN', '')
    updated_gmailnator_session = updated_cookies.get('gmailnator_session', '')

    if '%3D' in updated_xsrf_token:
        updated_xsrf_token = urllib.parse.unquote(updated_xsrf_token)

    url = 'https://www.emailnator.com/message-list'

    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        'content-type': 'application/json',
        'dnt': '1',
        'origin': 'https://www.emailnator.com',
        'priority': 'u=1, i',
        'referer': 'https://www.emailnator.com/inbox/',
        'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
        'x-xsrf-token': updated_xsrf_token
    }

    info(f"Checking inbox for: {Fore.YELLOW}{email}")

    data = json.dumps({"email": email})
    response = scraper.post(url, headers=headers, data=data)

    if response.status_code >= 400:
        error_msg = f"Failed to get inbox: {response.status_code} {response.text}"
        error(f"Inbox request failed: {response.status_code}")
        error(f"Response: {response.text[:100]}...")
        raise Exception(error_msg)

    updated_cookies = scraper.cookies.get_dict()
    updated_xsrf_token = updated_cookies.get('XSRF-TOKEN', xsrf_token)
    updated_gmailnator_session = updated_cookies.get('gmailnator_session', gmailnator_session)

    if updated_xsrf_token != xsrf_token or updated_gmailnator_session != gmailnator_session:
        save_to_data_file(updated_xsrf_token, updated_gmailnator_session)

    return response.json()

def main():
    print("""

 ** ====================================== **
 *    This script is created for free use   *
 *  Do not sell or distribute it for profit *
 ** ====================================== **

 * Author: @jinwooid                       
 * Github Link: github.com/jinwooid

    """)
    info("Generating email...")
    email, xsrf_token, gmailnator_session = generate_email()
    success(f"Generated: {Fore.YELLOW}{email}")

    info("Waiting before fetching inbox...")
    time.sleep(2)

    info("Fetching inbox...")
    inbox = get_inbox(email, xsrf_token, gmailnator_session)

    messages = inbox.get('messageData', [])
    if messages:
        success(f"Found {len(messages)} message(s) in inbox:")
        for i, msg in enumerate(messages, 1):
            print(f"{Fore.CYAN}[{i}]{Style.RESET_ALL} From: {Fore.YELLOW}{msg.get('from', 'Unknown')}{Style.RESET_ALL}")
            print(f"    Subject: {msg.get('subject', 'No subject')}")
            print(f"    Time: {Fore.GREEN}{msg.get('time', 'Unknown')}{Style.RESET_ALL}")
    else:
        warning("No messages found in inbox")

    success("Email operation completed successfully")

if __name__ == "__main__":
    main()