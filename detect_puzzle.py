import numpy as np
from PIL import Image
from bs4 import BeautifulSoup
import io
import requests
import cv2
import os


class GeeTestIdentifier:
    def __init__(self, background, puzzle_piece, debugger=False):
        '''
        GeeTestIdentifier class constructor.

        Parameters
        ----------
        background : str or bytes or file-like object
            The background image path or data.
        puzzle_piece : str or bytes or file-like object
            The puzzle piece image path or data.
        debugger : bool, optional
            Whether to draw the results on the background image. The default is False.
        '''
        self.background = self._read_image(background)
        self.puzzle_piece = self._read_image(puzzle_piece)
        self.debugger = debugger

    @staticmethod
    def test(background_path=None, puzzle_piece_path=None):
        """
        Test the puzzle piece detection with either local files or downloaded test images.

        Parameters
        ----------
        background_path : str, optional
            Path to local background image. If None, downloads test image.
        puzzle_piece_path : str, optional
            Path to local puzzle piece image. If None, downloads test image.
        """
        if background_path and puzzle_piece_path:
            identifier = GeeTestIdentifier(
                background=background_path,
                puzzle_piece=puzzle_piece_path,
                debugger=True
            )
        else:
            data = GeeTestIdentifier.load_test()
            identifier = GeeTestIdentifier(
                background=GeeTestIdentifier.load_image(data['background']),
                puzzle_piece=GeeTestIdentifier.load_image(data['puzzle']),
                debugger=True
            )
        result = identifier.find_puzzle_piece_position()
        print(f"Result: {result}")

    @staticmethod
    def load_image(url: str) -> np.ndarray:
        response = requests.get(url)
        response.raise_for_status()  # This will raise an error for bad responses
        return response.content

    @staticmethod
    def load_test():
        response = requests.get(
            'https://edge-functions-bot-protection-datadome.vercel.app/blocked',
            headers={
                'authority': 'edge-functions-bot-protection-datadome.vercel.app',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
                'cache-control': 'no-cache',
                'pragma': 'no-cache',
                'sec-ch-device-memory': '8',
                'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                'sec-ch-ua-arch': '"arm"',
                'sec-ch-ua-full-version-list': '"Not A(Brand";v="99.0.0.0", "Google Chrome";v="121.0.6167.85", "Chromium";v="121.0.6167.85"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-model': '""',
                'sec-ch-ua-platform': '"macOS"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            }
        )
        images = BeautifulSoup(response.text, 'html.parser').\
            find_all("link", {"rel": "preload", "as": "image"})
        return {
            "background": images[0]['href'],
            "puzzle": images[1]['href']
        }

    def _read_image(self, image_source):
        """
        Read an image from a file path, bytes, or a file-like object.
        """
        if isinstance(image_source, bytes):
            return cv2.imdecode(np.frombuffer(image_source, np.uint8), cv2.IMREAD_ANYCOLOR)
        elif hasattr(image_source, 'read'):  # Checks if it's a file-like object
            return cv2.imdecode(np.frombuffer(image_source.read(), np.uint8), cv2.IMREAD_ANYCOLOR)
        elif isinstance(image_source, str):  # Handle file path
            return cv2.imread(image_source)
        else:
            raise TypeError(
                "Invalid image source type. Must be bytes, file-like object, or file path.")

    def find_puzzle_piece_position(self):
        """
        Find the matching positions of puzzle pieces in a background image.
        Returns the position of both matches.
        """
        # Apply edge detection
        edge_puzzle_piece = cv2.Canny(self.puzzle_piece, 100, 200)
        edge_background = cv2.Canny(self.background, 100, 200)

        # Convert to RGB for visualization
        edge_puzzle_piece_rgb = cv2.cvtColor(
            edge_puzzle_piece, cv2.COLOR_GRAY2RGB)
        edge_background_rgb = cv2.cvtColor(edge_background, cv2.COLOR_GRAY2RGB)

        # Template matching
        res = cv2.matchTemplate(edge_background_rgb,
                                edge_puzzle_piece_rgb, cv2.TM_CCOEFF_NORMED)

        # Find two best matches
        matches = []
        for _ in range(2):
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            matches.append((max_loc, max_val))

            # Mask out the area around the found match to find the next best match
            h, w = edge_puzzle_piece.shape[:2]
            mask_size = 20  # Size of area to mask around match
            y_start = max(0, max_loc[1] - mask_size)
            y_end = min(res.shape[0], max_loc[1] + h + mask_size)
            x_start = max(0, max_loc[0] - mask_size)
            x_end = min(res.shape[1], max_loc[0] + w + mask_size)
            res[y_start:y_end, x_start:x_end] = 0

        # Sort matches by x coordinate (left to right)
        matches.sort(key=lambda x: x[0][0])
        print(matches)
        # Get the rightmost match
        top_left, max_val = matches[1]  # Use the second (rightmost) match
        h, w = edge_puzzle_piece.shape[:2]
        bottom_right = (top_left[0] + w, top_left[1] + h)

        # Calculate required values
        center_x = top_left[0] + w // 2
        center_y = top_left[1] + h // 2
        position_from_left = center_x
        position_from_bottom = self.background.shape[0] - center_y

        # Draw rectangle, lines, and coordinates if debugger is True
        if self.debugger:
            debug_img = self.background.copy()
            cv2.imwrite('input.png', debug_img)

            # Draw rectangles for both matches
            match_loc, match_val = matches[1]  # Use the second match
            match_br = (match_loc[0] + w, match_loc[1] + h)
            cv2.rectangle(debug_img, match_loc, match_br, (0, 0, 255), 2)

            # Draw lines and info for the chosen (rightmost) match
            cv2.line(debug_img, (center_x, 0), (center_x,
                     edge_background_rgb.shape[0]), (0, 255, 0), 2)
            cv2.line(debug_img, (0, center_y),
                     (edge_background_rgb.shape[1], center_y), (0, 255, 0), 2)

            # Add text with coordinates
            text = f"x: {center_x}, y: {center_y}"
            cv2.putText(debug_img, text, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(debug_img, f"Confidence: {max_val:.2f}", (
                10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # cv2.imshow("output",debug_img)
            # cv2.waitKey(0)
            # cv2.destroyAllWindows()
            cv2.imwrite('output.png', debug_img)

        return {
            "position_from_left": position_from_left,
            "position_from_bottom": position_from_bottom,
            "coordinates": [center_x, center_y],
            "confidence": float(max_val)
        }

    def get_puzzle_piece_box(self, img_bytes: bytes):
        """
        Identify the bounding box of the non-transparent part of an image.
        """
        image = Image.open(io.BytesIO(img_bytes))
        bbox = image.getbbox()
        cropped_image = image.crop(bbox)
        self.center = (bbox[3] - bbox[1]) // 2
        return cropped_image, bbox[0], bbox[1]


if __name__ == '__main__':
    # Create output directory if it doesn't exist
    output_dir = "output_puzz"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Get all puzzle images from puzzleimgs directory
    puzzle_dir = "puzzleimgs"
    puzzle_piece_path = "piece.png"
    background_path = "image1.png"
    # Process each puzzle image
    

    # Create identifier instance
    identifier = GeeTestIdentifier(
        background=background_path,
        puzzle_piece=puzzle_piece_path,
        debugger=True
    )

    # Find position and save result
   
    result = identifier.find_puzzle_piece_position()
    # print(f"Result for {background_path}: {result}")


    # Move output.png to output_puzz with puzzle name
    output_name = f"result_{background_path}"
   
