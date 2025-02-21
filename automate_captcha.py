import logging
import requests
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
import re

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
            logging.info("CAPTCHA is not solved.")
            time.sleep(2)  # Wait for the CAPTCHA to update
            return False
        except:
            logging.info("CAPTCHA is solved.")
            return True

    def solve_icon_captcha(self, max_retries=5):
        """
        Solve the icon selection CAPTCHA by selecting icons in the correct order.
        """
        for attempt in range(max_retries):
            logging.info(f"icon Attempt {attempt + 1}/{max_retries}")
            try:
                logging.info("Waiting for icon selection CAPTCHA to load...")
                icon_div = WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@style, 'background-image:')]"))
                )
                logging.info("Icon selection CAPTCHA found.")

                # Extract the CAPTCHA image URL
                style = icon_div.get_attribute("style")
                image_url = self.extract_background_image_url(style)
                if not image_url:
                    logging.error("Failed to extract CAPTCHA image URL.")
                    continue

                # Download the CAPTCHA image
                captcha_image_path = self.download_captcha_image(image_url)
                if not captcha_image_path:
                    logging.error("Failed to download CAPTCHA image.")
                    continue

                # Detect icons in the image
                icon_order = self.get_icon_order()  # Define the expected order of icons
                icon_positions = self.detect_icons(captcha_image_path, icon_order)
                logging.info(f"Detected icons: {icon_positions}")

                # Click the icons in the correct order
                for icon_position in icon_order:
                    if icon_position in icon_positions:
                        x, y = icon_positions[icon_position]
                        # Move to the icon position and click
                        actions = ActionChains(self.driver)
                        actions.move_to_element_with_offset(icon_div, x, y).click().perform()
                        logging.info(f"Clicked icon with position: {icon_position}")
                        time.sleep(2)

                # Check if the CAPTCHA is solved
                if self.is_captcha_solved():
                    return True

            except Exception as e:
                logging.error(f"Error solving icon selection CAPTCHA: {e}")
        
        return False
        
        
    def detect_icons(self, image_path, icon_order):
        """
        Detect icons in the image using combined template matching and color-based detection.
        """
        # Load the CAPTCHA image
        captcha_image = cv2.imread(image_path)
        if captcha_image is None:
            logging.error("Failed to load CAPTCHA image.")
            return {}

        # Preprocess the CAPTCHA image
        captcha_gray = self.preprocess_image(captcha_image)

        # Define icon templates (replace with your actual paths)
        icon_templates = {
            "star": 'templates/1.png',  # Star
            "calendar": 'templates/2.png',  # Calendar
            "cart": 'templates/3.png',  # Cart
        }

        icon_positions = {}

        # Process each icon using template matching
        for icon_name, template_path in icon_templates.items():
            # Load the template image
            icon = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            if icon is None:
                logging.error(f"Failed to load template image: {template_path}")
                continue

            # Preprocess the template image
            icon = self.preprocess_image(icon)

            # Perform multi-scale template matching
            scales = [0.8, 0.9, 1.0, 1.1, 1.2]
            best_score = 0.8  # Increased threshold for better accuracy
            best_position = (0, 0)

            for scale in scales:
                scaled_icon = cv2.resize(icon, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
                if scaled_icon.shape[0] > captcha_gray.shape[0] or scaled_icon.shape[1] > captcha_gray.shape[1]:
                    continue

                result = cv2.matchTemplate(captcha_gray, scaled_icon, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)

                if max_val > best_score:
                    best_score = max_val
                    best_position = max_loc

            logging.info(f"Icon: {icon_name}, Best Score: {best_score}, Best Position: {best_position}")

            if best_score >= 0.8:  # Only accept matches with high confidence
                icon_positions[icon_name] = best_position

        # If template matching fails, use color-based detection as a fallback
        if not icon_positions:
            logging.info("Falling back to color-based detection.")
            icon_positions = self.detect_icons_by_color(captcha_image)

        return icon_positions

    def detect_icons_by_color(self, image):
        """
        Detect icons using color-based detection.
        """
        icon_positions = {}
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Define color ranges for each icon
        color_ranges = {
            "star": {"lower": np.array([90, 200, 200]), "upper": np.array([100, 255, 255])},  # Cyan
            "cart": {"lower": np.array([85, 200, 200]), "upper": np.array([90, 255, 255])},  # Green
            "calendar": {"lower": np.array([120, 150, 200]), "upper": np.array([130, 255, 255])},  # Blue
        }

        for icon_name, color_range in color_ranges.items():
            mask = cv2.inRange(hsv_image, color_range["lower"], color_range["upper"])
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            positions = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w > 10 and h > 10:  # Filter out small noise
                    center_x, center_y = x + w // 2, y + h // 2
                    positions.append((center_x, center_y))

            if positions:
                # Take the first detected position (you can modify this logic if needed)
                icon_positions[icon_name] = positions[0]

        return icon_positions
    def preprocess_image(self, image):
        """
        Preprocess the image for better icon detection.
        """
        if len(image.shape) > 2:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Denoise the image
        image = cv2.fastNlMeansDenoising(image)

        # Enhance contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        image = clahe.apply(image)

        return image

    def get_icon_order(self):
        """
        Define the expected order of icons.
        """
        return ["star", "calendar", "cart"]

    def extract_background_image_url(self, style):
        """
        Extract the background image URL from the style attribute.
        """
        match = re.search(r"background-image:\s*url\(['\"]?(.*?)['\"]?\)", style)
        if match:
            return match.group(1)
        return None

    def download_captcha_image(self, image_url):
        """
        Download the CAPTCHA image and save it to a file.
        """
        try:
            response = requests.get(image_url)
            if response.status_code == 200:
                captcha_image_path = os.path.join(CAPTCHA_IMAGE_DIR, f"captcha_{int(time.time())}.png")
                with open(captcha_image_path, "wb") as f:
                    f.write(response.content)
                logging.info(f"CAPTCHA image saved to {captcha_image_path}")
                return captcha_image_path
        except Exception as e:
            logging.error(f"Failed to download CAPTCHA image: {e}")
        return None

# Other methods (solve_captcha_and_submit) remain unchanged

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
        # try:
        #     submit_button = WebDriverWait(driver, 10).until(
        #         EC.presence_of_element_located((By.XPATH, "//button[@type='submit']"))
        #     )
        #     logging.info("Submit button found.")
        #     submit_button.click()
        #     logging.info("Form submitted.")
        # except Exception as e:
        #     logging.error(f"Error submitting the form: {e}")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        logging.info("Closing the browser...")
        time.sleep(10)
        driver.quit()