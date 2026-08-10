an overview of what each tool does

armips.exe
----------
asm assembler / patcher

can do a variety of tasks.

in fact, armips can be used to extract various data
instead of just patching (check out the extract.bat script)

please do not replace! don't fix things that aren't broken!

C1.exe
------
process raw map into asm jetters compatible map

used during the build process after E1.exe generates a
"raw" map file from tiles and descriptor

E1.exe
------
creates a bmp file and descriptor from a tileset and jetters map

used during for the extract process

G1.exe
------
creates a raw map and tileset from a bmp

meant to be generic, basically replicates the function of grit

note: g1 process tiles from top-to-bottom, left-to-right
so the top left tile will be tile 1 or 0
(tile 0 will always be the empty tile)

GBAmdc.exe
----------
extracts and decompress lz77 directly from rom

used for the extract process

lzss.exe
--------
compress/decompress files as lz77

used for the build process
to compress tilesets


B8.exe
----------
8bpp Tile Builder via Map Layout. Reconstructs raw 8bpp GBA tiles from an indexed BMP by mapping its pixel positions back into the tile slots defined by an existing GBA map binary, accounting for tile horizontal/vertical flipping.

Build_Map.py
----------
4bpp Tile and Map Assembling Utility. Converts GBA 15-bit color palette, raw 4bpp tile, and map binaries into two indexed BMPs, a tile sheet (MPPAUSE_Editable.bmp) for editing and a fully assembled screen preview (MPPAUSE_Assembled.bmp) (This was made basically just for this graphic cause w.e).

decompile_to_tileset.exe
----------
Screenshot Decompiler. Reads an edited indexed BMP and a original GBA map file to extract, reverse-flip, and rebuild a raw 16-bit GBA color palette and tile binary without exceeding target VRAM limits.

dump_raw.py
----------
Raw ROM Extractor. Seeks to a specified hex offset in a ROM file and extracts a chunk of raw binary data of a given size to disk.

E8.exe
----------
8bpp Map Visualizer / Extractor. Converts GBA palette, 8bpp tile, and map binaries into a single assembled indexed BMP file, applying tile index offsets and hardware flips.

G4Custom.exe
----------
4bpp Custom Sprite Packer. Reads an indexed BMP image and packs its 8x8 pixel blocks into a raw GBA 4bpp tile binary (packing 2 pixels per byte, low/high nibbles).

G8.exe
----------
8bpp Graphics Encoder. Converts one or more indexed BMP images into a contiguous raw 8bpp GBA tile binary (1 byte per pixel).

lzssCustom.exe
----------
GBA LZ77 Compressor. Takes a raw binary file and encodes it into GBA BIOS-compliant LZ77 compressed format starting with the standard 0x10 header.

R4.exe
----------
Raw 4bpp Tile Dump Utility. Renders raw 4bpp tile graphics directly to a grid-aligned BMP tile sheet based on a specified tile width and GBA palette file, without requiring a map file (I made this bitch way too late after getting pissed off trying to hunt down map files for the remaining graphic).