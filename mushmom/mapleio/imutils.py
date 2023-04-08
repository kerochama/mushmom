"""
Image utils to help to manipulate sprites

"""

import numpy as np

from PIL import Image
from io import BytesIO


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


def thresh_alpha(img: Image, thresh: int = 128) -> Image:
    """
    Round alpha channel to 0 or 255

    Parameters
    ----------
    img: Image
      source image
    thresh: int
      threshold value

    Returns
    -------
    Resulting image

    """
    res = img.copy()
    _alpha = res.getchannel('A')

    # manipulate array
    arr = np.array(_alpha)
    arr[arr < thresh] = 0
    arr[arr >= thresh] = 255

    # update alpha channel
    alpha = Image.fromarray(arr)
    res.putalpha(alpha)
    return res

