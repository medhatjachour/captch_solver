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

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Directory to save CAPTCHA images
CAPTCHA_IMAGE_DIR = "captcha_images"
os.makedirs(CAPTCHA_IMAGE_DIR, exist_ok=True)

class CaptchaSolver:
    def __init__(self, driver):
        self.driver = driver

    def solve_slider_captcha(self, max_retries=5):
        """
        Solve the slider CAPTCHA by dragging the slider div to the correct position.
        Retry up to `max_retries` times if the CAPTCHA is not solved.
        """
        for attempt in range(max_retries):
            try:
                logging.info(f"Attempt {attempt + 1} to solve the slider CAPTCHA...")

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
                buffer = random.randint(5, 15)  # Add a random buffer to fine-tune the offset
                offset_x += buffer  # Fine-tune the offset
                logging.info(f"Moving slider by {offset_x} pixels (including buffer).")

                # Locate the slider div
                logging.info("Locating the slider div...")
                slider_div = WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@style, 'position: absolute; left: 8px;')]"))
                )
                logging.info("Slider div found.")

                # Log the initial position of the slider
                slider_location = slider_div.location
                logging.info(f"Slider initial position: {slider_location}")

                # Simulate human-like dragging of the slider div
                actions = ActionChains(self.driver)
                actions.click_and_hold(slider_div).perform()
                time.sleep(random.uniform(0.2, 0.5))  # Add a small random delay to mimic human interaction

                # Move the slider in small steps with slight variations
                steps = 10
                step_size = offset_x / steps
                for _ in range(steps):
                    actions.move_by_offset(step_size + random.uniform(-2, 2), random.uniform(-1, 1)).perform()
                    time.sleep(random.uniform(0.1, 0.3))  # Add a small random delay between steps

                actions.release().perform()
                logging.info("Slider moved.")

                # Log the final position of the slider
                slider_final_location = slider_div.location
                logging.info(f"Slider final position: {slider_final_location}")

                # Check if the CAPTCHA is solved
                time.sleep(2)  # Wait for the CAPTCHA to update
                if self.is_captcha_solved():
                    logging.info("Slider CAPTCHA solved successfully!")
                    return True
                else:
                    logging.warning("Slider CAPTCHA not solved. Retrying...")

            except Exception as e:
                logging.error(f"Error solving slider CAPTCHA: {e}")

        logging.error(f"Failed to solve the slider CAPTCHA after {max_retries} attempts.")
        return False





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