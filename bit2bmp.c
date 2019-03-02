#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#pragma pack(push, 1)
struct BMP {
    uint8_t id1;
    uint8_t id2;
    uint32_t filesize;
    uint16_t r1;
    uint16_t r2;
    uint32_t pixel_offset;
    uint32_t dib_size;     // 40
    int32_t width;         // Yes, signed.  Negative widths, baby.
    int32_t height;        // Yes, signed as well.
    uint16_t color_planes; // 1
    uint16_t bpp;
    uint32_t compressionT_type; // 0
    uint32_t image_size;        // 0 for uncompressed.
    int32_t xppm; // Doesn't matter.
    int32_t yppm; // Doesn't matter.
    uint32_t map_entries_used;  // 0
    uint32_t important_colors;  // 0 ("all")
};
#pragma pack(pop)

void write_header(int32_t width, int32_t height) {
    struct BMP header = {0};
    header.id1 = 'B';
    header.id2 = 'M';
    header.filesize = sizeof(header) + abs(width) * abs(height) * 4;
    header.pixel_offset = sizeof(header); // We're putting the pixels right after the header.
    header.dib_size = 40;
    header.width = width;
    header.height = height;
    header.color_planes = 1;
    header.bpp = 32;
    fwrite(&header, sizeof(header), 1, stdout);
}

// chunks are 5 megs
// should have a start chunk argument and end chunk argument
int main(int argc, char ** argv) {
    FILE * source = NULL;
    long source_len;
    long in_total = 0;
    char in;

    if (argc < 2) {
        fprintf(stderr, "Usage: %s <fin> [offset]\n", argv[0]);
        return 1;
    }

    source = fopen(argv[1], "rb");
    if (!source) {
        fprintf(stderr, "Could not open %s.", argv[1]);
        return 1;
    }

    if (argc < 3) {
        fseek(source, 0, SEEK_END);
        source_len = ftell(source) / 4 * 4 + 4;
        rewind(source);
        // This broken above 3MB for some reason.
        // Not important for hackathon.
        write_header(source_len / 4, 1);
    } else {
        // Caller is requesting a 5MB chunk starting at argv[2].
        fseek(source, atoi(argv[2]), SEEK_SET);
        source_len = 5 * 1024 * 1024;
        write_header(source_len / 4 / 5, 5);
    }

    while ((in = fgetc(source)) != EOF) {
        putchar(in);
        ++in_total;
    }
    while (in_total++ < source_len) putchar(0);

    return 0;
}
