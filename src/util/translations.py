class Translations:
    _translations = {
        "ar": {
            "app_title": "تطبيق الدكتور وليد",
            "select_pdf": "اختيار ملف PDF",
            "select_output": "اختيار مجلد الحفظ",
            "extract": "استخراج الصور",
            "ready": "جاهز",
            "processing": "جاري المعالجة...",
            "complete": "تم الاستخراج بنجاح",
            "settings": "الإعدادات",
            "language": "اللغة",
            "font_size": "حجم الخط",
            "theme": "المظهر",
            "about": "حول التطبيق",
        },
        "en": {
            "app_title": "Dr. Waleed App",
            "select_pdf": "Select PDF",
            "select_output": "Select Output",
            "extract": "Extract Images",
            "ready": "Ready",
            "processing": "Processing...",
            "complete": "Extraction Complete",
            "settings": "Settings",
            "language": "Language",
            "font_size": "Font Size",
            "theme": "Theme",
            "about": "About",
        },
    }

    @classmethod
    def get(cls, key, lang="ar"):
        return cls._translations.get(lang, cls._translations["en"]).get(key, key)
