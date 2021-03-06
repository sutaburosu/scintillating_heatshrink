// "octorokblue" (GIF orig:380 raw_payload:786 shrunk_payload:366 total:374 bytes)
// Compared to GIF: 98.42% 	Compared to raw: 47.58%
// using GIF index 4 as our transparency index 0 (blackened)
// ./heatshrink -w 8 -l 7 (background = 4; loop = 0; transparency = 4; )

FL_PROGMEM const struct HSpr_octorokblue {
	uint16_t datasize = 366;
	uint16_t frames = 3;
	uint16_t duration = 100;
	uint8_t flags = 0;
	uint8_t palette_entries = 6;
	uint8_t crgb[0] = {
		// 0x00, 0x00, 0x00,  // original palette index 4
		// 0x00, 0x00, 0x00,  // original palette index 0
		// 0x48, 0x60, 0xa8,  // original palette index 1
		// 0x78, 0x98, 0xf8,  // original palette index 2
		// 0xa8, 0xc8, 0xf8,  // original palette index 3
		// 0xf8, 0xf8, 0xf8,  // original palette index 5
	};
	uint8_t hs_data[366] = {
		0x00, 0x05, 0xa4, 0x58, 0x35, 0x17, 0x8c, 0xc7, 0xe3, 0x51, 0xc8, 0xfc, 0x00, 0x01, 0x03, 0x81, 
		0x40, 0x40, 0x00, 0xc3, 0x82, 0x20, 0x30, 0x18, 0x14, 0x0c, 0x00, 0x08, 0x22, 0x20, 0x1c, 0x0e, 
		0x09, 0x04, 0x82, 0x40, 0xe0, 0x41, 0x00, 0xb0, 0x18, 0x14, 0x0a, 0x07, 0x04, 0x82, 0xc1, 0x42, 
		0x01, 0x04, 0x60, 0xc3, 0xc1, 0x01, 0xe0, 0xe0, 0x42, 0x30, 0xa2, 0xe0, 0xd0, 0x48, 0x1c, 0x10, 
		0x84, 0x08, 0x3e, 0x18, 0x20, 0x08, 0x1c, 0x0e, 0x0b, 0x05, 0x08, 0x02, 0x2e, 0x85, 0x30, 0x04, 
		0x80, 0xc0, 0x60, 0x90, 0x43, 0x68, 0x20, 0x80, 0x38, 0x10, 0xe8, 0x10, 0x0c, 0x10, 0xcc, 0x1c, 
		0x08, 0x20, 0x0e, 0x05, 0x03, 0x07, 0x06, 0x38, 0x04, 0x81, 0x40, 0xa0, 0x20, 0xf0, 0x41, 0x70, 
		0x60, 0xf0, 0x60, 0x90, 0x70, 0x13, 0xe0, 0x20, 0x78, 0x20, 0x70, 0x38, 0x22, 0x1c, 0x18, 0x38, 
		0x18, 0xc4, 0x10, 0x3c, 0x10, 0xcc, 0x11, 0x2c, 0x20, 0x08, 0x11, 0x70, 0x13, 0x70, 0x20, 0x48, 
		0x10, 0x30, 0x18, 0x0c, 0x14, 0x10, 0x60, 0x10, 0x4c, 0x08, 0x3a, 0x15, 0xc6, 0x1c, 0x12, 0x0d, 
		0xdc, 0x1c, 0xc0, 0x11, 0x22, 0x0c, 0x38, 0x21, 0xfe, 0x19, 0xb8, 0x0c, 0x1e, 0x19, 0xfe, 0x14, 
		0x20, 0x15, 0xfe, 0x22, 0x06, 0x96, 0x06, 0x2e, 0x10, 0x1e, 0x04, 0x12, 0x06, 0xef, 0x0c, 0x0e, 
		0x08, 0xf1, 0x06, 0xce, 0x08, 0xde, 0x06, 0x0e, 0x07, 0x05, 0x82, 0x84, 0x01, 0x03, 0xc1, 0xbc, 
		0x03, 0x40, 0xa0, 0x4a, 0x00, 0x6e, 0x80, 0x80, 0x10, 0x50, 0x10, 0xa0, 0x25, 0x50, 0x57, 0xf8, 
		0x80, 0x70, 0x34, 0xf8, 0x47, 0xf8, 0x70, 0x78, 0x37, 0x70, 0x30, 0x70, 0x26, 0x78, 0x32, 0x20, 
		0x26, 0xf8, 0x57, 0xf0, 0x71, 0x70, 0x40, 0x78, 0x20, 0xe0, 0x57, 0xe8, 0x30, 0x78, 0x32, 0x98, 
		0x20, 0xe0, 0x40, 0x80, 0x62, 0x90, 0x41, 0x58, 0x50, 0x68, 0x75, 0x90, 0x22, 0xa8, 0x30, 0x70, 
		0x61, 0xc8, 0x26, 0x80, 0x47, 0x78, 0x40, 0x70, 0x57, 0x80, 0x40, 0x80, 0x50, 0x78, 0xe6, 0x78, 
		0x41, 0x78, 0x60, 0x78, 0x95, 0x50, 0x21, 0x28, 0x21, 0x00, 0x37, 0xf8, 0x78, 0x1a, 0x58, 0x11, 
		0xd0, 0x1b, 0xfc, 0x38, 0x38, 0x14, 0x16, 0x0a, 0x9b, 0x08, 0xef, 0x06, 0xda, 0x06, 0xf0, 0x06, 
		0x0f, 0x06, 0x08, 0x06, 0xff, 0x0a, 0x35, 0x04, 0x0f, 0x04, 0xba, 0x06, 0xff, 0x06, 0xef, 0x0a, 
		0xde, 0x04, 0x1d, 0x04, 0xff, 0x08, 0x2a, 0x05, 0x00, 0x80, 0x03, 0x81, 0xbc, 0x81, 0xbb, 0x84, 
		0x18, 0xc1, 0x9a, 0xc1, 0xbb, 0x45, 0x03, 0x81, 0x40, 0x0a, 0x20, 0x81, 0x81, 0x00, 
	};
} HSpr_octorokblue;
