from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget, QGridLayout
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

class PreviewDialog(QDialog):
    def __init__(self, images, parent=None):
        super().__init__(parent)
        self.setWindowTitle("معاينة الصور")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)

        top_layout = QHBoxLayout()
        instructions = QLabel("انقر على الصور السالبة لقلبها")
        instructions.setAlignment(Qt.AlignCenter)
        top_layout.addWidget(instructions)

        self.convert_all_btn = QPushButton("قلب جميع الصور")
        self.convert_all_btn.setCheckable(True)
        self.convert_all_btn.clicked.connect(self.toggle_all_images)
        top_layout.addWidget(self.convert_all_btn)

        layout.addLayout(top_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.grid_layout = QGridLayout(scroll_widget)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("موافق")
        self.cancel_button = QPushButton("إلغاء")
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        self.preview_labels = []
        self.show_previews(images)

        self.all_converted = False

    def toggle_all_images(self):
        self.all_converted = not self.all_converted

        if self.all_converted:
            self.convert_all_btn.setText("إلغاء قلب الصور")
            for label in self.preview_labels:
                label.is_inverted = True
                label.update_image()
                label.setStyleSheet("border: 2px solid red; margin: 2px;")
        else:
            self.convert_all_btn.setText("قلب جميع الصور")
            for label in self.preview_labels:
                label.is_inverted = False
                label.update_image()
                label.setStyleSheet("border: 2px solid gray; margin: 2px;")

    def show_previews(self, images):
        cols = 4
        for i, image_bytes in enumerate(images):
            try:
                row = i // cols
                col = i % cols
                label = ImagePreviewLabel(image_bytes, i)
                self.grid_layout.addWidget(label, row, col)
                self.preview_labels.append(label)
            except Exception as e:
                print(f"Error creating preview for image {i}: {str(e)}")

    def get_inverted_indices(self):
        return [label.is_inverted for label in self.preview_labels]