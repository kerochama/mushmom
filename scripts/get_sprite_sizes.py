"""
Grab default sprite sizes for body and head. Run once and save as consts,
but how they were generated

Known: 2px border around sprites

"""
import json
import requests

from PIL import Image
from io import BytesIO
from urllib import parse


_NO_BODY = [{"itemId": 2000, "version": "225"},
            {"itemId": 12000,"version": "225", "alpha": 0}]
_NO_HEAD = [{"itemId": 2000, "version": "225", "alpha": 0},
            {"itemId": 12000,"version": "225"}]


def pct_encode(d):
    """
    Percent encode items for API call

    :param d:
    :return:
    """
    return parse.quote(json.dumps(d)
                       .lstrip('[').rstrip(']')
                       .replace(', ', ',').replace(': ', ':'))


def get_body_height():
    """
    Get body with transparent head. Get height of body from bottom

    Known: 2 transparent rows at bottom

    :return:
    """
    url = f'https://maplestory.io/api/character/{pct_encode(_NO_BODY)}/stand1/0'
    ret = requests.get(url)

    if ret.status_code == 200:
        img = Image.open(BytesIO(ret.content))
        r, g, b, a = img.split()
        w, h = a.size

        # get first non-zero row (not transparent)
        byte_array = list(a.getdata())
        non0 = [any(byte_array[w * i:w * (i+1)]) for i in range(h)]
        row1 = next((i for i, x in enumerate(non0) if x), None)  # first row

        return h - row1

