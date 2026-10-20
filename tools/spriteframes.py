#!/usr/bin/env python3
import json
import os
import struct
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
CONFIG = os.path.join(ROOT, 'sprites', 'sprites.json')
FRAMES_DIR = os.path.join(ROOT, 'sprites', 'frames')
SHEET_W = 32

SIZES = {(0, 0): (8, 8), (0, 1): (16, 16), (0, 2): (32, 32), (0, 3): (64, 64),
         (1, 0): (16, 8), (1, 1): (32, 8), (1, 2): (32, 16), (1, 3): (64, 32),
         (2, 0): (8, 16), (2, 1): (8, 32), (2, 2): (16, 32), (2, 3): (32, 64)}
SHAPE_OF = {v: k for k, v in SIZES.items()}

BANK_TABLE = 0x080F69CC


# Rom bullsht
class Rom:
    def __init__(self, path):
        with open(path, 'rb') as f:
            self.data = f.read()
        self.path = path

    def u8(self, a):
        return self.data[a & 0x1FFFFFF]

    def u16(self, a):
        return struct.unpack_from('<H', self.data, a & 0x1FFFFFF)[0]

    def u32(self, a):
        return struct.unpack_from('<I', self.data, a & 0x1FFFFFF)[0]

    def isptr(self, v):
        return 0x08000000 <= v < 0x08000000 + len(self.data)

    def frame_table(self, table, count=None):
        """Pointers of a frame table.  Frame data sits just before its table,
        so stop at the first entry that isn't a pointer into the 64 KB before it."""
        out = []
        a = table
        while True:
            if count is not None and len(out) >= count:
                break
            v = self.u32(a)
            if not (self.isptr(v) and table - 0x10000 < v < table):
                break
            out.append(v)
            a += 4
        return out

    def frame_bytes(self, addr):
        n = self.u8(addr)
        return self.data[addr & 0x1FFFFFF:(addr & 0x1FFFFFF) + 1 + 7 * n]


def find_rom(cfg=None):
    names = []
    if cfg and cfg.get('rom'):
        names.append(cfg['rom'])
    names += ['jetters.gba', 'Jetters.gba', 'JETTERS.GBA']
    for n in names:
        p = os.path.join(ROOT, n)
        if os.path.exists(p):
            return Rom(p)
    for n in os.listdir(ROOT):
        if n.lower() == 'jetters.gba':
            return Rom(os.path.join(ROOT, n))
    sys.exit('Clean ROM not found: put the untouched Japanese ROM in the project root as jetters.gba')


