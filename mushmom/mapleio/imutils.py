"""
Image utils to help to manipulate sprites

"""

import numpy as np

from PIL import Image
from typing import Union, Iterable, Optional
from itertools import cycle
from io import BytesIO


def min_width(img: Image.Image, width: int) -> Image.Image:
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


def thresh_alpha(img: Image.Image, thresh: int = 128) -> Image.Image:
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


def get_bbox(
        im: Union[Iterable[Image.Image], Image.Image],
        ignore: Optional[tuple[int, int, int, int]] = None,
) -> tuple[int, int, int, int]:
    """
    Make color transparent and get bounding box for all frames

    Parameters
    ----------
    im: im: Union[Iterable[Image.Image], Image.Image]
        the image or list of frames
    ignore: Optional[tuple[int, int, int, int]]
        an RGBA color to use as transparent

    Returns
    -------
    Coordinates for bounding box

    """
    if isinstance(im, Image.Image):
        im = [im]

    bboxes = []
    for frame in im:
        if ignore:
            data = np.array(frame)
            r, g, b, a = data.T  # transpose
            _r, _g, _b, _a = ignore
            mask = (r == _r) & (g == _g) & (b == _b) & (a == _a)
            data[:, :, :4][mask.T] = (0, 0, 0, 0)  # untranspose mask
            bboxes.append(Image.fromarray(data).getbbox())
        else:
            bboxes.append(frame.getbbox())

    T = list(zip(*bboxes))  # transpose
    bbox = [min(x) for x in T[:2]] + [max(x) for x in T[2:]]
    return tuple(bbox)


def merge(
        im1: Union[Image.Image, Iterable[Image.Image]],
        im2: Union[Image.Image, Iterable[Image.Image]],
        pad: int = 40,
        z_order: int = 1,  # -1 = im2 on top of im1
        bgcolor: tuple[int] = (0, 0, 0, 0)
) -> Image.Image:
    """
    Merge into one image with mid widths separated by pad. If
    Iterable passed then alternate pasting layers

    Parameters
    ----------
    im1: Union[Image.Image, Iterable[Image.Image]]
        image on the left
    im2: Union[Image.Image, Iterable[Image.Image]]
        image on the right
    pad: int
        padding between the two images
    z_order: int
        1 if im1 is on top, -1 if im2 is on top
    bgcolor: tuple[int]
        background color of merged image

    Returns
    -------
    the merged image


    """
    if isinstance(im1, Image.Image):
        im1 = [im1]

    if isinstance(im2, Image.Image):
        im2 = [im2]

    n = max(len(im1), len(im2))
    cyc1, cyc2 = cycle(reversed(im1)), cycle(reversed(im2))

    # get output size
    # handle one image much longer than the other
    a, b = im1[0], im2[0]
    w = max(a.width, b.width, sum((a.width, b.width))//2 + pad)
    h = max(a.height, b.height)

    # generate output image
    res = Image.new('RGBA', (w, h), bgcolor)
    for i in range(n):
        l, r = next(cyc1), next(cyc2)
        layers = [  # first is underneath
            (r, (w-r.width, (h-r.height)//2)),
            (l, (0, (h-l.height)//2))
        ]

        for im, pos in (layers if z_order == 1 else reversed(layers)):
            res.paste(im, pos, mask=im)

    return res


def apply_background(
        im: Union[bytes, Image.Image],
        bg: Union[bytes, Image.Image, str],
        y_feet: Optional[int] = None,
        y_ground: Optional[int] = None,
) -> Optional[bytes]:
    """
    Apply background to the image

    Parameters
    ----------
    im: Union[bytes, Image]
        character data (should be FeetCenter)
    bg: Union[bytes, Image, tuple]
        background image data or RGBA color
    y_feet: Optional[int]
        pixels from bottom for feet in source image.  Default half height
    y_ground: Optional[int]
        pixels from bottom for ground in background.  Default max y

    Returns
    -------
    Optional[bytes]
        bytes of the generated image

    """
    # format image
    if isinstance(im, bytes):
        im = Image.open(BytesIO(im))

    w_im, h_im = im.size

    # format bg
    if isinstance(bg, bytes):
        bg = Image.open(BytesIO(bg)).convert('RGBA')
    elif isinstance(bg, tuple):
        bg = Image.new('RGBA', im.size, bg)

    w_bg, h_bg = bg.size

    # check if image bigger than background
    y_feet = y_feet or h_im//2
    y_ground = y_ground or h_bg
    if ((h_im-y_feet) > (h_bg-y_ground)) | (w_im > w_bg):
        return

    # paste center horizontal. vertical adjust for feet and ground pos
    bg.paste(im, ((w_bg - w_im)//2, (h_bg - h_im + y_feet - y_ground)), mask=im)

    byte_arr = BytesIO()
    bg.save(byte_arr, format='PNG')
    return byte_arr.getvalue()
