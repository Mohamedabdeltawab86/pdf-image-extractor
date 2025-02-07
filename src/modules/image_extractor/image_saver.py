# src/modules/image_extractor/image_saver.py
import io
from PIL import Image
import os
def save_image(image_bytes, output_dir, image_filename, should_invert=False):
    """Saves an image to the specified directory.

    Args:
        image_bytes: The image data as a byte string.
        output_dir: The directory to save the image.
        image_filename: The name of the file to save.
        should_invert: Whether to invert image.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))

        if should_invert:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img = Image.eval(img, lambda x: 255 - x)

        output_path = os.path.join(output_dir, image_filename)

        img.save(output_path)


    except Exception as e:
        print(f"Error saving image: {e}")