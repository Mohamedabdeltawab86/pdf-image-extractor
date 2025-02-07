# src/modules/note_extractor/widget.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog,
    QProgressBar, QComboBox, QHBoxLayout
)
from PyQt5.QtCore import pyqtSignal, QThread
from ..base_module import PDFModuleBase
import fitz
import os
from datetime import datetime

class NoteExtractionThread(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(bool, str)

    def __init__(self, pdf_path, output_format):
        super().__init__()
        self.pdf_path = pdf_path
        self.output_format = output_format

    def run(self):
        try:
            doc = fitz.open(self.pdf_path)
            total_pages = doc.page_count
            extracted_notes = []
            total_annotations = 0  # Keep track of total annotations

            for page_num in range(total_pages):
                page = doc[page_num]
                self.progress.emit(page_num + 1, total_pages)

                for annot in page.annots():
                    total_annotations += 1  # Increment for *every* annotation
                    note_info = self.process_annotation(page_num, annot)
                    if note_info:
                        extracted_notes.append(note_info)

            doc.close()

            # Get modified date of the file
            mod_time = os.path.getmtime(self.pdf_path)
            last_modified_date = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d')

            # Get base file name
            base_filename = os.path.splitext(os.path.basename(self.pdf_path))[0]

            # Emit finished signal with success message
            if extracted_notes:
                self.save_notes(extracted_notes, base_filename, total_annotations, last_modified_date)
                self.finished.emit(True, f"تم استخراج {len(extracted_notes)} تعليق.")
            else:
                self.finished.emit(True, "لا توجد تعليقات في الملف.")

        except Exception as e:
            self.finished.emit(False, f"حدث خطأ: {e}")

    def process_annotation(self, page_num, annot):
        """Processes a single annotation and returns a formatted string."""
        annot_type = annot.type[1]  # Extract type name (e.g., 'Text', 'Highlight')
        content = ""

        if annot_type in ("FreeText", "Text"):
            content = annot.info["content"] if annot.info.get("content") else ""

        elif annot_type in ("Highlight", "Underline", "StrikeOut", "Squiggly"):
            words = annot.parent.get_text("words", clip=annot.rect)
            content = " ".join([w[4] for w in words]) if words else ""

        if not content:
            return None

        date_str = annot.info.get("creationDate", "Unknown")
        if date_str != "Unknown":
            try:
                date_str = datetime.strptime(date_str[2:15], "%Y%m%d%H%M%S").strftime("%Y-%m-%d")
            except ValueError:
                pass  # Keep "Unknown" if parsing fails

        return {
            "page": page_num + 1,
            "type": annot_type,
            "content": content,
            "date": date_str,
        }

    def save_notes(self, notes, base_filename, total_annotations, last_modified_date):
        """Saves the extracted notes to a file (Markdown, HTML, or plain text)."""
        output_path = os.path.join(os.path.dirname(self.pdf_path), f"{base_filename}_notes.{self.get_extension()}")

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"# General Info\n")
                f.write(f"- **Book Name:** {base_filename}\n")
                f.write(f"- **Number of Notes:** {total_annotations}\n")
                f.write(f"- **Last Modified Date:** {last_modified_date}\n\n")

                if self.output_format == "Markdown":
                    for note in notes:
                        f.write(f"## Page {note['page']}\n")
                        f.write(f"- **Type:** {note['type']}\n")
                        f.write(f"- **Content:** {note['content']}\n")
                        f.write(f"- **Date:** {note['date']}\n\n")

                elif self.output_format == "HTML":
                    f.write("<html><head><title>PDF Notes</title></head><body>\n")
                    f.write(f"<h1>General Info</h1>\n")
                    f.write(f"<p><b>Book Name:</b> {base_filename}</p>\n")
                    f.write(f"<p><b>Number of Notes:</b> {total_annotations}</p>\n")
                    f.write(f"<p><b>Last Modified Date:</b> {last_modified_date}</p>\n")
                    f.write("<hr>\n")

                    for note in notes:
                        f.write(f"<h2>Page {note['page']}</h2>\n")
                        f.write(f"<p><b>Type:</b> {note['type']}</p>\n")
                        f.write(f"<p><b>Content:</b> {note['content']}</p>\n")
                        f.write(f"<p><b>Date:</b> {note['date']}</p>\n")
                        f.write("<hr>\n")
                    f.write("</body></html>\n")

                else:  # Plain Text
                    f.write(f"General Info\n")
                    f.write(f"Book Name: {base_filename}\n")
                    f.write(f"Number of Notes: {total_annotations}\n")
                    f.write(f"Last Modified Date: {last_modified_date}\n\n")
                    for note in notes:
                        f.write(f"Page: {note['page']}\n")
                        f.write(f"Type: {note['type']}\n")
                        f.write(f"Content: {note['content']}\n")
                        f.write(f"Date: {note['date']}\n\n")
        except Exception as e:
            print(f"Error writing to output file: {e}")

    def get_extension(self):
        if self.output_format == "Markdown":
            return "md"
        elif self.output_format == "HTML":
            return "html"
        else:
            return "txt"


class NoteExtractorModule(PDFModuleBase):
    def __init__(self):
        super().__init__()
        self.pdf_path = None  # Store PDF path
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # File selection
        file_layout = QHBoxLayout()
        self.file_label = QLabel("لم يتم اختيار ملف")
        self.browse_button = QPushButton("اختر ملف PDF")
        self.browse_button.clicked.connect(self.browse_file)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.browse_button)
        layout.addLayout(file_layout)

        # Format selection
        format_layout = QHBoxLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Markdown", "HTML", "Text"])
        format_layout.addWidget(QLabel("تنسيق الملف:"))
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)

        # Extract button
        self.extract_button = QPushButton("استخراج التعليقات")
        self.extract_button.clicked.connect(self.start_extraction)
        self.extract_button.setEnabled(False)
        layout.addWidget(self.extract_button)

        # Progress bar
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "اختر ملف PDF", "", "PDF files (*.pdf)"
        )
        if file_path:
            self.pdf_path = file_path  # Store the path
            self.file_label.setText(os.path.basename(file_path))
            self.extract_button.setEnabled(True)
            self.status_label.setText("")  # Clear status

    def start_extraction(self):
        if not self.pdf_path:
            return

        output_format = self.format_combo.currentText()
        self.extraction_thread = NoteExtractionThread(self.pdf_path, output_format)
        self.extraction_thread.progress.connect(self.update_progress)
        self.extraction_thread.finished.connect(self.extraction_complete)
        self.extraction_thread.start()

        self.extract_button.setEnabled(False)  # Disable while extracting
        self.status_label.setText("جارٍ الاستخراج...")

    def update_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def extraction_complete(self, success, message):
        self.status_label.setText(message)
        self.extract_button.setEnabled(True)  # Re-enable after extraction
        self.progress_bar.setValue(0)  # Reset progress bar

    def get_description(self):
        return "Extract notes and annotations from PDF files"

    def get_name(self):
        return "Note Extractor"

    def get_widget(self):
        return self
