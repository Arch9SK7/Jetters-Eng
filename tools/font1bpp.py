#!/usr/bin/env python3
"""
font1bpp.py - convert the story-mode font image (assets/Font.bmp) to build/Font.bin.

    python tools/font1bpp.py assets/Font.bmp build/Font.bin
"""
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit('Pillow is required: pip install pillow')


def convert(src, dst):
    im = Image.open(src).convert('RGB')
    w, h = im.size
    if w % 8 or h % 8:
        sys.exit('%s: width and height must be multiples of 8 (got %dx%d)' % (src, w, h))
    px = im.load()
    background = max(im.getcolors(maxcolors=w * h), key=lambda c: c[0])[1]
    cols, rows = w // 8, h // 8
    out = bytearray()
    for gy in range(rows):
        for gx in range(cols):
            for y in range(8):
                b = 0
                for x in range(8):
                    if px[gx * 8 + x, gy * 8 + y] != background:
                        b |= 0x80 >> x
                out.append(b)
    with open(dst, 'wb') as f:
        f.write(out)
    print('%s -> %s: %d glyphs (background colour %s)' % (src, dst, cols * rows, '#%02X%02X%02X' % background))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    convert(sys.argv[1], sys.argv[2])
