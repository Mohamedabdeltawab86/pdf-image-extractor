# src/modules/image_extractor/image_extraction_thread.py

from PyQt5.QtCore import QThread, pyqtSignal
import fitz
import os
from .image_saver import save_image
from .ppt_extractor import extract_to_ppt  # Correct import
import io
from PIL import Image
from pathlib import Path

class ImageExtractionThread(QThread):
    progress = pyqtSignal(int, int)  # Current page, total pages/images
    finished = pyqtSignal(tuple)  # (success: bool, message: str, result_data)

    def __init__(self, pdf_path, output_dir, start_page=None, end_page=None, preview_mode=False, save_as_ppt=False):
        super().__init__()
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.start_page = start_page
        self.end_page = end_page
        self.preview_mode = preview_mode
        self.save_as_ppt = save_as_ppt
        self.images = []  # Store image data for PPT or preview


    def run(self):
        try:
            doc = fitz.open(self.pdf_path)
            total_pages = doc.page_count

            # Adjust page range
            start = self.start_page -1 if self.start_page is not None else 0
            end = min(self.end_page, total_pages) if self.end_page is not None else total_pages

            if not self.preview_mode: # inform user if it is  not in preview mode
                print("extracting ....")

            for page_num in range(start, end):
                page = doc[page_num]
                image_list = page.get_images()

                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    if self.preview_mode or self.save_as_ppt:
                         self.images.append(image_bytes)  # Store for preview or PPT
                    elif not self.preview_mode:
                        # Construct a filename
                        image_filename = f"page_{page_num + 1}_img_{img_index}.png"  # Clearer filename
                        save_image(image_bytes, self.output_dir, image_filename)

                    self.progress.emit(page_num + 1, total_pages)

            doc.close()

            if self.preview_mode:
                self.finished.emit((True, "Preview ready", self.images))

            elif self.save_as_ppt:
                # Get base filename from the PDF path
                base_filename = Path(self.pdf_path).stem
                extract_to_ppt(self.images, self.output_dir, False, base_filename)  # Pass base_filename
                self.finished.emit((True, "PPTX created successfully.", len(self.images)))
            else:
                self.finished.emit((True, "Images extracted successfully.", len(self.images)))


        except Exception as e:
            self.finished.emit((False, f"Error during extraction: {e}", None))