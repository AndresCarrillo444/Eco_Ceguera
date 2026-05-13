import json, os, math
import pygame

# Paths 
_BASE = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE     = os.path.join(_BASE, "settings.json")
CUSTOM_LEVELS_DIR = os.path.join(_BASE, "custom_levels")
#  DEFAULT SETTINGS

DEFAULTS = {
    "sfx_volume":       0.6,
    "music_volume":     0.4,
    "high_contrast":    False,
    "show_trail":       True,
    "fullscreen":       False,
}


def settings_load():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Fill missing keys with defaults
        for k, v in DEFAULTS.items():
            data.setdefault(k, v)
        return data
    except Exception:
        return dict(DEFAULTS)


def settings_save(cfg):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


#  CUSTOM LEVEL I/O

def _ensure_dir():
    os.makedirs(CUSTOM_LEVELS_DIR, exist_ok=True)


def custom_levels_list():
    """Return sorted list of .json filenames (without extension) in custom_levels/."""
    _ensure_dir()
    return sorted(
        f[:-5] for f in os.listdir(CUSTOM_LEVELS_DIR)
        if f.endswith(".json")
    )


def custom_level_save(name, grid):
    """Save editor grid to custom_levels/<name>.json. Returns True on success."""
    _ensure_dir()
    safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip() or "nivel"
    path = os.path.join(CUSTOM_LEVELS_DIR, safe_name + ".json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"name": safe_name, "grid": grid}, f, ensure_ascii=False)
        return True
    except Exception:
        return False


def custom_level_load(name):
    """Load grid from custom_levels/<name>.json. Returns grid or None."""
    path = os.path.join(CUSTOM_LEVELS_DIR, name + ".json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("grid")
    except Exception:
        return None


def custom_level_delete(name):
    path = os.path.join(CUSTOM_LEVELS_DIR, name + ".json")
    try:
        os.remove(path)
        return True
    except Exception:
        return False

#  SETTINGS MENU DRAWING

def draw_settings_menu(surf, font, small_font, tick, cfg,
                       BLACK=(0,0,0), CYAN=(0,220,255), WHITE=(255,255,255),
                       GREEN=(60,255,120), GOLD=(255,210,0)):
    sw, sh = surf.get_size()
    cx, cy = sw // 2, sh // 2

    # dark overlay
    ov = pygame.Surface((sw, sh), pygame.SRCALPHA)
    ov.fill((0, 6, 12, 200))
    surf.blit(ov, (0, 0))

    # sonar rings
    for i in range(3):
        ph  = (tick * 0.5 + i * 120) % 360
        rad = int((ph / 360) * max(sw, sh) * 0.65)
        af  = 1.0 - ph / 360
        if rad > 0:
            pygame.draw.circle(surf, (0, int(140*af), int(180*af)), (cx, cy), rad, 1)

    # panel
    pw  = min(460, sw - 60)
    ph2 = 340
    px  = cx - pw // 2
    py  = cy - ph2 // 2

    ps = pygame.Surface((pw, ph2), pygame.SRCALPHA)
    ps.fill((0, 14, 24, 230))
    surf.blit(ps, (px, py))

    bv = int(90 + 130 * (math.sin(tick * 0.05) * 0.5 + 0.5))
    pygame.draw.rect(surf, (0, bv, min(255, bv + 70)), (px, py, pw, ph2), 2)
    csz = 10
    for qx, qy in [(px, py), (px+pw-csz, py), (px, py+ph2-csz), (px+pw-csz, py+ph2-csz)]:
        pygame.draw.rect(surf, (0, 200, 255), (qx, qy, csz, csz), 2)

    # title
    try:
        tf  = pygame.font.SysFont("consolas", 26, bold=True)
        lf  = pygame.font.SysFont("consolas", 14)
        vf  = pygame.font.SysFont("consolas", 13, bold=True)
        tip_f = pygame.font.SysFont("consolas", 11)
    except Exception:
        tf = lf = vf = tip_f = font

    gv   = int(140 + 100 * (math.sin(tick * 0.06) * 0.5 + 0.5))
    sh_t = tf.render("CONFIGURACION", True, (0, gv // 5, gv // 4))
    surf.blit(sh_t, (cx - sh_t.get_width() // 2 + 2, py + 16 + 2))
    t1   = tf.render("CONFIGURACION", True, (0, gv, min(255, gv + 60)))
    surf.blit(t1, (cx - t1.get_width() // 2, py + 16))

    pygame.draw.line(surf, (0, 60, 80), (px + 20, py + 54), (px + pw - 20, py + 54), 1)
    sep_w = int((pw - 40) * min(1.0, tick / 40))
    pygame.draw.line(surf, CYAN, (cx - sep_w//2, py + 54), (cx + sep_w//2, py + 54), 1)

    mpos   = pygame.mouse.get_pos()
    rects  = {}
    row_h  = 52
    row_x  = px + 20
    row_w  = pw - 40
    y0     = py + 66

    # SFX Volume 
    lbl = lf.render("Volumen de sonido", True, (120, 180, 200))
    surf.blit(lbl, (row_x, y0))
    vol = cfg.get("sfx_volume", 0.6)
    # bar
    bar_x, bar_y, bar_w, bar_h = row_x, y0 + 22, row_w - 64, 14
    pygame.draw.rect(surf, (0, 30, 45), (bar_x, bar_y, bar_w, bar_h))
    fill_w = int(bar_w * vol)
    if fill_w > 0:
        fill_c = (0, int(140 + 100*vol), int(80 + 120*vol))
        pygame.draw.rect(surf, fill_c, (bar_x, bar_y, fill_w, bar_h))
    pygame.draw.rect(surf, (0, 80, 110), (bar_x, bar_y, bar_w, bar_h), 1)
    val_s = vf.render(f"{int(vol*100)}%", True, WHITE)
    surf.blit(val_s, (bar_x + bar_w + 8, bar_y - 1))

    btn_sz = 22
    dn_r = pygame.Rect(row_x + row_w - 50, y0 + 16, btn_sz, btn_sz)
    up_r = pygame.Rect(row_x + row_w - 24, y0 + 16, btn_sz, btn_sz)
    for r, sym in [(dn_r, "−"), (up_r, "+")]:
        hov = r.collidepoint(mpos)
        bc  = (0, 160, 100) if hov else (0, 80, 55)
        pygame.draw.rect(surf, bc, r)
        pygame.draw.rect(surf, (0, 200, 130), r, 1)
        s = vf.render(sym, True, WHITE)
        surf.blit(s, (r.centerx - s.get_width()//2, r.centery - s.get_height()//2))
    rects["sfx_down"] = dn_r
    rects["sfx_up"]   = up_r

    #  High Contrast 
    y1 = y0 + row_h + 10
    lbl2 = lf.render("Alto contraste (sonar brillante)", True, (120, 180, 200))
    surf.blit(lbl2, (row_x, y1))
    hc = cfg.get("high_contrast", False)
    hc_r = pygame.Rect(row_x + row_w - 52, y1 - 2, 52, 26)
    hc_col = (0, 180, 90) if hc else (40, 50, 60)
    pygame.draw.rect(surf, hc_col, hc_r)
    pygame.draw.rect(surf, (0, 200, 100) if hc else (60, 70, 80), hc_r, 2)
    on_off = vf.render("ON" if hc else "OFF", True, WHITE if hc else (120,140,160))
    surf.blit(on_off, (hc_r.centerx - on_off.get_width()//2,
                        hc_r.centery - on_off.get_height()//2))
    rects["hc_toggle"] = hc_r

    #  Show Trails 
    y2 = y1 + row_h - 10
    lbl3 = lf.render("Mostrar estelas", True, (120, 180, 200))
    surf.blit(lbl3, (row_x, y2))
    tr = cfg.get("show_trail", True)
    tr_r = pygame.Rect(row_x + row_w - 52, y2 - 2, 52, 26)
    tr_col = (0, 180, 90) if tr else (40, 50, 60)
    pygame.draw.rect(surf, tr_col, tr_r)
    pygame.draw.rect(surf, (0, 200, 100) if tr else (60, 70, 80), tr_r, 2)
    on_off2 = vf.render("ON" if tr else "OFF", True, WHITE if tr else (120,140,160))
    surf.blit(on_off2, (tr_r.centerx - on_off2.get_width()//2,
                         tr_r.centery - on_off2.get_height()//2))
    rects["trail_toggle"] = tr_r

    #  Back button 
    back_r = pygame.Rect(cx - 100, py + ph2 - 56, 200, 40)
    bh     = back_r.collidepoint(mpos)
    bc2    = (0, 160, 80) if bh else (0, 80, 40)
    bs     = pygame.Surface((200, 40), pygame.SRCALPHA)
    bs.fill((*bc2, 220 if bh else 140))
    surf.blit(bs, back_r.topleft)
    pygame.draw.rect(surf, bc2, back_r, 2)
    try: bf = pygame.font.SysFont("consolas", 14, bold=True)
    except: bf = font
    bl = bf.render(">> GUARDAR Y VOLVER <<" if bh else "[ GUARDAR Y VOLVER ]", True, WHITE)
    surf.blit(bl, (cx - bl.get_width()//2, back_r.centery - bl.get_height()//2))
    rects["back"] = back_r

    tip = tip_f.render("ESC: cerrar configuracion", True, (40, 65, 80))
    surf.blit(tip, (cx - tip.get_width()//2, py + ph2 - 14))

    return rects


#  SAVE/LOAD UI for the editor  (name-entry dialog)

def draw_save_level_dialog(surf, font, small_font, tick, name_buf,
                           existing_names,
                           BLACK=(0,0,0), CYAN=(0,220,255), WHITE=(255,255,255)):
    sw, sh = surf.get_size()
    cx, cy = sw // 2, sh // 2

    ov = pygame.Surface((sw, sh), pygame.SRCALPHA)
    ov.fill((0, 6, 12, 210))
    surf.blit(ov, (0, 0))

    pw, ph2 = min(420, sw - 60), 230
    px, py  = cx - pw // 2, cy - ph2 // 2
    ps = pygame.Surface((pw, ph2), pygame.SRCALPHA)
    ps.fill((0, 16, 26, 235))
    surf.blit(ps, (px, py))
    bv = int(100 + 120 * (math.sin(tick * 0.07) * 0.5 + 0.5))
    pygame.draw.rect(surf, (0, bv, min(255, bv + 60)), (px, py, pw, ph2), 2)

    try:
        tf  = pygame.font.SysFont("consolas", 20, bold=True)
        lf  = pygame.font.SysFont("consolas", 13)
        nf  = pygame.font.SysFont("consolas", 16, bold=True)
    except Exception:
        tf = lf = nf = font

    t1 = tf.render("GUARDAR NIVEL", True, CYAN)
    surf.blit(t1, (cx - t1.get_width() // 2, py + 16))

    pr = lf.render("Nombre del nivel:", True, (120, 180, 200))
    surf.blit(pr, (cx - pr.get_width() // 2, py + 50))

    # text field
    fw, fh = pw - 60, 36
    fx, fy = cx - fw // 2, py + 74
    fs = pygame.Surface((fw, fh), pygame.SRCALPHA)
    fs.fill((0, 40, 24, 200))
    surf.blit(fs, (fx, fy))
    fb_v = int(130 + 100 * (math.sin(tick * 0.15) * 0.5 + 0.5))
    pygame.draw.rect(surf, (0, fb_v, int(fb_v * 0.5)), pygame.Rect(fx, fy, fw, fh), 2)
    cursor = "|" if (tick // 20) % 2 == 0 else " "
    ns = nf.render(name_buf + cursor, True, WHITE)
    surf.blit(ns, (fx + 8, fy + fh // 2 - ns.get_height() // 2))

    # duplicate warning
    if name_buf.strip() in existing_names:
        warn = lf.render("¡Nombre ya existe — se sobreescribirá!", True, (255, 160, 40))
        surf.blit(warn, (cx - warn.get_width() // 2, py + 118))

    mpos = pygame.mouse.get_pos()
    bw2, bh3 = 130, 36
    ok_r   = pygame.Rect(cx - bw2 - 8, py + ph2 - 52, bw2, bh3)
    canc_r = pygame.Rect(cx + 8,       py + ph2 - 52, bw2, bh3)

    for r, lbl, bc in [(ok_r, "GUARDAR", (0, 130, 65)), (canc_r, "CANCELAR", (80, 0, 0))]:
        hov = r.collidepoint(mpos) and (lbl != "GUARDAR" or name_buf.strip())
        col = tuple(min(255, int(c * 1.35)) for c in bc) if hov else bc
        bs2 = pygame.Surface((bw2, bh3), pygame.SRCALPHA)
        bs2.fill((*col, 220 if hov else 140))
        surf.blit(bs2, r.topleft)
        pygame.draw.rect(surf, col, r, 2)
        try: bf2 = pygame.font.SysFont("consolas", 13, bold=True)
        except: bf2 = font
        bl2 = bf2.render(lbl, True, WHITE if (lbl == "GUARDAR" and name_buf.strip()) or lbl == "CANCELAR" else (80,90,85))
        surf.blit(bl2, (r.centerx - bl2.get_width()//2, r.centery - bl2.get_height()//2))

    return ok_r, canc_r
