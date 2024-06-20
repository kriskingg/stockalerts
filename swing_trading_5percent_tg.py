import os
import sys
import time
import datetime
import requests
from bs4 import BeautifulSoup
import pandas as pd
import schedule
import logging
from time import sleep

# Setup basic logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants for Chartink
Charting_Link = "https://chartink.com/screener/"
Charting_url = 'https://chartink.com/screener/process'
Condition = os.getenv('CHARTINK_CONDITION', 'Default Condition if not set')
logging.debug("CHARTINK_CONDITION: {}".format(Condition))

# Telegram credentials from environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
logging.debug("TELEGRAM_TOKEN: {}".format(TELEGRAM_TOKEN))
logging.debug("TELEGRAM_CHAT_ID: {}".format(TELEGRAM_CHAT_ID))

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
                response = s.post(Charting_url, data={'scan_clause': Condition})
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

def run_scheduled_job():
    """Convert to IST and run job if it's 23:40 IST."""
    now_utc = datetime.datetime.utcnow()
    ist = now_utc + datetime.timedelta(hours=5, minutes=30)  # UTC+5:30
    if ist.strftime('%H:%M') == '23:40':
        logging.info("Running scheduled job.")
        GetDataFromChartink()

# Scheduling
schedule.every(1).minutes.do(run_scheduled_job)

# Main execution for testing
if __name__ == '__main__':
    GetDataFromChartink()  # Immediate execution for testing
    while True:
        schedule.run_pending()
        time.sleep(1)  # Check every second for closer interval handling