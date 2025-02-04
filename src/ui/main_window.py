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
    QTabWidget,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QComboBox,
    QScrollArea,
    QTextEdit,
    QSplitter,
    QToolTip,
    QListWidget,
    QGroupBox,
    QSlider,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDir, QTimer, QSize
from PyQt5.QtGui import QIcon, QFont, QFontDatabase, QPalette, QColor, QImage, QPixmap
import qtawesome as qta  # For better icons, install with: pip install qtawesome
from pathlib import Path
from ..core.pdf_processor import extract_images_from_pdf
from ..util.settings import Settings
from ..util.translations import Translations
from . import resources_rc  # Change this line
from pptx import Presentation
from pptx.util import Inches
import fitz
from ..util.image_handler import save_image, extract_to_ppt
from datetime import datetime
import os
from ..util.pdf_tools import PDFTools


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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.pdf_tools = PDFTools()
        self.current_language = self.settings.get_language()

        # Initialize font
        self.init_font()

        # Setup window properties
        self.setWindowTitle("تطبيق معالجة ملفات PDF")
        self.setMinimumSize(1200, 800)

        # Fix window icon - explicit path
        self.setWindowIcon(QIcon(":/icons/logo.png"))

        # Force RTL for title bar
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint)

        # Set window style with lighter, more transparent gradient
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f8fafc;
            }
            QTabWidget::pane {
                border: none;
                background: white;
                border-radius: 15px;
                margin: 20px;
            }
            QTabBar::tab {
                padding: 12px 30px;
                margin: 0px 2px;
                color: #64748b;
                border: none;
                background: #f1f5f9;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QTabBar::tab:selected {
                color: #4F46E5;
                background: white;
                font-weight: bold;
            }
            QPushButton {
                background: #4F46E5;
                color: white;
                border: none;
                padding: 12px 25px;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #4338CA;
            }
            QLineEdit {
                padding: 12px;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                background: white;
            }
            QLabel {
                color: #1e293b;
                font-size: 14px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #e2e8f0;
                height: 8px;
                background: #f1f5f9;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4F46E5;
                border: none;
                width: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }
        """
        )

        # Initialize variables
        self.pdf_path = None
        self.output_dir = None

        # Set up the UI
        self.setup_ui()

    def init_font(self):
        """Initialize and load the Arabic font"""
        # Print available fonts for debugging
        print("Available fonts:", QFontDatabase().families())

        # Load the custom font
        font_id = QFontDatabase.addApplicationFont(":/fonts/Cairo-Regular.ttf")
        if font_id != -1:
            print("Font loaded successfully")
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            print("Font family:", font_family)
            self.font = QFont(font_family, 12)
        else:
            print("Error loading font, using system Arabic font")
            self.font = QFont("Arial", 12)

        # Set the font
        self.setFont(self.font)

    def setup_ui(self):
        # Create central widget with main frame
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Add tabs
        self.tab_widget.addTab(self.create_image_tab(), "استخراج الصور")
        self.tab_widget.addTab(self.create_bookmark_tab(), "إضافة العناوين")
        self.tab_widget.addTab(self.create_extract_tab(), "استخراج العناوين")
        self.tab_widget.addTab(self.create_text_tab(), "استخراج النص")
        self.tab_widget.addTab(self.create_split_tab(), "تقسيم الملف")
        self.tab_widget.addTab(self.create_merge_tab(), "دمج الملفات")

        # Set RTL layout
        self.setLayoutDirection(Qt.RightToLeft)

    def create_image_tab(self):
        widget = QWidget()

        # Create horizontal splitter for preview
        splitter = QSplitter(Qt.Horizontal)

        # Left side - Controls
        left_widget = QWidget()
        layout = QVBoxLayout(left_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # PDF selection with preview button
        pdf_layout = QHBoxLayout()
        self.pdf_path_image = QLineEdit()
        self.pdf_path_image.setPlaceholderText("اختر ملف PDF...")
        btn_select_pdf = QPushButton(qta.icon("fa5s.file-pdf"), "تصفح")
        btn_preview = QPushButton(qta.icon("fa5s.eye"), "معاينة")
        btn_select_pdf.clicked.connect(self.select_pdf_image)
        btn_preview.clicked.connect(self.update_preview)
        pdf_layout.addWidget(btn_preview)
        pdf_layout.addWidget(btn_select_pdf)
        pdf_layout.addWidget(self.pdf_path_image)
        layout.addLayout(pdf_layout)

        # Page range with spinboxes and sliders
        range_frame = QFrame()
        range_frame.setStyleSheet(
            "QFrame { background: #f8fafc; border-radius: 8px; padding: 10px; }"
        )
        range_layout = QVBoxLayout(range_frame)

        self.all_pages_checkbox = QCheckBox("كل الصفحات")
        self.all_pages_checkbox.setChecked(True)
        self.all_pages_checkbox.stateChanged.connect(self.toggle_page_range)

        range_controls = QHBoxLayout()
        self.page_start_image = QSpinBox()
        self.page_end_image = QSpinBox()

        self.page_start_image.setPrefix("من: ")
        self.page_end_image.setPrefix("إلى: ")
        self.page_start_image.setMinimum(1)
        self.page_end_image.setMinimum(1)

        # Add sliders
        slider_layout = QHBoxLayout()
        self.start_slider = QSlider(Qt.Horizontal)
        self.end_slider = QSlider(Qt.Horizontal)

        # Connect sliders and spinboxes
        self.start_slider.valueChanged.connect(self.page_start_image.setValue)
        self.end_slider.valueChanged.connect(self.page_end_image.setValue)
        self.page_start_image.valueChanged.connect(self.start_slider.setValue)
        self.page_end_image.valueChanged.connect(self.end_slider.setValue)

        slider_layout.addWidget(self.start_slider)
        slider_layout.addWidget(self.end_slider)

        range_controls.addWidget(self.page_end_image)
        range_controls.addWidget(self.page_start_image)

        range_layout.addWidget(self.all_pages_checkbox)
        range_layout.addLayout(range_controls)
        range_layout.addLayout(slider_layout)
        layout.addWidget(range_frame)

        # Extraction options in a grouped frame
        options_frame = QFrame()
        options_frame.setStyleSheet(
            "QFrame { background: #f8fafc; border-radius: 8px; padding: 10px; }"
        )
        options_layout = QVBoxLayout(options_frame)

        # Output format
        format_group = QGroupBox("صيغة الإخراج")
        format_layout = QVBoxLayout()
        self.files_radio = QRadioButton("ملفات منفصلة")
        self.ppt_radio = QRadioButton("عرض تقديمي")
        self.pdf_radio = QRadioButton("ملف PDF جديد")
        self.files_radio.setChecked(True)
        format_layout.addWidget(self.files_radio)
        format_layout.addWidget(self.ppt_radio)
        format_layout.addWidget(self.pdf_radio)
        format_group.setLayout(format_layout)
        options_layout.addWidget(format_group)

        # Image options
        image_options = QGroupBox("خيارات الصور")
        image_layout = QVBoxLayout()

        self.invert_checkbox = QCheckBox("عكس الألوان")
        self.enhance_checkbox = QCheckBox("تحسين جودة الصور")
        self.remove_bg_checkbox = QCheckBox("إزالة الخلفية")

        self.dpi_combo = QComboBox()
        self.dpi_combo.addItems(["72 DPI", "150 DPI", "300 DPI", "600 DPI"])
        self.dpi_combo.setCurrentText("300 DPI")

        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "JPEG", "TIFF", "BMP"])

        image_layout.addWidget(self.invert_checkbox)
        image_layout.addWidget(self.enhance_checkbox)
        image_layout.addWidget(self.remove_bg_checkbox)
        image_layout.addWidget(QLabel("دقة الصور:"))
        image_layout.addWidget(self.dpi_combo)
        image_layout.addWidget(QLabel("صيغة الصور:"))
        image_layout.addWidget(self.format_combo)
        image_options.setLayout(image_layout)
        options_layout.addWidget(image_options)

        layout.addWidget(options_frame)

        # Progress section
        progress_frame = QFrame()
        progress_frame.setStyleSheet(
            "QFrame { background: #f8fafc; border-radius: 8px; padding: 10px; }"
        )
        progress_layout = QVBoxLayout(progress_frame)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: none;
                border-radius: 5px;
                background: #e2e8f0;
                text-align: center;
            }
            QProgressBar::chunk {
                background: #4F46E5;
                border-radius: 5px;
            }
        """
        )

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #4F46E5;")

        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        layout.addWidget(progress_frame)

        # Action buttons
        button_layout = QHBoxLayout()
        self.extract_button = QPushButton(qta.icon("fa5s.images"), "استخراج الصور")
        self.stop_button = QPushButton(qta.icon("fa5s.stop"), "إيقاف")
        self.extract_button.clicked.connect(self.start_extraction)
        self.stop_button.clicked.connect(self.stop_extraction)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.extract_button)
        layout.addLayout(button_layout)

        # Right side - Preview
        right_widget = QWidget()
        preview_layout = QVBoxLayout(right_widget)
        preview_layout.setContentsMargins(20, 20, 20, 20)

        self.preview_label = QLabel("معاينة الصفحة")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidget(self.preview_label)
        self.preview_scroll.setWidgetResizable(True)
        preview_layout.addWidget(self.preview_scroll)

        # Add widgets to splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        # Main layout
        main_layout = QVBoxLayout(widget)
        main_layout.addWidget(splitter)

        return widget

    def create_bookmark_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # PDF selection
        pdf_layout = QHBoxLayout()
        self.pdf_path_bookmark = QLineEdit()
        self.pdf_path_bookmark.setPlaceholderText("اختر ملف PDF...")
        btn_select_pdf = QPushButton("تصفح")
        btn_select_pdf.clicked.connect(self.select_pdf_bookmark)
        pdf_layout.addWidget(btn_select_pdf)
        pdf_layout.addWidget(self.pdf_path_bookmark)
        layout.addLayout(pdf_layout)

        # Bookmarks file selection
        bookmarks_layout = QHBoxLayout()
        self.bookmarks_path = QLineEdit()
        self.bookmarks_path.setPlaceholderText("اختر ملف العناوين...")
        btn_select_bookmarks = QPushButton("تصفح")
        btn_select_bookmarks.clicked.connect(self.select_bookmarks)
        bookmarks_layout.addWidget(btn_select_bookmarks)
        bookmarks_layout.addWidget(self.bookmarks_path)
        layout.addLayout(bookmarks_layout)

        # Add bookmarks button
        btn_add = QPushButton("إضافة العناوين")
        btn_add.clicked.connect(self.add_bookmarks)
        layout.addWidget(btn_add)

        # Status label
        self.status_label_bookmark = QLabel()
        layout.addWidget(self.status_label_bookmark)

        layout.addStretch()
        return widget

    def create_extract_tab(self):
        # Implementation of create_extract_tab method
        pass

    def create_text_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # PDF selection with icon
        pdf_layout = QHBoxLayout()
        self.pdf_path_text = QLineEdit()
        self.pdf_path_text.setPlaceholderText("اختر ملف PDF...")
        btn_select_pdf = QPushButton(qta.icon("fa5s.file-pdf"), "تصفح")
        btn_select_pdf.clicked.connect(self.select_pdf_text)
        pdf_layout.addWidget(btn_select_pdf)
        pdf_layout.addWidget(self.pdf_path_text)
        layout.addLayout(pdf_layout)

        # Page range with modern spinboxes
        range_layout = QHBoxLayout()
        self.page_start = QSpinBox()
        self.page_end = QSpinBox()
        self.page_start.setPrefix("من صفحة: ")
        self.page_end.setPrefix("إلى صفحة: ")
        self.page_start.setMinimum(1)
        self.page_end.setMinimum(1)
        range_layout.addWidget(self.page_end)
        range_layout.addWidget(self.page_start)
        layout.addLayout(range_layout)

        # Text options
        options_layout = QHBoxLayout()
        self.remove_linebreaks = QCheckBox("إزالة فواصل الأسطر")
        self.include_images = QCheckBox("تضمين النص من الصور")
        options_layout.addWidget(self.include_images)
        options_layout.addWidget(self.remove_linebreaks)
        layout.addLayout(options_layout)

        # Preview area
        self.text_preview = QTextEdit()
        self.text_preview.setPlaceholderText("معاينة النص المستخرج...")
        self.text_preview.setReadOnly(True)
        layout.addWidget(self.text_preview)

        # Action buttons with progress
        action_layout = QHBoxLayout()
        self.extract_progress = QProgressBar()
        self.extract_progress.setVisible(False)
        btn_extract = QPushButton(qta.icon("fa5s.file-export"), "استخراج النص")
        btn_extract.clicked.connect(self.extract_text)
        btn_copy = QPushButton(qta.icon("fa5s.copy"), "نسخ النص")
        btn_copy.clicked.connect(self.copy_text)
        action_layout.addWidget(self.extract_progress)
        action_layout.addWidget(btn_copy)
        action_layout.addWidget(btn_extract)
        layout.addLayout(action_layout)

        return widget

    def create_split_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # PDF selection
        pdf_layout = QHBoxLayout()
        self.pdf_path_split = QLineEdit()
        self.pdf_path_split.setPlaceholderText("اختر ملف PDF...")
        btn_select_pdf = QPushButton(qta.icon("fa5s.file-pdf"), "تصفح")
        btn_select_pdf.clicked.connect(self.select_pdf_split)
        pdf_layout.addWidget(btn_select_pdf)
        pdf_layout.addWidget(self.pdf_path_split)
        layout.addLayout(pdf_layout)

        # Split options
        options_layout = QHBoxLayout()
        self.split_method = QComboBox()
        self.split_method.addItems(
            ["تقسيم حسب العناوين", "تقسيم حسب عدد الصفحات", "تقسيم حسب صفحات محددة"]
        )
        self.split_method.currentIndexChanged.connect(self.update_split_options)
        options_layout.addWidget(self.split_method)
        layout.addLayout(options_layout)

        # Split settings (dynamic based on method)
        self.split_settings = QWidget()
        self.split_settings_layout = QVBoxLayout(self.split_settings)
        layout.addWidget(self.split_settings)

        # Progress and action
        self.split_progress = QProgressBar()
        self.split_progress.setVisible(False)
        btn_split = QPushButton(qta.icon("fa5s.cut"), "تقسيم الملف")
        btn_split.clicked.connect(self.split_pdf)
        layout.addWidget(self.split_progress)
        layout.addWidget(btn_split)

        return widget

    def create_merge_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # PDF list
        self.pdf_list = QListWidget()
        self.pdf_list.setDragDropMode(QListWidget.InternalMove)
        layout.addWidget(self.pdf_list)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_add = QPushButton(qta.icon("fa5s.plus"), "إضافة ملف")
        btn_remove = QPushButton(qta.icon("fa5s.minus"), "إزالة الملف")
        btn_clear = QPushButton(qta.icon("fa5s.trash"), "مسح القائمة")
        btn_add.clicked.connect(self.add_pdf_to_merge)
        btn_remove.clicked.connect(self.remove_pdf_from_merge)
        btn_clear.clicked.connect(self.clear_merge_list)
        btn_layout.addWidget(btn_clear)
        btn_layout.addWidget(btn_remove)
        btn_layout.addWidget(btn_add)
        layout.addLayout(btn_layout)

        # Merge options
        options_layout = QHBoxLayout()
        self.merge_bookmarks = QCheckBox("دمج العناوين")
        self.merge_outline = QCheckBox("إنشاء فهرس")
        options_layout.addWidget(self.merge_outline)
        options_layout.addWidget(self.merge_bookmarks)
        layout.addLayout(options_layout)

        # Progress and action
        self.merge_progress = QProgressBar()
        self.merge_progress.setVisible(False)
        btn_merge = QPushButton(qta.icon("fa5s.object-group"), "دمج الملفات")
        btn_merge.clicked.connect(self.merge_pdfs)
        layout.addWidget(self.merge_progress)
        layout.addWidget(btn_merge)

        return widget

    def setup_menubar(self):
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu(Translations.get("file", self.current_language))

        # Settings Action
        settings_action = QAction(
            QIcon(":/icons/settings_icon.png"),
            Translations.get("settings", self.current_language),
            self,
        )
        settings_action.triggered.connect(self.show_settings)
        file_menu.addAction(settings_action)

        # About Action
        about_action = QAction(Translations.get("about", self.current_language), self)
        about_action.triggered.connect(self.show_about)
        file_menu.addAction(about_action)

    def show_settings(self):
        from .settings_dialog import SettingsDialog

        dialog = SettingsDialog(self)
        if dialog.exec_():
            self.reload_ui()

    def show_about(self):
        QMessageBox.about(
            self,
            Translations.get("about", self.current_language),
            "Dr. Waleed's PDF Image Extractor\nVersion 1.0",
        )

    def reload_ui(self):
        self.current_language = self.settings.get_language()
        font = QFont(self.font.family(), self.settings.get_font_size())
        self.setFont(font)
        self.retranslate_ui()

    def retranslate_ui(self):
        # Update all text elements with new language
        self.setWindowTitle(Translations.get("app_title", self.current_language))
        # ... update other UI elements

    def get_button_style(self, primary=False, warning=False, hover=False):
        """Get button style with hover effect"""
        if primary:
            base_color = "#1976D2" if hover else "#2196F3"
            return f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {base_color}, stop:1 #1565C0);
                    color: white;
                    border: none;
                    padding: 15px 30px;
                    border-radius: 12px;
                    font-weight: bold;
                    font-size: 18px;
                }}
                QPushButton:disabled {{
                    background: #BDC3C7;
                }}
            """
        elif warning:
            base_color = "#c0392b" if hover else "#e74c3c"
            return f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {base_color}, stop:1 #c0392b);
                    color: white;
                    border: none;
                    padding: 15px 30px;
                    border-radius: 12px;
                    font-weight: bold;
                    font-size: 18px;
                }}
                QPushButton:disabled {{
                    background: #BDC3C7;
                }}
            """
        else:
            opacity = "0.95" if hover else "0.85"
            return f"""
                QPushButton {{
                    background: rgba(255, 255, 255, {opacity});
                    border: 2px solid rgba(25, 118, 210, 0.2);
                    padding: 15px 30px;
                    border-radius: 12px;
                    font-size: 16px;
                    color: #1976D2;
                }}
            """

    def select_pdf(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "اختيار ملف PDF", "", "PDF Files (*.pdf)"
        )
        if file_name:
            self.pdf_path = file_name
            self.pdf_label.setText(Path(file_name).name)
            self.update_extract_button()

    def select_output(self):
        dir_name = QFileDialog.getExistingDirectory(self, "اختيار مجلد الحفظ")
        if dir_name:
            self.output_dir = dir_name
            self.output_label.setText(Path(dir_name).name)
            self.update_extract_button()

    def update_extract_button(self):
        self.extract_button.setEnabled(bool(self.pdf_path and self.output_dir))

    def start_extraction(self):
        """Start image extraction with page range"""
        pdf_path = self.pdf_path_image.text()
        if not pdf_path:
            QMessageBox.warning(self, "تنبيه", "الرجاء اختيار ملف PDF أولاً")
            return

        # Get page range
        if self.all_pages_checkbox.isChecked():
            start_page = 1
            doc = fitz.open(pdf_path)
            end_page = doc.page_count
            doc.close()
        else:
            start_page = self.page_start_image.value()
            end_page = self.page_end_image.value()

        if start_page > end_page:
            QMessageBox.warning(
                self,
                "خطأ",
                "رقم صفحة البداية يجب أن يكون أقل من أو يساوي رقم صفحة النهاية",
            )
            return

        # Collect all options
        options = {
            "output_type": "pptx" if self.ppt_radio.isChecked() else "files",
            "invert": self.invert_checkbox.isChecked(),
            "enhance": (
                self.enhance_checkbox.isChecked()
                if hasattr(self, "enhance_checkbox")
                else False
            ),
            "remove_bg": (
                self.remove_bg_checkbox.isChecked()
                if hasattr(self, "remove_bg_checkbox")
                else False
            ),
            "dpi": (
                int(self.dpi_combo.currentText().split()[0])
                if hasattr(self, "dpi_combo")
                else 300
            ),
            "format": (
                self.format_combo.currentText()
                if hasattr(self, "format_combo")
                else "PNG"
            ),
        }

        # Start extraction
        self.extract_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("جاري استخراج الصور...")

        # Create worker thread with options
        self.extraction_thread = ExtractionWorker(
            pdf_path,
            self.settings.get_default_output_dir(),
            options["invert"],
            options["output_type"] == "pptx",
        )

        # Connect signals
        self.extraction_thread.progress.connect(self.update_progress)
        self.extraction_thread.finished.connect(self.extraction_complete)
        self.extraction_thread.error.connect(self.extraction_error)
        self.extraction_thread.start()

    def stop_extraction(self):
        """Stop the extraction process"""
        if hasattr(self, "extraction_thread") and self.extraction_thread.isRunning():
            self.extraction_thread.stop()
            self.extraction_thread.wait()
            self.status_label.setText("تم إيقاف العملية")
            self.extract_button.setEnabled(True)
            self.stop_button.setEnabled(False)

    def update_progress(self, progress_info):
        """Update progress with detailed information"""
        try:
            if isinstance(progress_info, tuple):
                current, total, message = progress_info
                if total > 0:  # Prevent division by zero
                    percentage = min(int((current / total) * 100), 100)
                    self.progress_bar.setValue(percentage)
                    self.status_label.setText(message)
                else:
                    self.status_label.setText(message)
            else:
                # Handle simple percentage updates
                percentage = min(int(progress_info), 100)
                self.progress_bar.setValue(percentage)
                self.status_label.setText(f"جاري المعالجة... {percentage}%")
        except Exception as e:
            print(f"Error updating progress: {str(e)}")
            self.status_label.setText("جاري المعالجة...")

    def extraction_complete(self, result):
        """Handle extraction completion"""
        success, message, count = result
        self.extract_button.setEnabled(True)
        self.stop_button.setEnabled(False)

        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText(f"تم استخراج {count} صورة بنجاح")

            # Clear progress after a short delay
            QTimer.singleShot(2000, lambda: self.progress_bar.setValue(0))

            # Show success message
            QMessageBox.information(
                self, "اكتمال العملية", f"تم استخراج {count} صورة بنجاح\n{message}"
            )
        else:
            self.progress_bar.setValue(0)
            self.status_label.setText(message)
            QMessageBox.warning(self, "خطأ", message)

    def extraction_error(self, error_message):
        self.progress_bar.setValue(0)
        self.status_label.setText(f"خطأ: {error_message}")
        self.extract_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def button_hover_effect(self, button, hover, primary=False, warning=False):
        """Add hover effect to buttons"""
        if primary:
            button.setStyleSheet(self.get_button_style(primary=True, hover=hover))
        elif warning:
            button.setStyleSheet(self.get_button_style(warning=True, hover=hover))
        else:
            button.setStyleSheet(self.get_button_style(hover=hover))

    def browse_pdf(self):
        start_dir = self.settings.get_last_directory()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "اختر ملف PDF", start_dir, "PDF Files (*.pdf)"
        )
        if file_path:
            self.pdf_path = file_path
            self.pdf_label.setText(Path(file_path).name)
            self.settings.save_last_pdf_path(file_path)
            self.update_extract_button()

    def get_output_filename(self):
        pdf_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
        timestamp = datetime.now().strftime("%H%M%S")
        return f"{pdf_name}_{timestamp}"

    def select_pdf_bookmark(self):
        """Select PDF file for bookmarks"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "اختر ملف PDF",
            self.settings.get_last_directory(),
            "PDF Files (*.pdf)",
        )
        if file_path:
            self.pdf_path_bookmark.setText(file_path)
            self.settings.save_last_pdf_path(file_path)

    def select_bookmarks(self):
        """Select bookmarks text file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "اختر ملف العناوين",
            self.settings.get_last_directory(),
            "Text Files (*.txt)",
        )
        if file_path:
            self.bookmarks_path.setText(file_path)

    def add_bookmarks(self):
        """Add bookmarks to PDF"""
        pdf_path = self.pdf_path_bookmark.text()
        bookmarks_path = self.bookmarks_path.text()

        if not pdf_path or not bookmarks_path:
            QMessageBox.warning(self, "تنبيه", "الرجاء اختيار ملف PDF وملف العناوين")
            return

        try:
            success, message = self.pdf_tools.add_bookmarks(pdf_path, bookmarks_path)
            if success:
                QMessageBox.information(self, "نجاح", message)
            else:
                QMessageBox.warning(self, "خطأ", message)
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ: {str(e)}")

    def select_pdf_text(self):
        """Select PDF file for text extraction"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "اختر ملف PDF",
            self.settings.get_last_directory(),
            "PDF Files (*.pdf)",
        )
        if file_path:
            self.pdf_path_text.setText(file_path)
            self.settings.save_last_pdf_path(file_path)

    def extract_text(self):
        """Extract text from PDF"""
        pdf_path = self.pdf_path_text.text()
        if not pdf_path:
            QMessageBox.warning(self, "تنبيه", "الرجاء اختيار ملف PDF")
            return

        try:
            start_page = self.page_start.value()
            end_page = self.page_end.value()
            remove_linebreaks = self.remove_linebreaks.isChecked()
            include_images = self.include_images.isChecked()

            text = self.pdf_tools.extract_text_with_options(
                pdf_path, start_page, end_page, remove_linebreaks, include_images
            )
            self.text_preview.setText(text)
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ: {str(e)}")

    def copy_text(self):
        """Copy extracted text to clipboard"""
        text = self.text_preview.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self.status_label_text.setText("تم نسخ النص")
            QTimer.singleShot(2000, lambda: self.status_label_text.clear())

    def select_pdf_split(self):
        """Select PDF file for splitting"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "اختر ملف PDF",
            self.settings.get_last_directory(),
            "PDF Files (*.pdf)",
        )
        if file_path:
            self.pdf_path_split.setText(file_path)
            self.settings.save_last_pdf_path(file_path)

    def update_split_options(self):
        """Update split options based on selected method"""
        # Clear previous options
        for i in reversed(range(self.split_settings_layout.count())):
            self.split_settings_layout.itemAt(i).widget().setParent(None)

        method = self.split_method.currentText()
        if method == "تقسيم حسب عدد الصفحات":
            self.pages_per_file = QSpinBox()
            self.pages_per_file.setMinimum(1)
            self.pages_per_file.setValue(10)
            self.pages_per_file.setPrefix("عدد الصفحات لكل ملف: ")
            self.split_settings_layout.addWidget(self.pages_per_file)
        elif method == "تقسيم حسب صفحات محددة":
            self.page_ranges = QLineEdit()
            self.page_ranges.setPlaceholderText("مثال: 1-5, 6-10, 11-15")
            self.split_settings_layout.addWidget(self.page_ranges)

    def split_pdf(self):
        """Split PDF based on selected method"""
        pdf_path = self.pdf_path_split.text()
        if not pdf_path:
            QMessageBox.warning(self, "تنبيه", "الرجاء اختيار ملف PDF")
            return

        try:
            method = self.split_method.currentText()
            output_dir = self.settings.get_default_output_dir()
            self.split_progress.setVisible(True)

            success = False
            message = ""

            if method == "تقسيم حسب العناوين":
                success, message = self.pdf_tools.split_pdf_by_bookmarks(
                    pdf_path, output_dir
                )

            elif method == "تقسيم حسب عدد الصفحات":
                pages_per_file = self.pages_per_file.value()
                success, message = self.pdf_tools.split_pdf_by_pages(
                    pdf_path, output_dir, pages_per_file
                )

            elif method == "تقسيم حسب صفحات محددة":
                try:
                    ranges = []
                    for range_str in self.page_ranges.text().split(","):
                        start, end = map(int, range_str.strip().split("-"))
                        ranges.append((start, end))
                    success, message = self.pdf_tools.split_pdf_by_ranges(
                        pdf_path, output_dir, ranges
                    )
                except ValueError:
                    message = (
                        "صيغة المدى غير صحيحة. الرجاء استخدام الصيغة: 1-5, 6-10, 11-15"
                    )
                    success = False

            self.split_progress.setVisible(False)

            if success:
                QMessageBox.information(self, "نجاح", message)
                # Open the output directory
                os.startfile(output_dir)
            else:
                QMessageBox.warning(self, "خطأ", message)

        except Exception as e:
            self.split_progress.setVisible(False)
            QMessageBox.critical(self, "خطأ", f"حدث خطأ: {str(e)}")

    def add_pdf_to_merge(self):
        """Add PDF file to merge list"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "اختر ملفات PDF",
            self.settings.get_last_directory(),
            "PDF Files (*.pdf)",
        )

        if files:
            for file_path in files:
                item = QtWidgets.QListWidgetItem(os.path.basename(file_path))
                item.setData(Qt.UserRole, file_path)  # Store full path
                self.pdf_list.addItem(item)

            # Save last directory
            self.settings.save_last_pdf_path(files[0])

    def remove_pdf_from_merge(self):
        """Remove selected PDF from merge list"""
        current_item = self.pdf_list.currentItem()
        if current_item:
            self.pdf_list.takeItem(self.pdf_list.row(current_item))

    def clear_merge_list(self):
        """Clear all PDFs from merge list"""
        self.pdf_list.clear()

    def merge_pdfs(self):
        """Merge selected PDFs"""
        if self.pdf_list.count() == 0:
            QMessageBox.warning(self, "تنبيه", "الرجاء إضافة ملفات PDF للدمج")
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ الملف المدمج",
            os.path.join(self.settings.get_default_output_dir(), "merged.pdf"),
            "PDF Files (*.pdf)",
        )

        if not output_path:
            return

        try:
            # Get all PDF paths
            pdf_paths = []
            for i in range(self.pdf_list.count()):
                item = self.pdf_list.item(i)
                pdf_paths.append(item.data(Qt.UserRole))

            # Show progress bar
            self.merge_progress.setVisible(True)
            self.merge_progress.setRange(0, len(pdf_paths))
            self.merge_progress.setValue(0)

            # Merge PDFs
            merge_bookmarks = self.merge_bookmarks.isChecked()
            create_outline = self.merge_outline.isChecked()

            success, message = self.pdf_tools.merge_pdfs(
                pdf_paths,
                output_path,
                merge_bookmarks,
                create_outline,
                progress_callback=lambda x: self.merge_progress.setValue(x),
            )

            self.merge_progress.setVisible(False)

            if success:
                QMessageBox.information(self, "نجاح", message)
                # Open containing folder
                os.startfile(os.path.dirname(output_path))
            else:
                QMessageBox.warning(self, "خطأ", message)

        except Exception as e:
            self.merge_progress.setVisible(False)
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء دمج الملفات: {str(e)}")

    def update_merge_progress(self, value):
        """Update merge progress bar"""
        self.merge_progress.setValue(value)

    def toggle_page_range(self, state):
        """Enable/disable page range inputs based on checkbox"""
        enabled = not bool(state)
        self.page_start_image.setEnabled(enabled)
        self.page_end_image.setEnabled(enabled)
        self.start_slider.setEnabled(enabled)
        self.end_slider.setEnabled(enabled)

    def select_pdf_image(self):
        """Select PDF file for image extraction"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "اختر ملف PDF",
            self.settings.get_last_directory(),
            "PDF Files (*.pdf)",
        )
        if file_path:
            self.pdf_path_image.setText(file_path)
            self.settings.save_last_pdf_path(file_path)

            # Update page range limits
            doc = fitz.open(file_path)
            max_pages = doc.page_count
            doc.close()

            self.page_start_image.setMaximum(max_pages)
            self.page_end_image.setMaximum(max_pages)
            self.page_end_image.setValue(max_pages)

            # Update sliders
            self.start_slider.setMinimum(1)
            self.start_slider.setMaximum(max_pages)
            self.end_slider.setMinimum(1)
            self.end_slider.setMaximum(max_pages)
            self.end_slider.setValue(max_pages)

    def update_preview(self):
        """Update the PDF page preview"""
        try:
            pdf_path = self.pdf_path_image.text()
            if not pdf_path:
                return

            # Get current page
            page_num = self.page_start_image.value() - 1

            doc = fitz.open(pdf_path)
            page = doc[page_num]

            # Convert page to image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = QImage(
                pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888
            )

            # Scale image to fit preview area while maintaining aspect ratio
            scaled_img = img.scaled(
                self.preview_scroll.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

            # Update preview
            self.preview_label.setPixmap(QPixmap.fromImage(scaled_img))
            doc.close()

        except Exception as e:
            self.preview_label.setText(f"خطأ في المعاينة: {str(e)}")

    def update_page_range(self, max_pages):
        """Update the range of page selection controls"""
        self.page_start_image.setMaximum(max_pages)
        self.page_end_image.setMaximum(max_pages)
        self.page_end_image.setValue(max_pages)

        self.start_slider.setMinimum(1)
        self.start_slider.setMaximum(max_pages)
        self.end_slider.setMinimum(1)
        self.end_slider.setMaximum(max_pages)
        self.end_slider.setValue(max_pages)
