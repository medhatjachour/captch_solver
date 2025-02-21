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
                canvas = WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//canvas[@width='316']"))
                )
                puzzle_piece_element = WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//canvas[@width='64']"))
                )
                slider_div = WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@style, 'position: absolute; left: 8px;')]"))
                )

                scale_ratio = self.get_canvas_scale(canvas)
                bg_img = self.get_canvas_image(canvas)
                puzzle_img = self.get_canvas_image(puzzle_piece_element)
                
                identifier = GeeTestIdentifier(bg_img, puzzle_img)
                result = identifier.find_puzzle_piece_position()
                
                target_x = result['coordinates'][0] * scale_ratio
                initial_x = 0
                logging.info(f"Scaled Target X: {target_x} | Initial X: {initial_x}")

                move_offset = target_x - initial_x - 25
                if move_offset < 0:
                    logging.warning("Negative movement detected! Using absolute value")
                    move_offset = abs(move_offset)
                logging.info(f"Moving RIGHT by {move_offset}px")
                
                self.drag_slider(slider_div, move_offset)

                if self.is_captcha_solved():
                    return True

            except Exception as e:
                logging.error(f"Attempt failed: {str(e)}")
        return False

    def get_canvas_scale(self, canvas_element):
        dom_width = int(canvas_element.get_attribute('width'))
        rendered_width = canvas_element.size['width']
        return rendered_width / dom_width

    def get_canvas_image(self, element):
        canvas_base64 = self.driver.execute_script(
            "return arguments[0].toDataURL('image/png').substring(21);", element
        )
        return base64.b64decode(canvas_base64)

    def drag_slider(self, slider, distance):
        action = ActionChains(self.driver)
        action.click_and_hold(slider).perform()
        steps = 10
        base_step = distance / steps
        for _ in range(steps):
            variance = random.uniform(-2, 2)
            action.move_by_offset(base_step + variance, random.uniform(-1, 1))
            action.pause(random.uniform(0.05, 0.2))
        action.release().perform()
        action.pause(0.5)

    def is_captcha_solved(self):
        try:
            time.sleep(5)
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@style, 'position: absolute; left: 8px;')]"))
            )
            logging.info("CAPTCHA is not solved.")
            time.sleep(2)
            return False
        except:
            logging.info("CAPTCHA is solved.")
            return True

    def solve_icon_captcha(self, max_retries=5):
        for attempt in range(max_retries):
            logging.info(f"Icon Attempt {attempt + 1}/{max_retries}")
            try:
                icon_div = WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@style, 'background-image:')]"))
                )
                logging.info("Icon selection CAPTCHA found.")

                div_location = icon_div.location
                div_size = icon_div.size
                logging.info(f"Icon div location: {div_location}, size: {div_size}")

                style = icon_div.get_attribute("style")
                image_url = self.extract_background_image_url(style)
                if not image_url:
                    logging.error("Failed to extract CAPTCHA image URL.")
                    continue

                captcha_image_path = self.download_captcha_image(image_url)
                if not captcha_image_path:
                    logging.error("Failed to download CAPTCHA image.")
                    continue

                captcha_image = cv2.imread(captcha_image_path)
                if captcha_image is None:
                    logging.error("Failed to load CAPTCHA image for scaling.")
                    continue
                image_height, image_width = captcha_image.shape[:2]
                logging.info(f"CAPTCHA image dimensions: {image_width}x{image_height}")

                scale_x = div_size['width'] / image_width
                scale_y = div_size['height'] / image_height
                logging.info(f"Scale ratios - X: {scale_x}, Y: {scale_y}")

                icon_order = self.get_icon_order()
                icon_positions = self.detect_icons(captcha_image_path, icon_order)
                logging.info(f"Detected icon positions: {icon_positions}")

                if not icon_positions or all(pos == (0, 0) for pos in icon_positions.values()):
                    logging.warning("No valid icon positions detected, skipping click.")
                    continue

                center_x = div_size['width'] // 2
                center_y = div_size['height'] // 2

                for icon_name in icon_order:
                    if icon_name in icon_positions:
                        x, y = icon_positions[icon_name]
                        scaled_x = int(x * scale_x)
                        scaled_y = int(y * scale_y)
                        offset_x = scaled_x - center_x
                        offset_y = scaled_y - center_y
                        offset_x = max(-center_x, min(offset_x, center_x - 1))
                        offset_y = max(-center_y, min(offset_y, center_y - 1))
                        logging.info(f"Clicking {icon_name} at image coords ({x}, {y}), scaled to ({scaled_x}, {scaled_y}), offset ({offset_x}, {offset_y})")
                        actions = ActionChains(self.driver)
                        actions.move_to_element(icon_div).move_by_offset(offset_x, offset_y).click().perform()
                        time.sleep(1)

                apply_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[text()='Apply']"))
                )
                logging.info("Apply button found, clicking it.")
                apply_button.click()
                time.sleep(2)

                if self.is_captcha_solvedImg():
                    logging.info("Icon CAPTCHA solved successfully.")
                    return True
                else:
                    logging.info("CAPTCHA not solved after clicking Apply, retrying.")

            except Exception as e:
                logging.error(f"Error solving icon selection CAPTCHA: {e}")
        logging.error("Failed to solve icon CAPTCHA after all retries.")
        return False

    def get_icon_order(self):
        try:
            instruction_container = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'captcha-instruction') or contains(text(), 'Click')]"))
            )
            logging.info("Instruction container found.")
            instruction_text = instruction_container.text.lower()

            icon_mapping = {
                "star": "star",
                "calendar": "calendar",
                "cart": "cart",
                "shopping": "cart",
                "date": "calendar",
                "event": "calendar"
            }

            icon_order = []
            for word in instruction_text.split():
                for keyword, icon_name in icon_mapping.items():
                    if keyword in word and icon_name not in icon_order:
                        icon_order.append(icon_name)
                        break

            if not icon_order:
                logging.error("No recognizable icons in instructions. Using default order.")
                return ["star", "calendar", "cart"]

            logging.info(f"Detected icon order from instructions: {icon_order}")
            return icon_order

        except Exception as e:
            logging.error(f"Error extracting icon order: {e}. Using default order.")
            return ["star", "calendar", "cart"]

    def detect_icons(self, image_path, icon_order):
        captcha_image = cv2.imread(image_path)
        if captcha_image is None:
            logging.error("Failed to load CAPTCHA image.")
            return {}

        captcha_gray = self.preprocess_image(captcha_image)

        icon_templates = {
            "star": 'templates/1.png',
            "calendar": 'templates/2.png',
            "cart": 'templates/3.png'
        }

        icon_positions = {}

        for icon_name, template_path in icon_templates.items():
            icon = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            if icon is None:
                logging.error(f"Failed to load template image: {template_path}")
                continue

            icon = self.preprocess_image(icon)
            scales = [0.5, 0.75, 1.0, 1.25, 1.5]
            best_score = 0
            best_position = (0, 0)

            for scale in scales:
                scaled_icon = cv2.resize(icon, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
                if scaled_icon.shape[0] > captcha_gray.shape[0] or scaled_icon.shape[1] > captcha_gray.shape[1]:
                    continue

                result = cv2.matchTemplate(captcha_gray, scaled_icon, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)

                if max_val > best_score:
                    best_score = max_val
                    best_position = (max_loc[0] + scaled_icon.shape[1] // 2,
                                   max_loc[1] + scaled_icon.shape[0] // 2)

            logging.info(f"Icon: {icon_name}, Best Score: {best_score}, Best Position: {best_position}, Template Size: {icon.shape}")

            if best_score >= 0.2:
                icon_positions[icon_name] = best_position

        if not icon_positions or len(icon_positions) < len(icon_order):
            logging.info("Falling back to color-based detection.")
            color_positions = self.detect_icons_by_color(captcha_image)
            icon_positions.update({k: v for k, v in color_positions.items() if k not in icon_positions})

        return icon_positions

    def detect_icons_by_color(self, image):
        icon_positions = {}
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        color_ranges = {
            "star": {"lower": np.array([90, 200, 200]), "upper": np.array([100, 255, 255])},
            "cart": {"lower": np.array([85, 200, 200]), "upper": np.array([90, 255, 255])},
            "calendar": {"lower": np.array([120, 150, 200]), "upper": np.array([130, 255, 255])}
        }

        for icon_name, color_range in color_ranges.items():
            mask = cv2.inRange(hsv_image, color_range["lower"], color_range["upper"])
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            positions = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w > 10 and h > 10:
                    center_x, center_y = x + w // 2, y + h // 2
                    positions.append((center_x, center_y))

            if positions:
                icon_positions[icon_name] = positions[0]

        return icon_positions

    def preprocess_image(self, image):
        if len(image.shape) > 2:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        image = cv2.fastNlMeansDenoising(image)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(image)

    def extract_background_image_url(self, style):
        match = re.search(r"background-image:\s*url\(['\"]?(.*?)['\"]?\)", style)
        return match.group(1) if match else None

    def download_captcha_image(self, image_url):
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

    def is_captcha_solvedImg(self):
        try:
            time.sleep(5)
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@style, 'background-image:')]"))
            )
            logging.info("Icon CAPTCHA is not solved (CAPTCHA container still present).")
            time.sleep(2)
            return False
        except:
            logging.info("Icon CAPTCHA is solved (CAPTCHA container gone).")
            return True

def solve_captcha_and_submit(website_url, username, email, password):
    driver = webdriver.Chrome()
    try:
        logging.info("Opening website...")
        driver.get(website_url)

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

        solver = CaptchaSolver(driver)
        if not solver.solve_slider_captcha():
            logging.error("Slider CAPTCHA failed, aborting.")
            return
        if not solver.solve_icon_captcha():
            logging.error("Icon CAPTCHA failed, aborting.")
            return

        logging.info("Submitting the form...")
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
        )
        logging.info("Submit button found.")
        submit_button.click()
        logging.info("Form submitted.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        logging.info("Closing the browser...")
        time.sleep(10)
        driver.quit()