"""
GENTAHAX MCP — Gerçek Growtopia Dünya Görüntüleyici (Minimap tarzı)
mr_berk edition

GENTAHAX'ın kendi Minimap'i (GTInternal.dll içindeki '##minimap_logic') nasıl çiziyorsa
aynı yolu izler:
  1) game/*.rttex dosyalarını açar  (RTPACK -> zlib -> RTTXTR -> RGBA, dikey çevrilmiş)
  2) Her item ID için texture dosyası + texturePos (x, y) + spreadType bilgisini
     oyunun kendi cache/items.dat dosyasından okur
  3) 32x32 sprite'ı keser; spreadType == 2 (Dirt, Bedrock, Cave BG...) için
     komşu bloklara göre 'Connected Texture' karesini seçer
  4) Önce BG, sonra FG sprite'ını alfa ile üst üste çizer

ASLA sahte veri üretmez: dünya kareleri sadece oyundan (checkTile/getTile) gelir,
görseller sadece kullanıcının bilgisayarındaki gerçek oyun dosyalarından okunur.
"""
import os
import re
import struct
import zlib
from functools import lru_cache
from pathlib import Path

TILE = 32
ITEMS_DAT_KEY = b"PBG892FXX982ABC*"

# spreadType == 2 (smart edge, 8x6 atlas) — kareler gerçek Dirt atlasının
# (tiles_page1.rttex @ 8,20) piksel analiziyle çıkarıldı.
# (ofsX, ofsY): (üst_boş, sol_boş, sağ_boş, alt_boş, solüst_çapraz_boş, sağüst_çapraz_boş)
_SMART_EDGE = [
    ((0, 0), (0, 0, 0, 0, 0, 0)),
    ((1, 0), (1, 0, 0, 0, 0, 0)),
    ((3, 0), (0, 1, 0, 0, 0, 0)),
    ((4, 0), (0, 0, 1, 0, 0, 0)),
    ((5, 0), (1, 1, 0, 0, 0, 0)),
    ((6, 0), (1, 0, 1, 0, 0, 0)),
    ((7, 0), (0, 1, 0, 1, 0, 0)),
    ((0, 1), (0, 0, 1, 1, 0, 0)),
    ((1, 1), (0, 1, 1, 0, 0, 0)),
    ((2, 1), (1, 1, 1, 0, 0, 0)),
    ((3, 1), (0, 1, 1, 1, 0, 0)),
    ((4, 1), (1, 1, 1, 1, 0, 0)),
    ((5, 1), (0, 0, 0, 0, 1, 0)),
    ((6, 1), (0, 0, 0, 0, 0, 1)),
    ((7, 1), (0, 0, 0, 1, 0, 0)),
    ((1, 2), (0, 0, 0, 0, 1, 1)),
    ((3, 2), (0, 0, 0, 1, 1, 0)),
    ((4, 2), (0, 0, 0, 1, 0, 1)),
    ((4, 3), (1, 0, 0, 1, 0, 0)),
    ((5, 3), (1, 1, 0, 1, 0, 0)),
    ((6, 3), (1, 0, 1, 1, 0, 0)),
    ((7, 3), (0, 1, 0, 0, 0, 1)),
    ((2, 4), (0, 0, 1, 0, 1, 0)),
    ((2, 5), (0, 0, 0, 1, 1, 1)),
    ((3, 5), (0, 1, 0, 1, 0, 1)),
    ((4, 5), (0, 0, 1, 1, 1, 0)),
]
_SE_WEIGHTS = (8, 8, 8, 2, 1, 1)


def growtopia_dir():
    env = os.environ.get("GROWTOPIA_DIR")
    if env and Path(env).exists():
        return Path(env)
    local = os.environ.get("LOCALAPPDATA")
    if local and (Path(local) / "Growtopia").exists():
        return Path(local) / "Growtopia"
    return None


@lru_cache(maxsize=64)
def load_rttex(name):
    """game/<name>.rttex -> PIL RGBA (cache/game öncelikli, çünkü güncel dosyalar orada)."""
    from PIL import Image
    gdir = growtopia_dir()
    if not gdir:
        return None
    base = os.path.basename(str(name))
    for cand in (gdir / "cache" / "game" / base, gdir / "game" / base):
        if cand.exists():
            raw = cand.read_bytes()
            if raw[:6] == b"RTPACK":
                raw = zlib.decompress(raw[32:])
            if raw[:6] != b"RTTXTR":
                continue
            h, w = struct.unpack_from("<II", raw, 8)
            img = Image.frombytes("RGBA", (w, h), raw[124:124 + w * h * 4])
            return img.transpose(Image.FLIP_TOP_BOTTOM)
    return None


