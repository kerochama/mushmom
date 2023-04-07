"""
Image utils to help to manipulate sprites

"""

from PIL import Image
from io import BytesIO
from aenum import Enum


def min_width(img: Image, width: int) -> Image:
    """
    Ensure image is wider than min width

    Parameters
    ----------
    img: Image
      source image
    width: int
      minimum width

    Returns
    -------
    Formatted image

    """
    w, h = img.size

    if w < width:
        res = Image.new('RGBA', (width, h))
        res.paste(img, (0, 0))
    else:
        res = img

    return res
