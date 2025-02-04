import os
from PIL import Image
import io
from pptx import Presentation
from pptx.util import Inches
from pptx.dml.color import RGBColor
import subprocess
import platform
import fitz
from PyQt5.QtCore import QThread, pyqtSignal


def invert_image(image_bytes):
    """
    Invert image using Pillow's built-in operations.

    Args:
        image_bytes (bytes): Original image bytes

    Returns:
        bytes: Inverted image bytes
    """
    # Convert bytes to image
    img = Image.open(io.BytesIO(image_bytes))

    # Convert to RGB if not already
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Invert the image using Pillow's built-in operation
    inverted_img = Image.eval(img, lambda x: 255 - x)

    # Save to bytes
    output_buffer = io.BytesIO()
    inverted_img.save(output_buffer, format="JPEG", quality=95)
    return output_buffer.getvalue()


def remove_black_background(image):
    """Remove the black background from an image."""
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    data = image.getdata()

    new_data = []
    for item in data:
        if item[0] < 50 and item[1] < 50 and item[2] < 50:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)

    image.putdata(new_data)
    return image


def save_image(image_bytes, output_dir, image_filename, should_invert=False):
    """
    Save image with optional inversion
    """
    try:
        # Convert bytes to image
        img = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB if not already
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Invert if requested
        if should_invert:
            img = remove_black_background(img)

        # Save to output
        base_name = os.path.splitext(image_filename)[0]
        output_filename = f"{base_name}.jpg"
        image_path = os.path.join(output_dir, output_filename)

        img.save(image_path, "JPEG", quality=95)
        print(f"Saved {'inverted' if should_invert else 'original'} {output_filename}")
        return True

    except Exception as e:
        print(f"Error saving image {image_filename}: {str(e)}")
        return False


def open_file(filepath):
    """Open a file with the default system application"""
    try:
        if platform.system() == "Darwin":  # macOS
            subprocess.call(("open", filepath))
        elif platform.system() == "Windows":  # Windows
            os.startfile(filepath)
        else:  # Linux variants
            subprocess.call(("xdg-open", filepath))
    except Exception as e:
        print(f"Error opening file: {str(e)}")


def extract_to_ppt(images, output_dir, should_invert=False):
    """Extract images to PowerPoint presentation"""
    try:
        prs = Presentation()

        # Set slide dimensions (16:9)
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

        # Set default slide background to black
        for layout in prs.slide_layouts:
            background = layout.background
            fill = background.fill
            fill.solid()
            fill.fore_color.rgb = RGBColor(0, 0, 0)

        for i, image_bytes in enumerate(images):
            # Add a slide
            slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank layout

            # Process image
            img = Image.open(io.BytesIO(image_bytes))

            # Convert to RGB if needed
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Invert if requested
            if should_invert:
                img = remove_black_background(img)

            # Save temporary file
            temp_path = os.path.join(output_dir, f"temp_{i}.png")
            img.save(temp_path, "PNG")

            # Calculate image dimensions to fit slide
            img_width, img_height = img.size
            aspect_ratio = img_width / img_height

            # Set maximum dimensions (leaving margins)
            max_width = Inches(12)  # 1.333 inch margin total
            max_height = Inches(6.5)  # 1 inch margin total

            # Calculate dimensions maintaining aspect ratio
            if aspect_ratio > max_width / max_height:
                width = max_width
                height = width / aspect_ratio
            else:
                height = max_height
                width = height * aspect_ratio

            # Center the image on slide
            left = (prs.slide_width - width) / 2
            top = (prs.slide_height - height) / 2

            # Add to slide
            pic = slide.shapes.add_picture(temp_path, left, top, width, height)

            # Remove temp file
            os.remove(temp_path)

        # Save presentation
        ppt_path = os.path.join(output_dir, "extracted_images.pptx")
        prs.save(ppt_path)

        # Open the PowerPoint file
        open_file(ppt_path)

        return len(images)

    except Exception as e:
        print(f"Error creating PowerPoint: {str(e)}")
        raise e


