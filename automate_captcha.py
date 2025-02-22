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
from detect_puzzle import GeeTestIdentifier  # Assuming this is a custom module

global TheAction

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

                if not icon_positions or any(icon not in icon_positions for icon in icon_order):
                    logging.warning("Missing or invalid icon positions detected, retrying with refresh.")
                    refresh_div = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[span[text()=\"I'm not a robot\"]]"))
                    )
                    self.driver.execute_script("arguments[0].click();", refresh_div)
                    time.sleep(5)
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
                        time.sleep(random.uniform(1.5, 2.5))  # Randomize click delay

                apply_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[text()='Apply']"))
                )
                logging.info("Apply button found, clicking it.")

                self.driver.execute_script("arguments[0].click();", apply_button)

                time.sleep(4)

                if self.is_captcha_solvedImg():
                    logging.info("Icon CAPTCHA solved successfully.")
                    if TheAction == "Register":
                        logging.info("Clicking on Signup button.")
                        signup_button = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[text()='Sign Up']"))
                        )
                        self.driver.execute_script("arguments[0].click();", signup_button)
                    else:
                        logging.info("Clicking on Login button.")
                        login_button = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[text()='Login']"))
                        )
                        self.driver.execute_script("arguments[0].click();", login_button)
                    return True

                else:
                    logging.info("CAPTCHA not solved after clicking Apply, retrying.")

            except Exception as e:
                logging.error(f"Error solving icon selection CAPTCHA: {e}")
                time.sleep(2)  # Brief pause before retry
        logging.error("Failed to solve icon CAPTCHA after all retries.")
        return False

    def get_icon_order(self):
        try:
            icon_container = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//div[contains(@style, 'position: absolute; top: 50%; left: 50%')]//div[contains(@style, 'display: flex;') and .//div[contains(@style, 'background: url(\"https://basiliskcaptcha.com/static/challenges/sprites/icons_sprite.png\"')]]"
                ))
            )
            logging.info("Icon order container found.")

            icon_elements = icon_container.find_elements(By.XPATH, ".//div[contains(@style, 'background: url')]")
            if not icon_elements:
                logging.error("No icon elements found in the container.")
                return ["star", "calendar", "cart"]

            offset_mapping = {
                "-21": "star",
                "-91": "cart",
                "-141": "calendar"
            }

            icon_order = []
            for element in icon_elements:
                style = element.get_attribute("style")
                logging.info(f"Icon element style: {style}")
                y_offset_match = re.search(r"background:.*?-\d+px\s+(\-\d+)px", style)
                if y_offset_match:
                    y_offset = y_offset_match.group(1)
                    icon_name = offset_mapping.get(y_offset, "unknown")
                    logging.info(f"Found icon: {icon_name} with y-offset: {y_offset}")
                    if icon_name != "unknown":
                        icon_order.append(icon_name)
                else:
                    logging.warning(f"Could not parse y-offset from style: {style}")

            if not icon_order:
                logging.error("No valid icons parsed from offsets.")
                return ["star", "calendar", "cart"]

            logging.info(f"Detected icon order: {icon_order}")
            return icon_order

        except Exception as e:
            logging.error(f"Error extracting icon order: {e}. Using default order.")
            return ["star", "calendar", "cart"]

    def detect_icons(self, image_path, icon_order):
        captcha_image = cv2.imread(image_path)
        if captcha_image is None:
            logging.error("Failed to load CAPTCHA image.")
            return {}

        # Preprocess image to isolate icons by color
        icon_masks = self.preprocess_image(captcha_image)
        icon_positions = {}
        used_positions = set()

        for icon_name in icon_order:
            mask = icon_masks[icon_name]
            # Find contours to locate the icon
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                # Sort contours by area and process the largest
                contours = sorted(contours, key=cv2.contourArea, reverse=True)
                for contour in contours[:1]:  # Only take the largest contour
                    if cv2.contourArea(contour) > 50:  # Minimum area threshold
                        M = cv2.moments(contour)
                        if M["m00"] != 0:
                            cX = int(M["m10"] / M["m00"])
                            cY = int(M["m01"] / M["m00"])
                            position = (cX, cY)
                            # Relax proximity check further if needed
                            if position not in used_positions and all(
                                np.sqrt((cX - up[0])**2 + (cY - up[1])**2) > 5 for up in used_positions
                            ):
                                icon_positions[icon_name] = position
                                used_positions.add(position)
                                logging.info(f"Detected {icon_name} at {position} (area: {cv2.contourArea(contour)})")
                            else:
                                logging.warning(f"Position for {icon_name} at {position} too close to another icon or already used (area: {cv2.contourArea(contour)})")
                        else:
                            logging.warning(f"No valid moments for {icon_name} contour")
                    else:
                        logging.warning(f"Contour for {icon_name} too small (area: {cv2.contourArea(contour)})")
            else:
                logging.warning(f"No contours found for {icon_name}")

        # Fallback for missing cart
        if "cart" not in icon_positions and "star" in icon_positions and "calendar" in icon_positions:
            logging.warning("Cart not detected, estimating position based on star and calendar")
            star_x, star_y = icon_positions["star"]
            cal_x, cal_y = icon_positions["calendar"]
            # Estimate cart position as midpoint or offset
            cart_x = (star_x + cal_x) // 2
            cart_y = (star_y + cal_y) // 2 + 20  # Offset slightly below midpoint
            position = (cart_x, cart_y)
            if position not in used_positions and all(
                np.sqrt((cart_x - up[0])**2 + (cart_y - up[1])**2) > 5 for up in used_positions
            ):
                icon_positions["cart"] = position
                used_positions.add(position)
                logging.info(f"Assigned fallback position for cart at {position}")

        # Debug image with detected positions
        debug_img = captcha_image.copy()
        for icon_name, pos in icon_positions.items():
            cv2.circle(debug_img, pos, 5, (0, 255, 0), -1)
            cv2.putText(debug_img, icon_name, (pos[0] + 10, pos[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.imwrite(os.path.join(CAPTCHA_IMAGE_DIR, "debug_icon_positions.png"), debug_img)

        return icon_positions
  
  

    def preprocess_image(self, image):
        if len(image.shape) != 3:
            logging.error("Image is not a color image")
            return {"star": np.zeros(image.shape, dtype=np.uint8),
                    "calendar": np.zeros(image.shape, dtype=np.uint8),
                    "cart": np.zeros(image.shape, dtype=np.uint8)}

        # Convert hex colors to BGR (OpenCV format)
        hex_to_bgr = {
            "14ffd5": (213, 255, 20),  # #14FFD5 -> BGR: (20, 255, 213)
            "00e0ff": (255, 224, 0),   # #00E0FF -> BGR: (255, 224, 0)
            "6666ff": (255, 102, 102)  # #6666FF -> BGR: (255, 102, 102)
        }

        # Convert to HSV for color-based detection
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Define precise HSV ranges for each icon
        icon_hsv_ranges = {
            "cart": ([82, 80, 80], [88, 255, 255]),      # #14FFD5 (H: ~85)
            "star": ([88, 80, 80], [94, 255, 255]),      # #00E0FF (H: ~91)
            "calendar": ([115, 80, 80], [125, 255, 255]) # #6666FF (H: ~120)
        }

        icon_masks = {}
        for icon_name, (lower, upper) in icon_hsv_ranges.items():
            lower = np.array(lower, dtype=np.uint8)
            upper = np.array(upper, dtype=np.uint8)
            mask = cv2.inRange(hsv, lower, upper)
            # Use a small kernel for subtle noise reduction
            kernel = np.ones((2, 2), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
            icon_masks[icon_name] = mask
            logging.info(f"Processed mask for {icon_name}, min: {np.min(mask)}, max: {np.max(mask)}")

        # Save combined mask for debugging
        combined_mask = np.zeros_like(icon_masks["star"])
        for mask in icon_masks.values():
            combined_mask = cv2.bitwise_or(combined_mask, mask)
        cv2.imwrite(os.path.join(CAPTCHA_IMAGE_DIR, "debug_combined_mask.png"), combined_mask)

        # Save individual masks for debugging
        for icon_name, mask in icon_masks.items():
            cv2.imwrite(os.path.join(CAPTCHA_IMAGE_DIR, f"debug_mask_{icon_name}.png"), mask)

        return icon_masks
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
                EC.presence_of_element_located((By.XPATH, "//div[span[text()=\"Apply\"]]"))
            )
            logging.info("Icon CAPTCHA is not solved (CAPTCHA container still present).")
            time.sleep(2)
            return False
        except:
            logging.info("Icon CAPTCHA is solved (CAPTCHA container gone).")
            return True

def solve_captcha_and_submit(website_url, username, email, password,action):
    driver = webdriver.Chrome()
    global TheAction
    TheAction = action
    logging.info(action)
    logging.info("Opening website...")
    driver.get(website_url)

    try:
        if action == "Register":
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
        
        else:
            logging.info("Filling the form...")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter your email here']"))
            )
            driver.find_element(By.XPATH, "//input[@placeholder='Enter your email here']").send_keys(email)
            driver.find_element(By.XPATH, "//button[text()='Сontinue']").click()
            time.sleep(2)
            driver.find_element(By.XPATH, "//input[@placeholder='Enter your password here']").send_keys(password)
            # driver.find_element(By.XPATH, "//button[text()='Сontinue']").click()
        
        time.sleep(2)
        driver.find_element(By.XPATH, "//div[span[text()=\"I'm not a robot\"]]").click()

        time.sleep(5)

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

if __name__ == "__main__":
    solve_captcha_and_submit("https://example.com", "testuser", "test@example.com", "password123")