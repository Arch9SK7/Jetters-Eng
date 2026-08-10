import sys

def extract_raw(rom_path, out_path, offset_hex, size_hex):
    try:
        with open(rom_path, 'rb') as rom:
            rom.seek(int(offset_hex, 16))
            data = rom.read(int(size_hex, 16))
        
        with open(out_path, 'wb') as out:
            out.write(data)
            
        print(f"Success! Extracted {int(size_hex, 16)} bytes from offset {offset_hex}.")
    except Exception as e:
        print(f"Failed to extract: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python dump_raw.py <rom.gba> <output.bin> <offset_hex> <size_hex>")
    else:
        extract_raw(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])