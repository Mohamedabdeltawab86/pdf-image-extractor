import fitz
from PyQt5.QtCore import QObject, pyqtSignal


class NoteExtractor(QObject):
    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(bool, str)  # success, message

    def extract_notes(self, pdf_path, output_path):
        try:
            doc = fitz.open(pdf_path)

            with open(output_path, "w", encoding="utf-8") as f:
                for page_num in range(doc.page_count):
                    page = doc[page_num]
                    annots = page.annots()

                    if annots:
                        f.write(f"\nPage {page_num + 1}:\n")
                        for annot in annots:
                            if annot.type[0] == 8:  # Text annotation
                                content = annot.info["content"]
                                f.write(f"- {content}\n")

                    self.progress.emit(page_num + 1, doc.page_count)

            doc.close()
            self.finished.emit(True, "Notes extracted successfully")

        except Exception as e:
            self.finished.emit(False, f"Error extracting notes: {str(e)}")
