import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging
from time import sleep

# Setup basic logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants for Chartink
Charting_Link = "https://chartink.com/screener/"
Charting_url = 'https://chartink.com/screener/process'
Condition = os.getenv('RSAEMA_CONDITION')
if Condition:
    logging.debug("RSAEMA_CONDITION is set: {}".format(Condition))
else:
    logging.error("RSAEMA_CONDITION is not set.")

# Telegram credentials from environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
if TELEGRAM_TOKEN:
    logging.debug("TELEGRAM_TOKEN is set.")
else:
    logging.error("TELEGRAM_TOKEN is not set.")
if TELEGRAM_CHAT_ID:
    logging.debug("TELEGRAM_CHAT_ID is set.")
else:
    logging.error("TELEGRAM_CHAT_ID is not set.")

def send_telegram_message(message):
    """Send a message to a predefined Telegram chat via bot using HTML formatting."""
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    response = requests.post(url, data=data)
    return response.json()

def format_data(data):
    """Format DataFrame data into a more readable HTML format."""
    return "<pre>" + data.to_string(index=False) + "</pre>"

def GetDataFromChartink():
    """Fetch data from Chartink based on the provided payload conditions."""
    retries = 3
    for attempt in range(retries):
        try:
            with requests.Session() as s:
                s.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
                logging.debug("Headers: {}".format(s.headers))
                r = s.get(Charting_Link)
                logging.debug("GET request to Charting_Link status code: {}".format(r.status_code))
                soup = BeautifulSoup(r.text, "html.parser")
                csrf_token = soup.select_one("[name='csrf-token']")['content']
                s.headers.update({'x-csrf-token': csrf_token})
                logging.debug("CSRF Token: {}".format(csrf_token))
                logging.debug("Scan Condition: {}".format(Condition))
                response = s.post(Charting_url, data={'scan_clause': Condition})
                logging.debug("POST request to Charting_url status code: {}".format(response.status_code))
                response_json = response.json()
                logging.debug("Request Data: {}".format({'scan_clause': Condition}))
                logging.debug("Response JSON: {}".format(response_json))
                if response.status_code == 200:
                    if 'data' in response_json and response_json['data']:
                        data = pd.DataFrame(response_json['data'])
                        formatted_message = format_data(data)
                        title = "Swing trading - Target 5%(Activate trailing stop loss once it reaches 4%) and SL 1%"
                        full_message = f"{title}\n{formatted_message}"
                        logging.info("Data received:\n{}".format(data))
                        send_telegram_message(f"Chartink Data:\n{full_message}")
                        return
                    else:
                        logging.info("No new data available.")
                        send_telegram_message("No new data available.")
                        if 'scan_error' in response_json:
                            logging.error("Scan error: {}".format(response_json['scan_error']))
                            send_telegram_message(f"Scan error: {response_json['scan_error']}")
                else:
                    logging.error("Failed to fetch data with status code: {}".format(response.status_code))
                    send_telegram_message(f"Failed to fetch data with status code: {response.status_code}")
        except Exception as e:
            logging.error("Exception during data fetch: {}".format(str(e)))
            send_telegram_message(f"Exception during data fetch: {str(e)}")
        sleep(10)  # wait before retrying
    logging.error("All retries failed")
    send_telegram_message("All retries failed")

if __name__ == '__main__':
    GetDataFromChartink()  # Immediate execution for testing
