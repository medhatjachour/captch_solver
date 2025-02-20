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

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Directory to save CAPTCHA images
CAPTCHA_IMAGE_DIR = "captcha_images"
os.makedirs(CAPTCHA_IMAGE_DIR, exist_ok=True)

class CaptchaSolver:
    def __init__(self, driver):
        self.driver = driver

    def solve_slider_captcha(self):
        """
        Solve the slider CAPTCHA by dragging the slider div to the correct position.
        """
        try:
            logging.info("Waiting for CAPTCHA canvas to load...")
            canvas = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//canvas[@width='316']"))
            )
            logging.info("CAPTCHA canvas found.")

            # Extract the CAPTCHA background image
            canvas_base64 = self.driver.execute_script(
                "return arguments[0].toDataURL('image/png').substring(21);", canvas
            )
            canvas_png = base64.b64decode(canvas_base64)
            captcha_image_path = os.path.join(CAPTCHA_IMAGE_DIR, f"captcha_{int(time.time())}.png")
            with open(captcha_image_path, "wb") as f:
                f.write(canvas_png)
            logging.info(f"CAPTCHA background image saved to {captcha_image_path}")

            # Wait for the puzzle piece element to be visible
            logging.info("Waiting for puzzle piece to load...")
            puzzle_piece_element = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//canvas[@width='64']"))
            )
            logging.info("Puzzle piece found.")

            # Extract the puzzle piece image
            puzzle_base64 = self.driver.execute_script(
                "return arguments[0].toDataURL('image/png').substring(21);", puzzle_piece_element
            )
            puzzle_png = base64.b64decode(puzzle_base64)
            puzzle_piece_path = os.path.join(CAPTCHA_IMAGE_DIR, f"puzzle_{int(time.time())}.png")
            with open(puzzle_piece_path, "wb") as f:
                f.write(puzzle_png)
            logging.info(f"Puzzle piece image saved to {puzzle_piece_path}")

            # Solve the CAPTCHA using template matching
            background = cv2.imread(captcha_image_path, cv2.IMREAD_GRAYSCALE)
            puzzle_piece = cv2.imread(puzzle_piece_path, cv2.IMREAD_GRAYSCALE)

            result = cv2.matchTemplate(background, puzzle_piece, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            # Calculate the offset to move the slider
            offset_x = max_loc[0] - 50  # Adjust based on the initial position of the puzzle piece
            logging.info(f"Moving slider by {offset_x} pixels.")

            # Locate the slider div
            logging.info("Locating the slider div...")
            slider_div = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@style, 'position: absolute; left: 8px;')]"))
            )
            logging.info("Slider div found.")

            # Log the initial position of the slider
            slider_location = slider_div.location
            logging.info(f"Slider initial position: {slider_location}")

            # Simulate dragging the slider div
            actions = ActionChains(self.driver)
            actions.click_and_hold(slider_div).perform()
            time.sleep(0.5)  # Add a small delay to mimic human interaction
            actions.move_by_offset(offset_x, 0).perform()
            time.sleep(0.5)  # Add a small delay to mimic human interaction
            actions.release().perform()
            logging.info("Slider moved.")

            # Log the final position of the slider
            slider_final_location = slider_div.location
            logging.info(f"Slider final position: {slider_final_location}")

            time.sleep(2)

        except Exception as e:
            logging.error(f"Error solving slider CAPTCHA: {e}")

    def solve_icon_captcha(self):
        """
        Solve the icon selection CAPTCHA by selecting icons in the correct order.
        """
        try:
            logging.info("Waiting for icon selection CAPTCHA to load...")
            icon_image = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//canvas[@width='64']"))
            )
            logging.info("Icon selection CAPTCHA found.")

            # Extract the image data from the canvas
            icon_image_base64 = self.driver.execute_script(
                "return arguments[0].toDataURL('image/png').substring(21);", icon_image
            )
            icon_image_png = base64.b64decode(icon_image_base64)
            icon_image_path = os.path.join(CAPTCHA_IMAGE_DIR, f"icon_{int(time.time())}.png")
            with open(icon_image_path, "wb") as f:
                f.write(icon_image_png)
            logging.info(f"Icon selection image saved to {icon_image_path}")

            # Detect icons in the image
            icon_positions = self.detect_icons(icon_image_path)
            logging.info(f"Detected icons: {icon_positions}")

            # Click the icons in the correct order
            for icon_name in ["star", "cart", "calendar"]:  # Replace with the correct order
                if icon_name in icon_positions:
                    x, y = icon_positions[icon_name]
                    icon_element = self.driver.find_element(By.XPATH, f"//div[@data-icon='{icon_name}']")
                    actions = ActionChains(self.driver)
                    actions.move_to_element(icon_element).click().perform()
                    logging.info(f"Clicked {icon_name} icon.")
                    time.sleep(1)

        except Exception as e:
            logging.error(f"Error solving icon selection CAPTCHA: {e}")

    def detect_icons(self, image_path):
        """
        Detect icons in the image and return their positions.
        """
        image = cv2.imread(image_path)
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Define color ranges for each icon
        color_ranges = {
            "star": {"lower": np.array([20, 100, 100]), "upper": np.array([30, 255, 255])},  # Adjust HSV values
            "cart": {"lower": np.array([0, 100, 100]), "upper": np.array([10, 255, 255])},   # Adjust HSV values
            "calendar": {"lower": np.array([100, 100, 100]), "upper": np.array([130, 255, 255])},  # Adjust HSV values
        }

        icon_positions = {}
        for icon_name, color_range in color_ranges.items():
            mask = cv2.inRange(hsv_image, color_range["lower"], color_range["upper"])
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w > 10 and h > 10:  # Filter out small noise
                    icon_positions[icon_name] = (x + w // 2, y + h // 2)

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