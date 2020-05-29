#!/usr/bin/env python3
import argparse
import os
import subprocess
from PIL import Image, ImageSequence

# Crikey!  heatshrink is rather cool, eh?  If you give it ~4.5KiB then it will
# a# for decompression buffers then it can do better than GIF89a
# https://github.com/atomicobject/heatshrink
# use the 'develop' branch which has many years of bugfixes over 'master'
hs_path = './heatshrink'

parser = argparse.ArgumentParser(description='Converts GIFs to a custom format for playback on microcontrollers')
parser.add_argument('-w', '--window', type=int, default=8, help='heatshrink window size (5 to 11)')
parser.add_argument('-l', '--lookahead', type=int, default=7, help='heatshrink lookahead size (3 to 1 less than --window)')
parser.add_argument('--blacken', action='store_true', help='force the declared background/transparency palette entry to black')
# TODO parser.add_argument('--benchmark', action='store_true', help='try all compression setting combos')
parser.add_argument('input_file', type=str, help='filename of the GIF to convert')
parser.add_argument('output_file', type=str, nargs='?', help='filename of the GIF to convert')
args = parser.parse_args()

if args.lookahead >= args.window or args.lookahead < 3:
    raise ValueError('Lookahead must be between 3 and Windowsize - 1')
if args.window < 4 or args.window > 15:
    raise ValueError('Window must be between 4 and 15')

# use the output filename if supplied, else generate one from the input
basepath = os.path.splitext(args.input_file)[0]
if args.output_file:
    basepath = os.path.splitext(args.output_file)[0]
else:
    args.output_file = basepath + '.h'
basename = os.path.basename(basepath)

if args.input_file == args.output_file:
    raise ValueError('Refusing to overwrite input file with output file.')

gif = Image.open(args.input_file)

if (gif.size != (16, 16)):
    print('The .ino & .h file must be modified to use images sized other than 16x16.\n'
          'This image is %dx%d.  Good luck with that!\n' % (gif.size[0], gif.size[1]))

# allocate whatever the GIF uses as the background index to our palette index 0
# or the declared transparent colour if any.
gif.compression_log = []
gif.palette_i = 0 # a "pointer" to the next fwd slot to populate
gif.palette_fwd_map = [None] * 256
gif.palette_bwd_map = [None] * 256
b = 0
if 'background' in gif.info:
    b = gif.info['background']
if 'transparency' in gif.info:
    b = gif.info['transparency']
    gif.compression_log += ['// using GIF index %d as our transparency index 0%s\n' 
        % (b, ' (blackened)' if args.blacken else '')]
gif.palette_fwd_map[b] = gif.palette_i
gif.palette_bwd_map[gif.palette_i] = b
gif.palette_i += 1
if not args.blacken:
    gif.final_palette = bytearray(gif.global_palette.palette[b*3:(b+1)*3])
else:
    gif.final_palette = bytearray([0, 0, 0])

# find the palette indices actually used by the images and relocate them to
# the lowest indices. Coalesce any duped RGB triplets. Aggregate all frames'
# pixels to help compression ratio.
gif.info['frames'] = 0
gif.pixels_raw = bytearray()
for frame in ImageSequence.Iterator(gif):
    if frame.palette.palette != gif.global_palette.palette:
        raise ValueError('GIF palette is modified between frames. Unsupported currently.')
    for pixel in frame.getdata():
        if gif.palette_fwd_map[pixel] is not None:
            gif.pixels_raw.append(gif.palette_fwd_map[pixel])
            continue
        rgb = bytearray(gif.global_palette.palette[pixel*3:(pixel+1)*3])
        i = -1
        if rgb in gif.final_palette[3:0]:
            i = gif.final_palette.index(rgb)
        if i < 1:  # don't remap anything to our transparency index
            gif.final_palette += rgb
            gif.pixels_raw.append(gif.palette_i)
            gif.palette_fwd_map[pixel] = gif.palette_i
            gif.palette_bwd_map[gif.palette_i] = pixel
            gif.palette_i += 1
        else:
            # i = gif.final_palette.index(rgb)
            gif.compression_log += ['// dupe RGB at GIF palette index %d;  remapping to our existing index %d\n' % (pixel, i)]
            gif.pixels_raw.append(i)
            gif.palette_fwd_map[pixel] = i
    gif.info['frames'] += 1
    # break   # TODO
