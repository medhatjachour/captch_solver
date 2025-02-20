from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import base64
import os
from PIL import Image
from detect_puzzle import GeeTestIdentifier  # Import the CAPTCHA solver from the repository

# Directory to save CAPTCHA images
CAPTCHA_IMAGE_DIR = "captcha_images"
os.makedirs(CAPTCHA_IMAGE_DIR, exist_ok=True)

def solve_captcha_and_submit(website_url, username, email, password):
    # Initialize the WebDriver (e.g., Chrome)
    driver = webdriver.Chrome()  # Replace with the path to your WebDriver if needed

    try:
        # Open the target website
        driver.get(website_url)

        # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter your user name']"))
        )

        # Enter the username and click the button
        driver.find_element(By.XPATH, "//input[@placeholder='Enter your user name']").send_keys(username)
        driver.find_element(By.XPATH, "//button[text()='Сontinue']").click()

        time.sleep(2)

        # Enter the email and click the button
        driver.find_element(By.XPATH, "//input[@placeholder='Enter your email here']").send_keys(email)
        driver.find_element(By.XPATH, "//button[text()='Сontinue']").click()

        time.sleep(2)

        # Enter the password and confirm it
        driver.find_element(By.XPATH, "//input[@placeholder='Enter password here']").send_keys(password)
        driver.find_element(By.XPATH, "//input[@placeholder='Repeat password']").send_keys(password)
        driver.find_element(By.XPATH, "//button[text()='Сontinue']").click()

        time.sleep(5)

        # Wait for the CAPTCHA canvas element to be visible
        canvas = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//canvas[@width='316']"))
        )

        # Extract the image data from the canvas
        canvas_base64 = driver.execute_script(
            "return arguments[0].toDataURL('image/png').substring(21);", canvas
        )
        canvas_png = base64.b64decode(canvas_base64)

        # Save the CAPTCHA image with a unique filename
        captcha_image_path = os.path.join(CAPTCHA_IMAGE_DIR, f"captcha_{int(time.time())}.png")
        with open(captcha_image_path, "wb") as f:
            f.write(canvas_png)

        # Solve the CAPTCHA using the repository's logic
        def solve_captcha(image_path):
            identifier = GeeTestIdentifier(
                background=image_path,
                puzzle_piece="puzzle_piece.png",  # Use a fixed path for the puzzle piece
                debugger=True
            )
            result = identifier.find_puzzle_piece_position()
            return result["position_from_left"]

        # Solve the CAPTCHA
        captcha_solution = solve_captcha(captcha_image_path)

        # Locate the CAPTCHA input field and submit the solution
        captcha_input = driver.find_element(By.XPATH, "//input[@id='captcha-input']")
        captcha_input.send_keys(str(captcha_solution))

        # Submit the form (if needed)
        submit_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        submit_button.click()

        # Wait for the result
        time.sleep(5)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the browser
        print("Reloading or closing the browser...")
        driver.quit()