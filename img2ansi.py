#!/usr/bin/env python3
import argparse
import math
import signal
import sys
import os
from PIL import Image

def calculate_brightness(img):
    histogram = img.histogram()
    pixels = sum(histogram)
    brightness = scale = len(histogram)

    for index in range(0, scale):
        ratio = histogram[index] / pixels
        brightness += ratio * (-scale + index)

    return brightness

def clamp(num):
    min_value = min_bright + ((max_bright - min_bright) / 5 * 1 - ((max_bright - min_bright) / 10))
    max_value = min_bright + ((max_bright - min_bright) / 5 * 5 - ((max_bright - min_bright) / 10))
    return max(min(num, max_value), min_value)

def determine_char(img_char, error):
    tl_img = img_char.crop((0,          0,           width_floor, height_floor))
    tr_img = img_char.crop((width_ceil, 0,           char_width,  height_floor))
    bl_img = img_char.crop((0,          height_ceil, width_floor, char_height))
    br_img = img_char.crop((width_ceil, height_ceil, char_width,  char_height))

    tl = calculate_brightness(tl_img)
    tr = calculate_brightness(tr_img)
    bl = calculate_brightness(bl_img)
    br = calculate_brightness(br_img)

    l = (tl + bl) / 2
    t = (tl + tr) / 2
    r = (tr + br) / 2
    b = (bl + br) / 2

    old_pixel = (tl + tr + bl + br) / 4
    old_pixel = clamp(old_pixel) + error
    new_pixel = min(chars.keys(), key=lambda x: abs(x - old_pixel))
    error = old_pixel - new_pixel

    if math.fabs(tl - tr) < bright_diff_2 and math.fabs(bl - br) < bright_diff_2 and math.fabs(t - b) > bright_diff_1:
        if t > b:
            char = '▀'
        else:
            char = '▄'
    elif math.fabs(tl - bl) < bright_diff_2 and math.fabs(tr - br) < bright_diff_2 and math.fabs(l - r) > bright_diff_1:
        if l > r:
            char = '▌'
        else:
            char = '▐'
    else:
        char = chars[new_pixel]

    return char, error

parser = argparse.ArgumentParser(add_help=False, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('-h', '--help',
                    action='help',
                    default=argparse.SUPPRESS,
                    help='show help message')
parser.add_argument('-v', '--version',
                    action='version',
                    version='img2ansi 1.0',
                    help='show version')
parser.add_argument('-i', '--images',
                    nargs='*',
                    default=argparse.SUPPRESS,
                    help='image sources')
parser.add_argument('-s', '--char-size',
                    default='8x16',
                    help='character size')
parser.add_argument('-d', '--dither',
                    action='store_true',
                    help='use Floyd–Steinberg dithering')
parser.add_argument('-t', '--threshold',
                    default='20',
                    help='brightness threshold in percentage for half block')
parser.add_argument('-min', '--min-brightness',
                    default='0',
                    help='minimum brightness of image(s)')
parser.add_argument('-max', '--max-brightness',
                    default='170',
                    help='maximum brightness of image(s)')
args = parser.parse_args()

if len(sys.argv) == 1:
    parser.print_help(sys.stderr)
    sys.exit(1)

signal.signal(signal.SIGINT, signal.SIG_DFL)

char_width = int(args.char_size.split('x')[0])
char_height = int(args.char_size.split('x')[1])
width_ceil = math.ceil(char_width / 2)
width_floor = math.floor(char_width / 2)
height_ceil = math.ceil(char_height / 2)
height_floor = math.floor(char_height / 2)

max_bright = int(args.max_brightness)
min_bright = int(args.min_brightness)
threshold = int(args.threshold)

chars = {
    min_bright + ((max_bright - min_bright) / 5 * 1 - ((max_bright - min_bright) / 10)): ' ',
    min_bright + ((max_bright - min_bright) / 5 * 2 - ((max_bright - min_bright) / 10)): '░',
    min_bright + ((max_bright - min_bright) / 5 * 3 - ((max_bright - min_bright) / 10)): '▒',
    min_bright + ((max_bright - min_bright) / 5 * 4 - ((max_bright - min_bright) / 10)): '▓',
    min_bright + ((max_bright - min_bright) / 5 * 5 - ((max_bright - min_bright) / 10)): '█',
}

if (max_bright <= min_bright):
    print('max brightness has to be greater than min brightness')
    sys.exit(0)

bright_diff_1 = (max_bright - min_bright) / (100 / threshold)
bright_diff_2 = bright_diff_1 / 2

for fl in args.images:
    basename = os.path.basename(fl)
    file_output = os.path.splitext(basename)[0] + '.nfo'

    img = Image.open(fl)
    img = img.convert('L')

    width, height = img.size
    lines = math.floor(height / char_height)
    columns = math.floor(width / char_width)

    pos_y = 0
    error_row_1 = [0] * (columns + 2)
    error_row_2 = [0] * (columns + 2)
    quant_error = 0
    file_content = ''
    for l in range(lines):
        pos_x = 0
        for c in range(columns):
            if args.dither:
                error_row_1[c+2] = error_row_1[c+2] + quant_error * 7 / 16
                error_row_2[c+0] = error_row_2[c+0] + quant_error * 3 / 16
                error_row_2[c+1] = error_row_2[c+1] + quant_error * 5 / 16
                error_row_2[c+2] = error_row_2[c+2] + quant_error * 1 / 16
            char_img = img.crop((pos_x, pos_y, pos_x + char_width, pos_y + char_height))
            char, quant_error = determine_char(char_img, error_row_1[c+2])
            file_content += char
            pos_x += char_width
        error_row_1 = error_row_2
        error_row_2 = [0] * (columns + 2)
        pos_y += char_height
        file_content = file_content.rstrip()
        file_content += '\n'
        percent = ((l + 1) / lines) * 100
        print('\r{}: {:.2f}%'.format(basename, percent), end='')
    f = open(file_output, "w", encoding='CP437')
    f.write(file_content)
    f.close()
    print()
