import random
import time
import cv2
import pyautogui
import pytesseract
import numpy as np
from PIL import Image
import json


def load_russian_words_from_json(json_file):
    with open(json_file, 'r', encoding='utf-8') as file:
        data = json.load(file)
        words = [entry['word'] for entry in data]
    return words


def get_possible_words(letters, word_list):
    letter_count = {}
    for char in letters:
        letter_count[char] = letter_count.get(char, 0) + 1

    possible_words = []

    for word in word_list:
        if 4 <= len(word) <= 8:
            word_count = {}
            for char in word:
                word_count[char] = word_count.get(char, 0) + 1

            if all(letter_count.get(char, 0) >= count for char, count in word_count.items()):
                possible_words.append(word)

    return possible_words


def is_russian_letter(letter):
    return 'А' <= letter <= 'Я' or 'а' <= 'я'


def find_letter_positions(image, rect_top_left, rect_bottom_right):
    letter_positions = {}

    full_screenshot = pyautogui.screenshot()
    full_screenshot_np = np.array(full_screenshot)

    offset_x = rect_top_left[0]
    offset_y = rect_top_left[1]

    boxes = pytesseract.image_to_boxes(image, lang='rus')

    for box in boxes.splitlines():
        b = box.split()
        letter = b[0]
        x_crop, y_crop = int(b[1]), int(b[2])

        x_full = x_crop + offset_x
        y_full = image.shape[0] - int(b[4]) + offset_y

        if is_russian_letter(letter):
            if letter.upper() not in letter_positions:
                letter_positions[letter.upper()] = []
            letter_positions[letter.upper()].append((x_full, y_full))

    return letter_positions


def preprocess_image(image, lower_bound, upper_bound):
    mask = cv2.inRange(image, lower_bound, upper_bound)
    res = cv2.bitwise_and(image, image, mask=mask)

    gray = cv2.cvtColor(res, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 5)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    kernel = np.ones((2, 2), np.uint8)
    thresh = cv2.erode(thresh, kernel, iterations=1)
    thresh = cv2.dilate(thresh, kernel, iterations=1)

    return thresh


def detect_colored_letters(image):
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    red_lower = np.array([0, 70, 50])
    red_upper = np.array([10, 255, 255])
    gray_lower = np.array([0, 0, 50])
    gray_upper = np.array([180, 50, 255])
    blue_lower = np.array([100, 150, 0])
    blue_upper = np.array([140, 255, 255])

    red_letters = preprocess_image(hsv_image, red_lower, red_upper)
    gray_letters = preprocess_image(hsv_image, gray_lower, gray_upper)
    blue_letters = preprocess_image(hsv_image, blue_lower, blue_upper)

    return red_letters, gray_letters, blue_letters


def filter_letters(scanned_text_red, scanned_text_gray, scanned_text_blue):
    letters_red = scanned_text_red.lower()
    letters_gray = scanned_text_gray.lower()
    letters_blue = scanned_text_blue.lower()

    if 'е' in letters_gray and 'ж' in letters_gray:
        letters_gray = letters_gray.replace('ж', '')
    if 'ч' in letters_gray and 'р' in letters_gray:
        letters_gray = letters_gray.replace('ч', '')

    return letters_red, letters_gray, letters_blue


def click_letters(letter_positions, word):
    used_positions = set()
    for letter in word:
        if letter.upper() in letter_positions:
            for position in letter_positions[letter.upper()]:
                if position not in used_positions:
                    pyautogui.click(position[0], position[1])
                    used_positions.add(position)
                    time.sleep(0.2)
                    break
    pyautogui.click(1145, 956)


def main():
    while True:
        try:
            if pyautogui.locateOnScreen("hod_my.png"):
                time.sleep(2.0)
                n = 5000

                json_file = 'words-russian-nouns.json'
                russian_words = load_russian_words_from_json(json_file)

                try:
                    pyautogui.click("clear_words.png")
                    time.sleep(0.5)
                except Exception:
                    pass

                screenshot = pyautogui.screenshot()

                rect_top_left = (720, 509)
                rect_bottom_right = (1200, 888)

                screenshot_roi = screenshot.crop(
                    (rect_top_left[0], rect_top_left[1], rect_bottom_right[0], rect_bottom_right[1])
                )
                screenshot_roi_np = np.array(screenshot_roi)

                gray_image = cv2.cvtColor(screenshot_roi_np, cv2.COLOR_BGR2GRAY)
                _, bw_image = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                bw_image_path = 'bw_image.png'
                cv2.imwrite(bw_image_path, bw_image)

                red_letters, gray_letters, blue_letters = detect_colored_letters(screenshot_roi_np)

                config = '--psm 6 --oem 3 -l rus'
                scanned_text_red = pytesseract.image_to_string(red_letters, config=config)
                scanned_text_gray = pytesseract.image_to_string(gray_letters, config=config)
                scanned_text_blue = pytesseract.image_to_string(blue_letters, config=config)

                scanned_text_red = scanned_text_red.replace('\n', '').replace(' ', '')
                scanned_text_gray = scanned_text_gray.replace('\n', '').replace(' ', '')
                scanned_text_blue = scanned_text_blue.replace('\n', '').replace(' ', '')

                letters_red, letters_gray, letters_blue = filter_letters(scanned_text_red, scanned_text_gray, scanned_text_blue)

                print(f"Буквы на красном фоне: {letters_red}")
                print(f"Буквы на сером фоне: {letters_gray}")
                print(f"Буквы на синем фоне: {letters_blue}")

                possible_words_red = get_possible_words(letters_red, russian_words)
                possible_words_gray = get_possible_words(letters_gray, russian_words)
                possible_words_blue = get_possible_words(letters_blue, russian_words)

                possible_words = list(set(possible_words_gray + possible_words_red) - set(possible_words_blue))

                if len(letters_gray) == 1:
                    letters_combined = letters_gray + letters_red + letters_blue
                    possible_words = get_possible_words(letters_combined, russian_words)

                filtered_words = []
                letter_count = {}

                for word in possible_words:
                    initial_letter = word[0]
                    letter_count[initial_letter] = letter_count.get(initial_letter, 0) + 1
                    if letter_count[initial_letter] <= 15:
                        filtered_words.append(word)
                        if len(filtered_words) == n:
                            break

                # if filtered_words:
                #     print("Используются буквы на сером + красном фоне:")
                #     for word in filtered_words:
                #         print(word)
                # else:
                #     print("Используются буквы на других фонах (например, синем + красном):")

                letter_positions = find_letter_positions(bw_image, rect_top_left, rect_bottom_right)

                if filtered_words:
                    word_to_click = str(random.choice(filtered_words)).upper()
                    click_letters(letter_positions, word_to_click)
                else:
                    print("Нет доступных слов для клика.")

                saved_image = Image.open(bw_image_path)
        except Exception:
            try:
                dalee_btn = pyautogui.locateOnScreen("dalee.png")
                pyautogui.click(dalee_btn)
            except Exception:
                try:
                    close_ad = pyautogui.locateOnScreen("ad_exit.png")
                    pyautogui.click(close_ad)
                except Exception:
                    try:
                        play_btn = pyautogui.locateOnScreen("play.png")
                        pyautogui.click(play_btn)
                    except Exception:
                        try:
                            if pyautogui.locateOnScreen("magazine.png"):
                                pyautogui.click(1258, 960)
                        except Exception:
                            continue
            continue


if __name__ == '__main__':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    main()
