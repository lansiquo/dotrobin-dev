#!/usr/bin/env python3
"""Tests for the image metadata check in check_site.py. Standard library only.

Usage: python3 .github/scripts/test_check_site.py

Every image is built here from bytes, so no photo or image tool is needed.
The PNG files decode as real images. The WebP and JPEG files are well-formed
containers with filler where the pixels would be, because the check reads the
container and never decodes pixels.
"""
import contextlib
import io
import pathlib
import struct
import sys
import tempfile
import unittest
import zlib
from unittest import mock

sys.dont_write_bytecode = True  # leave no __pycache__ folder in the repository
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_site  # noqa: E402

NEAR, LATE = 1_000, 70_000  # filler bytes ahead of the metadata; 70,000 is past 64 KiB
TIFF = b"II*\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00"  # an EXIF block with no tags
XMP = b"<x:xmpmeta xmlns:x='adobe:ns:meta/'/>"
EXIF_FOUND = ["image still has EXIF metadata"]


def png_chunk(kind, data=b""):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def png(filler, *chunks):
    """A one-row greyscale PNG with `filler` bytes of pixel data, then `chunks`."""
    header = struct.pack(">IIBBBBB", filler - 1, 1, 8, 0, 0, 0, 0)
    pixels = zlib.compress(bytes(filler), 0)
    return (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", header) + png_chunk(b"sRGB", b"\x00")
            + png_chunk(b"IDAT", pixels) + b"".join(chunks) + png_chunk(b"IEND"))


def webp_chunk(kind, data=b""):
    return kind + struct.pack("<I", len(data)) + data + bytes(len(data) % 2)


def webp(filler, *chunks):
    """A WebP container with `filler` bytes in the image chunk, then `chunks`."""
    body = b"WEBP" + webp_chunk(b"VP8X", bytes(10)) + webp_chunk(b"VP8 ", bytes(filler)) + b"".join(chunks)
    return b"RIFF" + struct.pack("<I", len(body)) + body


def jpeg_segment(marker, data=b""):
    return bytes([0xFF, marker]) + struct.pack(">H", len(data) + 2) + data


def jpeg(filler, *segments):
    """A JPEG container with `filler` bytes of other segments, then `segments`."""
    padding = b"".join(jpeg_segment(0xE2, bytes(min(35_000, filler - done)))
                       for done in range(0, filler, 35_000))
    return b"\xff\xd8" + jpeg_segment(0xE0, b"JFIF\x00") + padding + b"".join(segments) + b"\xff\xd9"


PNG_EXIF = png_chunk(b"eXIf", TIFF)
WEBP_EXIF = webp_chunk(b"EXIF", TIFF)
JPEG_EXIF = jpeg_segment(0xE1, b"Exif\x00\x00" + TIFF)


def check(images):
    """Runs the site check on a site holding `images`.

    Returns the exit code and the problems reported for each file.
    """
    with tempfile.TemporaryDirectory() as site:
        for name, data in images.items():
            pathlib.Path(site, name).write_bytes(data)
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["check_site.py", site]), contextlib.redirect_stdout(out):
            code = check_site.main()
    *lines, summary = out.getvalue().splitlines()
    problems = {}
    for line in lines:
        name, _, problem = line.partition(": ")
        problems.setdefault(name, []).append(problem)
    assert summary == f"0 pages checked, {len(lines)} problem(s)", summary
    return code, problems


class ImageMetadataTest(unittest.TestCase):
    def test_exif_is_found_wherever_it_sits_in_the_file(self):
        code, problems = check({
            "control-small.png": png(NEAR, PNG_EXIF),
            "control-small.webp": webp(NEAR, WEBP_EXIF),
            "control-small.jpg": jpeg(NEAR, JPEG_EXIF),
            "late-exif.png": png(LATE, PNG_EXIF),
            "late-exif.webp": webp(LATE, WEBP_EXIF),
            "late-exif.jpg": jpeg(LATE, JPEG_EXIF),
        })
        self.assertEqual(problems, {
            "control-small.png": EXIF_FOUND, "control-small.webp": EXIF_FOUND,
            "control-small.jpg": EXIF_FOUND,
            "late-exif.png": EXIF_FOUND, "late-exif.webp": EXIF_FOUND, "late-exif.jpg": EXIF_FOUND,
        })
        self.assertEqual(code, 1)

    def test_format_is_read_from_the_file_not_its_name(self):
        code, problems = check({"photo.png": jpeg(LATE, JPEG_EXIF), "photo.jpg": webp(LATE, WEBP_EXIF)})
        self.assertEqual(problems, {"photo.png": EXIF_FOUND, "photo.jpg": EXIF_FOUND})
        self.assertEqual(code, 1)

    def test_text_and_xmp_metadata_is_found_wherever_it_sits_in_the_file(self):
        code, problems = check({
            "comment.png": png(LATE, png_chunk(b"tEXt", b"Creation Time\x002026:11:12 06:00:00")),
            "exif-profile.png": png(LATE, png_chunk(
                b"zTXt", b"Raw profile type exif\x00\x00" + zlib.compress(TIFF))),
            "xmp.png": png(LATE, png_chunk(b"iTXt", b"XML:com.adobe.xmp\x00\x00\x00\x00\x00" + XMP)),
            "xmp.webp": webp(LATE, webp_chunk(b"XMP ", XMP)),
            "xmp.jpeg": jpeg(LATE, jpeg_segment(0xE1, b"http://ns.adobe.com/xap/1.0/\x00" + XMP)),
        })
        self.assertEqual(problems, {
            "comment.png": ["image still has text metadata (tEXt chunk)"],
            "exif-profile.png": ["image still has text metadata (zTXt chunk)"],
            "xmp.png": ["image still has text metadata (iTXt chunk)"],
            "xmp.webp": ["image still has XMP metadata"],
            "xmp.jpeg": ["image still has XMP metadata"],
        })
        self.assertEqual(code, 1)

    def test_images_without_metadata_pass(self):
        code, problems = check({
            "small.png": png(NEAR), "small.webp": webp(NEAR), "small.jpg": jpeg(NEAR),
            "large.png": png(LATE), "large.webp": webp(LATE), "large.jpg": jpeg(LATE),
        })
        self.assertEqual(problems, {})
        self.assertEqual(code, 0)

    def test_image_that_cannot_be_read_to_the_end_is_reported(self):
        code, problems = check({
            "cut-short.png": png(LATE, PNG_EXIF)[:66_000],
            "cut-short.webp": webp(LATE, WEBP_EXIF)[:66_000],
            "extra-bytes.png": png(NEAR) + bytes(LATE) + PNG_EXIF,
            "not-an-image.png": b"<svg xmlns='http://www.w3.org/2000/svg'/>",
        })
        self.assertEqual(sorted(problems),
                         ["cut-short.png", "cut-short.webp", "extra-bytes.png", "not-an-image.png"])
        for name, found in problems.items():
            self.assertEqual(len(found), 1, name)
            self.assertIn("image cannot be checked for metadata: ", found[0], name)
        self.assertEqual(code, 1)

    def test_image_over_the_size_limit_is_reported_not_skipped(self):
        images = {"big.png": png(LATE), "big.webp": webp(LATE), "big.jpg": jpeg(LATE)}
        with mock.patch.object(check_site, "MAX_IMAGE_BYTES", 65_536):
            code, problems = check(images)
        self.assertEqual(sorted(problems), ["big.jpg", "big.png", "big.webp"])
        for name, found in problems.items():
            self.assertEqual(
                found, ["image is larger than 65536 bytes, too large to check for metadata"], name)
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
