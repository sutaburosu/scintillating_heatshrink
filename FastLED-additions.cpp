#include <FastLED.h>
#include "FastLED-additions.h"

uint16_t XY(uint8_t x, uint8_t y) {
  uint8_t major, minor, sz_major, sz_minor;
  if (x >= kMatrixWidth || y >= kMatrixHeight)
    return NUM_LEDS;
  if (XY_MATRIX & ROWMAJOR)
    major = x, minor = y, sz_major = kMatrixWidth,  sz_minor = kMatrixHeight;
  else
    major = y, minor = x, sz_major = kMatrixHeight, sz_minor = kMatrixWidth;
  if ((XY_MATRIX & FLIPMAJOR) ^ (minor & 1 && (XY_MATRIX & SERPENTINE)))
    major = sz_major - 1 - major;
  if (XY_MATRIX & FLIPMINOR)
    minor = sz_minor - 1 - minor;
  return (uint16_t) minor * sz_major + major;
}