# frames model
class Piece:
    __slots__ = ('x', 'y', 'w', 'h', 'tile', 'prio', 'pal', 'flag', 'hflip', 'vflip', 'a0x', 'a1x')

    def __init__(self, **kw):
        self.x = 0; self.y = 0; self.w = 8; self.h = 8; self.tile = 0
        self.prio = 0; self.pal = 0; self.flag = 0xFF
        self.hflip = False; self.vflip = False; self.a0x = 0; self.a1x = 0
        for k, v in kw.items():
            setattr(self, k, v)

    def copy(self, **kw):
        p = Piece(**{k: getattr(self, k) for k in self.__slots__})
        for k, v in kw.items():
            setattr(p, k, v)
        return p

    @property
    def double(self):
        return bool(self.a0x & 0x02)

    def cells(self):
        """(sheet tile, unflipped screen x, y) for every 8x8 cell of the piece."""
        cw, ch = self.w // 8, self.h // 8
        ox = self.x + (self.w // 2 if self.double else 0)
        oy = self.y + (self.h // 2 if self.double else 0)
        for ty in range(ch):
            for tx in range(cw):
                sx = cw - 1 - tx if self.hflip else tx
                sy = ch - 1 - ty if self.vflip else ty
                yield self.tile + ty * SHEET_W + tx, ox + sx * 8, oy + sy * 8


def decode_frame(b):
    n = b[0]
    out = []
    for i in range(n):
        y, a0, xl, a1, t, fl = struct.unpack_from('<BBBBHB', b, 1 + 7 * i)
        shape, size = a0 >> 6, a1 >> 6
        x9 = ((a1 & 1) << 8) | xl
        w, h = SIZES[(shape, size)]
        out.append(Piece(x=x9 - 512 if x9 >= 256 else x9, y=y - 256 if y >= 128 else y, w=w, h=h,
                         tile=t & 0x3FF, prio=(t >> 10) & 3, pal=t >> 12, flag=fl,
                         hflip=bool(a1 & 0x10), vflip=bool(a1 & 0x20), a0x=a0 & 0x3F, a1x=a1 & 0x0E))
    return out


def encode_frame(pieces):
    if len(pieces) > 255:
        raise ValueError('a frame can hold at most 255 pieces')
    out = bytearray([len(pieces)])
    for p in pieces:
        if (p.w, p.h) not in SHAPE_OF:
            raise ValueError('invalid sprite size %dx%d' % (p.w, p.h))
        if not (-128 <= p.y <= 127) or not (-256 <= p.x <= 255):
            raise ValueError('piece offset out of range: x=%d y=%d' % (p.x, p.y))
        shape, size = SHAPE_OF[(p.w, p.h)]
        x9 = p.x & 0x1FF
        a0 = (shape << 6) | (p.a0x & 0x3F)
        a1 = (size << 6) | (0x20 if p.vflip else 0) | (0x10 if p.hflip else 0) | (p.a1x & 0x0E) | (x9 >> 8)
        t = (p.tile & 0x3FF) | ((p.prio & 3) << 10) | ((p.pal & 15) << 12)
        out += struct.pack('<BBBBHB', p.y & 0xFF, a0, x9 & 0xFF, a1, t, p.flag & 0xFF)
    return bytes(out)


def piece_to_text(p):
    s = 'piece x=%d y=%d size=%dx%d tile=%d' % (p.x, p.y, p.w, p.h, p.tile)
    if p.pal: s += ' pal=%d' % p.pal
    if p.prio: s += ' prio=%d' % p.prio
    s += ' flag=0x%02X' % p.flag
    if p.hflip: s += ' hflip'
    if p.vflip: s += ' vflip'
    if p.a0x: s += ' a0x=0x%02X' % p.a0x
    if p.a1x: s += ' a1x=0x%02X' % p.a1x
    return s


def parse_int(s):
    return int(s, 0)


def frames_to_text(name, table, frames, note=''):
    lines = ['# Sprite frames for %s, frame table 0x%08X' % (name, table),
             '# One "frame N" block per frame; pieces are drawn first-listed on top.',
             '# piece x/y = offset from the object origin, size = WxH in pixels,',
             '# tile = top-left tile in the sheet (sheet is 32 tiles wide: tile below N is N+32).',
             '# "rect" lines are also accepted: rect x=.. y=.. tile=.. cols=.. rows=.. [pal flag prio]',
             '#   -> split automatically into 8x8/16x8/32x8 pieces (empty tiles skipped when a sheet is set).']
    if note:
        lines += ['# ' + l for l in note.splitlines()]
    lines += ['table 0x%08X' % table, '']
    for i, ps in enumerate(frames):
        lines.append('frame %d' % i)
        for p in ps:
            lines.append('  ' + piece_to_text(p))
        lines.append('')
    return '\n'.join(lines)


def strip_runs(cells, row_of=lambda t: t // SHEET_W):
    """cells: list of (tile, sx, sy) sorted; returns horizontal runs where both
    screen x and sheet tile advance by one cell."""
    runs = []
    for c in sorted(cells, key=lambda c: (c[2], c[1])):
        if runs:
            r = runs[-1]
            t, sx, sy = r[-1]
            if c[2] == sy and c[1] == sx + 8 and c[0] == t + 1 and row_of(c[0]) == row_of(t) and len(r) < 4:
                r.append(c)
                continue
        runs.append([c])
    out = []
    for r in runs:  # 3 cells -> 16 + 8
        while r:
            n = 4 if len(r) >= 4 else 2 if len(r) >= 2 else 1
            out.append(r[:n])
            r = r[n:]
    return out


def parse_frames_text(text, sheet_tiles=None, path='?'):
    table = None
    frames = {}
    cur = None
    for ln, raw in enumerate(text.splitlines(), 1):
        line = raw.split('#', 1)[0].split(';', 1)[0].strip()
        if not line:
            continue
        tok = line.split()
        try:
            if tok[0] == 'table':
                table = parse_int(tok[1])
            elif tok[0] == 'frame':
                cur = parse_int(tok[1])
                if cur in frames:
                    raise ValueError('frame %d defined twice' % cur)
                frames[cur] = []
            elif tok[0] in ('piece', 'rect'):
                if cur is None:
                    raise ValueError('piece before any "frame N" line')
                kv = {}
                flags = set()
                for t in tok[1:]:
                    if '=' in t:
                        k, v = t.split('=', 1)
                        kv[k] = v
                    else:
                        flags.add(t)
                common = dict(pal=parse_int(kv.get('pal', '0')), prio=parse_int(kv.get('prio', '0')),
                              flag=parse_int(kv.get('flag', '0xFF')), a0x=parse_int(kv.get('a0x', '0')),
                              a1x=parse_int(kv.get('a1x', '0')))
                if tok[0] == 'piece':
                    w, h = (int(v) for v in kv['size'].lower().split('x'))
                    frames[cur].append(Piece(x=parse_int(kv['x']), y=parse_int(kv['y']), w=w, h=h,
                                             tile=parse_int(kv['tile']), hflip='hflip' in flags,
                                             vflip='vflip' in flags, **common))
                else:
                    x0, y0, t0 = parse_int(kv['x']), parse_int(kv['y']), parse_int(kv['tile'])
                    cols, rows = parse_int(kv.get('cols', '1')), parse_int(kv.get('rows', '1'))
                    cells = []
                    for r in range(rows):
                        for c in range(cols):
                            t = t0 + r * SHEET_W + c
                            if sheet_tiles is not None and 'keepempty' not in flags:
                                if t < len(sheet_tiles) and not any(sheet_tiles[t]):
                                    continue
                            cells.append((t, x0 + c * 8, y0 + r * 8))
                    for run in strip_runs(cells):
                        frames[cur].append(Piece(x=run[0][1], y=run[0][2], w=8 * len(run), h=8,
                                                 tile=run[0][0], **common))
            else:
                raise ValueError('unknown keyword "%s"' % tok[0])
        except (KeyError, ValueError, IndexError) as e:
            sys.exit('%s line %d: %s\n    %s' % (path, ln, e, raw))
    if table is None:
        sys.exit('%s: missing "table 0x........" line' % path)
    return table, frames


# config
def load_config():
    if not os.path.exists(CONFIG):
        sys.exit('missing %s' % CONFIG)
    with open(CONFIG) as f:
        return json.load(f)


MAPS_CONFIG = os.path.join(ROOT, 'sprites', 'tilemaps.json')


def load_maps_config():
    if not os.path.exists(MAPS_CONFIG):
        return {'maps': {}}
    with open(MAPS_CONFIG) as f:
        return json.load(f)


def save_maps_config(cfg):
    with open(MAPS_CONFIG, 'w', newline='\n') as f:
        json.dump(cfg, f, indent=2)


def sprite_cfg(cfg, name):
    for k, v in cfg['sprites'].items():
        if k.lower() == name.lower():
            return k, v
    sys.exit('unknown sprite "%s". Known: %s' % (name, ', '.join(cfg['sprites'])))


def tables_of(sc):
    return [parse_int(t) if isinstance(t, str) else t for t in sc['tables']]


def tile_range(s):
    out = set()
    for part in str(s).split(','):
        part = part.strip()
        if '-' in part:
            a, b = part.split('-')
            out |= set(range(parse_int(a), parse_int(b) + 1))
        elif part:
            out.add(parse_int(part))
    return out


def frames_path(name, table):
    return os.path.join(FRAMES_DIR, '%s_%08X.txt' % (name, table))


# images
def need_pil():
    if Image is None:
        sys.exit('Pillow is required for this command: pip install pillow')


def load_sheet(path):
    """Return (tiles as tuples of 64 palette indices, image)."""
    need_pil()
    im = Image.open(os.path.join(ROOT, path))
    if im.mode != 'P':
        sys.exit('%s must be an indexed (palette) image' % path)
    w, h = im.size
    px = im.load()
    tiles = []
    for ty in range(h // 8):
        for tx in range(w // 8):
            tiles.append(tuple(px[tx * 8 + x, ty * 8 + y] for y in range(8) for x in range(8)))
    return tiles, im


def render(frames_pieces, tiles, palette, scale=3, pad=8, outline=True, highlight=None):
    """Render one frame (list of pieces) the way the GBA would (no affine)."""
    need_pil()
    if not frames_pieces:
        return Image.new('RGB', (16 * scale, 16 * scale), (40, 40, 56))
    xs = [p.x for p in frames_pieces] + [p.x + p.w * (2 if p.double else 1) for p in frames_pieces]
    ys = [p.y for p in frames_pieces] + [p.y + p.h * (2 if p.double else 1) for p in frames_pieces]
    x0, y0, x1, y1 = min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad
    W, H = x1 - x0, y1 - y0
    img = Image.new('RGB', (W, H), (40, 40, 56))
    px = img.load()
    pal = [tuple(palette[i * 3:i * 3 + 3]) for i in range(len(palette) // 3)]
    for p in reversed(frames_pieces):
        for t, sx, sy in p.cells():
            if t >= len(tiles):
                continue
            data = tiles[t]
            for yy in range(8):
                for xx in range(8):
                    ix = 7 - xx if p.hflip else xx
                    iy = 7 - yy if p.vflip else yy
                    c = data[iy * 8 + ix]
                    if c:
                        X, Y = sx + xx - x0, sy + yy - y0
                        if 0 <= X < W and 0 <= Y < H:
                            px[X, Y] = pal[c] if c < len(pal) else (255, 0, 255)
    img = img.resize((W * scale, H * scale), Image.NEAREST)
    if outline:
        d = ImageDraw.Draw(img)
        for p in frames_pieces:
            bx = (p.x + (p.w // 2 if p.double else 0) - x0) * scale
            by = (p.y + (p.h // 2 if p.double else 0) - y0) * scale
            d.rectangle([bx, by, bx + p.w * scale - 1, by + p.h * scale - 1], outline=(0, 230, 0))
        # origin cross
        ox, oy = -x0 * scale, -y0 * scale
        d.line([ox - 4, oy, ox + 4, oy], fill=(255, 80, 80))
        d.line([ox, oy - 4, ox, oy + 4], fill=(255, 80, 80))
    return img


# commands
def cmd_list(args):
    rom = find_rom()
    cfg = load_config() if os.path.exists(CONFIG) else {'sprites': {}}
    known = {}
    for n, sc in cfg['sprites'].items():
        for t in tables_of(sc):
            known[t] = n
    print('Sprite banks (table at 0x%08X): bank / entry -> frame table, frame count' % BANK_TABLE)
    for bank in range(24):
        bp = rom.u32(BANK_TABLE + bank * 4)
        if not rom.isptr(bp):
            continue
        i = 0
        while i < 512:
            e = bp + i * 12
            A, B, C = rom.u32(e), rom.u32(e + 4), rom.u32(e + 8)
            if not (rom.isptr(A) and rom.isptr(B)):
                break
            fr = rom.frame_table(B)
            tag = '  <- ' + known[B] if B in known else ''
            print('  bank %2d entry %3d  frames @0x%08X  x%-3d anims @0x%08X%s' % (bank, i, B, len(fr), A, tag))
            i += 1


def coverage(rom, table):
    used = {}
    frames = [decode_frame(rom.frame_bytes(f)) for f in rom.frame_table(table)]
    for fi, ps in enumerate(frames):
        for p in ps:
            for t, _, _ in p.cells():
                used.setdefault(t, set()).add(fi)
    return frames, used


def cmd_report(args):
    if not args:
        sys.exit('usage: report <Sprite>')
    cfg = load_config()
    rom = find_rom(cfg)
    name, sc = sprite_cfg(cfg, args[0])
    sheet = sc['sheet']
    if sc.get('sheet_out') and os.path.exists(os.path.join(ROOT, sc['sheet_out'])) and '--rom' not in args:
        sheet = sc['sheet_out']
    tiles, im = load_sheet(sheet)
    sc = dict(sc, sheet=sheet)
    nonempty = {i for i, t in enumerate(tiles) if any(t)}
    rows = len(tiles) // SHEET_W
    outdir = os.path.join(ROOT, 'sprites', 'preview', name)
    os.makedirs(outdir, exist_ok=True)
    for table in tables_of(sc):
        fp = frames_path(name, table)
        if os.path.exists(fp) and '--rom' not in args:
            with open(fp) as f:
                _, fd = parse_frames_text(f.read(), tiles, fp)
            frames = [fd.get(i, []) for i in range(max(fd) + 1)] if fd else []
            src = os.path.relpath(fp, ROOT)
        else:
            frames, _ = coverage(rom, table)
            src = 'ROM'
        used = {}
        for fi, ps in enumerate(frames):
            for p in ps:
                for t, _, _ in p.cells():
                    used.setdefault(t, set()).add(fi)
        print('\n%s  frame table 0x%08X  (%d frames, layout from %s)' % (name, table, len(frames), src))
        print('  sheet %s: %d tiles, %d with pixels' % (sc['sheet'], len(tiles), len(nonempty)))
        print('  # drawn   X has pixels but NEVER drawn (inactive)   o drawn but empty   . unused')
        print('       ' + ''.join(str(c // 10) for c in range(SHEET_W)))
        print('       ' + ''.join(str(c % 10) for c in range(SHEET_W)))
        for r in range(rows):
            s = ''
            for c in range(SHEET_W):
                t = r * SHEET_W + c
                s += '#' if t in used and t in nonempty else 'X' if t in nonempty else 'o' if t in used else '.'
            print('  %4d %s' % (r * SHEET_W, s))
        inactive = sorted(nonempty - set(used))
        print('  inactive tiles (never shown in any frame): %s' % (inactive if inactive else 'none'))
        beyond = sorted(t for t in used if t >= len(tiles))
        if beyond:
            print('  WARNING frames reference tiles past the sheet: %s' % beyond)
        for fi, ps in enumerate(frames):
            ts = sorted({t for p in ps for t, _, _ in p.cells()})
            print('  frame %2d: %2d pieces, tiles %s' % (fi, len(ps), compress_ranges(ts)))
        pal = im.getpalette()
        imgs = []
        for fi, ps in enumerate(frames):
            r = render(ps, tiles, pal, scale=3)
            r.save(os.path.join(outdir, '%08X_frame%02d.png' % (table, fi)))
            imgs.append(r)
        if imgs:
            cw = max(i.width for i in imgs); chh = max(i.height for i in imgs)
            cols = 4
            sheet = Image.new('RGB', (cols * (cw + 6), ((len(imgs) + cols - 1) // cols) * (chh + 18)), (0, 0, 0))
            d = ImageDraw.Draw(sheet)
            for i, r in enumerate(imgs):
                X = (i % cols) * (cw + 6); Y = (i // cols) * (chh + 18)
                d.text((X + 2, Y + 2), 'frame %d' % i, fill=(255, 255, 0))
                sheet.paste(r, (X, Y + 16))
            sheet.save(os.path.join(outdir, '%08X_all_frames.png' % table))
    print('\nPreviews written to %s' % os.path.relpath(outdir, ROOT))


def compress_ranges(ts):
    if not ts:
        return '-'
    out = []
    s = p = ts[0]
    for t in ts[1:]:
        if t == p + 1:
            p = t
            continue
        out.append('%d' % s if s == p else '%d-%d' % (s, p))
        s = p = t
    out.append('%d' % s if s == p else '%d-%d' % (s, p))
    return ','.join(out)


def cmd_export(args):
    if not args:
        sys.exit('usage: export <Sprite> [--force]')
    cfg = load_config()
    rom = find_rom(cfg)
    name, sc = sprite_cfg(cfg, args[0])
    os.makedirs(FRAMES_DIR, exist_ok=True)
    for table in tables_of(sc):
        fp = frames_path(name, table)
        if os.path.exists(fp) and '--force' not in args:
            print('skip %s (exists; use --force to overwrite)' % os.path.relpath(fp, ROOT))
            continue
        frames, _ = coverage(rom, table)
        with open(fp, 'w', newline='\n') as f:
            f.write(frames_to_text(name, table, frames, sc.get('note', '')))
        print('wrote %s (%d frames)' % (os.path.relpath(fp, ROOT), len(frames)))


def cmd_build(args):
    cfg = load_config()
    rom = find_rom(cfg)
    out = os.path.join(ROOT, cfg.get('asm_out', 'build/sprite_frames.asm'))
    base = parse_int(cfg.get('free_space', '0x08780000'))
    limit = parse_int(cfg.get('free_space_end', '0x08800000'))
    files = sorted(f for f in os.listdir(FRAMES_DIR) if f.endswith('.txt')) if os.path.isdir(FRAMES_DIR) else []
    sheets = {}
    for n, sc in cfg['sprites'].items():
        for t in tables_of(sc):
            sheets[t] = sc.get('sheet_out') or sc.get('sheet')
    data_lines, ptr_lines = [], []
    addr = base
    changed_total = 0
    for fn in files:
        path = os.path.join(FRAMES_DIR, fn)
        with open(path) as f:
            text = f.read()
        table0 = None
        for line in text.splitlines():
            if line.strip().startswith('table'):
                table0 = parse_int(line.split()[1]); break
        st = None
        if table0 in sheets and sheets[table0] and Image is not None and os.path.exists(os.path.join(ROOT, sheets[table0])):
            st, _ = load_sheet(sheets[table0])
        table, frames = parse_frames_text(text, st, path)
        orig = rom.frame_table(table)
        label = os.path.splitext(fn)[0]
        changed = 0
        for i in sorted(frames):
            if i >= len(orig):
                sys.exit('%s: frame %d does not exist (table has %d frames; the animation scripts only use those)'
                         % (fn, i, len(orig)))
            new = encode_frame(frames[i])
            if new == rom.frame_bytes(orig[i]):
                continue
            lab = '%s_f%d' % (label, i)
            data_lines.append('%s: ; %d pieces' % (lab, len(frames[i])))
            for k in range(0, len(new), 16):
                data_lines.append('  .byte ' + ', '.join('0x%02X' % b for b in new[k:k + 16]))
            ptr_lines.append('.org 0x%08X\n  .word %s' % (table + 4 * i, lab))
            addr += len(new)
            changed += 1
        changed_total += changed
        print('%-28s %2d of %2d frames changed' % (fn, changed, len(orig)))
    if addr > limit:
        sys.exit('frame data does not fit in free space 0x%08X-0x%08X' % (base, limit))

    map_lines = []
    mcfg = load_maps_config()
    for mname, mc in mcfg.get('maps', {}).items():
        if not mc.get('rom') or not mc.get('file'):
            continue
        fpath = os.path.join(ROOT, mc['file'])
        if not os.path.exists(fpath):
            continue
        data = open(fpath, 'rb').read()
        want = int(mc['width']) * int(mc['height']) * 2
        if len(data) != want:
            sys.exit('map %s: %s is %d bytes, expected %d (%dx%d)' % (mname, mc['file'], len(data), want,
                                                                     mc['width'], mc['height']))
        ra = parse_int(mc['rom']) & 0x1FFFFFF
        if rom.data[ra:ra + want] == data:
            print('%-28s unchanged' % ('map ' + mname))
            continue
        map_lines.append('; map %s\n.org 0x%08X\n  .import "%s"' % (mname, 0x08000000 | ra, mc['file'].replace('/', '\\')))
        print('%-28s written in place at 0x%08X' % ('map ' + mname, 0x08000000 | ra))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', newline='\n') as f:
        f.write('; generated by tools/spriteframes.py build - do not edit, edit sprites/frames/*.txt\n')
        if data_lines:
            f.write('.org 0x%08X\n' % base)
            f.write('\n'.join(data_lines) + '\n')
            f.write('.if org() > 0x%08X\n  .error "sprite frame data overflowed its free space"\n.endif\n\n' % limit)
            f.write('; repoint frame tables\n')
            f.write('\n'.join(ptr_lines) + '\n')
        if map_lines:
            f.write('\n; background tilemaps\n' + '\n'.join(map_lines) + '\n')
    print('wrote %s: %d new frames, %d bytes at 0x%08X' % (os.path.relpath(out, ROOT), changed_total, addr - base, base))


def cmd_selftest(args):
    rom = find_rom()
    n = bad = skipped = 0
    for bank in range(24):
        bp = rom.u32(BANK_TABLE + bank * 4)
        if not rom.isptr(bp):
            continue
        i = 0
        while i < 512:
            e = bp + i * 12
            A, B = rom.u32(e), rom.u32(e + 4)
            if not (rom.isptr(A) and rom.isptr(B)):
                break
            for f in rom.frame_table(B):
                b = rom.frame_bytes(f)
                try:
                    ps = decode_frame(b)
                except KeyError:
                    skipped += 1
                    continue
                try:
                    txt = frames_to_text('t', B, [ps])
                    _, fr = parse_frames_text(txt)
                    ok = encode_frame(fr[0]) == b
                except Exception:
                    ok = False
                n += 1
                bad += not ok
            i += 1
    print('round-trip %d frames, %d mismatches (%d non-frame entries skipped)' % (n, bad, skipped))
    return bad == 0


# relayout
def word_frames(frames, rng):
    return [i for i, ps in enumerate(frames) if any(p.tile in rng for p in ps)]


def pick_rest(frames, idxs, rng):
    def key(i):
        ps = [p for p in frames[i] if p.tile in rng]
        ts = {t for p in ps for t, _, _ in p.cells()}
        return (len(ts), sum(p.flag == 0xFF for p in ps), -sum(p.double for p in ps), -i)
    return max(idxs, key=key)


def rest_layout(frames, rest, rng):
    pos = {}
    for p in frames[rest]:
        if p.tile in rng:
            for t, sx, sy in p.cells():
                pos.setdefault(t, (sx, sy))
    return pos


def cmd_words(args):
    """Render each word's rest frame from the current sheet into an editable image."""
    if not args:
        sys.exit('usage: words <Sprite> [--force]')
    cfg = load_config()
    rom = find_rom(cfg)
    name, sc = sprite_cfg(cfg, args[0])
    tiles, im = load_sheet(sc['sheet'])
    table = tables_of(sc)[0]
    frames, _ = coverage(rom, table)
    margin = 16
    changed = False
    for w in sc.get('words', []):
        rng = tile_range(w['tiles'])
        idxs = word_frames(frames, rng)
        rest = w.get('rest', pick_rest(frames, idxs, rng))
        pos = rest_layout(frames, rest, rng)
        xs = [p[0] for p in pos.values()]; ys = [p[1] for p in pos.values()]
        x0, y0 = min(xs) - margin, min(ys) - margin
        W = max(xs) + 8 + margin - x0; H = max(ys) + 8 + margin - y0
        W = (W + 7) // 8 * 8; H = (H + 7) // 8 * 8
        targets = [(w['image'], tiles, im)]
        for v in sc.get('variants', []):
            vp = w.get('variant_images', {}).get(v['name'])
            if vp:
                vt, vim = load_sheet(v['sheet'])
                targets.append((vp, vt, vim))
        wrote = False
        for ipath, src_tiles, src_im in targets:
            path = os.path.join(ROOT, ipath)
            if os.path.exists(path) and '--force' not in args:
                print('skip %s (exists; --force to overwrite)' % ipath)
                continue
            img = Image.new('P', (W, H), 0)
            img.putpalette(src_im.getpalette())
            px = img.load()
            for p in reversed(frames[rest]):
                if p.tile not in rng:
                    continue
                for t, sx, sy in p.cells():
                    for yy in range(8):
                        for xx in range(8):
                            c = src_tiles[t][yy * 8 + xx] if t < len(src_tiles) else 0
                            if c:
                                px[sx + xx - x0, sy + yy - y0] = c
            os.makedirs(os.path.dirname(path), exist_ok=True)
            img.save(path)
            print('wrote %s' % ipath)
            wrote = True
        if not wrote:
            continue
        w['anchor'] = [x0, y0]
        w['rest'] = rest
        changed = True
        print('  %s: %dx%d canvas, rest frame %d, anchor %d,%d' % (w['name'], W, H, rest, x0, y0))
    if changed:
        with open(CONFIG, 'w', newline='\n') as f:
            json.dump(cfg, f, indent=2)
        print('anchors saved to sprites/sprites.json')


def cmd_relayout(args):
    if not args:
        sys.exit('usage: relayout <Sprite>')
    need_pil()
    cfg = load_config()
    rom = find_rom(cfg)
    name, sc = sprite_cfg(cfg, args[0])
    tiles, im = load_sheet(sc['sheet'])
    ntiles = int(sc.get('max_tiles', len(tiles)))
    words = sc.get('words', [])
    if not words:
        sys.exit('%s has no "words" in sprites.json' % name)
    tables = tables_of(sc)
    all_frames = {t: coverage(rom, t)[0] for t in tables}


    word_src = set()
    for w in words:
        word_src |= tile_range(w['tiles'])
    if 'slots' in sc:
        slots = tile_range(sc['slots'])
    else:
        used_elsewhere = set()
        for fr in all_frames.values():
            for ps in fr:
                for p in ps:
                    if p.tile not in word_src:
                        used_elsewhere |= {t for t, _, _ in p.cells()}
        slots = (set(range(ntiles)) - used_elsewhere) | word_src
    slots = {s for s in slots if s < ntiles}

    free = sorted(slots)
    free_set = set(free)
    cell_tile = []  # per word: {(cx,cy): tile}
    word_cells = []
    new_tiles = list(tiles) + [tuple([0] * 64)] * max(0, ntiles - len(tiles))
    for s in slots:
        new_tiles[s] = tuple([0] * 64)
    variants = sc.get('variants', [])
    var_tiles = []
    for v in variants:
        vt, _ = load_sheet(v['sheet'])
        vt = list(vt) + [tuple([0] * 64)] * max(0, ntiles - len(vt))
        for s_ in slots:
            vt[s_] = tuple([0] * 64)
        var_tiles.append(vt)
    word_origin = []
    shared = {}  
    needed = []
    for w in words:
        paths = [w['image']] + [w.get('variant_images', {}).get(v['name']) for v in variants]
        pxs = []
        iw = ih = None
        for ip in paths:
            if not ip or not os.path.exists(os.path.join(ROOT, ip)):
                if ip is paths[0]:
                    sys.exit('missing word image %s - run "words %s" first' % (ip, name))
                pxs.append(None)
                continue
            wi = Image.open(os.path.join(ROOT, ip))
            if wi.mode != 'P':
                sys.exit('%s must be an indexed image using the sheet palette' % ip)
            if iw is None:
                iw, ih = wi.size
            elif wi.size != (iw, ih):
                sys.exit('%s must be the same size as %s (%dx%d)' % (ip, paths[0], iw, ih))
            pxs.append(wi.load())
        ink = sorted({(x, y) for px in pxs if px for y in range(ih) for x in range(iw) if px[x, y]})

        def cut(ox, oy):
            cs = {}
            for x, y in ink:
                cs.setdefault(((x + ox) // 8, (y + oy) // 8), None)
            for (cx, cy) in cs:
                cs[(cx, cy)] = tuple(
                    tuple(px[cx * 8 + xx - ox, cy * 8 + yy - oy]
                          if px and 0 <= cx * 8 + xx - ox < iw and 0 <= cy * 8 + yy - oy < ih else 0
                          for yy in range(8) for xx in range(8))
                    for px in pxs)
            return cs
        best = None
        for oy in range(8):
            for ox in range(8):
                cs = cut(ox, oy)
                key = (len(set(cs.values())), len(cs), oy, ox)
                if best is None or key < best[0]:
                    best = (key, ox, oy, cs)
        _, ox, oy, cells = best
        ax, ay = w.get('anchor', [0, 0])
        word_origin.append((ax - ox, ay - oy))
        word_cells.append(cells)
        mapping = {}
        new_here = 0
        for cy in sorted({c[1] for c in cells}):
            row = sorted(cx for (cx, yy) in cells if yy == cy)
            runs = []
            for cx in row:
                if cells[(cx, cy)] in shared:
                    mapping[(cx, cy)] = shared[cells[(cx, cy)]]
                    runs.append(None)
                    continue
                if runs and runs[-1] and runs[-1][-1] == cx - 1:
                    runs[-1].append(cx)
                else:
                    runs.append([cx])
            for run in [r for r in runs if r]:
                while run:
                    if cells[(run[0], cy)] in shared:
                        mapping[(run[0], cy)] = shared[cells[(run[0], cy)]]
                        run = run[1:]
                        continue
                    placed = False
                    for n in range(len(run), 0, -1):
                        for s in free:
                            if s in free_set and all((s + k) in free_set and (s + k) // SHEET_W == s // SHEET_W
                                                     for k in range(n)):
                                for k in range(n):
                                    data = cells[(run[k], cy)]
                                    if data in shared:
                                        mapping[(run[k], cy)] = shared[data]
                                        continue
                                    mapping[(run[k], cy)] = s + k
                                    shared[data] = s + k
                                    free_set.discard(s + k)
                                    new_tiles[s + k] = data[0]
                                    for vi in range(len(variants)):
                                        var_tiles[vi][s + k] = data[vi + 1]
                                    new_here += 1
                                run = run[n:]
                                placed = True
                                break
                        if placed:
                            break
                    if not placed:
                        total = sum(needed) + len(set(cells.values()))
                        sys.exit('Out of sheet space: the words need about %d tiles but the sheet only has %d slots '
                                 '("max_tiles" in sprites/sprites.json).\n'
                                 'Make the art a little narrower or shorter - each 8x8 block of the word image that has '
                                 'any pixels uses one tile.' % (total, len(slots)))
        needed.append(new_here)
        cell_tile.append(mapping)
        print('  %s: %d tiles (%d unique) with the grid shifted %d,%d px' % (w['name'], len(cells), len(set(cells.values())), ox, oy))
    used_tiles = len(slots) - len(free_set)
    print('%s: packed %d English tiles into %d available slots' % (name, used_tiles, len(slots)))

    def write_sheet(src_im, data_tiles, out_sheet):
        W, H = src_im.size
        rows_needed = (ntiles + SHEET_W - 1) // SHEET_W
        H = max(H, rows_needed * 8)
        ns = Image.new('P', (W, H), 0)
        ns.putpalette(src_im.getpalette())
        npx = ns.load()
        for t, data in enumerate(data_tiles[:max(ntiles, len(data_tiles))]):
            tx, ty = (t % SHEET_W) * 8, (t // SHEET_W) * 8
            if ty >= H:
                break
            for i, c in enumerate(data):
                npx[tx + i % 8, ty + i // 8] = c
        op = os.path.join(ROOT, out_sheet)
        os.makedirs(os.path.dirname(op), exist_ok=True)
        ns.save(op)
        print('wrote sheet %s' % out_sheet)
    write_sheet(im, new_tiles, sc.get('sheet_out', sc['sheet']))
    for vi, v in enumerate(variants):
        write_sheet(load_sheet(v['sheet'])[1], var_tiles[vi], v.get('sheet_out', v['sheet']))

    os.makedirs(FRAMES_DIR, exist_ok=True)
    for table in tables:
        frames = all_frames[table]
        out_frames = [list(ps) for ps in frames]
        for wi_, w in enumerate(words):
            rng = tile_range(w['tiles'])
            idxs = word_frames(frames, rng)
            rest = w.get('rest', pick_rest(frames, idxs, rng))
            rpos = rest_layout(frames, rest, rng)
            if 'anchor' not in w:
                sys.exit('word "%s" has no anchor - run "words %s" first or set "anchor": [x, y]' % (w['name'], name))
            ax, ay = word_origin[wi_]
            cells = word_cells[wi_]
            track = {}
            for (cx, cy) in cells:
                ex, ey = ax + cx * 8, ay + cy * 8
                best = None
                for t, (rx, ry) in rpos.items():
                    ov = max(0, 8 - abs(rx - ex)) * max(0, 8 - abs(ry - ey))
                    d = (rx - ex) ** 2 + (ry - ey) ** 2
                    k = (-ov, d)
                    if best is None or k < best[0]:
                        best = (k, t)
                track[(cx, cy)] = best[1]
            for fi in idxs:
                ps = frames[fi]
                occ = {}  # jp tile -> list of (dx, dy, piece, order)
                first_word = None
                for order, p in enumerate(ps):
                    if p.tile not in rng:
                        continue
                    if first_word is None:
                        first_word = order
                    for t, sx, sy in p.cells():
                        if t in rpos:
                            occ.setdefault(t, []).append((sx - rpos[t][0], sy - rpos[t][1], p, order))
                placed = {}  # attr key -> list of (tile, sx, sy, order)
                for (cx, cy), t in track.items():
                    for dx, dy, p, order in occ.get(t, []):
                        key = (p.pal, p.prio, p.flag, p.a0x, p.a1x, dx, dy)
                        placed.setdefault(key, []).append(
                            (cell_tile[wi_][(cx, cy)], ax + cx * 8 + dx, ay + cy * 8 + dy, order))
                gen = []
                for key, cl in placed.items():
                    pal, prio, flag, a0x, a1x, dx, dy = key
                    order = min(c[3] for c in cl)
                    for run in strip_runs([c[:3] for c in cl]):
                        w8 = 8 * len(run)
                        x, y = run[0][1], run[0][2]
                        if a0x & 0x02:
                            x -= w8 // 2; y -= 4
                        gen.append((order, y, x, Piece(x=x, y=y, w=w8, h=8, tile=run[0][0], pal=pal, prio=prio,
                                                       flag=flag, a0x=a0x, a1x=a1x)))
                gen.sort(key=lambda g: (g[0], g[1], g[2]))
                keep = [p for p in out_frames[fi] if p.tile not in rng]
                before = [p for p in out_frames[fi][:first_word or 0] if p.tile not in rng]
                after = [p for p in keep if p not in before]
                out_frames[fi] = before + [g[3] for g in gen] + after
                if len(out_frames[fi]) > 128:
                    print('  WARNING frame %d uses %d OAM pieces' % (fi, len(out_frames[fi])))
        fp = frames_path(name, table)
        note = ('GENERATED by "spriteframes.py relayout %s" from the word images in sprites.json.\n'
                'Re-running relayout overwrites this file. To hand-edit instead, remove "words" from the config.' % name)
        with open(fp, 'w', newline='\n') as f:
            f.write(frames_to_text(name, table, out_frames, note))
        print('wrote %s' % os.path.relpath(fp, ROOT))


GFX_TABLES = {5: (0x080F61AC, 130), 11: (0x080D45F0, 10)}


def lz77(rom, addr):
    a = addr & 0x1FFFFFF
    hdr = struct.unpack_from('<I', rom.data, a)[0]
    if hdr & 0xFF != 0x10:
        raise ValueError('no LZ77 data at 0x%08X' % addr)
    size = hdr >> 8
    out = bytearray()
    p = a + 4
    d = rom.data
    while len(out) < size:
        flags = d[p]; p += 1
        for _ in range(8):
            if len(out) >= size:
                break
            if flags & 0x80:
                b1, b2 = d[p], d[p + 1]; p += 2
                n = (b1 >> 4) + 3; disp = ((b1 & 0xF) << 8 | b2) + 1
                for _ in range(n):
                    out.append(out[-disp])
            else:
                out.append(d[p]); p += 1
            flags = (flags << 1) & 0xFF
    return bytes(out)


def bank_entries(rom):
    """All sprite bank entries: dicts with bank, entry, frames table, anim table, gfx info."""
    out = []
    for bank in range(24):
        bp = rom.u32(BANK_TABLE + bank * 4)
        if not rom.isptr(bp):
            continue
        i = 0
        while i < 512:
            e = bp + i * 12
            A, B = rom.u32(e), rom.u32(e + 4)
            if not (rom.isptr(A) and rom.isptr(B)):
                break
            ent = dict(bank=bank, entry=i, table=B, anims=A, frames=len(rom.frame_table(B)))
            if bank in GFX_TABLES and i < GFX_TABLES[bank][1]:
                g = GFX_TABLES[bank][0] + i * 16
                gfx, pal = rom.u32(g), rom.u32(g + 8)
                hdr = rom.u32(gfx)
                if hdr & 0xFF == 0x10:
                    ent.update(gfx=gfx, pal=pal, tiles=(hdr >> 8) // 32)
            out.append(ent)
            i += 1
    return out


def find_anim_table(rom, table):
    """Anim table that sits next to a frame table ({anims, frames, ...} entries)."""
    needle = struct.pack('<I', table)
    i = rom.data.find(needle)
    while i != -1:
        if i % 4 == 0 and i >= 4:
            A = struct.unpack_from('<I', rom.data, i - 4)[0]
            if rom.isptr(A) and A - 0x10000 < rom.u32(A) < A:
                return A
        i = rom.data.find(needle, i + 1)
    return None


def parse_anims(rom, table):
    A = find_anim_table(rom, table)
    if A is None:
        return []
    anims = []
    a = A
    while True:
        p = rom.u32(a)
        if not (rom.isptr(p) and A - 0x10000 < p < A) or len(anims) > 64:
            break
        steps = []
        q = p
        for _ in range(512):
            b = rom.u8(q)
            if b == 0xFF:
                break
            if b == 0xFC:
                q += 2; continue
            if b == 0xFD:
                q += 5; continue
            if b == 0xFE:
                q += 7; continue
            steps.append([b, max(1, rom.u8(q + 1))])
            q += 2
        anims.append(dict(addr=p, steps=steps))
        a += 4
    return anims


def extract_sheet(rom, gfx, pal, path):
    """Decompress a sprite graphic + palette into a 256-px-wide indexed BMP."""
    need_pil()
    data = lz77(rom, gfx)
    n = len(data) // 32
    rows = (n + SHEET_W - 1) // SHEET_W
    im = Image.new('P', (SHEET_W * 8, rows * 8), 0)
    palette = []
    for i in range(16):
        c = rom.u16(pal + i * 2)
        palette += [(c & 31) * 8, ((c >> 5) & 31) * 8, ((c >> 10) & 31) * 8]
    im.putpalette(palette + [0] * (768 - len(palette)))
    px = im.load()
    for t in range(n):
        tx, ty = (t % SHEET_W) * 8, (t // SHEET_W) * 8
        for k in range(32):
            b = data[t * 32 + k]
            px[tx + (k % 4) * 2, ty + k // 4] = b & 15
            px[tx + (k % 4) * 2 + 1, ty + k // 4] = b >> 4
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)
    return n


COMMANDS = {'list': cmd_list, 'report': cmd_report, 'export': cmd_export, 'build': cmd_build,
            'selftest': cmd_selftest, 'words': cmd_words, 'relayout': cmd_relayout}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    r = COMMANDS[sys.argv[1]](sys.argv[2:])
    if r is False:
        sys.exit(1)
