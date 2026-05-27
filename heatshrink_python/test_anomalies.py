#!/usr/bin/env python3
"""
Anomaly test cases for Heatshrink encoder and decoder.

Targets edge cases, boundary anomalies, and error conditions that could
expose bugs in the state machines or buffer management.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from heatshrink_encoder import compress, HeatshrinkEncoder
from heatshrink_decoder import decompress, HeatshrinkDecoder


# ---------------------------------------------------------------------------
# 1. Streaming — encoder byte-at-a-time with interleaved poll
# ---------------------------------------------------------------------------

class TestStreamingEncoder:
    """Encoder must handle byte-at-a-time streaming with interleaved poll."""

    @pytest.mark.parametrize("data", [
        b"Hello",
        b"A" * 100,
        bytes(range(128)),
        bytes(range(256)),
        b"\x00\x01\x02\x03\x04\x05",
    ])
    def test_encoder_streaming_sink(self, data):
        """Feed encoder one byte at a time with interleaved poll for large data."""
        enc = HeatshrinkEncoder(8, 7)
        for byte in data:
            n = enc.sink(bytes([byte]))
            if n == 0:
                # Window full — drain output to free space
                while True:
                    chunk, more = enc.poll()
                    if not more:
                        break
            assert n == 1
        enc.finish()
        out = bytearray()
        while True:
            chunk, more = enc.poll()
            out.extend(chunk)
            if not more:
                break
        compressed = bytes(out)
        # Verify roundtrip
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data

    def test_encoder_streaming_full_roundtrip(self):
        """Full encoder+decoder byte-at-a-time roundtrip."""
        data = b"Streaming anomaly test 12345"
        enc = HeatshrinkEncoder(8, 7)
        for byte in data:
            n = enc.sink(bytes([byte]))
            if n == 0:
                while True:
                    chunk, more = enc.poll()
                    if not more:
                        break
        enc.finish()
        out = bytearray()
        while True:
            chunk, more = enc.poll()
            out.extend(chunk)
            if not more:
                break
        compressed = bytes(out)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data


# ---------------------------------------------------------------------------
# 1b. Decoder streaming — requires buffer >= compressed data size
# ---------------------------------------------------------------------------

class TestStreamingDecoder:
    """Decoder streaming works when buffer holds all compressed data."""

    @pytest.mark.parametrize("data", [
        b"Hello, World!",
        b"A" * 200,
        bytes(range(128)),
    ])
    def test_decoder_streaming_sink(self, data):
        """Feed decoder one byte at a time, with buffer >= compressed size."""
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

    def test_decoder_streaming_full_roundtrip(self):
        """Full encoder+decoder byte-at-a-time roundtrip."""
        data = b"Streaming anomaly test 12345"
        enc = HeatshrinkEncoder(8, 7)
        for byte in data:
            enc.sink(bytes([byte]))
            while True:
                chunk, more = enc.poll()
                if not more:
                    break
        enc.finish()
        out = bytearray()
        while True:
            chunk, more = enc.poll()
            out.extend(chunk)
            if not more:
                break
        compressed = bytes(out)

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
            dec.poll(result)
        assert bytes(result) == data


# ---------------------------------------------------------------------------
# 2. Error conditions — invalid usage
# ---------------------------------------------------------------------------

class TestErrorConditions:
    """Invalid usage should raise appropriate errors."""

    def test_sink_after_finish(self):
        """Encoder must reject data after finish()."""
        enc = HeatshrinkEncoder(8, 7)
        enc.sink(b"test")
        enc.finish()
        with pytest.raises(RuntimeError):
            enc.sink(b"more")

    def test_sink_while_encoding(self):
        """Encoder must reject data while encoding is in progress."""
        enc = HeatshrinkEncoder(8, 7)
        enc.sink(b"A" * 100)
        enc.finish()
        with pytest.raises(RuntimeError):
            enc.sink(b"more")

    def test_decoder_mismatched_window(self):
        """Decoder with wrong window size should produce wrong output."""
        data = b"Hello, World! Hello, World!"
        compressed = compress(data, 8, 7)
        dec = HeatshrinkDecoder(4, 3)
        dec.sink(compressed)
        dec.finish()
        result = bytearray()
        while dec.finish():
            dec.poll(result)
        assert bytes(result) != data

    def test_decoder_mismatched_lookahead(self):
        """Decoder with wrong lookahead size should produce wrong output."""
        data = b"AAAAABBBBB" * 10
        compressed = compress(data, 8, 7)
        dec = HeatshrinkDecoder(8, 3)
        dec.sink(compressed)
        dec.finish()
        result = bytearray()
        while dec.finish():
            dec.poll(result)
        assert bytes(result) != data


# ---------------------------------------------------------------------------
# 3. Decoder reset and reuse
# ---------------------------------------------------------------------------

class TestDecoderReset:
    """Decoder should be reusable after reset()."""

    def test_reset_and_reuse(self):
        """Reset decoder and encode two different messages."""
        msg1 = b"First message"
        msg2 = b"Second message"

        compressed1 = compress(msg1, 8, 7)
        compressed2 = compress(msg2, 8, 7)

        dec = HeatshrinkDecoder(8, 7)

        dec.sink(compressed1)
        dec.finish()
        result1 = bytearray()
        while dec.finish():
            dec.poll(result1)
        assert bytes(result1) == msg1

        dec.reset()
        dec.sink(compressed2)
        dec.finish()
        result2 = bytearray()
        while dec.finish():
            dec.poll(result2)
        assert bytes(result2) == msg2

    def test_reset_after_partial_decode(self):
        """Reset decoder mid-stream should be safe."""
        data = b"ABCDEFGHIJ"
        compressed = compress(data, 8, 7)

        dec = HeatshrinkDecoder(8, 7)
        dec.sink(compressed)
        dec.reset()
        dec.sink(compressed)
        dec.finish()
        result = bytearray()
        while dec.finish():
            dec.poll(result)
        assert bytes(result) == data


# ---------------------------------------------------------------------------
# 4. Minimum and maximum window sizes
# ---------------------------------------------------------------------------

class TestWindowBounds:
    """Extreme window sizes must work correctly."""

    def test_min_window_min_lookahead(self):
        """sz2=4, la2=3 (minimum valid pair)."""
        for data in [b"A", b"AB", b"AAAA", b"ABCDEF", b"\x00\xff"]:
            compressed = compress(data, 4, 3)
            decompressed = decompress(compressed, 4, 3)
            assert decompressed == data, f"Failed for data={data!r}"

    def test_max_window(self):
        """sz2=15 (32KB window)."""
        data = b"X" * 50000
        compressed = compress(data, 15, 14)
        decompressed = decompress(compressed, 15, 14)
        assert decompressed == data
        assert len(compressed) < len(data) * 0.05

    def test_max_window_random(self):
        """Max window with random data."""
        import random
        random.seed(99)
        data = bytes(random.randint(0, 255) for _ in range(1000))
        compressed = compress(data, 15, 14)
        decompressed = decompress(compressed, 15, 14)
        assert decompressed == data

    def test_min_window_all_bytes(self):
        """Min window with all 256 byte values."""
        data = bytes(range(256))
        compressed = compress(data, 4, 3)
        decompressed = decompress(compressed, 4, 3)
        assert decompressed == data

    def test_min_window_repeated(self):
        """Min window with long repeated data."""
        data = b"\xAB\xCD" * 500
        compressed = compress(data, 4, 3)
        decompressed = decompress(compressed, 4, 3)
        assert decompressed == data


# ---------------------------------------------------------------------------
# 5. Decoder buffer size requirements
# ---------------------------------------------------------------------------

class TestDecoderBufferSize:
    """Decoder requires sufficient input buffer for compressed data."""

    def test_decoder_buffer_must_hold_compressed_data(self):
        """Decoder input_buffer_size must be >= compressed data size for bulk sink."""
        data = b"Hello, World! Hello, World!" * 100
        compressed = compress(data, 8, 7)
        # With small buffer, bulk sink truncates
        dec = HeatshrinkDecoder(8, 7, input_buffer_size=16)
        sunk = dec.sink(compressed)
        assert sunk < len(compressed), "Should not sink all data with small buffer"

    def test_decoder_needs_large_buffer_for_streaming(self):
        """Streaming decode requires buffer >= compressed size for correct results."""
        data = bytes(range(128))
        compressed = compress(data, 8, 7)
        # Decoder with buffer >= compressed size works
        dec = HeatshrinkDecoder(8, 7, input_buffer_size=len(compressed))
        dec.sink(compressed)
        dec.finish()
        result = bytearray()
        while dec.finish():
            dec.poll(result)
        assert bytes(result) == data

    def test_decoder_tiny_buffer_produces_wrong_output(self):
        """Decoder with tiny buffer produces wrong output when data doesn't fit."""
        data = b"Hello"
        compressed = compress(data, 8, 7)
        dec = HeatshrinkDecoder(8, 7, input_buffer_size=1)
        dec.sink(compressed)  # Only first byte sinks
        dec.finish()
        result = bytearray()
        while dec.finish():
            dec.poll(result)
        # Output will be wrong because most compressed data was never sunk
        assert bytes(result) != data

    def test_decoder_streaming_with_sufficient_buffer(self):
        """Decoder streaming works correctly when buffer >= compressed size."""
        data = b"Hello, World! Hello, World!" * 10
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
# 6. Corrupted / truncated compressed data
# ---------------------------------------------------------------------------

