"""
Image preprocessing for Wan2.2 inference
"""
from PIL import Image, ImageOps
from pathlib import Path
from typing import Tuple


# ti2v-5B supported sizes
SUPPORTED_SIZES = {
    'landscape': (1280, 704),  # 가로형 (16:9 비율)
    'portrait': (704, 1280)     # 세로형 (9:16 비율)
}


def get_target_size(image_width: int, image_height: int) -> Tuple[int, int]:
    """
    Determine target size based on image aspect ratio

    Args:
        image_width: Input image width
        image_height: Input image height

    Returns:
        (width, height) tuple for target size
    """
    aspect_ratio = image_width / image_height

    # If wider than tall, use landscape
    if aspect_ratio >= 1.0:
        return SUPPORTED_SIZES['landscape']
    else:
        return SUPPORTED_SIZES['portrait']


def resize_and_pad(image: Image.Image, target_size: Tuple[int, int],
                   pad_color: Tuple[int, int, int] = (0, 0, 0)) -> Image.Image:
    """
    Resize image to fit target size while maintaining aspect ratio,
    then pad to exact target size

    Args:
        image: PIL Image
        target_size: (width, height) target dimensions
        pad_color: RGB color for padding (default: black)

    Returns:
        Processed PIL Image
    """
    target_width, target_height = target_size

    # Calculate scaling to fit within target size
    img_ratio = image.width / image.height
    target_ratio = target_width / target_height

    if img_ratio > target_ratio:
        # Image is wider, fit by width
        new_width = target_width
        new_height = int(target_width / img_ratio)
    else:
        # Image is taller, fit by height
        new_height = target_height
        new_width = int(target_height * img_ratio)

    # Resize image
    resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Create new image with target size and pad color
    padded = Image.new('RGB', target_size, pad_color)

    # Paste resized image centered
    paste_x = (target_width - new_width) // 2
    paste_y = (target_height - new_height) // 2
    padded.paste(resized, (paste_x, paste_y))

    return padded


def preprocess_image(input_path: str, output_path: str = None,
                    pad_color: Tuple[int, int, int] = (0, 0, 0)) -> Tuple[str, str]:
    """
    Preprocess image for Wan2.2 inference

    Args:
        input_path: Path to input image
        output_path: Path to save processed image (optional, overwrites input if None)
        pad_color: RGB color for padding (default: black)

    Returns:
        (processed_image_path, size_string) tuple
        size_string is like "1280*704" or "704*1280"

    Raises:
        FileNotFoundError if input image doesn't exist
    """
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input image not found: {input_path}")

    # Load image
    image = Image.open(input_path)

    # Convert to RGB if needed
    if image.mode != 'RGB':
        image = image.convert('RGB')

    # Determine target size based on aspect ratio
    target_size = get_target_size(image.width, image.height)

    # Resize and pad
    processed = resize_and_pad(image, target_size, pad_color)

    # Save
    if output_path is None:
        output_path = input_path

    processed.save(output_path, quality=95)

    # Return path and size string
    size_string = f"{target_size[0]}*{target_size[1]}"

    return output_path, size_string


def get_size_for_image(image_path: str) -> str:
    """
    Get appropriate size string for an image without processing it

    Args:
        image_path: Path to image

    Returns:
        Size string like "1280*704" or "704*1280"
    """
    image = Image.open(image_path)
    target_size = get_target_size(image.width, image.height)
    return f"{target_size[0]}*{target_size[1]}"
