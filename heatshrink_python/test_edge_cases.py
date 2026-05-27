#!/usr/bin/env python3
"""
Additional edge case tests for Heatshrink C vs Python.
Focuses on malformed data, buffer boundaries, and decoder robustness.
"""

import pytest
import sys
import os
import random

sys.path.insert(0, os.path.dirname(__file__))
from heatshrink_encoder import compress, HeatshrinkEncoder
from heatshrink_decoder import decompress, HeatshrinkDecoder


def compress_with_params(data, window_sz2, lookahead_sz2):
    """Compress with specific parameters."""
    enc = HeatshrinkEncoder(window_sz2, lookahead_sz2)
    result = bytearray()
    offset = 0
    while offset < len(data):
        cp_sz = enc.sink(data[offset:])
        offset += cp_sz
        while True:
            out, more = enc.poll()
            result.extend(out)
            if not more:
                break
    enc.finish()
    while True:
        out, more = enc.poll()
        result.extend(out)
        if not more:
            break
    return bytes(result)


def roundtrip(data, window_sz2, lookahead_sz2):
    """Compress and decompress."""
    compressed = compress_with_params(data, window_sz2, lookahead_sz2)
    return decompress(compressed, window_sz2, lookahead_sz2)


# =============================================================================
# Malformed/Truncated Data Tests
# =============================================================================