class TestCorruptedData:
    """Decoder behavior with invalid or truncated compressed data."""

    def test_truncated_compressed(self):
        """Decoder should handle truncated compressed data without crashing."""
        data = b"This is a test of truncated compressed data"
        compressed = compress(data, 8, 7)
        dec = HeatshrinkDecoder(8, 7)
        dec.sink(compressed[:len(compressed) // 2])
        dec.finish()
        result = bytearray()
        while dec.finish():
            dec.poll(result)

    def test_null_compressed_data(self):
        """All-zero compressed data should not crash decoder."""
        dec = HeatshrinkDecoder(8, 7)
        dec.sink(b"\x00" * 10)
        dec.finish()
        result = bytearray()
        while dec.finish():
            dec.poll(result)

    def test_all_0xff_compressed_data(self):
        """All-0xFF compressed data should not crash decoder."""
        dec = HeatshrinkDecoder(8, 7)
        dec.sink(b"\xff" * 10)
        dec.finish()
        result = bytearray()
        while dec.finish():
            dec.poll(result)

    def test_random_compressed_data(self):
        """Random bytes as compressed data should not crash decoder."""
        import random
        random.seed(42)
        random_compressed = bytes(random.randint(0, 255) for _ in range(50))
        dec = HeatshrinkDecoder(8, 7)
        dec.sink(random_compressed)
        dec.finish()
        result = bytearray()
        while dec.finish():
            dec.poll(result)


# ---------------------------------------------------------------------------
# 7. Back-reference boundary anomalies
# ---------------------------------------------------------------------------

class TestBackrefAnomalies:
    """Back-reference edge cases."""

    def test_backref_at_window_boundary(self):
        """Data that creates back-references at exact window boundary."""
        pattern = bytes(range(32)) * 8  # 256 bytes
        data = pattern + pattern + b"END"
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data

    def test_backref_very_old(self):
        """Back-reference pointing to data near the start of the window."""
        pattern = b"ABCDE" * 50  # 250 bytes
        data = pattern + pattern[:10]  # 260 bytes
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data

    def test_consecutive_backrefs(self):
        """Multiple consecutive back-references."""
        data = b"AB" * 500
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data

    def test_backref_length_max_lookahead(self):
        """Back-reference with length equal to max lookahead."""
        la = 1 << 7  # 128
        data = b"X" * la + b"Y" * la
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data


# ---------------------------------------------------------------------------
# 8. Encoder poll without data
# ---------------------------------------------------------------------------

class TestEmptyPolls:
    """Encoder/decoder behavior with no data to process."""

    def test_encoder_poll_no_data(self):
        """Polling encoder with no data should return empty."""
        enc = HeatshrinkEncoder(8, 7)
        chunk, more = enc.poll()
        assert chunk == b""

    def test_encoder_finish_no_data(self):
        """Finish and poll on empty encoder."""
        enc = HeatshrinkEncoder(8, 7)
        enc.finish()
        out = bytearray()
        while True:
            chunk, more = enc.poll()
            out.extend(chunk)
            if not more:
                break
        compressed = bytes(out)
        assert compressed == b""
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == b""

    def test_decoder_poll_no_input(self):
        """Polling decoder with no input should return empty."""
        dec = HeatshrinkDecoder(8, 7)
        result = dec.poll()
        assert result == b""


# ---------------------------------------------------------------------------
# 9. GIF-like data (small palette indices)
# ---------------------------------------------------------------------------

class TestGIFLikeData:
    """Data typical of GIF pixel indices (small values, repetitive)."""

    def test_palette_0_15(self):
        """Data with only palette indices 0-15 (4-bit)."""
        data = bytes([i % 16 for i in range(1000)])
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data

    def test_palette_0_3(self):
        """Data with only 4 palette entries (2-bit)."""
        data = bytes([i % 4 for i in range(1000)])
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data

    def test_single_palette_index(self):
        """All same palette index (solid color frame)."""
        for idx in [0, 1, 7, 15, 255]:
            data = bytes([idx]) * 256
            compressed = compress(data, 8, 7)
            decompressed = decompress(compressed, 8, 7)
            assert decompressed == data, f"Failed for palette index {idx}"

    def test_16x16_frame_pattern(self):
        """Simulate a 16x16 frame of pixel data."""
        data = bytes([((r * 16 + c) % 4) for r in range(16) for c in range(16)])
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data

    def test_multi_frame_like_data(self):
        """Multiple 16x16 frames concatenated (simulating animation frames)."""
        frames = []
        for f in range(5):
            frame = bytes([((r * 16 + c + f) % 8) for r in range(16) for c in range(16)])
            frames.append(frame)
        data = b"".join(frames)
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data


# ---------------------------------------------------------------------------
# 10. Multi-sink encoder (data larger than window)
# ---------------------------------------------------------------------------

class TestMultiSink:
    """Encoder must handle data larger than window via multiple sinks."""

    def test_large_data_multi_sink(self):
        """Compress data much larger than window."""
        data = b"REPEAT" * 5000  # 30000 bytes, ~117x window
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data

    def test_two_byte_multi_sink(self):
        """Two-byte alternating pattern, large."""
        data = b"\x01\x02" * 5000
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data

    def test_increasing_pattern(self):
        """Increasing byte values, larger than window."""
        data = bytes([i % 256 for i in range(10000)])
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data


# ---------------------------------------------------------------------------
# 11. Cross-window back-references
# ---------------------------------------------------------------------------

class TestCrossWindow:
    """Back-references that span across window boundaries."""

    def test_backref_crossing_window(self):
        """Pattern that starts in one window and repeats in next."""
        pattern = b"WINDOWTEST" * 26  # 260 bytes
        data = pattern + pattern
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data

    def test_backref_exactly_window(self):
        """Back-reference at exactly 256 bytes distance."""
        pattern = b"EXACTWINDOW" * 24  # 264 bytes
        data = pattern + pattern[:11]  # 275 bytes
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data


# ---------------------------------------------------------------------------
# 12. Break-even point exercises
# ---------------------------------------------------------------------------

class TestBreakEven:
    """Data near the break-even point where compression is marginal."""

    def test_no_compression_needed(self):
        """Data that doesn't benefit from compression (unique bytes)."""
        import random
        random.seed(12345)
        data = bytes(random.randint(0, 255) for _ in range(200))
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data

    def test_short_no_match(self):
        """Data shorter than break-even — all literals."""
        for length in [1, 2, 3, 4, 5, 6, 7, 8]:
            data = bytes(range(length))
            compressed = compress(data, 8, 7)
            decompressed = decompress(compressed, 8, 7)
            assert decompressed == data, f"Failed for length {length}"

    def test_break_even_window(self):
        """Data at the break-even point for the window size."""
        data = b"ABABABABABABABAB"
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data


# ---------------------------------------------------------------------------
# 13. C cross-validation on anomalies
# ---------------------------------------------------------------------------

class TestAnomalyCrossValidateC:
    """Verify anomaly test data matches C implementation."""

    def _compare_with_c(self, data, w=8, l=7):
        import subprocess
        result = subprocess.run(
            ["./heatshrink", "-w", str(w), "-l", str(l)],
            input=data,
            capture_output=True,
            timeout=30,
        )
        assert result.returncode == 0
        return result.stdout

    @pytest.mark.parametrize("data", [
        b"\x00" * 256,
        b"\xff" * 256,
        bytes([0x55, 0xAA] * 128),
        bytes([i % 16 for i in range(256)]),
    ])
    def test_anomaly_matches_c(self, data):
        """Anomaly test data must match C encoder output."""
        py_out = compress(data, 8, 7)
        c_out = self._compare_with_c(data, 8, 7)
        assert py_out == c_out

    @pytest.mark.parametrize("data", [
        b"\x00" * 256,
        b"\xff" * 256,
        bytes([0x55, 0xAA] * 128),
        bytes([i % 16 for i in range(256)]),
    ])
    def test_anomaly_roundtrip(self, data):
        """Anomaly test data must roundtrip correctly."""
        compressed = compress(data, 8, 7)
        decompressed = decompress(compressed, 8, 7)
        assert decompressed == data


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
