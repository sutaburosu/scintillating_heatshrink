#!/usr/bin/env python3
"""
Python implementation of Heatshrink decompressor.
Based on: https://github.com/atomicobject/heatshrink
Version: 0.4.1
"""

HEATSHRINK_MIN_WINDOW_BITS = 4
HEATSHRINK_MAX_WINDOW_BITS = 15
HEATSHRINK_MIN_LOOKAHEAD_BITS = 3

# Decoder states
HSDS_TAG_BIT = 0
HSDS_YIELD_LITERAL = 1
HSDS_BACKREF_INDEX_MSB = 2
HSDS_BACKREF_INDEX_LSB = 3
HSDS_BACKREF_COUNT_MSB = 4
HSDS_BACKREF_COUNT_LSB = 5
HSDS_YIELD_BACKREF = 6

NO_BITS = 0xFFFF


class HeatshrinkDecoder:
    def __init__(self, window_sz2=8, lookahead_sz2=7, input_buffer_size=32):
        if window_sz2 < HEATSHRINK_MIN_WINDOW_BITS or window_sz2 > HEATSHRINK_MAX_WINDOW_BITS:
            raise ValueError(f"window_sz2 must be {HEATSHRINK_MIN_WINDOW_BITS}-{HEATSHRINK_MAX_WINDOW_BITS}")
        if lookahead_sz2 < HEATSHRINK_MIN_LOOKAHEAD_BITS or lookahead_sz2 >= window_sz2:
            raise ValueError(f"lookahead_sz2 must be {HEATSHRINK_MIN_LOOKAHEAD_BITS}-{window_sz2-1}")
        
        self.window_sz2 = window_sz2
        self.lookahead_sz2 = lookahead_sz2
        self.input_buffer_size = input_buffer_size
        self.window_size = 1 << window_sz2
        
        # Buffer layout: [input_buffer][window_buffer]
        self.buffers = bytearray(input_buffer_size + self.window_size)
        self.input_size = 0
        self.input_index = 0
        self.bit_index = 0x00
        self.current_byte = 0x00
        self.output_count = 0
        self.output_index = 0
        self.head_index = 0
        self.state = HSDS_TAG_BIT
        self._finished = False
    
    def reset(self):
        self.buffers = bytearray(self.input_buffer_size + self.window_size)
        self.state = HSDS_TAG_BIT
        self.input_size = 0
        self.input_index = 0
        self.bit_index = 0x00
        self.current_byte = 0x00
        self.output_count = 0
        self.output_index = 0
        self.head_index = 0
    
    def sink(self, data):
        """Sink compressed data into the decoder."""
        rem = self.input_buffer_size - self.input_size
        if rem == 0:
            return 0
        
        cp_sz = min(rem, len(data))
        
        # Write to position input_size, matching C implementation.
        # When input_size == 0 (all consumed), reset input_index so reads
        # start from the new data at position 0.
        if self.input_size == 0:
            self.input_index = 0
        self.buffers[self.input_size:self.input_size + cp_sz] = data[:cp_sz]
        
        self.input_size += cp_sz
        return cp_sz
    
    def poll(self, out_buf=None):
        """Poll for decompressed output. Appends to out_buf if provided."""
        if out_buf is None:
            out_buf = bytearray()
        
        initial_size = len(out_buf)
        
        while True:
            in_state = self.state
            
            if self.state == HSDS_TAG_BIT:
                self.state = self._st_tag_bit()
            elif self.state == HSDS_YIELD_LITERAL:
                self.state = self._st_yield_literal(out_buf)
            elif self.state == HSDS_BACKREF_INDEX_MSB:
                self.state = self._st_backref_index_msb()
            elif self.state == HSDS_BACKREF_INDEX_LSB:
                self.state = self._st_backref_index_lsb()
            elif self.state == HSDS_BACKREF_COUNT_MSB:
                self.state = self._st_backref_count_msb()
            elif self.state == HSDS_BACKREF_COUNT_LSB:
                self.state = self._st_backref_count_lsb()
            elif self.state == HSDS_YIELD_BACKREF:
                self.state = self._st_yield_backref(out_buf)
            else:
                raise RuntimeError(f"Unknown state: {self.state}")
            
            # If state didn't change, we can't make progress
            if self.state == in_state:
                break
        
        return bytes(out_buf[initial_size:])
    
    def finish(self):
        """Notify decoder that input stream is finished.
        
        Returns:
            0 (FINISH_DONE) if decoding is complete, 1 (FINISH_MORE) if more output remains.
            
        After calling finish(), continue calling poll() until finish() returns 0.
        """
        if self.state == HSDS_TAG_BIT:
            return 0 if self.input_size == 0 else 1
        elif self.state in (HSDS_BACKREF_INDEX_LSB, HSDS_BACKREF_INDEX_MSB,
                            HSDS_BACKREF_COUNT_LSB, HSDS_BACKREF_COUNT_MSB):
            return 0 if self.input_size == 0 else 1
        elif self.state == HSDS_YIELD_LITERAL:
            return 0 if self.input_size == 0 else 1
        else:
            return 1  # YIELD_BACKREF always has more
    
    def _get_bits(self, count):
        """Get the next COUNT bits from the input buffer."""
        if count > 15:
            return NO_BITS
        
        # C reference: if no more bytes can be pulled and current bits
        # are insufficient for the requested count, suspend immediately.
        # This prevents reading across byte boundaries when data is incomplete.
        if self.input_size == 0 and self.bit_index < (1 << (count - 1)):
            return NO_BITS
        
        accumulator = 0
        
        for i in range(count):
            if self.bit_index == 0x00:
                if self.input_size == 0:
                    return NO_BITS
                self.current_byte = self.buffers[self.input_index]
                self.input_index += 1
                if self.input_index == self.input_buffer_size:
                    self.input_index = 0
                self.input_size -= 1
                self.bit_index = 0x80
            
            accumulator <<= 1
            if self.current_byte & self.bit_index:
                accumulator |= 0x01
            self.bit_index >>= 1
        
        return accumulator
    
    def _window_buf(self):
        """Get memoryview of window buffer for in-place modification."""
        return memoryview(self.buffers)[self.input_buffer_size:]
    
    def _st_tag_bit(self):
        bits = self._get_bits(1)
        if bits == NO_BITS:
            return HSDS_TAG_BIT
        elif bits == 1:
            return HSDS_YIELD_LITERAL
        elif self.window_sz2 > 8:
            return HSDS_BACKREF_INDEX_MSB
        else:
            self.output_index = 0
            return HSDS_BACKREF_INDEX_LSB
    
    def _st_yield_literal(self, out_buf):
        byte = self._get_bits(8)
        if byte == NO_BITS:
            return HSDS_YIELD_LITERAL
        
        mask = (1 << self.window_sz2) - 1
        c = byte & 0xFF
        window = self._window_buf()
        window[self.head_index & mask] = c
        out_buf.append(c)
        self.head_index += 1
        return HSDS_TAG_BIT
    
    def _st_backref_index_msb(self):
        bit_ct = self.window_sz2
        bits = self._get_bits(bit_ct - 8)
        if bits == NO_BITS:
            return HSDS_BACKREF_INDEX_MSB
        self.output_index = bits << 8
        return HSDS_BACKREF_INDEX_LSB
    
    def _st_backref_index_lsb(self):
        bit_ct = self.window_sz2
        bits = self._get_bits(bit_ct if bit_ct < 8 else 8)
        if bits == NO_BITS:
            return HSDS_BACKREF_INDEX_LSB
        self.output_index |= bits
        self.output_index += 1
        br_bit_ct = self.lookahead_sz2
        self.output_count = 0
        return HSDS_BACKREF_COUNT_MSB if br_bit_ct > 8 else HSDS_BACKREF_COUNT_LSB
    
    def _st_backref_count_msb(self):
        br_bit_ct = self.lookahead_sz2
        bits = self._get_bits(br_bit_ct - 8)
        if bits == NO_BITS:
            return HSDS_BACKREF_COUNT_MSB
        self.output_count = bits << 8
        return HSDS_BACKREF_COUNT_LSB
    
    def _st_backref_count_lsb(self):
        br_bit_ct = self.lookahead_sz2
        bits = self._get_bits(br_bit_ct if br_bit_ct < 8 else 8)
        if bits == NO_BITS:
            return HSDS_BACKREF_COUNT_LSB
        self.output_count |= bits
        self.output_count += 1
        return HSDS_YIELD_BACKREF
    
    def _st_yield_backref(self, out_buf):
        window = self._window_buf()
        mask = (1 << self.window_sz2) - 1
        neg_offset = self.output_index
        
        # Calculate how many bytes to output (limited by output_count)
        count = self.output_count
        
        for i in range(count):
            idx = (self.head_index - neg_offset) & mask
            c = window[idx]
            out_buf.append(c)
            window[self.head_index & mask] = c
            self.head_index += 1
        
        self.output_count = 0
        return HSDS_TAG_BIT


def decompress(data, window_sz2=8, lookahead_sz2=7):
    """
    Decompress heatshrink-compressed data.
    
    Args:
        data: bytes of compressed data
        window_sz2: 2^n window size (must match encoder)
        lookahead_sz2: 2^n lookahead size (must match encoder)
    
    Returns:
        decompressed bytes
    """
    dec = HeatshrinkDecoder(window_sz2, lookahead_sz2, input_buffer_size=max(32, len(data) + 32))
    result = bytearray()
    
    # Sink all data
    dec.sink(data)
    dec.finish()  # Mark input as finished
    
    # Poll for output until finish() returns 0 (DONE)
    while dec.finish():
        dec.poll(result)
    
    return bytes(result)


if __name__ == '__main__':
    import sys
    import subprocess
    
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    with open(input_file, 'rb') as f:
        compressed = f.read()
    
    decompressed = decompress(compressed, 8, 7)
    sys.stdout.buffer.write(decompressed)
    print(f"\nDecompressed {len(compressed)} -> {len(decompressed)} bytes", file=sys.stderr)