@lru_cache(maxsize=1)
def load_items_dat():
    """cache/items.dat -> {id: (isim, texture, texX, texY, spreadType)}

    Her item kaydında: id(u32) ... isim(u16 uzunluk + XOR'lu) texture(u16 uzunluk + ascii)
    hash(u32) visual(u8) val(u32) texX(u8) texY(u8) spreadType(u8) ...
    İsim XOR anahtarı 'PBG892FXX982ABC*' ile çözülerek kayıt doğrulanır.
    """
    gdir = growtopia_dir()
    out = {}
    if not gdir:
        return out
    p = gdir / "cache" / "items.dat"
    if not p.exists():
        p = gdir / "items.dat"
    if not p.exists():
        return out
    data = p.read_bytes()
    klen = len(ITEMS_DAT_KEY)
    for m in re.finditer(rb"[A-Za-z0-9_/]{1,64}\.rttex", data):
        ts, te = m.start(), m.end()
        if ts < 12 or te + 14 > len(data):
            continue
        if struct.unpack_from("<H", data, ts - 2)[0] != te - ts:
            continue
        for nlen in range(1, 80):
            pos = ts - 4 - nlen
            if pos < 8:
                break
            if struct.unpack_from("<H", data, pos)[0] != nlen:
                continue
            iid = struct.unpack_from("<I", data, pos - 8)[0]
            if iid in out or iid > 100000:
                break
            raw = data[pos + 2:pos + 2 + nlen]
            name = bytes(raw[i] ^ ITEMS_DAT_KEY[(i + iid) % klen] for i in range(nlen))
            if all(32 <= b < 127 for b in name):
                tx, ty, spread = struct.unpack_from("<BBB", data, te + 9)
                out[iid] = (name.decode("ascii"), m.group(0).decode("ascii"), tx, ty, spread)
            break
    return out


def item_visual(iid):
    return load_items_dat().get(int(iid))


def _smart_edge_offset(sig):
    best, best_score = (0, 0), -1
    for ofs, s in _SMART_EDGE:
        score = sum(w for a, b, w in zip(sig, s, _SE_WEIGHTS) if a == b)
        if score > best_score:
            best, best_score = ofs, score
    return best


def _sprite(iid, layer_grid, x, y, width, height):
    vis = item_visual(iid)
    if not vis:
        return None
    _, tex, tx, ty, spread = vis
    atlas = load_rttex(tex)
    if atlas is None:
        return None
    ox, oy = 0, 0
    if spread == 2:
        def same(nx, ny):
            if not (0 <= nx < width and 0 <= ny < height):
                return True  # dünya kenarı kapalı sayılır
            return layer_grid[ny][nx] == iid
        up, left, right, down = same(x, y - 1), same(x - 1, y), same(x + 1, y), same(x, y + 1)
        sig = (
            int(not up), int(not left), int(not right), int(not down),
            int(up and left and not same(x - 1, y - 1)),
            int(up and right and not same(x + 1, y - 1)),
        )
        ox, oy = _smart_edge_offset(sig)
    sx, sy = (tx + ox) * TILE, (ty + oy) * TILE
    if sx + TILE > atlas.width or sy + TILE > atlas.height:
        sx, sy = tx * TILE, ty * TILE
    return atlas.crop((sx, sy, sx + TILE, sy + TILE))


def render_world(tiles, width, height, player=None, tile_px=16):
    """tiles: [(x, y, fg, bg)] (oyundan gelen gerçek veri) -> (PIL.Image, istatistik)"""
    from PIL import Image
    fg_grid = [[0] * width for _ in range(height)]
    bg_grid = [[0] * width for _ in range(height)]
    for x, y, fg, bg in tiles:
        if 0 <= x < width and 0 <= y < height:
            fg_grid[y][x] = fg
            bg_grid[y][x] = bg

    canvas = Image.new("RGBA", (width * TILE, height * TILE))
    # Growtopia varsayılan gökyüzü (üstten alta açık maviye geçiş)
    sky = Image.new("RGBA", (1, height * TILE))
    for py in range(height * TILE):
        r = py / max(1, height * TILE - 1)
        sky.putpixel((0, py), (int(96 + 60 * r), int(178 + 40 * r), int(234 + 14 * r), 255))
    canvas.paste(sky.resize((width * TILE, height * TILE)), (0, 0))

    missing = set()
    for layer in (bg_grid, fg_grid):
        for y in range(height):
            row = layer[y]
            for x in range(width):
                iid = row[x]
                if not iid:
                    continue
                spr = _sprite(iid, layer, x, y, width, height)
                if spr is None:
                    missing.add(iid)
                    continue
                canvas.alpha_composite(spr, (x * TILE, y * TILE))

    if player and 0 <= player[0] < width and 0 <= player[1] < height:
        from PIL import ImageDraw
        d = ImageDraw.Draw(canvas)
        cx, cy = player[0] * TILE + TILE // 2, player[1] * TILE + TILE // 2
        d.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], outline=(255, 40, 40, 255), width=4)

    if tile_px != TILE:
        canvas = canvas.resize((width * tile_px, height * tile_px), Image.BOX)
    return canvas, {"missing_textures": sorted(missing)}