class TestMalformedData:
    """Test decoder behavior with malformed input."""

    def test_truncated_compressed_data(self):
        """Decoder should handle truncated data gracefully."""
        data = b"hello world"
        compressed = compress_with_params(data, 8, 7)
        # Truncate to half
        truncated = compressed[:len(compressed)//2]
        # Should not crash, but output may be wrong
        result = decompress(truncated, 8, 7)
        # Result may be partial or garbage, but shouldn't crash

    def test_empty_compressed_data(self):
        """Empty compressed data should not crash."""
        result = decompress(b"", 8, 7)
        assert result == b""

    def test_single_byte_compressed(self):
        """Single byte compressed data."""
        # Compress a single byte
        compressed = compress_with_params(b"A", 8, 7)
        result = decompress(compressed, 8, 7)
        assert result == b"A"

    def test_all_zero_bytes_compressed(self):
        """Compressed data that is all zeros."""
        # Create valid compressed data for "AAAAA"
        compressed = compress_with_params(b"AAAAA", 8, 7)
        # Replace with all zeros (malformed)
        malformed = b"\x00" * len(compressed)
        # Should not crash
        result = decompress(malformed, 8, 7)

    def test_all_ff_bytes_compressed(self):
        """Compressed data that is all 0xFF."""
        compressed = compress_with_params(b"AAAAA", 8, 7)
        malformed = b"\xff" * len(compressed)
        # Should not crash
        result = decompress(malformed, 8, 7)

    def test_random_bytes_as_compressed(self):
        """Random bytes as compressed data should not crash."""
        random.seed(42)
        random_data = bytes(random.randint(0, 255) for _ in range(50))
        # Should not crash
        result = decompress(random_data, 8, 7)


# =============================================================================
# Window Boundary Tests
# =============================================================================

class TestWindowBoundaries:
    """Test behavior at window size boundaries."""

    def test_exactly_window_size_data(self):
        """Data exactly equal to window size."""
        for w in [4, 5, 6, 7, 8]:
            window_size = 1 << w
            data = b"A" * window_size
            result = roundtrip(data, w, w - 1)
            assert result == data, f"Failed for window={w}"

    def test_window_size_plus_one(self):
        """Data one byte larger than window size."""
        for w in [4, 5, 6, 7, 8]:
            window_size = 1 << w
            data = b"A" * (window_size + 1)
            result = roundtrip(data, w, w - 1)
            assert result == data, f"Failed for window={w}, size={window_size+1}"

    def test_window_size_minus_one(self):
        """Data one byte smaller than window size."""
        for w in [5, 6, 7, 8]:
            window_size = 1 << w
            data = b"A" * (window_size - 1)
            result = roundtrip(data, w, w - 1)
            assert result == data, f"Failed for window={w}"

    def test_two_windows_data(self):
        """Data equal to two window sizes."""
        for w in [4, 5, 6, 7]:
            window_size = 1 << w
            data = b"A" * (window_size * 2)
            result = roundtrip(data, w, w - 1)
            assert result == data, f"Failed for window={w}"

    def test_pattern_at_window_boundary(self):
        """Pattern that repeats exactly at window boundary."""
        data = (b"ABCD" * 64)  # 256 bytes = window_sz2=8
        result = roundtrip(data, 8, 7)
        assert result == data

    def test_non_repeating_at_window_boundary(self):
        """Non-repeating data at window boundary."""
        data = bytes(range(256))  # 256 unique bytes
        result = roundtrip(data, 8, 7)
        assert result == data


# =============================================================================
# Lookahead Boundary Tests
# =============================================================================

class TestLookaheadBoundaries:
    """Test behavior at lookahead size boundaries."""

    def test_max_backref_length(self):
        """Back-reference with length equal to lookahead max."""
        # lookahead_sz2=7 -> max backref = 128
        data = b"A" * 128
        result = roundtrip(data, 8, 7)
        assert result == data

    def test_max_backref_plus_one(self):
        """Back-reference one byte longer than lookahead max."""
        data = b"A" * 129
        result = roundtrip(data, 8, 7)
        assert result == data

    def test_min_backref_length(self):
        """Minimum back-reference (length 2)."""
        data = b"AA"
        result = roundtrip(data, 8, 7)
        assert result == data

    def test_lookahead_sz2_min(self):
        """Minimum lookahead_sz2=3."""
        data = b"abcabcabc"
        result = roundtrip(data, 8, 3)
        assert result == data


# =============================================================================
# Decoder Buffer Size Tests
# =============================================================================

class TestDecoderBufferSize:
    """Test decoder with various input buffer sizes."""

    def test_buffer_exactly_compressed_size(self):
        """Buffer exactly matches compressed data size."""
        data = b"hello world test"
        compressed = compress_with_params(data, 8, 7)
        dec = HeatshrinkDecoder(8, 7, input_buffer_size=len(compressed))
        result = bytearray()
        dec.sink(compressed)
        dec.finish()
        while dec.finish():
            dec.poll(result)
        assert bytes(result) == data

    def test_buffer_larger_than_compressed(self):
        """Buffer larger than compressed data."""
        data = b"hello world test"
        compressed = compress_with_params(data, 8, 7)
        dec = HeatshrinkDecoder(8, 7, input_buffer_size=len(compressed) + 100)
        result = bytearray()
        dec.sink(compressed)
        dec.finish()
        while dec.finish():
            dec.poll(result)
        assert bytes(result) == data

    def test_buffer_smaller_than_compressed(self):
        """Buffer smaller than compressed data - should fail gracefully."""
        data = b"hello world"
        compressed = compress_with_params(data, 8, 7)
        dec = HeatshrinkDecoder(8, 7, input_buffer_size=2)  # Too small
        # Sink what fits
        sunk = dec.sink(compressed)
        assert sunk < len(compressed)  # Should not sink all

    def test_byte_by_byte_with_exact_buffer(self):
        """Byte-by-byte decoding with exact buffer size."""
        data = b"test data 123"
        compressed = compress_with_params(data, 8, 7)
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


# =============================================================================
# Encoder State Machine Tests
# =============================================================================

class TestEncoderStateMachine:
    """Test encoder state machine edge cases."""

    def test_fill_then_finish(self):
        """Fill buffer completely, then finish."""
        enc = HeatshrinkEncoder(8, 7)
        enc.sink(b"A" * 256)  # Exactly fills window
        assert enc.state == 1  # FILLED
        enc.finish()
        result = bytearray()
        while True:
            out, more = enc.poll()
            result.extend(out)
            if not more:
                break
        # Should produce valid compressed output

    def test_partial_fill_then_finish(self):
        """Fill buffer partially, then finish."""
        enc = HeatshrinkEncoder(8, 7)
        enc.sink(b"hello")  # Partial fill
        enc.finish()
        result = bytearray()
        while True:
            out, more = enc.poll()
            result.extend(out)
            if not more:
                break
        # Should produce valid compressed output

    def test_multiple_sinks_then_finish(self):
        """Multiple sink calls, then finish."""
        enc = HeatshrinkEncoder(8, 7)
        for i in range(0, 100, 10):
            enc.sink(b"X" * 10)
        enc.finish()
        result = bytearray()
        while True:
            out, more = enc.poll()
            result.extend(out)
            if not more:
                break
        compressed = bytes(result)
        # Verify roundtrip
        dec = HeatshrinkDecoder(8, 7, len(compressed) + 32)
        dec_output = bytearray()
        dec.sink(compressed)
        dec.finish()
        while dec.finish():
            dec.poll(dec_output)
        assert bytes(dec_output) == b"X" * 100

    def test_finish_then_poll_then_finish(self):
        """Call finish(), poll, then finish() again."""
        enc = HeatshrinkEncoder(8, 7)
        enc.sink(b"test")
        enc.finish()
        # Drain output
        while True:
            out, more = enc.poll()
            if not more:
                break
        # finish() should return DONE
        assert enc.finish() == 0


# =============================================================================
# Cross-validation with C on edge cases
# =============================================================================

class TestCReferenceEdgeCases:
    """Cross-validate with C reference on edge cases."""

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(os.path.dirname(__file__), 'heatshrink')),
        reason="C reference not available"
    )
    def test_c_identical_16_bytes(self):
        """16 bytes should produce identical output."""
        data = bytes(range(16))
        py_out = compress_with_params(data, 8, 7)
        c_out = self._compress_with_c(data, 8, 7)
        assert py_out == c_out

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(os.path.dirname(__file__), 'heatshrink')),
        reason="C reference not available"
    )
    def test_c_identical_256_bytes(self):
        """256 bytes should produce identical output."""
        data = bytes(range(256))
        py_out = compress_with_params(data, 8, 7)
        c_out = self._compress_with_c(data, 8, 7)
        assert py_out == c_out

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(os.path.dirname(__file__), 'heatshrink')),
        reason="C reference not available"
    )
    def test_c_identical_all_same_100(self):
        """100 same bytes should produce identical output."""
        data = b"X" * 100
        py_out = compress_with_params(data, 8, 7)
        c_out = self._compress_with_c(data, 8, 7)
        assert py_out == c_out

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(os.path.dirname(__file__), 'heatshrink')),
        reason="C reference not available"
    )
    def test_c_identical_window_sz2_4(self):
        """window_sz2=4 should produce identical output."""
        data = b"abcabcabcabc"
        py_out = compress_with_params(data, 4, 3)
        c_out = self._compress_with_c(data, 4, 3)
        assert py_out == c_out

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(os.path.dirname(__file__), 'heatshrink')),
        reason="C reference not available"
    )
    def test_c_identical_window_sz2_14(self):
        """window_sz2=14 should produce identical output."""
        data = b"test data " * 50
        py_out = compress_with_params(data, 14, 13)
        c_out = self._compress_with_c(data, 14, 13)
        assert py_out == c_out

    @staticmethod
    def _compress_with_c(data, window_sz2, lookahead_sz2):
        try:
            import subprocess
            c_binary = os.path.join(os.path.dirname(__file__), 'heatshrink')
            result = subprocess.run(
                [c_binary, '-w', str(window_sz2), '-l', str(lookahead_sz2)],
                input=data,
                capture_output=True,
                timeout=10
            )
            return result.stdout
        except Exception:
            return None


# =============================================================================
# Performance/Stress Tests
# =============================================================================

class TestStress:
    """Stress tests for robustness."""

    def test_large_repeating_pattern(self):
        """Large repeating pattern."""
        data = (b"pattern" * 1000)
        result = roundtrip(data, 8, 7)
        assert result == data

    def test_large_random(self):
        """Large random data."""
        random.seed(99)
        data = bytes(random.randint(0, 255) for _ in range(10000))
        result = roundtrip(data, 8, 7)
        assert result == data

    def test_alternating_bytes(self):
        """Alternating byte pattern."""
        data = bytes([i % 256 for i in range(1000)])
        result = roundtrip(data, 8, 7)
        assert result == data

    def test_incrementing_then_decrementing(self):
        """Incrementing then decrementing pattern."""
        data = bytes(range(128)) + bytes(range(127, -1, -1))
        result = roundtrip(data, 8, 7)
        assert result == data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
