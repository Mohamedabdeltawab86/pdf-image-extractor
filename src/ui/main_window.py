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
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDir
from PyQt5.QtGui import QIcon, QFont, QFontDatabase, QPalette, QColor
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
        self.current_language = self.settings.get_language()

        # Initialize font
        self.init_font()

        # Setup window properties
        self.setWindowTitle("تطبيق الدكتور وليد")
        self.setMinimumSize(1024, 768)

        # Fix window icon - explicit path
        self.setWindowIcon(QIcon(":/icons/logo.png"))

        # Force RTL for title bar
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint)

        # Set window style with lighter, more transparent gradient
        self.setStyleSheet(
            """
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(100, 181, 246, 180),  /* Light blue */
                    stop:0.5 rgba(30, 136, 229, 160), /* Medium blue */
                    stop:1 rgba(21, 101, 192, 140)    /* Darker blue */
                );
            }
            QFrame#mainFrame {
                background: rgba(255, 255, 255, 245);
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.5);
            }
            QLabel#titleLabel {
                color: #1976D2;
                background: rgba(255, 255, 255, 0.3);
                border-radius: 15px;
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
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(40, 40, 40, 40)

        # Create main frame with shadow effect
        main_frame = QFrame()
        main_frame.setObjectName("mainFrame")

        # Add drop shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 0)
        main_frame.setGraphicsEffect(shadow)

        frame_layout = QVBoxLayout(main_frame)
        frame_layout.setSpacing(30)
        frame_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.addWidget(main_frame)

        # Title with updated style
        title = QLabel("تطبيق استخراج الصور من ملفات PDF")
        title.setObjectName("titleLabel")
        title.setFont(QFont(self.font.family(), 32, QFont.Bold))
        title.setStyleSheet(
            """
            padding: 20px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(255, 255, 255, 0.3), 
                stop:0.5 rgba(255, 255, 255, 0.4), 
                stop:1 rgba(255, 255, 255, 0.3));
            border-radius: 15px;
            color: #1976D2;
            border: 1px solid rgba(255, 255, 255, 0.5);
        """
        )
        title.setAlignment(Qt.AlignCenter)
        frame_layout.addWidget(title)

        # PDF Selection with glass effect
        pdf_layout = QHBoxLayout()
        self.pdf_label = QLabel("لم يتم اختيار ملف PDF")
        self.pdf_label.setStyleSheet(
            """
            padding: 15px;
            background: rgba(255, 255, 255, 0.8);
            border-radius: 12px;
            border: 2px solid rgba(25, 118, 210, 0.2);
            font-size: 16px;
            color: #1976D2;
        """
        )

        pdf_button = QPushButton("  اختيار ملف PDF")
        pdf_button.setIcon(qta.icon("fa5s.file-pdf", color="#1a237e", scale_factor=1.5))
        pdf_button.setIconSize(pdf_button.iconSize() * 2)
        pdf_button.setStyleSheet(self.get_button_style())
        pdf_button.setMinimumHeight(50)
        pdf_button.clicked.connect(self.select_pdf)

        # Add hover effect
        pdf_button.setAutoFillBackground(True)
        pdf_button.enterEvent = lambda e: self.button_hover_effect(pdf_button, True)
        pdf_button.leaveEvent = lambda e: self.button_hover_effect(pdf_button, False)

        pdf_layout.addWidget(self.pdf_label, stretch=1)
        pdf_layout.addWidget(pdf_button)
        frame_layout.addLayout(pdf_layout)

        # Output Directory Selection
        output_layout = QHBoxLayout()
        self.output_label = QLabel("لم يتم اختيار مجلد الحفظ")
        self.output_label.setStyleSheet(
            """
            padding: 15px;
            background: rgba(255, 255, 255, 0.8);
            border-radius: 12px;
            border: 2px solid rgba(25, 118, 210, 0.2);
            font-size: 16px;
            color: #1976D2;
        """
        )

        output_button = QPushButton("  اختيار مجلد الحفظ")
        output_button.setIcon(
            qta.icon("fa5s.folder-open", color="#1a237e", scale_factor=1.5)
        )
        output_button.setIconSize(output_button.iconSize() * 2)
        output_button.setStyleSheet(self.get_button_style())
        output_button.setMinimumHeight(50)
        output_button.clicked.connect(self.select_output)

        # Add hover effect
        output_button.enterEvent = lambda e: self.button_hover_effect(
            output_button, True
        )
        output_button.leaveEvent = lambda e: self.button_hover_effect(
            output_button, False
        )

        output_layout.addWidget(self.output_label, stretch=1)
        output_layout.addWidget(output_button)
        frame_layout.addLayout(output_layout)

        # Add Radio Buttons for Inversion Option
        inversion_group = QButtonGroup(self)
        inversion_layout = QHBoxLayout()

        self.normal_radio = QRadioButton("صور عادية")
        self.inverted_radio = QRadioButton("صور معكوسة")
        self.normal_radio.setChecked(True)  # Default to normal

        for radio in [self.normal_radio, self.inverted_radio]:
            radio.setStyleSheet(
                """
                QRadioButton {
                    font-size: 16px;
                    color: #1976D2;
                    padding: 10px;
                }
                QRadioButton::indicator {
                    width: 20px;
                    height: 20px;
                }
            """
            )
            inversion_group.addButton(radio)
            inversion_layout.addWidget(radio)

        frame_layout.addLayout(inversion_layout)

        # Add Radio Buttons for Export Option
        export_group = QButtonGroup(self)
        export_layout = QHBoxLayout()

        self.files_radio = QRadioButton("حفظ كملفات")
        self.ppt_radio = QRadioButton("حفظ كعرض تقديمي")
        self.files_radio.setChecked(True)  # Default to files

        for radio in [self.files_radio, self.ppt_radio]:
            radio.setStyleSheet(
                """
                QRadioButton {
                    font-size: 16px;
                    color: #1976D2;
                    padding: 10px;
                }
                QRadioButton::indicator {
                    width: 20px;
                    height: 20px;
                }
            """
            )
            export_group.addButton(radio)
            export_layout.addWidget(radio)

        frame_layout.addLayout(export_layout)

        # Progress Bar and Status Label
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 2px solid rgba(25, 118, 210, 0.2);
                border-radius: 15px;
                text-align: center;
                background: rgba(255, 255, 255, 0.8);
                height: 30px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2196F3, stop:1 #1976D2);
                border-radius: 13px;
            }
        """
        )
        frame_layout.addWidget(self.progress_bar)

        # Status Label
        self.status_label = QLabel("جاهز")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(
            """
            color: #1976D2;
            font-size: 18px;
            padding: 10px;
            background: rgba(255, 255, 255, 0.8);
            border-radius: 10px;
            border: 1px solid rgba(25, 118, 210, 0.2);
        """
        )
        frame_layout.addWidget(self.status_label)

        # Buttons Layout
        buttons_layout = QHBoxLayout()

        # Extract Button
        self.extract_button = QPushButton("استخراج الصور")
        self.extract_button.setIcon(
            qta.icon("fa5s.images", color="white", scale_factor=1.5)
        )
        self.extract_button.setStyleSheet(self.get_button_style(primary=True))
        self.extract_button.clicked.connect(self.start_extraction)
        self.extract_button.setEnabled(False)
        buttons_layout.addWidget(self.extract_button)

        # Stop Button
        self.stop_button = QPushButton("إيقاف")
        self.stop_button.setIcon(qta.icon("fa5s.stop", color="white", scale_factor=1.5))
        self.stop_button.setStyleSheet(self.get_button_style(warning=True))
        self.stop_button.clicked.connect(self.stop_extraction)
        self.stop_button.setEnabled(False)
        buttons_layout.addWidget(self.stop_button)

        frame_layout.addLayout(buttons_layout)

        # Add stretching space
        frame_layout.addStretch()

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
        if not self.pdf_path or not self.output_dir:
            return

        self.extract_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.status_label.setText("جاري استخراج الصور...")

        # Create and start worker thread
        self.worker = ExtractionWorker(
            self.pdf_path,
            self.output_dir,
            self.inverted_radio.isChecked(),
            self.ppt_radio.isChecked(),
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.extraction_complete)
        self.worker.error.connect(self.extraction_error)
        self.worker.start()

    def stop_extraction(self):
        if hasattr(self, "worker") and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            self.status_label.setText("تم إيقاف العملية")
            self.extract_button.setEnabled(True)
            self.stop_button.setEnabled(False)

    def update_progress(self, current, total):
        percentage = (current / total) * 100
        self.progress_bar.setValue(int(percentage))
        self.status_label.setText(f"جاري المعالجة... {current}/{total}")

    def extraction_complete(self, num_images):
        self.progress_bar.setValue(100)
        if self.ppt_radio.isChecked():
            self.status_label.setText(
                f"تم استخراج {num_images} صورة وفتح ملف العرض التقديمي!"
            )
        else:
            self.status_label.setText(f"تم استخراج {num_images} صورة بنجاح!")
        self.extract_button.setEnabled(True)
        self.stop_button.setEnabled(False)

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
