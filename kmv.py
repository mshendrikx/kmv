import time
import logging
import os

from seleniumbase import Driver
from selenium.webdriver.common.by import By
from whatsapp_api import whatsapp_send_message, whatsapp_restart_session
from dotenv import load_dotenv
from datetime import datetime 

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Configuration
TARGET_URL = "https://www.abasteceai-futebol.com.br/"  # Change to your target page after login
REFRESH_INTERVAL = os.environ.get("REFRESH_INTERVAL")  # Seconds between refreshes
HEADLESS_MODE = False  # Set to False to see the browser
WHATSAPP_BASE_URL = os.environ.get("WHATSAPP_BASE_URL")
WHATSAPP_API_KEY = os.environ.get("WHATSAPP_API_KEY")
WHATSAPP_SESSION = os.environ.get("WHATSAPP_SESSION")
CELL_PHONE_NUMBERS = os.environ.get("CELL_PHONE_NUMBERS").split(",")  # List of phone numbers to send messages to

def main():
    
    final_date_txt = os.environ.get("FINAL_DATE")  # The final date to stop the script
    final_date = datetime.strptime(final_date_txt, "%Y-%m-%d %H:%M:%S")
    search_team = os.environ.get("SEARCH_TEAM")  # The team to search for
    search_text = os.environ.get("SEARCH_TEXT")  # The opponent team to search for
    teams_xpath = f'/html/body/app-root/div/div/app-home-container/app-view-home/div/div[2]/div/app-home-welcome/section/div/app-home-welcome-clubs'
    #search_xpath = f'/html/body/app-root/div/app-header-container/app-view-header/div/div[2]/input'
    result_xpath = f'/html/body/app-root/div/app-header-container/app-view-header/div[1]/div[2]/app-modal-search'
    # Initialize the SeleniumBase Driver
    driver = Driver(
        headless=HEADLESS_MODE,
        uc_cdp=True,  # Undetected ChromeDriver mode
        incognito=False,  # Some sites don't work well in incognito
        agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )

    try:
        
        # Navigate to target page after successful login
        driver.get(TARGET_URL)       

        logging.info(f"Starting page refresh every {REFRESH_INTERVAL} seconds")
        logging.info(f"Target URL: {TARGET_URL}")
        logging.info("Press Ctrl+C to stop the script")

        while True:
            try:
                
                if final_date < datetime.now():
                    logging.info("final_date is in the future.")
                    break
                driver.wait_for_element(teams_xpath, timeout=10)
                teams_div = driver.find_elements(".club.animated.fadeInUp.ng-star-inserted")
                for item in teams_div:
                    if search_team in item.text:
                        logging.info(f"Found team: {item.text}")
                        team = item
                        item.click()
                        break
                if not team:
                    logging.info(f"Team {search_team} not found.")
                    break
                
                driver.wait_for_element('.home-products', timeout=10)
                
                team_matches = driver.find_elements(".match-item.ng-star-inserted")
                
                found = False
                for team_match in team_matches:
                    if search_text in team_match.text:
                        logging.info(f"Match found: {team_match.text}")
                        found = True
                        whatsapp_restart_session(
                            base_url=WHATSAPP_BASE_URL,
                            api_key=WHATSAPP_API_KEY,
                            session=WHATSAPP_SESSION,
                        )
                        whatsapp_send_message(
                            base_url=WHATSAPP_BASE_URL,
                            api_key=WHATSAPP_API_KEY,
                            session=WHATSAPP_SESSION,
                            contacts=CELL_PHONE_NUMBERS,
                            content=team_match.screenshot_as_base64,
                            content_type="MessageMedia",
                        )
                        team_match.screenshot('team_match.png')
                        break
                    
                if found:
                    break
                
                # Wait for the next refresh
                time.sleep(int(REFRESH_INTERVAL))
                # Refresh the page
                driver.refresh()
                logging.info("Page refreshed successfully")
                
            except Exception as e:
                logging.error(f"Error: {str(e)}")
                driver.refresh()

    except KeyboardInterrupt:
        logging.info("\nScript stopped by user")
        
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        
    finally:
        driver.quit()
        logging.info("Browser closed successfully")

if __name__ == "__main__":
    main()