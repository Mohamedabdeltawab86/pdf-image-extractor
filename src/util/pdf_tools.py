import fitz
import json
import shutil
import os
from pathlib import Path


class PDFTools:
    @staticmethod
    def add_bookmarks(pdf_path, bookmarks_path):
        """Add bookmarks to PDF from text file"""
        temp_output_path = "temp_output.pdf"
        pdf_file = None

        try:
            pdf_file = fitz.open(pdf_path)
            toc = []

            with open(bookmarks_path, encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split(":")
                    if len(parts) == 2:
                        title = parts[0].strip()
                        try:
                            page = int(parts[1].strip())
                            toc.append([1, title, page])
                        except ValueError:
                            raise ValueError(
                                f"Invalid page number for bookmark '{title}': {parts[1]}"
                            )

            pdf_file.set_toc(toc)
            pdf_file.save(temp_output_path, incremental=False)
            pdf_file.close()
            shutil.move(temp_output_path, pdf_path)
            return True, "تمت إضافة العناوين بنجاح"

        except Exception as e:
            return False, f"خطأ: {str(e)}"
        finally:
            if pdf_file:
                pdf_file.close()

    @staticmethod
    def extract_bookmarks(pdf_path):
        """Extract bookmarks to JSON"""
        try:
            pdf_file = fitz.open(pdf_path)
            toc = pdf_file.get_toc()

            if not toc:
                return False, "لا توجد عناوين في الملف"

            bookmarks = []
            for i, item in enumerate(toc):
                title = item[1]
                start_page = item[2]
                end_page = (
                    toc[i + 1][2] - 1 if i < len(toc) - 1 else pdf_file.page_count - 1
                )

                bookmarks.append(
                    {
                        "title": title,
                        "start_page": start_page,
                        "end_page": end_page,
                        "page_count": end_page - start_page + 1,
                    }
                )

            output_path = f"{pdf_path}.bookmarks.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(bookmarks, f, indent=4, ensure_ascii=False)

            return True, f"تم حفظ العناوين في {output_path}"

        except Exception as e:
            return False, f"خطأ: {str(e)}"

    @staticmethod
    def extract_text_with_options(
        pdf_path, start_page, end_page, remove_linebreaks=False, include_images=False
    ):
        """Extract text with advanced options"""
        try:
            doc = fitz.open(pdf_path)
            text = []

            for page_num in range(start_page - 1, min(end_page, doc.page_count)):
                page = doc[page_num]

                # Get text
                page_text = page.get_text()

                # Handle line breaks
                if remove_linebreaks:
                    page_text = " ".join(page_text.split())

                # Get text from images if requested
                if include_images:
                    for img in page.get_images():
                        # Use OCR here if implemented
                        pass

                text.append(page_text)

            return "\n\n".join(text)

        except Exception as e:
            raise Exception(f"خطأ في استخراج النص: {str(e)}")

    @staticmethod
    def split_pdf_by_bookmarks(pdf_path, output_dir):
        """Split PDF based on bookmarks"""
        try:
            doc = fitz.open(pdf_path)
            toc = doc.get_toc()

            if not toc:
                return False, "لا توجد عناوين في الملف"

            for i, item in enumerate(toc):
                title = item[1]
                start_page = item[2] - 1
                end_page = toc[i + 1][2] - 1 if i < len(toc) - 1 else doc.page_count

                new_doc = fitz.open()
                new_doc.insert_pdf(doc, from_page=start_page, to_page=end_page - 1)

                safe_title = "".join(
                    x for x in title if x.isalnum() or x in (" ", "-", "_")
                )
                output_path = os.path.join(output_dir, f"{safe_title}.pdf")
                new_doc.save(output_path)
                new_doc.close()

            doc.close()
            return True, f"تم تقسيم الملف بنجاح إلى {len(toc)} ملفات"

        except Exception as e:
            return False, f"خطأ في تقسيم الملف: {str(e)}"

    @staticmethod
    def split_pdf_by_pages(pdf_path, output_dir, pages_per_file):
        """Split PDF into chunks of specified pages"""
        try:
            doc = fitz.open(pdf_path)
            total_pages = doc.page_count

            for start in range(0, total_pages, pages_per_file):
                end = min(start + pages_per_file, total_pages)

                new_doc = fitz.open()
                new_doc.insert_pdf(doc, from_page=start, to_page=end - 1)

                output_path = os.path.join(output_dir, f"split_{start+1}-{end}.pdf")
                new_doc.save(output_path)
                new_doc.close()

            doc.close()
            return (
                True,
                f"تم تقسيم الملف بنجاح إلى {(total_pages + pages_per_file - 1) // pages_per_file} ملفات",
            )

        except Exception as e:
            return False, f"خطأ في تقسيم الملف: {str(e)}"

    @staticmethod
    def split_pdf_by_ranges(pdf_path, output_dir, ranges):
        """Split PDF by specified page ranges"""
        try:
            doc = fitz.open(pdf_path)

            for i, page_range in enumerate(ranges):
                start, end = page_range

                new_doc = fitz.open()
                new_doc.insert_pdf(doc, from_page=start - 1, to_page=end - 1)

                output_path = os.path.join(output_dir, f"split_{start}-{end}.pdf")
                new_doc.save(output_path)
                new_doc.close()

            doc.close()
            return True, f"تم تقسيم الملف بنجاح إلى {len(ranges)} ملفات"

        except Exception as e:
            return False, f"خطأ في تقسيم الملف: {str(e)}"

    @staticmethod
    def merge_pdfs(
        pdf_paths,
        output_path,
        merge_bookmarks=True,
        create_outline=True,
        progress_callback=None,
    ):
        """Merge multiple PDFs with options and progress reporting"""
        try:
            merged_doc = fitz.open()
            outline = []
            current_page = 0

            for i, pdf_path in enumerate(pdf_paths):
                doc = fitz.open(pdf_path)

                # Add document to merged file
                merged_doc.insert_pdf(doc)

                if create_outline:
                    # Add file name to outline
                    name = os.path.splitext(os.path.basename(pdf_path))[0]
                    outline.append([1, name, current_page + 1])

                if merge_bookmarks:
                    # Get and adjust bookmarks
                    toc = doc.get_toc()
                    for item in toc:
                        level, title, page = item[:3]
                        outline.append([level, title, page + current_page])

                current_page += doc.page_count
                doc.close()

                # Report progress
                if progress_callback:
                    progress_callback(i + 1)

            if outline:
                merged_doc.set_toc(outline)

            merged_doc.save(output_path)
            merged_doc.close()

            return True, f"تم دمج الملفات بنجاح وحفظها في:\n{output_path}"

        except Exception as e:
            return False, f"خطأ أثناء دمج الملفات: {str(e)}"
