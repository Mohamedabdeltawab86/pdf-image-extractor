from PyQt5.QtCore import QSettings


class Settings:
    def __init__(self):
        self.settings = QSettings("DrWaleed", "ImageExtractor")

    def get_language(self):
        return self.settings.value("language", "ar")  # Default to Arabic

    def set_language(self, lang):
        self.settings.setValue("language", lang)

    def get_font_size(self):
        return self.settings.value("font_size", 12, type=int)

    def set_font_size(self, size):
        self.settings.setValue("font_size", size)
