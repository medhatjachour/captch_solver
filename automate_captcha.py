import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import base64
import os
import cv2
import numpy as np
from PIL import Image
import random

from detect_puzzle import GeeTestIdentifier

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Directory to save CAPTCHA images
CAPTCHA_IMAGE_DIR = "captcha_images"
os.makedirs(CAPTCHA_IMAGE_DIR, exist_ok=True)

class CaptchaSolver:
    def __init__(self, driver):
        self.driver = driver

    def solve_slider_captcha(self, max_retries=5):
        for attempt in range(max_retries):
            try:
                logging.info(f"Attempt {attempt + 1}/{max_retries}")

                # Get elements
                canvas = WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//canvas[@width='316']"))
                )
                puzzle_piece_element = WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//canvas[@width='64']"))
                )
                slider_div = WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@style, 'position: absolute; left: 8px;')]"))
                )

                # Get scale ratio
                scale_ratio = self.get_canvas_scale(canvas)
                
                # Process images
                bg_img = self.get_canvas_image(canvas)
                puzzle_img = self.get_canvas_image(puzzle_piece_element)
                
                identifier = GeeTestIdentifier(bg_img, puzzle_img)
                result = identifier.find_puzzle_piece_position()
                
                # Apply scaling to coordinates
                target_x = result['coordinates'][0] * scale_ratio
                initial_x = 0
                
                logging.info(f"Scaled Target X: {target_x} | Initial X: {initial_x}")

                # Calculate movement
                move_offset = target_x - initial_x - 25
                if move_offset < 0:
                    logging.warning("Negative movement detected! Using absolute value")
                    move_offset = abs(move_offset)
                    
                logging.info(f"Moving RIGHT by {move_offset}px")
                
                # Human-like drag
                self.drag_slider(slider_div, move_offset)

                if self.is_captcha_solved():
                    return True

            except Exception as e:
                logging.error(f"Attempt failed: {str(e)}")
        
        return False

    def get_canvas_scale(self, canvas_element):
        """Calculate scale ratio between actual size and rendered size"""
        dom_width = int(canvas_element.get_attribute('width'))
        rendered_width = canvas_element.size['width']
        return rendered_width / dom_width

    def get_canvas_image(self, element):
        """Extract canvas image as OpenCV format"""
        canvas_base64 = self.driver.execute_script(
            "return arguments[0].toDataURL('image/png').substring(21);", element
        )
        return base64.b64decode(canvas_base64)

    def drag_slider(self, slider, distance):
        """Human-like slider movement"""
        action = ActionChains(self.driver)
        action.click_and_hold(slider).perform()
        
        # Split movement into 10 steps with random variations
        steps = 10
        base_step = distance / steps
        for _ in range(steps):
            variance = random.uniform(-2, 2)
            action.move_by_offset(base_step + variance, random.uniform(-1, 1))
            action.pause(random.uniform(0.05, 0.2))
        
        action.release().perform()
        action.pause(0.5)



    def is_captcha_solved(self):
        """
        Check if the CAPTCHA is solved by looking for a success message or the absence of the CAPTCHA.
        """
        try:
            time.sleep(5)  # Wait for the CAPTCHA to update
            # Example: Check if the CAPTCHA canvas is no longer present
            WebDriverWait(self.driver, 5).until(
               
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@style, 'position: absolute; left: 8px;')]"))
            )
            logging.info("CAPTCHA is solved.")
            time.sleep(2)  # Wait for the CAPTCHA to update
            return False
        except:
            logging.info("CAPTCHA is not solved.")
            return True
    def solve_icon_captcha(self):
        """
        Solve the icon selection CAPTCHA by selecting icons in the correct order.
        """
        try:
            logging.info("Waiting for icon selection CAPTCHA to load...")
            icon_div = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@style, 'display: flex;')]"))
            )
            logging.info("Icon selection CAPTCHA found.")

            # Extract the icon order from the div
            icon_order = []
            icon_elements = icon_div.find_elements(By.XPATH, ".//div")
            for icon_element in icon_elements:
                style = icon_element.get_attribute("style")
                if "background:" in style:
                    # Extract the background position (e.g., "-2px -91px")
                    background_position = style.split("background:")[1].split("no-repeat")[0].strip()
                    icon_order.append(background_position)
            logging.info(f"Icon order: {icon_order}")

            # Extract the CAPTCHA image
            logging.info("Extracting CAPTCHA image...")
            canvas = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//canvas[@width='316']"))
            )
            canvas_base64 = self.driver.execute_script(
                "return arguments[0].toDataURL('image/png').substring(21);", canvas
            )
            canvas_png = base64.b64decode(canvas_base64)
            captcha_image_path = os.path.join(CAPTCHA_IMAGE_DIR, f"icon_captcha_{int(time.time())}.png")
            with open(captcha_image_path, "wb") as f:
                f.write(canvas_png)
            logging.info(f"CAPTCHA image saved to {captcha_image_path}")

            # Detect icons in the image
            icon_positions = self.detect_icons(captcha_image_path, icon_order)
            logging.info(f"Detected icons: {icon_positions}")

            # Click the icons in the correct order
            for icon_name in icon_order:
                if icon_name in icon_positions:
                    x, y = icon_positions[icon_name]
                    icon_element = self.driver.find_element(By.XPATH, f"//div[contains(@style, '{icon_name}')]")
                    actions = ActionChains(self.driver)
                    actions.move_to_element(icon_element).click().perform()
                    logging.info(f"Clicked icon with position: {icon_name}")
                    time.sleep(1)

        except Exception as e:
            logging.error(f"Error solving icon selection CAPTCHA: {e}")

    def detect_icons(self, image_path, icon_order):
        """
        Detect icons in the image and return their positions.
        """
        image = cv2.imread(image_path)
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Define color ranges for each icon based on the background position
        icon_positions = {}
        for icon_position in icon_order:
            # Extract the y-coordinate from the background position (e.g., "-2px -91px" -> 91)
            y_offset = int(icon_position.split(" ")[1].replace("px", ""))
            
            # Define a color range based on the y-offset
            lower_bound = np.array([0, 0, y_offset - 10])
            upper_bound = np.array([255, 255, y_offset + 10])

            # Create a mask to detect the icon
            mask = cv2.inRange(hsv_image, lower_bound, upper_bound)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w > 10 and h > 10:  # Filter out small noise
                    icon_positions[icon_position] = (x + w // 2, y + h // 2)

        return icon_positions

def solve_captcha_and_submit(website_url, username, email, password):
    driver = webdriver.Chrome()
    try:
        logging.info("Opening website...")
        driver.get(website_url)

        # Fill the form
        logging.info("Filling the form...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter your user name']"))
        )
        driver.find_element(By.XPATH, "//input[@placeholder='Enter your user name']").send_keys(username)
        driver.find_element(By.XPATH, "//button[text()='Сontinue']").click()
        time.sleep(2)

        driver.find_element(By.XPATH, "//input[@placeholder='Enter your email here']").send_keys(email)
        driver.find_element(By.XPATH, "//button[text()='Сontinue']").click()
        time.sleep(2)

        driver.find_element(By.XPATH, "//input[@placeholder='Enter password here']").send_keys(password)
        driver.find_element(By.XPATH, "//input[@placeholder='Repeat password']").send_keys(password)
        driver.find_element(By.XPATH, "//button[text()='Сontinue']").click()
        time.sleep(2)
        driver.find_element(By.XPATH, "//div[span[text()=\"I'm not a robot\"]]").click()

        time.sleep(10)



        # Solve the slider CAPTCHA
        solver = CaptchaSolver(driver)
        solver.solve_slider_captcha()

        # Solve the icon selection CAPTCHA
        solver.solve_icon_captcha()

        # Submit the form
        logging.info("Submitting the form...")
        try:
            submit_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//button[@type='submit']"))
            )
            logging.info("Submit button found.")
            submit_button.click()
            logging.info("Form submitted.")
        except Exception as e:
            logging.error(f"Error submitting the form: {e}")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        logging.info("Closing the browser...")
        time.sleep(10)
        driver.quit()