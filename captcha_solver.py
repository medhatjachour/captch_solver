import cv2
import numpy as np
from PIL import Image
import io
import requests
from bs4 import BeautifulSoup
import os

class GeeTestIdentifier:
    def __init__(self, background, puzzle_piece, debugger=False):
        self.background = self._read_image(background)
        self.puzzle_piece = self._read_image(puzzle_piece)
        self.debugger = debugger

    @staticmethod
    def _read_image(image_source):
        if isinstance(image_source, bytes):
            return cv2.imdecode(np.frombuffer(image_source, np.uint8), cv2.IMREAD_ANYCOLOR)
        elif hasattr(image_source, 'read'):
            return cv2.imdecode(np.frombuffer(image_source.read(), np.uint8), cv2.IMREAD_ANYCOLOR)
        elif isinstance(image_source, str):
            return cv2.imread(image_source)
        else:
            raise TypeError("Invalid image source type.")

    def find_puzzle_piece_position(self):
        edge_puzzle_piece = cv2.Canny(self.puzzle_piece, 100, 200)
        edge_background = cv2.Canny(self.background, 100, 200)

        edge_puzzle_piece_rgb = cv2.cvtColor(edge_puzzle_piece, cv2.COLOR_GRAY2RGB)
        edge_background_rgb = cv2.cvtColor(edge_background, cv2.COLOR_GRAY2RGB)

        res = cv2.matchTemplate(edge_background_rgb, edge_puzzle_piece_rgb, cv2.TM_CCOEFF_NORMED)

        matches = []
        for _ in range(2):
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            matches.append((max_loc, max_val))

            h, w = edge_puzzle_piece.shape[:2]
            mask_size = 20
            y_start = max(0, max_loc[1] - mask_size)
            y_end = min(res.shape[0], max_loc[1] + h + mask_size)
            x_start = max(0, max_loc[0] - mask_size)
            x_end = min(res.shape[1], max_loc[0] + w + mask_size)
            res[y_start:y_end, x_start:x_end] = 0

        matches.sort(key=lambda x: x[0][0])
        top_left, max_val = matches[1]
        h, w = edge_puzzle_piece.shape[:2]
        center_x = top_left[0] + w // 2
        center_y = top_left[1] + h // 2

        if self.debugger:
            debug_img = self.background.copy()
            cv2.rectangle(debug_img, top_left, (top_left[0] + w, top_left[1] + h), (0, 0, 255), 2)
            cv2.imwrite('output.png', debug_img)

        return {
            "position_from_left": center_x,
            "position_from_bottom": self.background.shape[0] - center_y,
            "coordinates": [center_x, center_y],
            "confidence": float(max_val)
        }