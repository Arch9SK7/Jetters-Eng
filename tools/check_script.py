#!/usr/bin/env python3
import glob
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
TOKEN = re.compile(r'<\$[0-9A-Fa-f]{2}>|<[^<>]+>|.')
BREAKS = re.compile(r'<(?:LINE|HALF|WAIT|NEXT|END|PAUSE|CLOSE|E01F_CLEAR)>')


def load_table(path):
    tbl = {}
    for raw in open(path, encoding='utf-8', errors='replace'):
        line = raw.rstrip('\r\n')
        if line.startswith('/'):
            line = line[1:]
        if '=' not in line:
            continue
        k, v = line.split('=', 1)
        if k and len(k) % 2 == 0 and all(c in '0123456789ABCDEFabcdef' for c in k):
            tbl.setdefault(v, len(k) // 2)
    return tbl


def load_widths(path):
    widths = {}
    try:
        txt = open(path, encoding='utf-8', errors='replace').read()
    except OSError:
        return widths
    rows = re.findall(r'^\.db ([\d, ]+)', txt, re.M)
    vals = [int(x) for r in rows[:6] for x in r.split(',') if x.strip()]
    for i, v in enumerate(vals):
        widths[chr(0x20 + i)] = v
    return widths


def scan(path, tbl, widths):
    size = 0
    jmp = None
    unknown = {}
    lines = []
    for ln, raw in enumerate(open(path, encoding='utf-8', errors='replace'), 1):
        line = raw.rstrip('\r\n')
        m = re.match(r'\s*#JMP\(\$([0-9A-Fa-f]+)', line)
        if m:
            if jmp is None:
                jmp = int(m.group(1), 16)
            else:
                print('  note: %s:%d has a second #JMP - only the first is checked' % (os.path.basename(path), ln))
            continue
        if line.startswith('//') or line.lstrip().startswith('#') or not line.strip():
            continue
        for tok in TOKEN.findall(line):
            if tok.startswith('<$'):
                size += 1
            elif tok.startswith('<') and len(tok) > 1:
                if tok in tbl:
                    size += tbl[tok]
                else:
                    unknown[tok] = unknown.get(tok, 0) + 1
                    size += 1
            else:
                if tok not in tbl:
                    unknown[tok] = unknown.get(tok, 0) + 1
                size += tbl.get(tok, 1)
        for seg in BREAKS.split(line):
            plain = re.sub(r'<[^<>]+>', '', seg)
            if plain.strip():
                lines.append((sum(widths.get(c, 8) for c in plain), ln, plain))
    return jmp, size, unknown, lines


def main_args(args):
    rom = None
    width = None
    if '--rom' in args:
        rom = args[args.index('--rom') + 1]
    if '--width' in args:
        width = int(args[args.index('--width') + 1])
    tbl = load_table(os.path.join(ROOT, 'script', 'jetters_eng.tbl'))
    widths = load_widths(os.path.join(ROOT, 'asm', 'Font.asm'))
    files = sorted(glob.glob(os.path.join(ROOT, 'script', 'jetters_*.txt')))
    info = []
    for f in files:
        jmp, size, unknown, lines = scan(f, tbl, widths)
        if jmp is None:
            print('ERROR %s has no #JMP' % os.path.basename(f))
            return 1
        info.append((jmp, size, os.path.basename(f), unknown, lines))
    info.sort()
    ok = True
    print('Script blocks (sizes are close estimates of what Atlas writes):')
    for i, (jmp, size, name, unknown, _) in enumerate(info):
        end = jmp + size
        nxt = info[i + 1][0] if i + 1 < len(info) else None
        room = (nxt - jmp) if nxt is not None else None
        flag = ''
        if nxt is not None and end > nxt:
            flag = '  <-- OVERLAPS %s by %d bytes!' % (info[i + 1][2], end - nxt)
            ok = False
        elif room is not None and size > room * 0.9:
            flag = '  (over 90%% full)'
        print('  %-18s 0x%06X-0x%06X  %6d bytes%s%s' % (
            name, jmp, end, size, '  free %6d' % (room - size) if room is not None and room >= size else '', flag))
        if unknown:
            print('     characters/tags not in the table: %s' % ', '.join('%r x%d' % kv for kv in sorted(unknown.items())))
    if rom:
        path = rom if os.path.isabs(rom) else os.path.join(ROOT, rom)
        data = open(path, 'rb').read()
        for jmp, size, name, _, _ in info:
            area = data[jmp:jmp + size + 16]
            if any(b not in (0x00, 0xFF) for b in area):
                first = next(k for k, b in enumerate(area) if b not in (0x00, 0xFF))
                print('ERROR %s: ROM already has data at 0x%06X (inside this text block) - '
                      'armips put something there; move the #JMP' % (name, jmp + first))
                ok = False
    allines = sorted((w, n, ln, p) for _, _, n, _, ls in info for (w, ln, p) in ls)
    if width:
        wide = [x for x in allines if x[0] > width]
        print('\n%d line(s) wider than %d px:' % (len(wide), width))
        for w, n, ln, p in reversed(wide):
            print('  %3d px  %s:%d  %s' % (w, n, ln, p.strip()))
    else:
        print('\nWidest lines (use --width N to list all over N px):')
        for w, n, ln, p in reversed(allines[-5:]):
            print('  %3d px  %s:%d  %s' % (w, n, ln, p.strip()))
    if not ok:
        print('\nScript check FAILED - fix the #JMP addresses above so no block overlaps the next.')
        return 1
    print('\nScript check OK.')
    return 0


def main():
    return main_args(sys.argv[1:])


if __name__ == '__main__':
    sys.exit(main())
