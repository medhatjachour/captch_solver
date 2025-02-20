import cv2
import numpy as np
import matplotlib.pyplot as plt

def load_image(image_path):
    image = cv2.imread(image_path)
    return cv2.cvtColor(image, cv2.COLOR_BGR2HSV), image

def get_color_ranges():
    return {
        "star": {"lower": np.array([90, 200, 200]), "upper": np.array([100, 255, 255])},  # Cyan clair (#00e0ff)
        "cart": {"lower": np.array([85, 200, 200]), "upper": np.array([90, 255, 255])},  # Vert clair (#14ffd5)
        "calendar": {"lower": np.array([120, 150, 200]), "upper": np.array([130, 255, 255])},  # Bleu (#6464fb)
    }

def detect_color(mask_color_name, hsv_image, lower_bound, upper_bound, image):
    mask = cv2.inRange(hsv_image, lower_bound, upper_bound)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    positions = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w > 10 and h > 10:  # Éliminer les petits bruits
            center_x, center_y = x + w // 2, y + h // 2
            positions.append(center_x)
            positions.append(center_y)
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.circle(image, (center_x, center_y), 5, (0, 0, 255), -1)
            cv2.putText(
                image,
                mask_color_name,
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1,
            )
        print(positions)
    return positions

def detect_icons(image_path):
    image_hsv, image = load_image(image_path)
    color_ranges = get_color_ranges()
    icon_positions = {}
    for icon_name, color_range in color_ranges.items():
        positions = detect_color(icon_name, image_hsv, color_range["lower"], color_range["upper"], image)
        icon_positions[icon_name] = positions
    return image, icon_positions

def display_image(image):
    plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    plt.title("Icônes détectées")
    plt.axis("off")
    plt.show()

if __name__ == "__main__":
    directory_path ="/Users/senzo/Documents/khamssat-projet/serveur/imgs"
    
    image_path = "received_icon.png"
    detected_image, icon_positions = detect_icons(image_path)
    display_image(detected_image)
    print(icon_positions)