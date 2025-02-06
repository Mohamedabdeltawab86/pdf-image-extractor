import fitz
from PyQt5.QtCore import QObject, pyqtSignal


class BookmarkExtractor(QObject):
    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(bool, str)  # success, message

    def extract_bookmarks(self, pdf_path, output_path):
        try:
            doc = fitz.open(pdf_path)
            toc = doc.get_toc()

            with open(output_path, "w", encoding="utf-8") as f:
                for level, title, page in toc:
                    indent = "  " * (level - 1)
                    f.write(f"{indent}- {title} (Page {page})\n")

            doc.close()
            self.finished.emit(True, "Bookmarks extracted successfully")

        except Exception as e:
            self.finished.emit(False, f"Error extracting bookmarks: {str(e)}")
