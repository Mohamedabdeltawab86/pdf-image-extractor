import os
from PIL import Image
import io
from pptx import Presentation
from pptx.util import Inches
from pptx.dml.color import RGBColor
import subprocess
import platform


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
