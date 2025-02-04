import unittest
import os
from pathlib import Path
from src.core.pdf_processor import extract_images_from_pdf
from src.util.image_handler import save_image
from PIL import Image
import io


class TestPDFProcessor(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_dir = Path("tests/test_files")
        self.output_dir = Path("tests/test_output")

        # Create test directories if they don't exist
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Path to a sample PDF for testing
        self.sample_pdf = self.test_dir / "sample.pdf"

    def tearDown(self):
        """Clean up after each test method."""
        # Remove all files in the output directory
        for file in self.output_dir.glob("*"):
            file.unlink()

    def test_extract_images_with_invalid_pdf(self):
        """Test handling of non-existent PDF file."""
        with self.assertRaises(Exception):
            extract_images_from_pdf("nonexistent.pdf", str(self.output_dir))

    def test_extract_images_with_valid_pdf(self):
        """Test extraction from a valid PDF file."""
        # Skip if sample PDF doesn't exist
        if not self.sample_pdf.exists():
            self.skipTest("Sample PDF file not found")

        # Extract images
        num_images = extract_images_from_pdf(str(self.sample_pdf), str(self.output_dir))

        # Check if images were extracted
        self.assertGreater(num_images, 0, "No images were extracted")

        # Check if files were created
        extracted_files = list(self.output_dir.glob("*"))
        self.assertEqual(
            len(extracted_files),
            num_images,
            "Number of files doesn't match extraction count",
        )


class TestImageHandler(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.output_dir = Path("tests/test_output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Clean up after each test method."""
        for file in self.output_dir.glob("*"):
            file.unlink()

    def test_save_image(self):
        """Test saving and inverting an image."""
        # Create a simple test image
        test_image = Image.new("RGB", (100, 100), color="white")
        buffer = io.BytesIO()
        test_image.save(buffer, format="JPEG")
        image_bytes = buffer.getvalue()

        # Save and invert the image
        result = save_image(image_bytes, str(self.output_dir), "test.jpg")

        # Check if save was successful
        self.assertTrue(result, "Image save failed")

        # Check if file exists
        saved_file = self.output_dir / "test.jpg"
        self.assertTrue(saved_file.exists(), "Saved file not found")

        # Check if image is valid and inverted
        saved_image = Image.open(saved_file)
        self.assertEqual(saved_image.mode, "RGB", "Image mode is not RGB")

        # Check a sample pixel to verify inversion
        pixel = saved_image.getpixel((0, 0))
        self.assertTrue(
            all(x < 128 for x in pixel), "Image doesn't appear to be inverted"
        )


def create_sample_pdf():
    """
    Helper function to create a sample PDF for testing.
    You would need to implement this based on your needs.
    """
    pass


if __name__ == "__main__":
    unittest.main()
