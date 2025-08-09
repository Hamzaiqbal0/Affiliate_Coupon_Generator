import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    WebDriverException
)

# Constants
TARGET_URL = "https://www.imbodhi.co/AIDEN90764?fbclid=IwZXh0bgNhZW0CMTAAYnJpZBExMTI5bGVXRnBMRk9TMU1CZAEeas2QWfK00XymuCbybtfuPGwHs3OzQb3rK8AAYOh1saYwlVNiuMrrnBIUHqQ_aem_O8RdWrFjEjJnCuZZZF24Cw"
OUTPUT_FILE = "coupons.txt"

# Utility: Save coupon to file
def save_coupon(code):
    """Appends a coupon code to the output file."""
    try:
        with open(OUTPUT_FILE, "a") as f:
            f.write(code + "\n")
        print(f"✅ Coupon saved: {code}")
    except IOError as e:
        print(f"❌ Error saving coupon to file: {e}")

# Utility: Set up the driver
def setup_driver():
    """Initializes and returns a Chrome WebDriver instance."""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--window-size=1920,1080")
    
    chrome_options.page_load_strategy = 'eager' 

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("🌐 Chrome driver initialized successfully.")
        return driver
    except WebDriverException as e:
        print(f"❌ Failed to set up Chrome driver: {e}")
        print("Please ensure Chrome is installed and chromedriver is compatible with your Chrome version.")
        return None

# Utility: Attempt to close a popup
def attempt_close_popup(driver, wait):
    """Attempts to close the specific popup based on provided HTML."""
    print("Trying to close popup...")
    close_button_xpath = "//div[@id='__ss-modal-content']//button[./*[name()='svg']/*[name()='polygon']]"
    
    try:
        close_button = WebDriverWait(driver, 7).until(EC.element_to_be_clickable((By.XPATH, close_button_xpath))) # Reduced timeout to 7s
        driver.execute_script("arguments[0].click();", close_button)
        print("✅ Popup closed via custom SVG button XPath.")
        return True
    except TimeoutException:
        print("⚠️ No specific popup close button found within 7s timeout.")
        return False
    except ElementClickInterceptedException:
        print("❌ Popup close button was intercepted. Trying JavaScript click.")
        try:
            driver.execute_script("arguments[0].click();", close_button)
            print("✅ Popup closed via JavaScript click after interception.")
            return True
        except Exception as js_e:
            print(f"❌ Failed to close popup with JavaScript click: {js_e}")
            return False
    except Exception as e:
        print(f"❌ An error occurred while trying to close popup: {e}")
        return False

