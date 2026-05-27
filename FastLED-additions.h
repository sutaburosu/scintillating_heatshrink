#ifndef FASTLED_ADDITIONS_HH
#define FASTLED_ADDITIONS_HH 1

#include <FastLED.h>

#ifndef kMatrixWidth
#define kMatrixWidth 16
#endif
#ifndef kMatrixHeight
#define kMatrixHeight 16
#endif
#ifndef XY_MATRIX
#define XY_MATRIX (SERPENTINE | ROWMAJOR)
#endif
#ifndef NUM_LEDS
#define NUM_LEDS (kMatrixWidth * kMatrixHeight)
#endif

// untested portability to non-AVR systems
#if FASTLED_USE_PROGMEM == 1
#define FL_PGM_READ_PTR_NEAR(x) (pgm_read_ptr_near(x))
#else
#define FL_PGM_READ_PTR_NEAR(addr) ({typeof(addr) _addr = (addr); *(void * const *)(_addr); })
#define memcpy_P(dest, src, n) memcpy(dest, src, n)
#endif

enum XY_matrix_config {
  SERPENTINE = 1,
  ROWMAJOR = 2,
  FLIPMAJOR = 4,
  FLIPMINOR = 8
};

uint16_t XY(uint8_t x, uint8_t y);
CRGB fadeTowardColour(CRGB& cur, const CRGB& target, uint8_t amount);
CRGB fadeTowardColour_video(CRGB& cur, const CRGB& target, uint8_t amount);
#endif