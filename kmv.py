import time
import logging
import os

from seleniumbase import Driver
from selenium.webdriver.common.by import By
from whatsapp_api import whatsapp_send_message, whatsapp_restart_session
from dotenv import load_dotenv
from datetime import datetime 

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Configuration
TARGET_URL = "https://www.abasteceai-futebol.com.br/"  # Change to your target page after login
REFRESH_INTERVAL = int(os.environ.get("REFRESH_INTERVAL"))  # Seconds between refreshes
WHATSAPP_BASE_URL = os.environ.get("WHATSAPP_BASE_URL")
WHATSAPP_API_KEY = os.environ.get("WHATSAPP_API_KEY")
WHATSAPP_SESSION = os.environ.get("WHATSAPP_SESSION")
DB_URL = os.environ.get("DB_URL", "mariadb+mariadbconnector://user:password@localhost/kmv")

# Connect to MySQL server (without specifying database)
db_user = os.environ.get("DB_USERNAME")
db_pass = os.environ.get("DB_PASSWORD")
db_host = os.environ.get("DB_HOST")
db_port = os.environ.get("DB_PORT")
db_name = os.environ.get("DB_DATABASE")
db_url = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

# SQLAlchemy setup
Base = declarative_base()

class Search(Base):
    __tablename__ = 'searches'
    id = Column(Integer, primary_key=True)
    team = Column(String(255))
    text = Column(String(255))
    cell_phone = Column(String(255))
    final_date = Column(DateTime)

engine = create_engine(db_url)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)
   
def get_searches_db():
    session = SessionLocal()
    searches = []
    try:
        results = session.query(Search).all()
        for s in results:
            if s.final_date < datetime.now():
                session.delete(s)
                continue
            else:
                searches.append([s.id, s.team, s.text, s.cell_phone])
    except Exception as e:
        logging.error(f"Error reading DB: {str(e)}")
    finally:
        session.close()
    return searches

def main():
    
    whatsapp_restart_session(
        base_url=WHATSAPP_BASE_URL,
        api_key=WHATSAPP_API_KEY,
        session=WHATSAPP_SESSION,
    )
    
    time.sleep(10)  # Wait for WhatsApp session to stabilize
    
    while 1 == 1:
        
        searches = get_searches_db()
        
        if not searches:
            logging.info("No searches found. Waiting for new searches.")
            time.sleep(60)
            continue

        # Initialize the SeleniumBase Driver
        driver = Driver(
            headless=True,
            uc_cdp=True,  # Undetected ChromeDriver mode
            incognito=False,  # Some sites don't work well in incognito
            agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        for search in searches:
            
            search_id = search[0]
            search_team = search[1]
            search_text = search[2]
            cell_phone = [search[3]]

            teams_xpath = f'/html/body/app-root/div/div/app-home-container/app-view-home/div/div[2]/div/app-home-welcome/section/div/app-home-welcome-clubs'

            try:

                # Navigate to target page after successful login
                driver.get(TARGET_URL)       

                logging.info(f"Starting page refresh every {REFRESH_INTERVAL} seconds")
                logging.info(f"Target URL: {TARGET_URL}")
                logging.info("Press Ctrl+C to stop the script")
                
                try:
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
                        continue
                    
                    driver.wait_for_element('.home-products', timeout=10)
                    team_matches = driver.find_elements(".match-item.ng-star-inserted")
                    found = False
                    for team_match in team_matches:
                        if search_text in team_match.text:
                            logging.info(f"Match found: {team_match.text}")
                            found = True
                            send_fail = whatsapp_send_message(
                                base_url=WHATSAPP_BASE_URL,
                                api_key=WHATSAPP_API_KEY,
                                session=WHATSAPP_SESSION,
                                contacts=cell_phone,
                                content=team_match.screenshot_as_base64,
                                content_type="MessageMedia",
                            )
                            time.sleep(5)  # Wait a bit after sending message
                            #team_match.screenshot('team_match.png')
                            break
                        
                    if found:
                        wa_ok = True
                        for cell_fail in send_fail:
                            logging.error(f"Failed to send message to {cell_fail}")
                            wa_ok = False
                        if wa_ok:
                            logging.info("Message sent successfully to all contacts")
                            session = SessionLocal()
                            try:
                                search_to_delete = session.query(Search).filter(Search.id == search_id).first()
                                if search_to_delete:
                                    session.delete(search_to_delete)
                                    session.commit()
                                    logging.info(f"Search ID {search_id} deleted from database")
                            except Exception as e:
                                logging.error(f"Error deleting search ID {search_id}: {str(e)}")                                          
                            
                            session.close()
                            
                except Exception as e:
                    logging.error(f"Error: {str(e)}")
                    driver.refresh()

            except KeyboardInterrupt:
                logging.info("\nScript stopped by user")

            except Exception as e:
                logging.error(f"Fatal error: {str(e)}")                
                
        driver.quit()
        logging.info("Browser closed successfully")

        # Wait for the next refresh
        time.sleep(REFRESH_INTERVAL)
        # Refresh the page

        logging.info("Page refreshed successfully")
            

if __name__ == "__main__":
    main()