from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt
from PIL import Image
import io
from PyQt5.QtGui import QPixmap, QImage

class ImagePreviewLabel(QLabel):
    def __init__(self, image_bytes, index):
        super().__init__()
        self.image_bytes = image_bytes
        self.index = index
        self.is_inverted = False
        self.setFixedSize(200, 200)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border: 2px solid gray; margin: 2px;")
        self.setScaledContents(True)
        self.update_image()
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("انقر للقلب")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_inverted = not self.is_inverted
            self.update_image()
            self.setStyleSheet(
                f"border: 2px solid {'red' if self.is_inverted else 'gray'}; margin: 2px;"
            )

    def update_image(self):
        img = Image.open(io.BytesIO(self.image_bytes))
        if self.is_inverted:
            if img.mode != "RGB":
                img = img.convert("RGB")
            img = Image.eval(img, lambda x: 255 - x)

        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format="PNG")
        img_byte_arr = img_byte_arr.getvalue()

        image = QImage.fromData(img_byte_arr)
        pixmap = QPixmap.fromImage(image)
        self.setPixmap(
            pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )