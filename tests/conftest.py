import pytest
from pathlib import Path
from PIL import Image, ImageDraw


@pytest.fixture
def sample_image_path(tmp_path: Path) -> Path:
    """Create a simple image with known text for testing."""
    img = Image.new("RGB", (400, 100), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 30), "Hello World", fill="black")
    path = tmp_path / "test_image.png"
    img.save(path)
    return path


@pytest.fixture
def sample_image(sample_image_path: Path) -> Image.Image:
    return Image.open(sample_image_path)
