import os
import shutil
from pathlib import Path

import cv2
import numpy as np
import pytesseract

BASE_DIR = Path(__file__).resolve().parent


class PlateReader:
    def configure_tesseract(self):
        configured = pytesseract.pytesseract.tesseract_cmd
        if configured:
            if os.path.isfile(configured):
                return True
            command_path = shutil.which(configured)
            if command_path:
                pytesseract.pytesseract.tesseract_cmd = command_path
                return True

        candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for path in candidates:
            if os.path.isfile(path):
                pytesseract.pytesseract.tesseract_cmd = path
                return True

        command_path = shutil.which("tesseract")
        if command_path:
            pytesseract.pytesseract.tesseract_cmd = command_path
            return True

        return False

    def load_model(self, weight_path: str, cfg_path: str, classes_path: str | None = None):
        self.net = cv2.dnn.readNet(weight_path, cfg_path)
        classes_file = Path(classes_path) if classes_path else BASE_DIR / "classes-ocr.names"
        with classes_file.open("r", encoding="utf-8") as handle:
            self.classes = [line.strip() for line in handle.readlines() if line.strip()]
        self.layers_names = self.net.getLayerNames()
        out_layers = np.array(self.net.getUnconnectedOutLayers()).flatten()
        self.output_layers = [self.layers_names[int(i) - 1] for i in out_layers]
        self.colors = np.random.uniform(0, 255, size=(len(self.classes), 3))

    def load_image(self, img_path):
        img = cv2.imread(img_path)
        if img is None:
            raise RuntimeError(f"Unable to read image: {img_path}")
        height, width, channels = img.shape
        return img, height, width, channels

    def read_plate(self, img):
        blob = cv2.dnn.blobFromImage(
            img,
            scalefactor=0.00392,
            size=(320, 320),
            mean=(0, 0, 0),
            swapRB=True,
            crop=False,
        )
        self.net.setInput(blob)
        outputs = self.net.forward(self.output_layers)
        return blob, outputs

    def get_boxes(self, outputs, width, height, threshold=0.3):
        boxes = []
        confidences = []
        class_ids = []
        for output in outputs:
            for detect in output:
                scores = detect[5:]
                class_id = int(np.argmax(scores))
                confidence = float(scores[class_id])
                if confidence > threshold:
                    center_x = int(detect[0] * width)
                    center_y = int(detect[1] * height)
                    w = int(detect[2] * width)
                    h = int(detect[3] * height)
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    boxes.append([x, y, w, h])
                    confidences.append(confidence)
                    class_ids.append(class_id)
        return boxes, confidences, class_ids

    def draw_labels(self, boxes, confidences, class_ids, img):
        indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.1, 0.1)
        if len(indexes) == 0:
            return img, ""
        keep = set(np.array(indexes).flatten().tolist())
        font = cv2.FONT_HERSHEY_PLAIN
        characters = []
        for i in range(len(boxes)):
            if i not in keep:
                continue
            x, y, w, h = boxes[i]
            label = str(self.classes[class_ids[i]])
            color = self.colors[i % len(self.colors)]
            cv2.rectangle(img, (x, y), (x + w, y + h), color, 3)
            confidence = round(confidences[i], 3) * 100
            cv2.putText(img, f"{confidence}%", (x, y - 6), font, 1, color, 2)
            characters.append((label, x))
        characters.sort(key=lambda x: x[1])
        tokens = [label for label, _ in characters]

        arabic_token = None
        arabic_index = None
        preferred = {"waw", "ch", "a", "b", "d", "h", "w"}
        for idx, token in enumerate(tokens):
            if token in preferred:
                arabic_token = token
                arabic_index = idx
                break

        if arabic_token is None or arabic_index is None:
            return img, "".join(tokens)

        token_to_index = {
            "a": ord("a"),
            "b": ord("b"),
            "d": ord("d"),
            "h": ord("h"),
            "w": ord("w"),
            "waw": ord("w"),
            "ch": ord("c") + ord("h"),
        }
        arabic_bytes = self.arabic_chars(token_to_index.get(arabic_token, 0))
        arabic_char = str(arabic_bytes, encoding="utf-8") if arabic_bytes else ""

        left = "".join(tokens[:arabic_index])
        right = "".join(tokens[arabic_index + 1 :])
        plate = f"{left} | {arabic_char} | {right}"
        return img, plate

    def arabic_chars(self, index):
        if index == ord("a"):
            return "أ".encode("utf-8")
        if index == ord("b"):
            return "ب".encode("utf-8")
        if index == 2 * ord("w") + ord("a") or index == ord("w"):
            return "و".encode("utf-8")
        if index == ord("d"):
            return "د".encode("utf-8")
        if index == ord("h"):
            return "ه".encode("utf-8")
        if index == ord("c") + ord("h"):
            return "ش".encode("utf-8")
        return b""

    def tesseract_ocr(self, image, lang="eng", psm=7):
        if not self.configure_tesseract():
            raise RuntimeError("Tesseract introuvable dans le conteneur.")
        alphanumeric = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        options = f"-l {lang} --psm {psm} -c tessedit_char_whitelist={alphanumeric}"
        return pytesseract.image_to_string(image, config=options)