class ImageExtractionThread(QThread):
    progress = pyqtSignal(object)
    finished = pyqtSignal(tuple)

    def __init__(self, pdf_path, output_dir, start_page, end_page, options):
        super().__init__()
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.start_page = start_page
        self.end_page = end_page
        self.options = options if options else {}  # Ensure options is not None
        self._is_running = True

    def run(self):
        doc = None
        try:
            # Get total page count at the start
            doc = fitz.open(self.pdf_path)
            doc_page_count = len(doc)

            if self.options.get("preview_only"):
                images = []

                # Use specified page range
                start = self.start_page - 1
                end = self.end_page if self.end_page else doc_page_count

                for page_num in range(start, end):
                    if not self._is_running:
                        break

                    for img in doc.get_page_images(page_num):
                        try:
                            xref = img[0]
                            base_image = doc.extract_image(xref)
                            if base_image:
                                images.append(base_image["image"])
                        except Exception as e:
                            print(f"Error extracting image: {str(e)}")
                            continue

                doc.close()
                doc = None  # Clear the reference
                self.finished.emit((True, "تم استخراج الصور للمعاينة", images))
                return

            # For actual extraction, use the preview images
            images = self.options.get("preview_images", [])
            inverted_indices = self.options.get("inverted_indices", [])

            if self._is_running and images:
                if self.options.get("output_type") == "pptx":
                    # Create PowerPoint with the preview images
                    prs = Presentation()

                    # Get PDF filename without extension for PowerPoint name
                    pdf_name = os.path.splitext(os.path.basename(self.pdf_path))[0]

                    # Get page range for filename
                    page_range = ""
                    if self.start_page != 1 or (
                        self.end_page and self.end_page != doc_page_count
                    ):
                        page_range = (
                            f" {self.start_page}-{self.end_page or doc_page_count}"
                        )

                    for i, image_bytes in enumerate(images):
                        if not self._is_running:
                            break

                        slide = prs.slides.add_slide(prs.slide_layouts[6])

                        # Create a new BytesIO object for each image
                        img_stream = io.BytesIO(image_bytes)
                        img = Image.open(img_stream)

                        # Apply inversion if needed
                        if (
                            inverted_indices
                            and len(inverted_indices) > i
                            and inverted_indices[i]
                        ):
                            if img.mode != "RGB":
                                img = img.convert("RGB")
                            img = Image.eval(img, lambda x: 255 - x)

                        # Save temp image with unique name
                        temp_path = os.path.join(self.output_dir, f"temp_{i}.png")
                        img.save(temp_path, "PNG")

                        # Add to slide
                        slide.shapes.add_picture(
                            temp_path, 0, 0, prs.slide_width, prs.slide_height
                        )

                        # Clean up temp file immediately
                        os.remove(temp_path)
                        img_stream.close()

                    # Save with PDF name and page range
                    output_path = os.path.join(
                        self.output_dir, f"{pdf_name}{page_range}.pptx"
                    )

                    try:
                        prs.save(output_path)
                        if os.path.exists(output_path):
                            self.open_file(output_path)
                            self.finished.emit(
                                (True, f"تم حفظ وفتح {len(images)} صورة", len(images))
                            )
                        else:
                            self.finished.emit((False, "خطأ: فشل حفظ الملف", 0))
                    except PermissionError:
                        self.finished.emit((False, "خطأ: الملف مفتوح في برنامج آخر", 0))
                    except Exception as e:
                        self.finished.emit((False, "خطأ: فشل حفظ الملف", 0))

                else:
                    # Save as separate images
                    pdf_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
                    page_range = ""
                    if self.start_page != 1 or (
                        self.end_page and self.end_page != doc_page_count
                    ):
                        page_range = (
                            f" {self.start_page}-{self.end_page or doc_page_count}"
                        )

                    saved_count = 0
                    for i, image_bytes in enumerate(images):
                        if not self._is_running:
                            break

                        try:
                            img = Image.open(io.BytesIO(image_bytes))

                            # Apply inversion if needed
                            if (
                                inverted_indices
                                and len(inverted_indices) > i
                                and inverted_indices[i]
                            ):
                                if img.mode != "RGB":
                                    img = img.convert("RGB")
                                img = Image.eval(img, lambda x: 255 - x)

                            output_path = os.path.join(
                                self.output_dir, f"{pdf_name}{page_range}_{i+1}.png"
                            )
                            img.save(output_path, quality=95)
                            saved_count += 1
                        except Exception as e:
                            print(f"Error saving image {i+1}: {str(e)}")

                    if saved_count > 0:
                        self.finished.emit(
                            (True, f"تم حفظ {saved_count} صورة", saved_count)
                        )
                    else:
                        self.finished.emit((False, "خطأ: لم يتم حفظ أي صورة", 0))

            else:
                self.finished.emit((False, "خطأ: لا توجد صور في النطاق المحدد", 0))

        except Exception as e:
            print(f"Error during extraction: {str(e)}")
            self.finished.emit((False, "خطأ: فشل المعالجة", 0))
        finally:
            if doc:
                doc.close()

    def open_file(self, filepath):
        """Open a file with the default system application"""
        try:
            if platform.system() == "Windows":
                os.startfile(filepath)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(("open", filepath))
            else:  # Linux
                subprocess.call(("xdg-open", filepath))
        except Exception as e:
            print(f"Error opening file: {str(e)}")
