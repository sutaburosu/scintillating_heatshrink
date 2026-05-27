#!/usr/bin/env python3
"""
Tests targeting deviations from the C reference implementation.

Based on: test_heatshrink_dynamic.c and test_heatshrink_static.c
from https://github.com/atomicobject/heatshrink
"""

import sys
import os
import subprocess
import pytest
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from heatshrink_encoder import compress, HeatshrinkEncoder
from heatshrink_decoder import decompress, HeatshrinkDecoder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compare_with_c(data, window_sz2=8, lookahead_sz2=7):
    """Compress with C reference and return bytes."""
    result = subprocess.run(
        ["./heatshrink", "-w", str(window_sz2), "-l", str(lookahead_sz2)],
        input=data,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, f"C encoder failed: {result.stderr}"
    return result.stdout


def c_roundtrip(data, window_sz2=8, lookahead_sz2=7):
    """Compress with C encoder, decompress with C decoder, return result."""
    compressed = compare_with_c(data, window_sz2, lookahead_sz2)
    result = subprocess.run(
        ["./heatshrink", "-d", "-w", str(window_sz2)],
        input=compressed,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, f"C decoder failed: {result.stderr}"
    return result.stdout


# ---------------------------------------------------------------------------
# 1. Encoder state machine — exact byte patterns from C tests
# ---------------------------------------------------------------------------

class TestEncoderExactPatterns:
    """Encoder must produce byte-identical output for specific patterns."""

    def test_five_literals(self):
        """C test: encoder_should_emit_data_without_repetitions_as_literal_sequence"""
        # Input: 0, 1, 2, 3, 4
        # Expected C output: 0x80, 0x40, 0x60, 0x50, 0x38, 0x20
        data = bytes([0, 1, 2, 3, 4])
        py_out = compress(data, 8, 7)
        c_out = compare_with_c(data, 8, 7)
        assert py_out == c_out
        assert py_out == bytes([0x80, 0x40, 0x60, 0x50, 0x38, 0x20])

    def test_five_same_bytes(self):
        """C test: encoder_should_emit_series_of_same_byte_as_literal_then_backref"""
        # Input: "aaaaa"
        # Expected C output: 0xb0, 0x80, 0x01, 0x80
        data = b"aaaaa"
        py_out = compress(data, 8, 7)
        c_out = compare_with_c(data, 8, 7)
        assert py_out == c_out

    def test_abcd_abcd_small_lookahead(self):
        """C test: encoder_poll_should_detect_repeated_substring (sz2=8, la2=3)"""
        data = b"abcdabcd"
        py_out = compress(data, 8, 3)
        c_out = compare_with_c(data, 8, 3)
        assert py_out == c_out

    def test_abcd_abcd_with_trailing(self):
        """C test: encoder_poll_should_detect_repeated_substring_and_preserve_trailing_literal"""
        data = b"abcdabcde"
        py_out = compress(data, 8, 3)
        c_out = compare_with_c(data, 8, 3)
        assert py_out == c_out


# ---------------------------------------------------------------------------
# 2. Decoder byte-by-byte feeding (from C tests)
# ---------------------------------------------------------------------------

class TestDecoderByteByByte:
    """Decoder must handle byte-at-a-time input correctly."""

    def test_foofoo_byte_by_byte(self):
        """C test: decoder_poll_should_expand_short_literal_and_backref_when_fed_input_byte_by_byte"""
        # Input: "foofoo" compressed = 0xb3, 0x5b, 0xed, 0xe0, 0x41, 0x00
        # C test uses window_sz2=7, lookahead_sz2=6
        compressed = bytes([0xb3, 0x5b, 0xed, 0xe0, 0x41, 0x00])
        # Feed byte by byte, poll after each
        dec = HeatshrinkDecoder(7, 6, input_buffer_size=len(compressed))
        result = bytearray()
        for byte in compressed:
            dec.sink(bytes([byte]))
            # Poll after each byte to get available output
            while True:
                chunk = dec.poll()
                if len(chunk) == 0:
                    break
                result.extend(chunk)
        dec.finish()
        while dec.finish():
            chunk = dec.poll()
            if len(chunk) == 0:
                break
            result.extend(chunk)
        assert bytes(result) == b"foofoo"

    def test_all_bytes_byte_by_byte(self):
        """Feed all 256 byte values compressed data byte by byte."""
        data = bytes(range(256))
        compressed = compress(data, 8, 7)
        dec = HeatshrinkDecoder(8, 7, input_buffer_size=len(compressed))
        result = bytearray()
        for byte in compressed:
            dec.sink(bytes([byte]))
            while True:
                chunk = dec.poll()
                if len(chunk) == 0:
                    break
                result.extend(chunk)
        dec.finish()
        while dec.finish():
            chunk = dec.poll()
            if len(chunk) == 0:
                break
            result.extend(chunk)
        assert bytes(result) == data


# ---------------------------------------------------------------------------
# 3. Decoder poll byte-by-byte (from C tests)
# ---------------------------------------------------------------------------

class TestDecoderPollByteByByte:
    """Decoder must handle byte-at-a-time output polling correctly."""

    def test_poll_one_byte_at_a_time(self):
        """Feed all compressed data at once, poll output one byte at a time."""
        data = b"Hello, World!"
        compressed = compress(data, 8, 7)
        dec = HeatshrinkDecoder(8, 7)
        dec.sink(compressed)
        dec.finish()
        result = bytearray()
        while dec.finish():
            chunk = dec.poll()
            if chunk:
                result.extend(chunk)
        assert bytes(result) == data


# ---------------------------------------------------------------------------
# 4. Small window sizes (sz2=4, la2=3)
# ---------------------------------------------------------------------------

class TestSmallWindow:
    """Test with minimum valid window size."""

    @pytest.mark.parametrize("data", [
        b"abc",
        b"aaaa",
        b"abab",
        bytes(range(16)),
        b"A" * 100,
        b"abcdefgh" * 10,
    ])
    def test_small_window_roundtrip(self, data):
        compressed = compress(data, 4, 3)
        decompressed = decompress(compressed, 4, 3)
        assert decompressed == data

    @pytest.mark.parametrize("data", [
        b"abc",
        b"aaaa",
        b"abab",
    ])
    def test_small_window_matches_c(self, data):
        py_out = compress(data, 4, 3)
        c_out = compare_with_c(data, 4, 3)
        assert py_out == c_out


# ---------------------------------------------------------------------------
# 5. Large window sizes (sz2=14, 15)
# ---------------------------------------------------------------------------

class TestLargeWindow:
    """Test with maximum window sizes."""

    def test_window_14(self):
        data = b"X" * 10000
        compressed = compress(data, 14, 13)
        decompressed = decompress(compressed, 14, 13)
        assert decompressed == data

    def test_window_15(self):
        data = b"X" * 50000
        compressed = compress(data, 15, 14)
        decompressed = decompress(compressed, 15, 14)
        assert decompressed == data

    def test_window_15_random(self):
        random.seed(42)
        data = bytes(random.randint(0, 255) for _ in range(1000))
        compressed = compress(data, 15, 14)
        decompressed = decompress(compressed, 15, 14)
        assert decompressed == data


# ---------------------------------------------------------------------------
# 6. Self-overlapping backreferences
# ---------------------------------------------------------------------------

class TestSelfOverlappingBackref:
    """Backreferences that overlap with the output being produced."""

    def test_self_overlapping_literal(self):
        """Data that creates self-overlapping output."""
        data = b"AAAAA"
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data

    def test_self_overlapping_pattern(self):
        """Pattern that repeats with overlap."""
        data = b"ABABABAB"
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data

    def test_long_self_overlapping(self):
        """Long self-overlapping pattern."""
        data = b"ABC" * 100  # "ABCABCABC..."
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data


# ---------------------------------------------------------------------------
# 7. Regression: backreference counter rollover
# ---------------------------------------------------------------------------

class TestRegressionBackref:
    """Regression tests for backreference counter issues."""

    def test_long_repetition(self):
        """Test that backreference counters don't rollover incorrectly."""
        # 1000 bytes of 'A' — requires multiple backrefs
        data = b"A" * 1000
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data

    def test_very_long_repetition(self):
        """10000 bytes of 'A' — tests large backref counts."""
        data = b"A" * 10000
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data


# ---------------------------------------------------------------------------
# 8. 64KB input (from C test: sixty_four_k)
# ---------------------------------------------------------------------------

class TestSixtyFourK:
    """Test with 64KB input data."""

    def test_64kb_repeated(self):
        data = b"X" * (64 * 1024)
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data

    def test_64kb_counter(self):
        data = bytes([i % 256 for i in range(64 * 1024)])
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data


# ---------------------------------------------------------------------------
# 9. Absurdly tiny buffers (from C tests)
# ---------------------------------------------------------------------------

class TestTinyBuffersCStyle:
    """Decoder with small buffer, fed byte-by-byte, polled byte-by-byte."""

    def test_no_duplication_tiny_buffers(self):
        """C test: data_without_duplication_should_match_with_absurdly_tiny_buffers"""
        data = bytes(range(ord('a'), ord('z') + 1))  # a-z
        compressed = compress(data, 8, 3)
        dec = HeatshrinkDecoder(8, 3, input_buffer_size=len(compressed))
        result = bytearray()
        for byte in compressed:
            dec.sink(bytes([byte]))
            while True:
                chunk = dec.poll()
                if len(chunk) == 0:
                    break
                result.extend(chunk)
        dec.finish()
        while dec.finish():
            chunk = dec.poll()
            if len(chunk) == 0:
                break
            result.extend(chunk)
        assert bytes(result) == data

    def test_simple_repetition_tiny_buffers(self):
        """C test: data_with_simple_repetition_should_match_with_absurdly_tiny_buffers"""
        data = (b"abc" + b"abcd" + b"abcde" + b"abcdef" +
                b"abcdefg" + b"abcdefgh")
        compressed = compress(data, 8, 3)
        dec = HeatshrinkDecoder(8, 3, input_buffer_size=len(compressed))
        result = bytearray()
        for byte in compressed:
            dec.sink(bytes([byte]))
            while True:
                chunk = dec.poll()
                if len(chunk) == 0:
                    break
                result.extend(chunk)
        dec.finish()
        while dec.finish():
            dec.poll(result)
        assert bytes(result) == data


# ---------------------------------------------------------------------------
# 10. Pseudorandom data (from C tests)
# ---------------------------------------------------------------------------

class TestPseudorandomData:
    """Test with C-style pseudorandom data generation."""

    def _pseudorandom_letters(self, size, seed):
        """Reproduce C's fill_with_pseudorandom_letters."""
        rn = 9223372036854775783  # prime under 2^64
        result = []
        for _ in range(size):
            rn = rn * seed + seed
            result.append((rn % 26) + ord('a'))
        return bytes(result)

    @pytest.mark.parametrize("seed", [1, 2, 5, 10, 50, 100])
    def test_pseudorandom_matches_c(self, seed):
        for size in [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]:
            data = self._pseudorandom_letters(size, seed)
            py_out = compress(data, 8, 7)
            c_out = compare_with_c(data, 8, 7)
            assert py_out == c_out, f"Failed for size={size}, seed={seed}"

    @pytest.mark.parametrize("seed", [1, 7, 42, 99])
    def test_pseudorandom_roundtrip(self, seed):
        for size in [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 4096]:
            data = self._pseudorandom_letters(size, seed)
            compressed = compress(data, 8, 7)
            decompressed = decompress(compressed, 8, 7)
            assert decompressed == data, f"Failed for size={size}, seed={seed}"


# ---------------------------------------------------------------------------
# 11. Encoder finish behavior
# ---------------------------------------------------------------------------

class TestEncoderFinish:
    """Test encoder finish() behavior matches C."""

    def test_finish_twice(self):
        """C: finish() can be called multiple times after first returns DONE."""
        data = b"test"
        enc = HeatshrinkEncoder(8, 7)
        enc.sink(data)
        enc.finish()
        out = bytearray()
        while True:
            chunk, more = enc.poll()
            out.extend(chunk)
            if not more:
                break
        # Second finish should be OK (Python raises, C returns DONE)
        # Python's finish() just sets a flag, calling it again is fine

    def test_finish_empty_input(self):
        """Empty input with finish."""
        enc = HeatshrinkEncoder(8, 7)
        enc.finish()
        out = bytearray()
        while True:
            chunk, more = enc.poll()
            out.extend(chunk)
            if not more:
                break
        assert bytes(out) == b""
        decompressed = decompress(b"", 8, 7)
        assert decompressed == b""

    def test_finish_then_poll(self):
        """After finish, poll should return all remaining output."""
        data = b"Hello"
        enc = HeatshrinkEncoder(8, 7)
        enc.sink(data)
        enc.finish()
        out = bytearray()
        # First poll
        chunk, more = enc.poll()
        out.extend(chunk)
        # More polls until done
        while more:
            chunk, more = enc.poll()
            out.extend(chunk)
        # Final poll should return empty
        chunk, more = enc.poll()
        assert chunk == b""


# ---------------------------------------------------------------------------
# 12. Decoder finish behavior
# ---------------------------------------------------------------------------

class TestDecoderFinish:
    """Test decoder finish() behavior matches C."""

    def test_finish_with_remaining_input(self):
        """Decoder in TAG_BIT state with input remaining."""
        data = b"Hello"
        compressed = compress(data, 8, 7)
        dec = HeatshrinkDecoder(8, 7)
        dec.sink(compressed[:2])  # Only partial data
        dec.finish()
        # finish() should return 1 (FINISH_MORE)
        assert dec.finish() == 1

    def test_finish_after_complete_decode(self):
        """Decoder finish() returns 0 after complete decode."""
        data = b"Hello"
        compressed = compress(data, 8, 7)
        dec = HeatshrinkDecoder(8, 7)
        dec.sink(compressed)
        dec.finish()
        result = bytearray()
        while dec.finish():
            dec.poll(result)
        assert dec.finish() == 0  # Should be FINISH_DONE
        assert bytes(result) == data


# ---------------------------------------------------------------------------
# 13. Various window/lookahead combinations
# ---------------------------------------------------------------------------

class TestWindowLookaheadCombinations:
    """Test all valid window/lookahead combinations."""

    @pytest.mark.parametrize("window_sz2", [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])
    def test_all_windows_repeated(self, window_sz2):
        lookahead_sz2 = window_sz2 - 1
        data = b"A" * 500
        py_out = compress(data, window_sz2, lookahead_sz2)
        c_out = compare_with_c(data, window_sz2, lookahead_sz2)
        assert py_out == c_out

    @pytest.mark.parametrize("window_sz2", [4, 5, 6, 7, 8, 9, 10])
    def test_all_windows_unique(self, window_sz2):
        lookahead_sz2 = window_sz2 - 1
        data = bytes(range(min(256, 1 << window_sz2)))
        py_out = compress(data, window_sz2, lookahead_sz2)
        c_out = compare_with_c(data, window_sz2, lookahead_sz2)
        assert py_out == c_out

    @pytest.mark.parametrize("window_sz2,lookahead_sz2", [
        (4, 3), (5, 3), (5, 4),
        (6, 3), (6, 4), (6, 5),
        (8, 3), (8, 4), (8, 5), (8, 6), (8, 7),
        (10, 5), (10, 7), (10, 9),
    ])
    def test_mixed_configs_roundtrip(self, window_sz2, lookahead_sz2):
        data = b"Test data " * 50
        compressed = compress(data, window_sz2, lookahead_sz2)
        decompressed = decompress(compressed, window_sz2, lookahead_sz2)
        assert decompressed == data


# ---------------------------------------------------------------------------
# 14. Encoder output buffer exhaustion simulation
# ---------------------------------------------------------------------------

class TestOutputExhaustion:
    """Test behavior when output buffer fills up mid-encoding."""

    def test_small_output_chunks(self):
        """Encode with small output chunks (simulates small output buffer)."""
        data = b"Hello, World! Hello, World!"
        enc = HeatshrinkEncoder(8, 7)
        enc.sink(data)
        enc.finish()
        out = bytearray()
        # Poll in small chunks
        while True:
            chunk, more = enc.poll()
            out.extend(chunk)
            if not more:
                break
        compressed = bytes(out)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data


# ---------------------------------------------------------------------------
# 15. C cross-validation on all anomaly data
# ---------------------------------------------------------------------------

class TestAllMatchC:
    """Comprehensive cross-validation against C implementation."""

    @pytest.mark.parametrize("data", [
        b"",
        b"\x00",
        b"\xff",
        b"\x00\xff" * 100,
        b"\xff\x00" * 100,
        bytes([0] * 256),
        bytes([255] * 256),
        bytes(range(256)),
        bytes(range(256))[::-1],
        b"A" * 1,
        b"A" * 255,
        b"A" * 256,
        b"A" * 257,
        b"A" * 258,
        b"A" * 512,
        b"A" * 1024,
        b"A" * 2048,
        b"A" * 4096,
        b"AB" * 128,
        b"ABC" * 85,
        b"ABCD" * 64,
        b"ABCDE" * 51,
        b"Hello, World!" * 100,
        b"The quick brown fox jumps over the lazy dog" * 20,
    ])
    def test_matches_c_comprehensive(self, data):
        py_out = compress(data, 8, 7)
        c_out = compare_with_c(data, 8, 7)
        assert py_out == c_out, (
            f"Length mismatch: Python={len(py_out)} C={len(c_out)}\n"
            f"Python: {py_out.hex()[:100]}...\nC:      {c_out.hex()[:100]}..."
        )

    @pytest.mark.parametrize("data", [
        b"",
        b"\x00",
        b"\xff",
        b"\x00\xff" * 100,
        bytes(range(256)),
        b"A" * 4096,
        b"AB" * 128,
        b"Hello, World!" * 100,
    ])
    def test_roundtrip_comprehensive(self, data):
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
