# src/modules/image_extractor/widget.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QProgressBar, QButtonGroup, QRadioButton,
    QCheckBox, QSpinBox, QDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings
import os
import fitz
from pathlib import Path
from ..base_module import PDFModuleBase  # Import from the correct location
from .preview_dialog import PreviewDialog
from .image_saver import save_image
from .ppt_extractor import extract_to_ppt
from .image_extraction_thread import ImageExtractionThread


class ImageExtractorModule(PDFModuleBase):
    def __init__(self):
        super().__init__()
        self.init_variables()
        self.setup_ui()

    def init_variables(self):
        self.settings = QSettings("PDFExtractor", "ImageExtractor")
        self.last_directory = self.settings.value("last_directory", os.path.expanduser("~"))
        self.output_dir = os.path.join(os.path.expanduser("~"), "Documents")
        self.pdf_path = None
        self.extraction_thread = None
        self.preview_images = []
        self.inverted_indices = []

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)  # Now this works!

        # File selection
        file_layout = QHBoxLayout()
        self.file_label = QLabel("لم يتم اختيار ملف")
        self.browse_button = QPushButton("اختر ملف PDF")
        self.browse_button.clicked.connect(self.browse_file)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.browse_button)
        layout.addLayout(file_layout)

        # ... (rest of your setup_ui code remains the same) ...

        # Page range selection
        page_range_layout = QHBoxLayout()
        self.page_range_check = QCheckBox("تحديد نطاق الصفحات")
        self.page_range_check.stateChanged.connect(self.toggle_page_range)
        self.start_page_spin = QSpinBox()
        self.end_page_spin = QSpinBox()
        page_range_layout.addWidget(self.page_range_check)
        page_range_layout.addWidget(QLabel("من صفحة:"))
        page_range_layout.addWidget(self.start_page_spin)
        page_range_layout.addWidget(QLabel("إلى صفحة:"))
        page_range_layout.addWidget(self.end_page_spin)
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
        self.images_radio = QRadioButton("حفظ كصور منفصلة")
        self.ppt_radio.setChecked(True)
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

        # Output directory selection
        output_dir_layout = QHBoxLayout()
        self.output_dir_path = QLabel("المستندات")
        self.output_dir_button = QPushButton("اختر المجلد")
        self.output_dir_button.clicked.connect(self.select_output_dir)
        output_dir_layout.addWidget(QLabel("مجلد الحفظ:"))
        output_dir_layout.addWidget(self.output_dir_path)
        output_dir_layout.addWidget(self.output_dir_button)
        layout.addLayout(output_dir_layout)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "اختر ملف PDF", self.last_directory, "PDF files (*.pdf)"
        )

        if file_path:
            self.last_directory = os.path.dirname(file_path)
            self.settings.setValue("last_directory", self.last_directory)

            self.pdf_path = file_path
            self.file_label.setText(os.path.basename(file_path))

            try:
                doc = fitz.open(file_path)
                page_count = doc.page_count
                doc.close()

                self.start_page_spin.setMaximum(page_count)
                self.end_page_spin.setMaximum(page_count)
                self.end_page_spin.setValue(page_count)

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
            self.output_dir_path.setText(os.path.basename(dir_path))

    def start_preview(self):
        self.status_label.setText("جاري استخراج الصور للمعاينة...")
        self.progress_bar.setValue(0)

        start_page = self.start_page_spin.value() if self.page_range_check.isChecked() else 1
        end_page = self.end_page_spin.value() if self.page_range_check.isChecked() else None

        self.extraction_thread = ImageExtractionThread(
            pdf_path=self.pdf_path,
            output_dir=self.output_dir,
            start_page=start_page,
            end_page=end_page,
            preview_mode=True
        )
        self.extraction_thread.progress.connect(self.update_progress)
        self.extraction_thread.finished.connect(self.preview_complete)
        self.extraction_thread.start()

        self.preview_button.setEnabled(False)
        self.extract_button.setEnabled(False)
        self.status_label.setText("جارٍ تحميل المعاينة...")

    def start_extraction(self):
        if not self.pdf_path:
            return

        start_page = self.start_page_spin.value() - 1 if self.page_range_check.isChecked() else 0
        end_page = self.end_page_spin.value() if self.page_range_check.isChecked() else None

        self.extraction_thread = ImageExtractionThread(
            pdf_path=self.pdf_path,
            output_dir=self.output_dir,
            start_page=start_page,
            end_page=end_page,
            preview_mode=False,
            save_as_ppt=self.ppt_radio.isChecked()
        )
        self.extraction_thread.progress.connect(self.update_progress)
        self.extraction_thread.finished.connect(self.extraction_complete)
        self.extraction_thread.start()

        self.preview_button.setEnabled(False)
        self.extract_button.setEnabled(False)
        self.status_label.setText("جارٍ استخراج الصور...")

    def update_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def preview_complete(self, result):
        success, message, images = result
        if success:
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

    def extraction_complete(self, result):
        self.preview_button.setEnabled(True)
        self.extract_button.setEnabled(True)
        success, message, count = result
        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText(message)
        else:
            self.progress_bar.setValue(0)
            self.status_label.setText(message)

    def toggle_page_range(self, state):
        enabled = bool(state)
        self.start_page_spin.setEnabled(enabled)
        self.end_page_spin.setEnabled(enabled)

    # Implement abstract methods
    def get_description(self):
        return "Extract images from PDF files."

    def get_name(self):
        return "Image Extractor"

    def get_widget(self):
        return self