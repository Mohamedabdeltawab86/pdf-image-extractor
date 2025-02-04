from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QProgressBar,
    QMenuBar,
    QMenu,
    QAction,
    QFontDialog,
    QMessageBox,
    QStyle,
    QFrame,
    QGraphicsDropShadowEffect,
    QRadioButton,
    QButtonGroup,
    QScrollArea,
    QGridLayout,
    QDialog,
    QCheckBox,
    QSpinBox,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDir, QSettings
from PyQt5.QtGui import QIcon, QFont, QFontDatabase, QPalette, QColor, QPixmap, QImage
import qtawesome as qta  # For better icons, install with: pip install qtawesome
from pathlib import Path
from ..core.pdf_processor import extract_images_from_pdf
from ..util.settings import Settings
from ..util.translations import Translations
from . import resources_rc  # Change this line
from pptx import Presentation
from pptx.util import Inches
import fitz
from ..util.image_handler import save_image, extract_to_ppt, ImageExtractionThread
import io
from PIL import Image
import os


class ExtractionWorker(QThread):
    """Worker thread for PDF processing to keep UI responsive"""

    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, pdf_path, output_dir, should_invert, export_to_ppt):
        super().__init__()
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.should_invert = should_invert
        self.export_to_ppt = export_to_ppt
        self._is_running = True

    def run(self):
        try:
            doc = fitz.open(self.pdf_path)
            images = []
            image_count = 0
            total_images = 0

            # First count total images
            for page in doc:
                total_images += len(page.get_images())

            for page_num in range(len(doc)):
                if not self._is_running:
                    doc.close()
                    return

                page = doc[page_num]
                image_list = page.get_images()

                for img_index, img in enumerate(image_list):
                    if not self._is_running:
                        doc.close()
                        return

                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]

                        if self.export_to_ppt:
                            images.append(image_bytes)
                        else:
                            # Save as individual files
                            image_filename = f"image_{image_count:04d}.jpg"
                            save_image(
                                image_bytes,
                                self.output_dir,
                                image_filename,
                                self.should_invert,
                            )

                        image_count += 1
                        self.progress.emit(image_count, total_images)

                    except Exception as e:
                        print(f"Error processing image: {str(e)}")
                        continue

            if self.export_to_ppt and self._is_running and images:
                # Create PowerPoint with all images
                extract_to_ppt(images, self.output_dir, self.should_invert)

            doc.close()
            if self._is_running:
                self.finished.emit(image_count)

        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self._is_running = False


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
            # Invert the image
            if img.mode != "RGB":
                img = img.convert("RGB")
            img = Image.eval(img, lambda x: 255 - x)

        # Convert PIL image to QPixmap
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

        # Instructions and buttons layout
        top_layout = QHBoxLayout()

        # Instructions label
        instructions = QLabel("انقر على الصور السالبة لقلبها")
        instructions.setAlignment(Qt.AlignCenter)
        top_layout.addWidget(instructions)

        # Convert All button
        self.convert_all_btn = QPushButton("قلب جميع الصور")
        self.convert_all_btn.setCheckable(True)  # Make button toggleable
        self.convert_all_btn.clicked.connect(self.toggle_all_images)
        top_layout.addWidget(self.convert_all_btn)

        layout.addLayout(top_layout)

        # Scroll area for images
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.grid_layout = QGridLayout(scroll_widget)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("موافق")
        self.cancel_button = QPushButton("إلغاء")
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        # Connect buttons
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        # Show images
        self.preview_labels = []
        self.show_previews(images)

        # Track the state of all images
        self.all_converted = False

    def toggle_all_images(self):
        self.all_converted = not self.all_converted

        if self.all_converted:
            # Convert all images
            self.convert_all_btn.setText("إلغاء قلب الصور")
            for label in self.preview_labels:
                label.is_inverted = True
                label.update_image()
                label.setStyleSheet("border: 2px solid red; margin: 2px;")
        else:
            # Revert all images
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Image Extractor")
        self.setMinimumWidth(400)

        # Initialize settings
        self.settings = QSettings("PDFExtractor", "ImageExtractor")
        self.last_directory = self.settings.value(
            "last_directory", os.path.expanduser("~")
        )

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # File selection
        file_layout = QHBoxLayout()
        self.file_label = QLabel("لم يتم اختيار ملف")
        self.browse_button = QPushButton("اختر ملف PDF")
        self.browse_button.clicked.connect(self.browse_file)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.browse_button)
        layout.addLayout(file_layout)

        # Page range selection
        page_range_layout = QHBoxLayout()
        self.page_range_check = QCheckBox("تحديد نطاق الصفحات")
        self.page_range_check.stateChanged.connect(self.toggle_page_range)
        page_range_layout.addWidget(self.page_range_check)

        self.start_page_label = QLabel("من صفحة:")
        self.start_page_spin = QSpinBox()
        self.start_page_spin.setMinimum(1)
        self.start_page_spin.setEnabled(False)

        self.end_page_label = QLabel("إلى صفحة:")
        self.end_page_spin = QSpinBox()
        self.end_page_spin.setMinimum(1)
        self.end_page_spin.setEnabled(False)

        page_range_layout.addWidget(self.start_page_label)
        page_range_layout.addWidget(self.start_page_spin)
        page_range_layout.addWidget(self.end_page_label)
        page_range_layout.addWidget(self.end_page_spin)
        page_range_layout.addStretch()
        layout.addLayout(page_range_layout)

        # Preview button
        self.preview_button = QPushButton("معاينة")
        self.preview_button.clicked.connect(self.start_preview)
        self.preview_button.setEnabled(False)
        layout.addWidget(self.preview_button)

        # Output type selection
        output_layout = QHBoxLayout()
        self.output_group = QButtonGroup()

        self.ppt_radio = QRadioButton("حفظ كعرض تقديمي")
        self.ppt_radio.setChecked(True)
        self.images_radio = QRadioButton("حفظ كصور منفصلة")

        self.output_group.addButton(self.ppt_radio)
        self.output_group.addButton(self.images_radio)

        output_layout.addWidget(self.ppt_radio)
        output_layout.addWidget(self.images_radio)
        layout.addLayout(output_layout)

        # Extract button
        self.extract_button = QPushButton("استخراج الصور")
        self.extract_button.clicked.connect(self.start_extraction)
        self.extract_button.setEnabled(False)
        layout.addWidget(self.extract_button)

        # Progress bar
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # Add output directory selection
        output_dir_layout = QHBoxLayout()
        self.output_dir_label = QLabel("مجلد الحفظ:")
        self.output_dir_path = QLabel("المستندات")
        self.output_dir_button = QPushButton("اختر المجلد")
        self.output_dir_button.clicked.connect(self.select_output_dir)

        output_dir_layout.addWidget(self.output_dir_label)
        output_dir_layout.addWidget(self.output_dir_path)
        output_dir_layout.addWidget(self.output_dir_button)
        layout.addLayout(output_dir_layout)

        # Initialize output directory to Documents folder
        self.output_dir = os.path.join(os.path.expanduser("~"), "Documents")

        self.pdf_path = None
        self.extraction_thread = None
        self.preview_images = []
        self.inverted_indices = []

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "اختر ملف PDF", self.last_directory, "PDF files (*.pdf)"
        )

        if file_path:
            # Save the new directory
            self.last_directory = os.path.dirname(file_path)
            self.settings.setValue("last_directory", self.last_directory)

            self.pdf_path = file_path
            self.file_label.setText(os.path.basename(file_path))

            # Update page range spinners with PDF page count
            try:
                doc = fitz.open(file_path)
                page_count = doc.page_count
                doc.close()

                self.start_page_spin.setMaximum(page_count)
                self.end_page_spin.setMaximum(page_count)
                self.end_page_spin.setValue(page_count)

                # Enable preview button
                self.preview_button.setEnabled(True)
                self.extract_button.setEnabled(False)
                self.status_label.setText("اختر نطاق الصفحات ثم اضغط معاينة")
            except Exception as e:
                print(f"Error getting page count: {str(e)}")

    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "اختر مجلد الحفظ", self.output_dir
        )
        if dir_path:
            self.output_dir = dir_path
            # Show only the last folder name in the label
            self.output_dir_path.setText(os.path.basename(dir_path))

    def start_preview(self):
        self.status_label.setText("جاري استخراج الصور للمعاينة...")
        self.progress_bar.setValue(0)

        # Get page range
        start_page = (
            self.start_page_spin.value() if self.page_range_check.isChecked() else 1
        )
        end_page = (
            self.end_page_spin.value() if self.page_range_check.isChecked() else None
        )

        # Start extraction thread for preview
        self.extraction_thread = ImageExtractionThread(
            pdf_path=self.pdf_path,
            output_dir=self.output_dir,  # Use selected output directory
            start_page=start_page,
            end_page=end_page,
            options={"preview_only": True},
        )
        self.extraction_thread.progress.connect(self.update_progress)
        self.extraction_thread.finished.connect(self.show_preview_dialog)
        self.extraction_thread.start()

    def show_preview_dialog(self, result):
        success, message, images = result
        if success and images:
            dialog = PreviewDialog(images, self)
            if dialog.exec_() == QDialog.Accepted:
                self.preview_images = images
                self.inverted_indices = dialog.get_inverted_indices()
                self.extract_button.setEnabled(True)
                self.status_label.setText("تم تحديد الصور للاستخراج")
            else:
                self.status_label.setText("تم إلغاء المعاينة")
                self.extract_button.setEnabled(False)
        else:
            self.status_label.setText(message)
            self.extract_button.setEnabled(False)

    def start_extraction(self):
        if not self.pdf_path or not self.preview_images:
            return

        self.extract_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("جاري استخراج الصور...")

        # Get page range
        start_page = (
            self.start_page_spin.value() if self.page_range_check.isChecked() else 1
        )
        end_page = (
            self.end_page_spin.value() if self.page_range_check.isChecked() else None
        )

        self.extraction_thread = ImageExtractionThread(
            pdf_path=self.pdf_path,
            output_dir=self.output_dir,  # Use selected output directory
            start_page=start_page,
            end_page=end_page,
            options={
                "output_type": "pptx" if self.ppt_radio.isChecked() else "images",
                "inverted_indices": self.inverted_indices,
                "preview_images": self.preview_images,
            },
        )

        self.extraction_thread.progress.connect(self.update_progress)
        self.extraction_thread.finished.connect(self.extraction_complete)
        self.extraction_thread.start()

    def update_progress(self, current, total):
        percentage = (current / total) * 100
        self.progress_bar.setValue(int(percentage))
        self.status_label.setText(f"جاري المعالجة... {current}/{total}")

    def extraction_complete(self, result):
        success, message, count = result
        self.extract_button.setEnabled(True)

        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText(message)  # Just show the message directly
        else:
            self.progress_bar.setValue(0)
            self.status_label.setText(message)  # Error messages already formatted

    def toggle_page_range(self, state):
        enabled = bool(state)
        self.start_page_spin.setEnabled(enabled)
        self.end_page_spin.setEnabled(enabled)