#     print('.', endl='')
# print()

# compress all the palettes and pixels with heatshrink
this_hs_cmd = [hs_path, '-w', str(args.window), '-l', str(args.lookahead)]
gif.compression_payload = gif.final_palette + gif.pixels_raw
with subprocess.Popen(this_hs_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
    gif.heatshrink_bytes, gif.heatshrink_stderrdata = proc.communicate(gif.compression_payload)

size_struct_params = 8   # 8 bytes struct housekeeping
size_payload_hs = len(gif.heatshrink_bytes)
size_palette = len(gif.final_palette) * 3 * 0 # embedded in compressed stream now
size_total = size_payload_hs + size_struct_params + size_palette
size_raw = len(gif.pixels_raw)
size_payload_raw = len(gif.compression_payload)
size_gif = os.path.getsize(args.input_file)
size_gif_pct = (100. * size_total) / size_gif
size_raw_pct = (100. * size_total) / size_payload_raw

gif.compression_log.insert(0, 
    '// "%s" (GIF orig:%d raw_payload:%d shrunk_payload:%d total:%d bytes)\n'
    '// Compared to GIF: %.2f%% \tCompared to raw: %.2f%%\n' % (
    basename, size_gif, size_payload_raw, size_payload_hs, size_total,
    size_gif_pct, size_raw_pct))
gif.compression_log += ['// ' + ' '.join(this_hs_cmd) + ' (']
for i in 'background', 'loop', 'transparency', 'mode':
    if i not in gif.info:
        continue 
    gif.compression_log += ['%s = %d; ' % (i, gif.info[i])]
gif.compression_log += [')\n']

# write the .h file
h = open(args.output_file, 'w')
print(''.join(gif.compression_log), file=h)

print('FL_PROGMEM const struct HSpr_%s {' % (basename), file=h)
print('\tuint16_t datasize = %d;' % (len(gif.heatshrink_bytes)), file=h)
print('\tuint16_t frames = %d;' % (gif.info['frames']), file=h)
print('\tuint16_t duration = %d;' % (gif.info['duration']), file=h)
print('\tuint8_t flags = %d;' % (0), file=h)
print('\tuint8_t palette_entries = %d;' % (len(gif.final_palette) // 3), file=h)

print('\tuint8_t crgb[%d] = {' % (size_palette), file=h)
# print(gif.final_palette)
# print(gif.palette_fwd_map)
comment = ''
if not size_palette:
    comment = '// '
for i, pal in enumerate([gif.final_palette[i:i+3] for i in range(0, len(gif.final_palette), 3)]):
    rev = gif.palette_bwd_map[i]
    r, g, b = pal
    # print(i, rev, r, g, b)
    print('\t\t%s0x%02x, 0x%02x, 0x%02x,  // original palette index %d' % (comment, r, g, b, rev), file=h)
print('\t};', file=h)

print('\tuint8_t hs_data[%d] = {' % (len(gif.heatshrink_bytes)), file=h, end='')
for i, byte in enumerate(gif.heatshrink_bytes):
    if i % 16 == 0:
        print('\n\t\t', file=h, end='')
    print('0x%02x, ' % (byte), file=h, end='')
print('\n\t};', file=h)
print('} HSpr_%s;' % (basename), file=h)

h.close()

include = '#include "GIF/%s.h"' % (basename)
include += ' ' * (51 - len(include))
print(include + '//%5d bytes%4d cols%4d frame%s Compared to GIF: %3.2f%%' %
    (size_total, len(gif.final_palette) // 3, gif.info['frames'], 
    ' ' if gif.info['frames'] == 1 else 's', size_gif_pct))

exit()
