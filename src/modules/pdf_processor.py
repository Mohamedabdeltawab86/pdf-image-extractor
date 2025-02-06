import fitz
from pathlib import Path
from ..util.image_handler import save_image


def extract_images_from_pdf(pdf_path, output_dir, skip_small=True, min_size=100):
    """
    Extract images from a PDF file and save them to the specified directory.

    Args:
        pdf_path (str): Path to the PDF file
        output_dir (str): Directory where images will be saved
        skip_small (bool): Skip small images that might be icons or artifacts
        min_size (int): Minimum width/height for images to be extracted
    """
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Open the PDF
    pdf_document = fitz.open(pdf_path)
    image_count = 0

    # Iterate through each page
    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        images = page.get_images()

        # Iterate through images on the page
        for img_index, img in enumerate(images):
            xref = img[0]
            base_image = pdf_document.extract_image(xref)

            if base_image:
                # Get image info
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                width = base_image.get("width", 0)
                height = base_image.get("height", 0)

                # Skip small images if requested
                if skip_small and (width < min_size or height < min_size):
                    print(
                        f"Skipping small image on page {page_num + 1} ({width}x{height})"
                    )
                    continue

                image_filename = f"image_{page_num + 1}_{img_index + 1}.{image_ext}"

                if save_image(image_bytes, output_dir, image_filename):
                    image_count += 1
                    print(f"Saved {image_filename} ({width}x{height})")

    pdf_document.close()
    return image_count
