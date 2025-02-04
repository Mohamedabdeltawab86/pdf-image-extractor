from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QSpinBox,
)
from PyQt5.QtCore import Qt
from ..util.settings import Settings
from ..util.translations import Translations


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = Settings()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Language Selection
        lang_layout = QHBoxLayout()
        lang_label = QLabel(Translations.get("language"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["العربية", "English"])
        self.lang_combo.setCurrentText(
            "العربية" if self.settings.get_language() == "ar" else "English"
        )
        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(self.lang_combo)
        layout.addLayout(lang_layout)

        # Font Size
        size_layout = QHBoxLayout()
        size_label = QLabel(Translations.get("font_size"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 24)
        self.size_spin.setValue(self.settings.get_font_size())
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.size_spin)
        layout.addLayout(size_layout)

        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton(Translations.get("save"))
        cancel_button = QPushButton(Translations.get("cancel"))
        save_button.clicked.connect(self.save_settings)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

    def save_settings(self):
        self.settings.set_language(
            "ar" if self.lang_combo.currentText() == "العربية" else "en"
        )
        self.settings.set_font_size(self.size_spin.value())
        self.accept()
