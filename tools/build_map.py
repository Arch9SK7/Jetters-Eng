import sys
import struct
from PIL import Image

def build_images(pal_path, tile_path, map_path):
    try:
        #Read the Palette (First 16 colors for 4bpp)
        with open(pal_path, 'rb') as f:
            pal_data = f.read(32)
        
        flat_palette = []
        for i in range(16):
            color16 = struct.unpack('<H', pal_data[i*2:i*2+2])[0]
            #Convert 15-bit GBA color to 24-bit RGB
            r = (color16 & 0x1F) * 8
            g = ((color16 >> 5) & 0x1F) * 8
            b = ((color16 >> 10) & 0x1F) * 8
            flat_palette.extend([r, g, b])
            
        #Fill remaining palette slots (up to 256 colors) with black for PIL
        flat_palette.extend([0] * (256 * 3 - len(flat_palette)))

        #Read and Slice the Tiles
        with open(tile_path, 'rb') as f:
            tile_data = f.read()
            
        tiles = []
        for i in range(0, len(tile_data), 32):
            tile_bytes = tile_data[i:i+32]
            if len(tile_bytes) < 32:
                break
            tile_img = Image.new('P', (8, 8))
            tile_img.putpalette(flat_palette)
            pixels = tile_img.load()
            
            #Unpack 4bpp pixels
            for y in range(8):
                for x in range(0, 8, 2):
                    byte_idx = y * 4 + (x // 2)
                    byte = tile_bytes[byte_idx]
                    pixels[x, y] = byte & 0x0F
                    pixels[x+1, y] = (byte >> 4) & 0x0F
            tiles.append(tile_img)

        #Export the Palette-Accurate Jigsaw
        tiles_across = 16
        tiles_down = (len(tiles) + tiles_across - 1) // tiles_across
        jigsaw_img = Image.new('P', (tiles_across * 8, tiles_down * 8))
        jigsaw_img.putpalette(flat_palette)
        
        for idx, t_img in enumerate(tiles):
            tx = (idx % tiles_across) * 8
            ty = (idx // tiles_across) * 8
            jigsaw_img.paste(t_img, (tx, ty))
            
        jigsaw_img.save("extract/MPPAUSE_Editable.bmp")
        print("Success: Generated MPPAUSE_Editable.bmp (Paint your English letters on THIS one!)")

        #Export the Fully Assembled Map (Reference Only)
        with open(map_path, 'rb') as f:
            map_data = f.read()
            
        map_entries = len(map_data) // 2
        map_width = 32 # Standard GBA screen width
        map_height = map_entries // map_width
        
        assembled_img = Image.new('P', (map_width * 8, map_height * 8))
        assembled_img.putpalette(flat_palette)
        
        for i in range(map_entries):
            entry = struct.unpack('<H', map_data[i*2:i*2+2])[0]
            tile_id = entry & 0x03FF
            h_flip = (entry >> 10) & 1
            v_flip = (entry >> 11) & 1
            
            if tile_id < len(tiles):
                t_img = tiles[tile_id].copy()
                if h_flip:
                    t_img = t_img.transpose(Image.FLIP_LEFT_RIGHT)
                if v_flip:
                    t_img = t_img.transpose(Image.FLIP_TOP_BOTTOM)
                
                mx = (i % map_width) * 8
                my = (i // map_width) * 8
                assembled_img.paste(t_img, (mx, my))
                
        assembled_img.save("extract/MPPAUSE_Assembled.bmp")
        print("Success: Generated MPPAUSE_Assembled.bmp")

    except Exception as e:
        print(f"Failed to build images: {e}")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python build_map.py <pal.bin> <tiles.bin> <map.bin>")
    else:
        build_images(sys.argv[1], sys.argv[2], sys.argv[3])