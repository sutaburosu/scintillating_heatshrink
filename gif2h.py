#!/usr/bin/env python3
"""Converts a 16x16 GIF to a heatshrink-compressed C header for microcontroller playback."""

import argparse
import os
import sys

from PIL import Image, ImageSequence
from PIL import GifImagePlugin

# Keep frames in P mode when they share the global palette,
# preserving original palette indices.
GifImagePlugin.LOADING_STRATEGY = GifImagePlugin.LoadingStrategy.RGB_AFTER_DIFFERENT_PALETTE_ONLY

# Import heatshrink Python encoder (same repo as this script)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_heatshrink_path = os.path.join(_script_dir, 'heatshrink_python')
if _heatshrink_path not in sys.path:
    sys.path.insert(0, _heatshrink_path)
from heatshrink_encoder import compress


class GifConverter:
    """Converts a 16x16 GIF to a heatshrink-compressed C header."""

    def __init__(self, gif_path):
        self.gif = Image.open(gif_path)
        self.gif_path = gif_path
        self.window = 8
        self.lookahead = 7
        self.transparent_idx = 0  # GIF index mapped to our index 0
        self.palette_i = 0         # next free slot in our palette
        self.palette_fwd_map: list[int | None] = [None] * 256  # GIF index -> our index
        self.palette_bwd_map: list[int | None] = [None] * 256  # our index -> GIF index
        self.final_palette = bytearray()
        self.pixels_raw = bytearray()
        self.compression_log: list[str] = []
        self.num_frames = 0
        self._compressed_bytes: bytes | None = None
 

    def _get_palette_source(self):
        """Return the best available palette source (global or first frame)."""
        if self.gif.global_palette and self.gif.global_palette.palette:
            return self.gif.global_palette.palette
        for frame in ImageSequence.Iterator(self.gif):
            if frame.palette and frame.palette.palette:
                return frame.palette.palette
        return None

    def find_transparent_index(self):
        """Find the GIF's background or transparency index to use as our index 0."""
        info = self.gif.info
        bg_index = info.get('background', 0)
        if 'transparency' in info:
            self.transparent_idx = info['transparency']
            self.compression_log.append(
                f'// using GIF index {self.transparent_idx} as our transparency index 0\n'
            )
        else:
            self.transparent_idx = bg_index

        # Map the GIF's background/transparency index to our palette index 0
        self.palette_fwd_map[self.transparent_idx] = self.palette_i
        self.palette_bwd_map[self.palette_i] = self.transparent_idx
        self.palette_i += 1

        # Check for L-mode (grayscale) GIFs with no palette
        if self.gif.mode == 'L' and not self.gif.global_palette:
            self.compression_log.append('// L-mode (grayscale) GIF - synthetic palette\n')
            # Initialize transparent color as black (index 0 is the mask)
            self.final_palette.extend([0, 0, 0])
            # Pre-populate palette with all 256 gray values
            for i in range(256):
                if i == self.transparent_idx:
                    continue
                self.final_palette.extend([i, i, i])
                self.palette_fwd_map[i] = self.palette_i
                self.palette_bwd_map[self.palette_i] = i
                self.palette_i += 1
            return

        # Copy transparent color from palette source
        pal_source = self._get_palette_source()
        start = self.transparent_idx * 3
        self.final_palette.extend(pal_source[start:start + 3])

    def extract_frame_pixels(self, frame):
        """Extract pixel data from a frame, handling P, RGB, RGBA, and L modes.

        Returns an iterable of palette indices (integers).
        """
        pixel_data = frame.get_flattened_data()

        if frame.mode in ('P', 'L'):
            return pixel_data

        # RGB/RGBA mode: map each pixel to the closest palette index
        indices = []
        for pixel in pixel_data:
            red = pixel[0]
            green = pixel[1]
            blue = pixel[2]
            alpha = pixel[3] if len(pixel) == 4 else 255

            if alpha < 128:
                indices.append(0)
                continue

            min_dist = float('inf')
            closest_idx = 0
            for i in range(0, len(self.final_palette), 3):
                dr = red - self.final_palette[i]
                dg = green - self.final_palette[i + 1]
                db = blue - self.final_palette[i + 2]
                dist = dr * dr + dg * dg + db * db
                if dist < min_dist:
                    min_dist = dist
                    closest_idx = i // 3
            indices.append(closest_idx)

        return indices

    def _rebuild_frame_mapping(self, frame_pal):
        """Rebuild palette_fwd_map/bwd_map for a frame with a different local palette."""
        for idx in range(len(frame_pal) // 3):
            if self.palette_fwd_map[idx] is not None:
                continue
            rgb = bytes(frame_pal[idx * 3:(idx + 1) * 3])
            existing_idx = -1
            for i in range(3, len(self.final_palette), 3):
                if self.final_palette[i:i+3] == rgb:
                    existing_idx = i // 3
                    break
            if existing_idx == -1:
                self.final_palette.extend(rgb)
                self.palette_fwd_map[idx] = self.palette_i
                self.palette_bwd_map[self.palette_i] = idx
                self.palette_i += 1
            else:
                self.palette_fwd_map[idx] = existing_idx
                self.palette_bwd_map[existing_idx] = idx

    def process_frames(self):
        """Iterate over all frames, remap palette indices, and collect pixel data."""
        global_pal = self.gif.global_palette.palette if self.gif.global_palette else None

        for frame in ImageSequence.Iterator(self.gif):
            frame_pal = frame.palette.palette if frame.palette else None
            # Use per-frame palette when it differs from global, or when there is no global palette
            if frame_pal is not None and frame_pal != global_pal:
                self._rebuild_frame_mapping(frame_pal)

            is_rgb = frame.mode in ('RGB', 'RGBA')
            for pixel_idx in self.extract_frame_pixels(frame):
                # RGB/RGBA frames: extract_frame_pixels returns palette indices directly
                # P/L mode frames: extract_frame_pixels returns GIF indices, need remapping
                if is_rgb:
                    self.pixels_raw.append(pixel_idx)
                    continue

                mapped = self.palette_fwd_map[pixel_idx]
                if mapped is not None:
                    self.pixels_raw.append(mapped)
                    continue

                # New color: check if it's a duplicate of an existing palette entry
                rgb = bytes(frame_pal[pixel_idx * 3:(pixel_idx + 1) * 3])
                existing_idx = -1
                for i in range(3, len(self.final_palette), 3):
                    if self.final_palette[i:i+3] == rgb:
                        existing_idx = i // 3
                        break

                if existing_idx == -1:
                    self.final_palette.extend(rgb)
                    self.pixels_raw.append(self.palette_i)
                    self.palette_fwd_map[pixel_idx] = self.palette_i
                    self.palette_bwd_map[self.palette_i] = pixel_idx
                    self.palette_i += 1
                else:
                    self.compression_log.append(
                        f'// dupe RGB at GIF palette index {pixel_idx}; '
                        f'remapping to our existing index {existing_idx}\n'
                    )
                    self.pixels_raw.append(existing_idx)
                    self.palette_fwd_map[pixel_idx] = existing_idx

            self.num_frames += 1

    def compress(self):
        """Compress the palette and pixel data with heatshrink."""
        if self._compressed_bytes is not None:
            return self._compressed_bytes
        compression_payload = self.final_palette + self.pixels_raw
        self._compressed_bytes = compress(compression_payload, self.window, self.lookahead)
        return self._compressed_bytes

    def write_header(self, output_path, window, lookahead):
        """Write the C header file."""
        basename = os.path.basename(os.path.splitext(output_path)[0])
        heatshrink_bytes = self.compress()
        num_colors = len(self.final_palette) // 3

        # Compute size statistics
        payload_size = len(heatshrink_bytes)
        struct_overhead = 8
        total_size = payload_size + struct_overhead
        raw_payload_size = len(self.pixels_raw)
        gif_size = os.path.getsize(self.gif_path)
        gif_pct = (100.0 * total_size) / gif_size
        raw_pct = (100.0 * total_size) / raw_payload_size

        # Build compression log header
        self.compression_log.insert(0,
            f'// "{basename}" (GIF orig:{gif_size} raw_payload:{raw_payload_size} '
            f'shrunk_payload:{payload_size} total:{total_size} bytes)\n'
            f'// Compared to GIF: {gif_pct:.2f}% \tCompared to raw: {raw_pct:.2f}%\n'
        )
        self.compression_log.append(f'// ./heatshrink -w {window} -l {lookahead} (')
        log_fields = []
        for field in ('background', 'loop', 'transparency', 'mode'):
            if field in self.gif.info:
                log_fields.append(f'{field} = {self.gif.info[field]}; ')
        self.compression_log.append(''.join(log_fields) + ')\n')

        with open(output_path, 'w') as out:
            out.write(''.join(self.compression_log))
            out.write(f'\nFL_PROGMEM const struct HSpr_{basename} {{\n')
            out.write(f'\tuint16_t datasize = {payload_size};\n')
            out.write(f'\tuint16_t frames = {self.num_frames};\n')
            out.write(f'\tuint16_t duration = {self.gif.info.get("duration", 100)};\n')
            out.write(f'\tuint8_t flags = 0;\n')
            out.write(f'\tuint8_t palette_entries = {num_colors};\n')

            # Palette section (empty for heatshrink-compressed format)
            out.write('\tuint8_t crgb[0] = {\n')
            for local_idx in range(num_colors):
                orig_idx = self.palette_bwd_map[local_idx]
                r = self.final_palette[local_idx * 3]
                g = self.final_palette[local_idx * 3 + 1]
                b = self.final_palette[local_idx * 3 + 2]
                out.write(f'\t\t// 0x{r:02x}, 0x{g:02x}, 0x{b:02x}, '
                          f'  // original palette index {orig_idx}\n')
            out.write('\t};\n')

            # Compressed data section
            out.write(f'\tuint8_t hs_data[{payload_size}] = {{')
            for i, byte in enumerate(heatshrink_bytes):
                if i % 16 == 0:
                    out.write('\n\t\t')
                out.write(f'0x{byte:02x}, ')
            out.write('\n\t};\n')
            out.write(f'}} HSpr_{basename};\n')

    def print_summary(self, output_path):
        """Print a one-line summary for hsprites.h."""
        basename = os.path.basename(os.path.splitext(output_path)[0])
        heatshrink_bytes = self.compress()
        num_colors = len(self.final_palette) // 3
        total_size = len(heatshrink_bytes) + 8
        gif_size = os.path.getsize(self.gif_path)
        gif_pct = (100.0 * total_size) / gif_size
        frames_str = 'frame' if self.num_frames == 1 else 'frames'

        include = f'#include "GIF/{basename}.h"'
        padding = ' ' * (51 - len(include))
        print(f'{include}{padding}//%5d bytes%4d cols%4d %s Compared to GIF: %3.2f%%' %
              (total_size, num_colors, self.num_frames, frames_str, gif_pct))


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Converts GIFs to a custom format for playback on microcontrollers'
    )
    parser.add_argument('-w', '--window', type=int, default=8,
                        help='heatshrink window size (5 to 11)')
    parser.add_argument('-l', '--lookahead', type=int, default=7,
                        help='heatshrink lookahead size (3 to 1 less than --window)')
    parser.add_argument('input_file', type=str, help='filename of the GIF to convert')
    parser.add_argument('output_file', type=str, nargs='?',
                        help='filename of the output header (default: <input>.h)')
    return parser.parse_args()


def main():
    args = parse_args()

    if args.lookahead >= args.window or args.lookahead < 3:
        raise ValueError('Lookahead must be between 3 and Windowsize - 1')
    if args.window < 4 or args.window > 15:
        raise ValueError('Window must be between 4 and 15')

    # Determine output path
    basepath = os.path.splitext(args.input_file)[0]
    if args.output_file:
        basepath = os.path.splitext(args.output_file)[0]
    else:
        args.output_file = basepath + '.h'

    if args.input_file == args.output_file:
        raise ValueError('Refusing to overwrite input file with output file.')

    # Validate size
    gif = Image.open(args.input_file)
    if gif.size != (16, 16):
        print(f'The .ino & .h file must be modified to use images sized other than 16x16.\n'
              f'This image is {gif.size[0]}x{gif.size[1]}.  Good luck with that!\n')
        sys.exit(1)

    # Run conversion
    converter = GifConverter(args.input_file)
    converter.window = args.window
    converter.lookahead = args.lookahead
    converter.gif_path = args.input_file
    converter.find_transparent_index()
    converter.process_frames()
    converter.write_header(args.output_file, args.window, args.lookahead)
    converter.print_summary(args.output_file)


if __name__ == '__main__':
    main()
