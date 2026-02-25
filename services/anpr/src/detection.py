from pathlib import Path

import cv2
import numpy as np

BASE_DIR = Path(__file__).resolve().parent


class PlateDetector:
    def load_model(self, weight_path: str, cfg_path: str, classes_path: str | None = None) -> None:
        self.net = cv2.dnn.readNet(weight_path, cfg_path)
        classes_file = Path(classes_path) if classes_path else BASE_DIR / "classes-detection.names"
        with classes_file.open("r", encoding="utf-8") as handle:
            self.classes = [line.strip() for line in handle.readlines() if line.strip()]
        self.layers_names = self.net.getLayerNames()
        out_layers = np.array(self.net.getUnconnectedOutLayers()).flatten()
        self.output_layers = [self.layers_names[int(i) - 1] for i in out_layers]

    def load_image(self, img_path: str):
        img = cv2.imread(img_path)
        if img is None:
            raise RuntimeError(f"Unable to read image: {img_path}")
        height, width, channels = img.shape
        return img, height, width, channels

    def detect_plates(self, img):
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
            for detection in output:
                scores = detection[5:]
                class_id = int(np.argmax(scores))
                confidence = float(scores[class_id])
                if confidence > threshold:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    boxes.append([x, y, w, h])
                    confidences.append(confidence)
                    class_ids.append(class_id)
        return boxes, confidences, class_ids

    def draw_labels(self, boxes, confidences, class_ids, img):
        indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.1, 0.1)
        if len(indexes) == 0:
            return img, []
        keep = set(np.array(indexes).flatten().tolist())
        font = cv2.FONT_HERSHEY_PLAIN
        plates = []
        h_img, w_img = img.shape[:2]
        for i in range(len(boxes)):
            if i not in keep:
                continue
            x, y, w, h = boxes[i]
            x1 = max(0, x)
            y1 = max(0, y)
            x2 = min(w_img, x + w)
            y2 = min(h_img, y + h)
            crop_img = img[y1:y2, x1:x2]
            try:
                crop_resized = cv2.resize(crop_img, dsize=(470, 110))
                plates.append(crop_resized)
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 8)
                confidence = round(confidences[i], 3) * 100
                cv2.putText(img, f"{confidence}%", (x1 + 20, max(20, y1 - 20)), font, 12, (0, 255, 0), 6)
            except cv2.error:
                continue
        return img, plates