# Main scraping session
def run_session(session_id):
    """Runs a single scraping session to retrieve one coupon."""
    print(f"\n--- 🔁 Session {session_id}: Starting... ---")
    driver = setup_driver()
    if driver is None:
        print(f"❌ Session {session_id} failed to start due to driver setup error. Aborting session.")
        return

    driver.set_page_load_timeout(90) 
    wait = WebDriverWait(driver, 30) # General wait time for elements

    try:
        print(f"🌐 Session {session_id}: Navigating to URL: {TARGET_URL}")
        driver.get(TARGET_URL) 
        print(f"✅ Session {session_id}: Page loaded (or eager load completed).")

        popup_present_and_visible = False
        try:
            # Check if the popup container is present and visible
            WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, '__ss-modal-content'))) # Shorter wait for initial popup check
            popup_present_and_visible = True
            print(f"✅ Session {session_id}: Popup container is visible.")
        except TimeoutException:
            print(f"ℹ️ Session {session_id}: Popup container not visible within expected time. Proceeding without explicit popup close attempt.")
        
        if popup_present_and_visible:
            popup_handled = attempt_close_popup(driver, wait) # Use main 'wait' for closing, or specific shorter one
            if popup_handled:
                print(f"✅ Session {session_id}: Popup successfully handled.")
                try:
                    # Wait for popup disappearance (give it a bit more time if it's slow to vanish)
                    WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.ID, '__ss-modal-content')))
                    print(f"✅ Session {session_id}: Popup container is no longer visible.")
                except TimeoutException:
                    print(f"⚠️ Session {session_id}: Popup container still visible after attempting to close. May block next action.")
            else:
                print(f"ℹ️ Session {session_id}: Popup was present but could not be closed. May block next action.")
        
        # Small buffer just in case of animations or rendering delays not covered by explicit waits
        time.sleep(1) # Increased from 0.5s slightly for settling if popup was there

        # --- Checkmate 2: Wait for and click the "Redeem Offer" button ---
        print(f"🎁 Session {session_id}: Waiting for 'Redeem Offer' button...")
        redeem_button = None
        
        # Strategy: First try to find Redeem Offer button *inside* the modal, if modal was present
        if popup_present_and_visible:
            redeem_button_xpath_modal = "//div[@id='__ss-modal-content']//button[contains(text(), 'Redeem Offer')]"
            try:
                # Use a shorter wait if it's expected immediately within the modal
                redeem_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, redeem_button_xpath_modal)))
                print(f"✅ Session {session_id}: Found 'Redeem Offer' button inside popup.")
            except TimeoutException:
                print(f"⚠️ Session {session_id}: 'Redeem Offer' button not found inside popup. Trying main page.")
        
        # If not found in modal, or modal wasn't present, try a general Redeem Offer button
        if redeem_button is None:
            redeem_button_xpath_general = "//button[contains(text(), 'Redeem Offer')]" # More general XPath
            try:
                redeem_button = wait.until(EC.element_to_be_clickable((By.XPATH, redeem_button_xpath_general)))
                print(f"✅ Session {session_id}: Found 'Redeem Offer' button on main page.")
            except TimeoutException:
                print(f"❌ Session {session_id}: 'Redeem Offer' button not found or not clickable on main page within timeout ({wait._timeout}s).") # Fixed AttributeError here
                raise 
        
        # Now click the button if found
        if redeem_button:
            try:
                driver.execute_script("arguments[0].click();", redeem_button)
                print(f"✅ Session {session_id}: Clicked 'Redeem Offer'.")
            except ElementClickInterceptedException:
                print(f"❌ Session {session_id}: 'Redeem Offer' button was intercepted. Trying JavaScript click.")
                try:
                    driver.execute_script("arguments[0].click();", redeem_button)
                    print(f"✅ Session {session_id}: Clicked 'Redeem Offer' via JavaScript after interception.")
                except Exception as js_e:
                    print(f"❌ Session {session_id}: Failed to click 'Redeem Offer' with JavaScript click: {js_e}")
                    raise 
            except Exception as e:
                print(f"❌ Session {session_id}: An error occurred while trying to click 'Redeem Offer': {e}")
                raise
        else: # Should be caught by TimeoutException if redeem_button is None and no raise
            print(f"❌ Session {session_id}: 'Redeem Offer' button not found by any strategy.")
            raise NoSuchElementException("Redeem Offer button not found.")


        # --- Checkmate 3: Extract the coupon code ---
        print(f"⏳ Session {session_id}: Waiting for coupon code to appear...")
        coupon_div_xpath = "//div[./img[contains(@src, 'copy-blue-icon.png')]]"
        
        try:
            coupon_element = wait.until(EC.visibility_of_element_located((By.XPATH, coupon_div_xpath)))
            coupon_code = coupon_element.text.strip()
            
            if coupon_code:
                coupon_code_parts = coupon_code.split(' ')[0] 
                if len(coupon_code_parts) > 5 and all(c.isalnum() or c == '-' for c in coupon_code_parts): 
                    print(f"🎉 Session {session_id}: Coupon Found: {coupon_code_parts}")
                    save_coupon(coupon_code_parts)
                else:
                    print(f"⚠️ Session {session_id}: Extracted text '{coupon_code}' but it does not look like a valid coupon code pattern.")
                    raise ValueError("Extracted text did not seem to be a valid coupon.")
            else:
                print(f"⚠️ Session {session_id}: Found coupon element, but it contained no text.")
                raise ValueError("Coupon element found but was empty.")
        except TimeoutException:
            print(f"❌ Session {session_id}: Coupon code element did not appear or was not visible within timeout ({wait._timeout}s).") # Fixed AttributeError here
            raise 
        except NoSuchElementException:
            print(f"❌ Session {session_id}: Coupon code element not found on the page after clicking 'Redeem Offer'.")
            raise 
        except Exception as e:
            print(f"❌ Session {session_id}: An error occurred while trying to extract coupon code: {e}")
            raise

    except TimeoutException as e:
        print(f"❌ Session {session_id}: Timeout error - A key element or page load took too long. Detail: {e}")
    except NoSuchElementException as e:
        print(f"❌ Session {session_id}: Element not found error - An expected element was not found. Detail: {e}")
    except ElementClickInterceptedException as e:
        print(f"❌ Session {session_id}: Click Intercepted Error - An element couldn't be clicked because another element was on top of it. Detail: {e}")
    except ValueError as e:
        print(f"❌ Session {session_id}: Data extraction issue. Detail: {e}")
    except WebDriverException as e:
        print(f"❌ Session {session_id}: WebDriver Error - {e}")
    except Exception as e:
        print(f"❌ Session {session_id}: An unexpected general error occurred: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if driver:
            driver.quit()
            print(f"--- 🔴 Session {session_id}: Closed browser. ---")
        else:
            print(f"--- 🔴 Session {session_id}: Ended (driver was not initialized). ---")

if __name__ == "__main__":
    NUM_SESSIONS = 50
    for i in range(NUM_SESSIONS):
        run_session(i + 1)
        if i < NUM_SESSIONS - 1:
            time.sleep(2)