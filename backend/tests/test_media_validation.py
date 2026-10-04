import io
import unittest

from app.utils.media_validation import (
    validate_media_file,
    guess_media_type,
    ALLOWED_IMAGE_EXTENSIONS,
)


def _make_valid_png() -> bytes:
    """Generate a real 1x1 PNG so Pillow's integrity checks pass."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (1, 1), (0, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


VALID_PNG = _make_valid_png()

# A minimal valid MP4 header signature (starts with 4-byte size + 'ftyp').
VALID_MP4 = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2mp41"

OVERSIZE = b"x" * (11 * 1024 * 1024)


class MediaValidationTests(unittest.TestCase):
    def test_valid_png_returns_image(self):
        media_type, content_type = validate_media_file("photo.png", "image/png", VALID_PNG)
        self.assertEqual(media_type, "image")
        self.assertEqual(content_type, "image/png")

    def test_valid_mp4_returns_video(self):
        media_type, content_type = validate_media_file("clip.mp4", "video/mp4", VALID_MP4)
        self.assertEqual(media_type, "video")

    def test_unsupported_extension_rejected(self):
        with self.assertRaises(ValueError):
            validate_media_file("evil.exe", None, b"MZ\x90\x00")

    def test_oversized_file_rejected(self):
        with self.assertRaises(ValueError):
            validate_media_file("big.png", "image/png", OVERSIZE)

    def test_empty_file_rejected(self):
        with self.assertRaises(ValueError):
            validate_media_file("empty.png", "image/png", b"")

    def test_spoofed_image_rejected(self):
        # Fake 'png' that is actually arbitrary text: Pillow must reject it.
        with self.assertRaises(ValueError):
            validate_media_file("fake.png", "image/png", b"this is definitely not a png image")

    def test_guess_media_type_by_extension(self):
        self.assertEqual(guess_media_type("a.JPG", None), "image")
        self.assertEqual(guess_media_type("b.webm", None), "video")
        self.assertIsNone(guess_media_type("c.txt", "text/plain"))


if __name__ == "__main__":
    unittest.main()