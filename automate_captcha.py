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
            time.sleep(2)
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
                logging.info(f"Icon order to be clicked: {icon_order}")
                icon_positions = self.detect_icons(captcha_image_path, icon_order)
                logging.info(f"Detected icon positions: {icon_positions}")

                if not icon_positions or all(pos == (0, 0) for pos in icon_positions.values()):
                    logging.warning("No valid icon positions detected, skipping click.")
                    continue

                missing_icons = [icon for icon in icon_order if icon not in icon_positions]
                if missing_icons:
                    logging.error(f"Missing positions for icons: {missing_icons}")
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
            # Target the popup's flex container with sprite icons
            icon_container = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.XPATH, 
                    "//div[contains(@style, 'position: absolute; top: 50%; left: 50%')]//div[contains(@style, 'display: flex;') and .//div[contains(@style, 'background: url(\"https://basiliskcaptcha.com/static/challenges/sprites/icons_sprite.png\"')]]"
                ))
            )
            logging.info("Icon order container found.")

            # Extract icon elements within the container
            icon_elements = icon_container.find_elements(By.XPATH, ".//div[contains(@style, 'background: url')]")
            if not icon_elements:
                logging.error("No icon elements found in the container.")
                all_divs = icon_container.find_elements(By.XPATH, ".//div")
                for div in all_divs:
                    logging.info(f"Child div style: {div.get_attribute('style')}")
                return ["star", "calendar", "cart"]

            # Map y-offsets to icon names
            offset_mapping = {
                "-21": "star",
                "-91": "calendar",
                "-141": "cart"
            }

            icon_order = []
            for element in icon_elements:
                style = element.get_attribute("style")
                y_offset_match = re.search(r"background:.*?(\-\d+)px", style)
                if y_offset_match:
                    y_offset = y_offset_match.group(1)
                    icon_name = offset_mapping.get(y_offset, "unknown")
                    if icon_name != "unknown":
                        icon_order.append(icon_name)
                    logging.info(f"Found icon: {icon_name} with y-offset: {y_offset}")
                else:
                    logging.warning(f"Could not parse y-offset from style: {style}")

            if not icon_order:
                logging.error("No valid icons parsed from offsets.")
                return ["star", "calendar", "cart"]

            logging.info(f"Detected icon order from offsets: {icon_order}")
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

        # Load sprite sheet
        sprite_url = "https://basiliskcaptcha.com/static/challenges/sprites/icons_sprite.png"
        sprite_image_path = os.path.join(CAPTCHA_IMAGE_DIR, "icons_sprite.png")
        if not os.path.exists(sprite_image_path):
            sprite_response = requests.get(sprite_url)
            if sprite_response.status_code != 200:
                logging.error("Failed to download sprite sheet.")
                return {}
            with open(sprite_image_path, "wb") as f:
                f.write(sprite_response.content)

        sprite_image = cv2.imread(sprite_image_path, cv2.IMREAD_GRAYSCALE)
        if sprite_image is None:
            logging.error("Failed to load sprite image.")
            return {}

        sprite_image = self.preprocess_image(sprite_image)

        # Define icon regions from sprite sheet (22x22 pixels)
        icon_templates = {
            "star": sprite_image[21:43, 2:24],      # -21px to -43px
            "calendar": sprite_image[91:113, 2:24], # -91px to -113px
            "cart": sprite_image[141:163, 2:24]     # -141px to -163px
        }

        all_matches = {}
        icon_positions = {}
        used_positions = set()

        # Detect matches for each icon
        for icon_name, template in icon_templates.items():
            scales = [0.8, 0.9, 1.0, 1.1, 1.2]
            matches = []

            for scale in scales:
                scaled_template = cv2.resize(template, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
                if scaled_template.shape[0] > captcha_gray.shape[0] or scaled_template.shape[1] > captcha_gray.shape[1]:
                    continue

                result = cv2.matchTemplate(captcha_gray, scaled_template, cv2.TM_CCOEFF_NORMED)
                locations = np.where(result >= 0.4)  # Adjusted threshold
                for pt in zip(*locations[::-1]):
                    position = (pt[0] + scaled_template.shape[1] // 2, pt[1] + scaled_template.shape[0] // 2)
                    score = result[pt[1], pt[0]]
                    matches.append((position, score))

            matches.sort(key=lambda x: x[1], reverse=True)
            all_matches[icon_name] = matches[:3]  # Top 3 matches
            logging.info(f"Icon: {icon_name}, Matches Found: {len(matches)}, Top Matches: {matches[:3] if matches else 'None'}, Template Size: {template.shape}")

        # Assign positions in order with spatial separation
        for icon_name in icon_order:
            if icon_name in all_matches and all_matches[icon_name]:
                for position, score in all_matches[icon_name]:
                    pos_tuple = (position[0], position[1])
                    is_valid = True
                    for used_pos in used_positions:
                        dist = np.sqrt((position[0] - used_pos[0])**2 + (position[1] - used_pos[1])**2)
                        if dist < 30:  # Minimum distance
                            is_valid = False
                            break
                    if (is_valid and 
                        pos_tuple not in used_positions and 
                        0 <= position[0] < captcha_gray.shape[1] and 
                        0 <= position[1] < captcha_gray.shape[0]):
                        icon_positions[icon_name] = position
                        used_positions.add(pos_tuple)
                        logging.info(f"Assigned {icon_name} to position {position} with score {score}")
                        break
                else:
                    logging.warning(f"No valid unique position for {icon_name}, using best available.")
                    if all_matches[icon_name]:
                        icon_positions[icon_name] = all_matches[icon_name][0][0]
            else:
                logging.error(f"No matches found for {icon_name}")

        return icon_positions

    def preprocess_image(self, image):
        if len(image.shape) > 2:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        image = cv2.fastNlMeansDenoising(image, h=10)
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

    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        logging.info("Closing the browser...")
        time.sleep(10)
        driver.quit()

