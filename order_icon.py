import cv2
import numpy as np


def load_image(filepath, grayscale=False):
    image = cv2.imread(filepath, 0 if grayscale else 1)
    if image is None:
        raise FileNotFoundError(
            f"Erreur: Impossible de charger l'image depuis {filepath}")
    return image


def preprocess_image(image):
    # Apply adaptive thresholding to handle varying lighting conditions
    if len(image.shape) > 2:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Denoise the image
    image = cv2.fastNlMeansDenoising(image)

    # Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    image = clahe.apply(image)

    return image


def resize_icon(icon, target_shape, min_size=20):
    # Ensure icon is not too small
    if icon.shape[0] < min_size or icon.shape[1] < min_size:
        scale_factor = max(min_size / icon.shape[0], min_size / icon.shape[1])
        new_width = int(icon.shape[1] * scale_factor)
        new_height = int(icon.shape[0] * scale_factor)
        icon = cv2.resize(icon, (new_width, new_height),
                          interpolation=cv2.INTER_CUBIC)

    # Resize if larger than target
    if icon.shape[0] > target_shape[0] or icon.shape[1] > target_shape[1]:
        scale_factor = min(
            target_shape[0] / icon.shape[0], target_shape[1] / icon.shape[1])
        new_width = int(icon.shape[1] * scale_factor)
        new_height = int(icon.shape[0] * scale_factor)
        icon = cv2.resize(icon, (new_width, new_height),
                          interpolation=cv2.INTER_AREA)

    return icon


def find_icon(icon, image, threshold=0.5):
    # Try multiple scales for better detection
    scales = [0.8, 0.9, 1.0, 1.1, 1.2]
    best_result = None
    best_score = threshold

    for scale in scales:
        scaled_icon = cv2.resize(icon, None, fx=scale,
                                 fy=scale, interpolation=cv2.INTER_CUBIC)
        if scaled_icon.shape[0] > image.shape[0] or scaled_icon.shape[1] > image.shape[1]:
            continue

        result = cv2.matchTemplate(image, scaled_icon, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > best_score:
            best_score = max_val
            best_result = (max_loc, max_val)

    if best_result is None:
        return (0, 0), 0
    return best_result


def order_icons(captcha_filepath, icon_filepaths={
    "calendar": 'templates/2.png',
    "cart": 'templates/3.png',
            "star": 'templates/1.png'
}, confidence_threshold=0.5):

    captcha_image = load_image(captcha_filepath)
    # Preprocess the captcha image
    captcha_gray = preprocess_image(captcha_image)

    icons = {}
    icon_positions = []

    # Process each icon
    for name, filepath in icon_filepaths.items():
        icon = load_image(filepath, grayscale=True)
        # Preprocess the icon template
        icon = preprocess_image(icon)
        icons[name] = resize_icon(icon, captcha_gray.shape)

        position, score = find_icon(
            icons[name], captcha_gray, confidence_threshold)

        if score >= confidence_threshold:
            icon_positions.append({
                'name': name,
                'x': position[0],
                'position': position,
                'score': score
            })

    if not icon_positions:
        raise ValueError("No icons were detected with sufficient confidence")

    ordered_icons = sorted(icon_positions, key=lambda x: x['x'])
    order = [icon['name'] for icon in ordered_icons]

    return order, [icon['score'] for icon in ordered_icons]


if __name__ == "__main__":
    import os

    imgs_dir = 'imgs'
    for filename in os.listdir(imgs_dir):
        if filename.endswith('.png'):
            captcha_filepath = os.path.join(imgs_dir, filename)
            try:
                order, confidence_scores = order_icons(captcha_filepath)
                print(order)
                print(f"\nIcons ordered from left to right for {filename}:")
                for idx, (name, score) in enumerate(zip(order, confidence_scores)):
                    print(f"{idx + 1}. {name} (confidence: {score:.2f})")
                print(f"\nFinal order for {filename}: {' -> '.join(order)}")
            except (FileNotFoundError, ValueError) as e:
                print(f"Error processing {filename}: {e}")
