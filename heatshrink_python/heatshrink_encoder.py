#!/usr/bin/env python3
"""
Python implementation of Heatshrink compressor.
Produces byte-identical output to the C reference implementation.

Based on: https://github.com/atomicobject/heatshrink
Version: 0.4.1
"""

# Encoding markers
HEATSHRINK_LITERAL_MARKER = 0x01
HEATSHRINK_BACKREF_MARKER = 0x00

# States
HSES_NOT_FULL = 0
HSES_FILLED = 1
HSES_SEARCH = 2
HSES_YIELD_TAG_BIT = 3
HSES_YIELD_LITERAL = 4
HSES_YIELD_BR_INDEX = 5
HSES_YIELD_BR_LENGTH = 6
HSES_SAVE_BACKLOG = 7
HSES_FLUSH_BITS = 8
HSES_DONE = 9

# Encoder flags
FLAG_IS_FINISHING = 0x01

MATCH_NOT_FOUND = 0xFFFF

HEATSHRINK_MIN_WINDOW_BITS = 4
HEATSHRINK_MAX_WINDOW_BITS = 15
HEATSHRINK_MIN_LOOKAHEAD_BITS = 3


class HeatshrinkEncoder:
    def __init__(self, window_sz2=8, lookahead_sz2=7):
        """
        Initialize encoder.
        
        Args:
            window_sz2: 2^n size of sliding window (4-15)
            lookahead_sz2: 2^n size of lookahead buffer (3 to window_sz2-1)
        """
        if window_sz2 < HEATSHRINK_MIN_WINDOW_BITS or window_sz2 > HEATSHRINK_MAX_WINDOW_BITS:
            raise ValueError(f"window_sz2 must be {HEATSHRINK_MIN_WINDOW_BITS}-{HEATSHRINK_MAX_WINDOW_BITS}, got {window_sz2}")
        if lookahead_sz2 < HEATSHRINK_MIN_LOOKAHEAD_BITS or lookahead_sz2 >= window_sz2:
            raise ValueError(f"lookahead_sz2 must be {HEATSHRINK_MIN_LOOKAHEAD_BITS}-{window_sz2-1}, got {lookahead_sz2}")
        
        self.window_sz2 = window_sz2
        self.lookahead_sz2 = lookahead_sz2
        self.window_size = 1 << window_sz2
        self.lookahead_size = 1 << lookahead_sz2
        
        # Double-sized buffer: first half is backlog, second half is input
        self.buffer = bytearray(2 * self.window_size)
        self.input_size = 0
        self.state = HSES_NOT_FULL
        self.match_scan_index = 0
        self.flags = 0
        self.bit_index = 0x80
        self.current_byte = 0x00
        self.match_length = 0
        self.match_pos = 0
        
        # Outgoing bits buffer
        self.outgoing_bits = 0x0000
        self.outgoing_bits_count = 0
        
        # Output buffer
        self.output = bytearray()
    
    def sink(self, data):
        """
        Feed input data into the encoder.
        
        Args:
            data: bytes to compress
            
        Returns:
            number of bytes actually sunk
        """
        if self.flags & FLAG_IS_FINISHING:
            raise RuntimeError("Cannot sink data after calling finish()")
        if self.state != HSES_NOT_FULL:
            raise RuntimeError("Cannot sink data while encoding is in progress")
        
        rem = self.window_size - self.input_size
        cp_sz = min(rem, len(data))
        write_offset = self.window_size + self.input_size
        self.buffer[write_offset:write_offset + cp_sz] = data[:cp_sz]
        self.input_size += cp_sz
        
        if self.input_size == self.window_size:
            self.state = HSES_FILLED
        
        return cp_sz
    
    def finish(self):
        """Mark input stream as complete.
        
        Returns:
            0 (FINISH_DONE) if encoding is complete, 1 (FINISH_MORE) if more output remains.
        """
        self.flags |= FLAG_IS_FINISHING
        if self.state == HSES_NOT_FULL:
            self.state = HSES_FILLED
        return 0 if self.state == HSES_DONE else 1  # 0=FINISH_DONE, 1=FINISH_MORE
    
    def poll(self, out_buf=None):
        """
        Poll for compressed output.
        
        Args:
            out_buf: optional bytearray to append output to. If None, creates new one.
            
        Returns:
            tuple of (bytes_output, more_flag)
            more_flag is 0 when done, 1 when more output is available
        """
        if out_buf is None:
            out_buf = bytearray()
        
        initial_size = len(out_buf)
        
        while True:
            in_state = self.state
            
            if self.state == HSES_NOT_FULL:
                # Need more input or finish called - can't make progress
                break
                
            elif self.state == HSES_FILLED:
                self.state = HSES_SEARCH
                
            elif self.state == HSES_SEARCH:
                self.state = self._step_search()
                
            elif self.state == HSES_YIELD_TAG_BIT:
                self._yield_tag_bit(out_buf)
                self.state = self._get_next_state_after_tag()
                
            elif self.state == HSES_YIELD_LITERAL:
                self._yield_literal(out_buf)
                self.state = HSES_SEARCH
                
            elif self.state == HSES_YIELD_BR_INDEX:
                pushed = self._push_outgoing_bits(out_buf)
                if pushed == 0:
                    # Ready for br length
                    self.outgoing_bits = self.match_length - 1
                    self.outgoing_bits_count = self.lookahead_sz2
                    self.state = HSES_YIELD_BR_LENGTH
                    
            elif self.state == HSES_YIELD_BR_LENGTH:
                pushed = self._push_outgoing_bits(out_buf)
                if pushed == 0:
                    self.match_scan_index += self.match_length
                    self.match_length = 0
                    self.state = HSES_SEARCH
                    
            elif self.state == HSES_SAVE_BACKLOG:
                self._save_backlog()
                self.state = HSES_NOT_FULL
                
            elif self.state == HSES_FLUSH_BITS:
                if self.bit_index == 0x80:
                    self.state = HSES_DONE
                else:
                    out_buf.append(self.current_byte)
                    self.state = HSES_DONE
                    
            elif self.state == HSES_DONE:
                break
            
            else:
                raise RuntimeError(f"Unknown state: {self.state}")
            
            # If state didn't change, we can't make progress
            # Exception: YIELD_BR_INDEX and YIELD_BR_LENGTH may stay in same state
            # while pushing bits
            if self.state == in_state and in_state not in (HSES_YIELD_BR_INDEX, HSES_YIELD_BR_LENGTH):
                break
        
        return bytes(out_buf[initial_size:]), 0 if self.state == HSES_DONE or self.state == HSES_NOT_FULL else 1
        
    def _step_search(self):
        """Search for matches in the sliding window."""
        fin = bool(self.flags & FLAG_IS_FINISHING)
        # PR #87: When finishing with no input, flush bits instead of underflowing
        if fin and self.input_size == 0:
            return HSES_FLUSH_BITS
        
        subtrahend = 1 if fin else self.lookahead_size
        # Emulate C unsigned arithmetic: if input_size < subtrahend, min_scan wraps
        # to a large value, so match_scan_index > min_scan is always False
        if self.input_size >= subtrahend:
            min_scan = self.input_size - subtrahend
            if self.match_scan_index > min_scan:
                # Search buffer exhausted
                return HSES_FLUSH_BITS if fin else HSES_SAVE_BACKLOG
        
        input_offset = self.window_size
        end = input_offset + self.match_scan_index
        start = end - self.window_size
        
        max_possible = self.lookahead_size
        if self.input_size - self.match_scan_index < self.lookahead_size:
            max_possible = self.input_size - self.match_scan_index
        
        match_length = 0
        match_pos, match_length = self._find_longest_match(start, end, max_possible)
        
        if match_pos == MATCH_NOT_FOUND:
            self.match_scan_index += 1
            self.match_length = 0
            return HSES_YIELD_TAG_BIT
        else:
            self.match_pos = match_pos
            self.match_length = match_length
            return HSES_YIELD_TAG_BIT
    
    def _find_longest_match(self, start, end, maxlen):
        """
        Find longest match for buffer[end:end+maxlen] in buffer[start:end].
        
        Returns:
            tuple of (distance_from_end, match_length) or (MATCH_NOT_FOUND, 0)
        """
        buf = self.buffer
        buf_len = len(buf)
        match_maxlen = 0
        match_index = 0
        
        # Actual available length from end
        avail_len = min(maxlen, buf_len - end)
        if avail_len == 0:
            return (MATCH_NOT_FOUND, 0)
        
        needlepoint = buf[end:end + avail_len]
        
        # Search backwards from end-1 to start
        for pos in range(end - 1, start - 1, -1):
            # Available length from pos
            pos_avail = min(maxlen, buf_len - pos)
            if pos_avail == 0:
                continue
                
            pospoint = buf[pos:pos + pos_avail]
            
            # Quick check: first byte must match
            if pospoint[0] != needlepoint[0]:
                continue
            # Also check byte at match_maxlen position (optimization from C code)
            if match_maxlen < avail_len and pospoint[match_maxlen] != needlepoint[match_maxlen]:
                continue
            
            # Find match length
            match_len = 1
            for j in range(1, min(pos_avail, avail_len)):
                if pospoint[j] != needlepoint[j]:
                    break
                match_len += 1
            
            if match_len > match_maxlen:
                match_maxlen = match_len
                match_index = pos
                if match_len == avail_len:
                    break
        
        if match_maxlen == 0:
            return (MATCH_NOT_FOUND, 0)
        
        # Break-even point calculation
        break_even_point = (1 + self.window_sz2 + self.lookahead_sz2)
        
        if match_maxlen > (break_even_point // 8):
            return (end - match_index, match_maxlen)
        else:
            return (MATCH_NOT_FOUND, 0)
    
    def _yield_tag_bit(self, output):
        """Emit the tag bit for current match decision."""
        if self.match_length == 0:
            # Literal
            self._push_bits(1, HEATSHRINK_LITERAL_MARKER, output)
        else:
            # Back-reference
            self._push_bits(1, HEATSHRINK_BACKREF_MARKER, output)
            self.outgoing_bits = self.match_pos - 1
            self.outgoing_bits_count = self.window_sz2
    
    def _get_next_state_after_tag(self):
        """Determine next state after emitting tag bit."""
        if self.match_length == 0:
            return HSES_YIELD_LITERAL
        else:
            return HSES_YIELD_BR_INDEX
    
    def _yield_literal(self, output):
        """Emit a literal byte."""
        processed_offset = self.match_scan_index - 1
        input_offset = self.window_size + processed_offset
        c = self.buffer[input_offset]
        self._push_bits(8, c, output)
    
    def _push_outgoing_bits(self, output):
        """
        Push up to 8 bits from outgoing_bits to output.
        
        Returns:
            number of bits pushed
        """
        if self.outgoing_bits_count == 0:
            return 0
        
        if self.outgoing_bits_count > 8:
            count = 8
            bits = (self.outgoing_bits >> (self.outgoing_bits_count - 8)) & 0xFF
        else:
            count = self.outgoing_bits_count
            bits = self.outgoing_bits & 0xFF
        
        if count > 0:
            self._push_bits(count, bits, output)
            self.outgoing_bits_count -= count
        
        return count
    
    def _push_bits(self, count, bits, output):
        """
        Push count bits (MSB first) to output buffer.
        
        Args:
            count: number of bits (1-8)
            bits: the bits to push
            output: output bytearray to append to
        """
        # Optimization: if pushing a whole byte at the start of a new output byte,
        # push it directly without going through the bit loop.
        if count == 8 and self.bit_index == 0x80:
            output.append(bits)
        else:
            for i in range(count - 1, -1, -1):
                bit = (bits >> i) & 1
                if bit:
                    self.current_byte |= self.bit_index
                
                self.bit_index >>= 1
                if self.bit_index == 0x00:
                    self.bit_index = 0x80
                    output.append(self.current_byte)
                    self.current_byte = 0x00
    
    def _save_backlog(self):
        """Copy unprocessed data to beginning of buffer."""
        msi = self.match_scan_index
        rem = self.window_size - msi
        shift_sz = self.window_size + rem
        
        # Move unprocessed bytes to beginning
        src_start = self.window_size - rem
        self.buffer[:shift_sz] = self.buffer[src_start:src_start + shift_sz]
        
        self.match_scan_index = 0
        self.input_size -= self.window_size - rem


def compress(data, window_sz2=8, lookahead_sz2=7):
    """
    Compress data using Heatshrink algorithm.
    
    Args:
        data: bytes to compress
        window_sz2: 2^n window size (4-15, default 8 = 256 bytes)
        lookahead_sz2: 2^n lookahead size (3 to window_sz2-1, default 7 = 128 bytes)
        
    Returns:
        compressed bytes
    """
    enc = HeatshrinkEncoder(window_sz2, lookahead_sz2)
    result = bytearray()
    
    # Sink data in chunks and poll for output
    offset = 0
    while offset < len(data):
        cp_sz = enc.sink(data[offset:])
        offset += cp_sz
        
        # Poll for output (may need multiple polls)
        while True:
            out, more = enc.poll()
            result.extend(out)
            if not more:
                break
    
    enc.finish()
    
    # Poll for remaining output
    while True:
        out, more = enc.poll()
        result.extend(out)
        if not more:
            break
    
    return bytes(result)


if __name__ == '__main__':
    import sys
    import subprocess
    
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} [-w WINDOW_BITS] [-l LOOKAHEAD_BITS] <input> [output]")
        print(f"  WINDOW_BITS: 4-15 (default 8)")
        print(f"  LOOKAHEAD_BITS: 3 to WINDOW_BITS-1 (default 7)")
        sys.exit(1)
    
    window_sz2 = 8
    lookahead_sz2 = 7
    args = sys.argv[1:]
    
    while args and args[0].startswith('-'):
        if args[0] == '-w' and len(args) > 1:
            window_sz2 = int(args[1])
            args = args[2:]
        elif args[0] == '-l' and len(args) > 1:
            lookahead_sz2 = int(args[1])
            args = args[2:]
        else:
            break
    
    if not args:
        print("Error: input file required")
        sys.exit(1)
    
    input_file = args[0]
    output_file = args[1] if len(args) > 1 else None
    
    with open(input_file, 'rb') as f:
        data = f.read()
    
    compressed = compress(data, window_sz2, lookahead_sz2)
    
    if output_file:
        with open(output_file, 'wb') as f:
            f.write(compressed)
        print(f"{len(data)} -> {len(compressed)} bytes", file=sys.stderr)
    else:
        sys.stdout.buffer.write(compressed)
    
    # Compare with C implementation if available
    try:
        c_result = subprocess.run(
            ['./heatshrink', '-w', str(window_sz2), '-l', str(lookahead_sz2)],
            input=data,
            capture_output=True,
            timeout=30
        )
        if c_result.returncode == 0:
            if c_result.stdout == compressed:
                print("Output matches C implementation: IDENTICAL", file=sys.stderr)
            else:
                print(f"C output: {len(c_result.stdout)} bytes, Python: {len(compressed)} bytes", file=sys.stderr)
                # Show first difference
                for i, (a, b) in enumerate(zip(c_result.stdout, compressed)):
                    if a != b:
                        print(f"First diff at byte {i}: C=0x{a:02x} Python=0x{b:02x}", file=sys.stderr)
                        break
                else:
                    print(f"Prefix matches, length differs: C={len(c_result.stdout)} Python={len(compressed)}", file=sys.stderr)
    except FileNotFoundError:
        pass
    except subprocess.TimeoutExpired:
        pass
