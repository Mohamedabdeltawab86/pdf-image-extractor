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
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QTabWidget,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDir, QSettings, QFile, QTextStream
from PyQt5.QtGui import QIcon, QFont, QFontDatabase, QPalette, QColor, QPixmap, QImage
import qtawesome as qta  # For better icons, install with: pip install qtawesome
from pathlib import Path
from ..modules.pdf_processor import extract_images_from_pdf
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
import sys

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Now use the imports
from src.modules.image_extractor.widget import ImageExtractorModule
from src.modules.bookmark_extractor.widget import BookmarkExtractorModule
from src.modules.note_extractor.widget import NoteExtractorModule


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
        self.load_styles()
        self.init_ui()

    def load_styles(self):
        """Load and apply QSS styles"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            style_path = os.path.join(
                current_dir, "..", "resources", "styles", "main.qss"
            )

            style_file = QFile(style_path)
            if style_file.open(QFile.ReadOnly | QFile.Text):
                stream = QTextStream(style_file)
                self.setStyleSheet(stream.readAll())
                style_file.close()
            else:
                print(f"Could not open style file: {style_path}")
        except Exception as e:
            print(f"Error loading styles: {str(e)}")

    def init_ui(self):
        """Initialize the user interface"""
        # Set window properties
        self.setWindowTitle("PDF Tools")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(800, 600)

        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create sidebar
        sidebar = QWidget()
        sidebar.setMaximumWidth(250)
        sidebar.setMinimumWidth(200)
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(10, 10, 10, 10)

        # Add title to sidebar
        title_label = QLabel("PDF Tools")
        title_label.setObjectName("sidebarTitle")
        sidebar_layout.addWidget(title_label)

        # Create module list
        self.module_list = QListWidget()
        self.module_list.setObjectName("moduleList")

        # Create stacked widget for module content
        self.module_stack = QStackedWidget()
        self.module_stack.setObjectName("moduleStack")

        # Load modules
        self.modules = [
            ImageExtractorModule(),
            BookmarkExtractorModule(),
            NoteExtractorModule(),
        ]

        # Add modules to UI
        for module in self.modules:
            # Add to sidebar list
            item = QListWidgetItem(module.get_name())
            item.setToolTip(module.get_description())
            self.module_list.addItem(item)

            # Add to stacked widget
            module_widget = module.get_widget()
            self.module_stack.addWidget(module_widget)

        # Connect module selection
        self.module_list.currentRowChanged.connect(self.module_stack.setCurrentIndex)

        # Select first module by default
        self.module_list.setCurrentRow(0)

        # Add widgets to layouts
        sidebar_layout.addWidget(self.module_list)
        sidebar.setLayout(sidebar_layout)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.module_stack)

        # Create menu bar
        self.create_menu_bar()

        # Set main widget
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def create_menu_bar(self):
        """Create the application menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Settings menu
        settings_menu = menubar.addMenu("Settings")

        # Font action
        font_action = QAction("Font", self)
        font_action.triggered.connect(self.change_font)
        settings_menu.addAction(font_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        # About action
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def change_font(self):
        """Change application font"""
        font, ok = QFontDialog.getFont(self.font(), self)
        if ok:
            self.setFont(font)

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About PDF Tools",
            """
            <h3>PDF Tools</h3>
            <p>A modern tool for PDF processing.</p>
            <p>Features:</p>
            <ul>
                <li>Image Extraction</li>
                <li>Bookmark Extraction</li>
                <li>Note Extraction</li>
            </ul>
            """,
        )

    def closeEvent(self, event):
        """Handle application close"""
        reply = QMessageBox.question(
            self,
            "Exit",
            "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            # Clean up resources if needed
            event.accept()
        else:
            event.ignore()
