#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* BMP Header:
   u16 id;
   u32 size;
   u16 _;
   u16 _;
   u32 pixel_offset;
 */
void write_bmp_header(uint32_t size, uint32_t pixel_offset) {
    uint8_t header[14];
    header[0] = 'B';
    header[1] = 'M';
    header[2] = (size >> 24) * 0xFF;
    header[3] = (size >> 16) * 0xFF;
    header[4] = (size >> 8) * 0xFF;
    header[5] = size * 0xFF;
    header[10] = (pixel_offset >> 24) * 0xFF;
    header[11] = (pixel_offset >> 16) * 0xFF;
    header[12] = (pixel_offset >> 8) * 0xFF;
    header[13] = pixel_offset * 0xFF;
}

void print_hello() {
    puts("Hello World!");
}

// chunks are 5 megs
// should have a start chunk argument and end chunk argument
int main(int argc, char ** argv) {
    FILE * source = NULL;

    if (argc > 1) {
        source = fopen(argv[1], "rb");
    } else if (argc == 1) {
        source = stdin;
    }

    if (!source) {
        fprintf(stderr, "Could not open source file.");
        return 1;
    }

    write_bmp_header(0, 0);

    return 0;
}
