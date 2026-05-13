
import json, os, math, random
import pygame
try:
    from eco_online_lb import ol_get, ol_status, ol_is_ready, ol_is_configured
except Exception:
    def ol_get(i):          return []
    def ol_status():        return "unconfigured"
    def ol_is_ready():      return False
    def ol_is_configured(): return False

#  PAUSE MENU

def draw_pause_menu(surf, font, small_font, tick, from_editor=False,
                    BLACK=(0,0,0), CYAN=(0,220,255), WHITE=(255,255,255)):
    sw, sh = surf.get_size()
    cx, cy = sw // 2, sh // 2

    # dark backdrop
    ov = pygame.Surface((sw, sh), pygame.SRCALPHA)
    ov.fill((0, 8, 14, 190))
    surf.blit(ov, (0, 0))

    # slow sonar rings
    for i in range(3):
        ph  = (tick * 0.6 + i * 120) % 360
        rad = int((ph / 360) * max(sw, sh) * 0.7)
        af  = 1.0 - ph / 360
        if rad > 0:
            pygame.draw.circle(surf, (0, int(160*af), int(200*af)), (cx, cy), rad, 1)

    # panel
    n_btns = 3 if from_editor else 2
    pw  = min(400, sw - 60)
    ph2 = 100 + n_btns * 58
    px  = cx - pw // 2
    py  = cy - ph2 // 2

    ps = pygame.Surface((pw, ph2), pygame.SRCALPHA)
    ps.fill((0, 16, 26, 225))
    surf.blit(ps, (px, py))

    bv = int(100 + 120 * (math.sin(tick * 0.05) * 0.5 + 0.5))
    pygame.draw.rect(surf, (0, bv, min(255, bv + 60)), (px, py, pw, ph2), 2)
    csz = 10
    for qx, qy in [(px, py), (px+pw-csz, py), (px, py+ph2-csz), (px+pw-csz, py+ph2-csz)]:
        pygame.draw.rect(surf, (0, 200, 255), (qx, qy, csz, csz), 2)

    # title
    try:
        tf    = pygame.font.SysFont("consolas", 30, bold=True)
        bf    = pygame.font.SysFont("consolas", 16, bold=True)
        tip_f = pygame.font.SysFont("consolas", 11)
    except Exception:
        tf = bf = tip_f = font

    gv   = int(150 + 90 * (math.sin(tick * 0.06) * 0.5 + 0.5))
    sh_t = tf.render("PAUSA", True, (0, gv // 5, gv // 4))
    surf.blit(sh_t, (cx - sh_t.get_width() // 2 + 2, py + 18 + 2))
    t1   = tf.render("PAUSA", True, (0, gv, min(255, gv + 60)))
    surf.blit(t1, (cx - t1.get_width() // 2, py + 18))

    # separator
    pygame.draw.line(surf, (0, 60, 80), (px + 20, py + 62), (px + pw - 20, py + 62), 1)
    sep_w = int((pw - 40) * min(1.0, tick / 40))
    pygame.draw.line(surf, CYAN, (cx - sep_w//2, py + 62), (cx + sep_w//2, py + 62), 1)

    # buttons
    bw, bh, bgap = pw - 60, 44, 10
    bx           = cx - bw // 2
    mpos         = pygame.mouse.get_pos()
    rects        = {}

    btn_defs = [("resume", "REANUDAR",       (0, 140, 70)),
                ("menu",   "MENU PRINCIPAL",  (60, 60, 80))]
    if from_editor:
        btn_defs.insert(1, ("editor", "VOLVER AL EDITOR", (0, 80, 140)))

    for idx, (key, label, bc) in enumerate(btn_defs):
        by   = py + 76 + idx * (bh + bgap)
        rect = pygame.Rect(bx, by, bw, bh)
        rects[key] = rect
        hov  = rect.collidepoint(mpos)
        fc   = tuple(min(255, int(c * (1.35 if hov else 1.0))) for c in bc)
        bs   = pygame.Surface((bw, bh), pygame.SRCALPHA)
        bs.fill((*fc, 220 if hov else 140))
        surf.blit(bs, rect.topleft)
        pygame.draw.rect(surf, fc, rect, 2)
        if hov:
            pygame.draw.line(surf, fc, (bx + 4, by + 6), (bx + 4, by + bh - 6), 2)
        lbl_s = bf.render(">  " + label if hov else label, True,
                          WHITE if hov else (160, 200, 220))
        surf.blit(lbl_s, (cx - lbl_s.get_width() // 2,
                           by + bh // 2 - lbl_s.get_height() // 2))

    tip = tip_f.render("ESC: reanudar", True, (40, 65, 80))
    surf.blit(tip, (cx - tip.get_width() // 2, py + ph2 - 16))

    return rects

#  LEADERBOARD

LEADERBOARD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leaderboard.json")

def lb_load():
    try:
        with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def lb_save(data):
    try:
        with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def lb_submit(level_idx, name, elapsed_ticks, score):
    """Register a run. Returns True if it's a new record (faster time)."""
    data  = lb_load()
    key   = str(level_idx)
    entry = {"name": (name or "---")[:16], "ticks": elapsed_ticks, "score": score}
    if key not in data or elapsed_ticks < data[key]["ticks"]:
        data[key] = entry
        lb_save(data)
        return True
    return False


def lb_is_record(level_idx, elapsed_ticks):
    data = lb_load()
    key  = str(level_idx)
    return key not in data or elapsed_ticks < data[key]["ticks"]


def draw_name_input(surf, font, small_font, tick, name_buf, level_idx, score,
                    elapsed_ticks, LEVEL_CONFIGS, TILE, BLACK, CYAN, GOLD, GREEN, WHITE):
    sw, sh = surf.get_size()
    cx, cy = sw // 2, sh // 2

    # semi-transparent backdrop
    ov = pygame.Surface((sw, sh), pygame.SRCALPHA)
    ov.fill((0, 10, 6, 200))
    surf.blit(ov, (0, 0))

    # animated victory rings (gold)
    for i in range(5):
        ph  = (tick * 1.4 + i * 72) % 360
        rad = int((ph / 360) * max(sw, sh) * 0.7)
        af  = 1.0 - ph / 360
        if rad > 0:
            pygame.draw.circle(surf, (int(255*af), int(180*af), 0), (cx, cy), rad, 1)

    # glass panel
    pw, ph2 = min(520, sw - 60), 310
    px, py  = cx - pw // 2, cy - ph2 // 2
    ps = pygame.Surface((pw, ph2), pygame.SRCALPHA)
    ps.fill((0, 28, 14, 220))
    surf.blit(ps, (px, py))

    bv = int(130 + 110 * (math.sin(tick * 0.07) * 0.5 + 0.5))
    pygame.draw.rect(surf, (0, bv, int(bv * 0.45)), (px, py, pw, ph2), 2)
    csz = 12
    for qx, qy in [(px, py), (px+pw-csz, py), (px, py+ph2-csz), (px+pw-csz, py+ph2-csz)]:
        pygame.draw.rect(surf, (0, 220, 100), (qx, qy, csz, csz), 2)

    # title
    try:
        tf  = pygame.font.SysFont("consolas", 36, bold=True)
        sf2 = pygame.font.SysFont("consolas", 14)
        ff  = pygame.font.SysFont("consolas", 20, bold=True)
        lf2 = pygame.font.SysFont("consolas", 13)
    except Exception:
        tf = ff = sf2 = lf2 = font

    gv2   = int(180 + 70 * (math.sin(tick * 0.09) * 0.5 + 0.5))
    # shadow
    sh_t  = tf.render("¡NUEVO RÉCORD!", True, (0, gv2 // 5, 0))
    surf.blit(sh_t, (cx - sh_t.get_width() // 2 + 3, py + 20 + 3))
    t1    = tf.render("¡NUEVO RÉCORD!", True, (0, gv2, int(gv2 * 0.45)))
    surf.blit(t1, (cx - t1.get_width() // 2, py + 20))

    # level name
    cfg_name = LEVEL_CONFIGS[level_idx]['name'] if level_idx < len(LEVEL_CONFIGS) else ""
    lv_s = sf2.render(f"Nivel {level_idx + 1}  —  {cfg_name}", True, (100, 200, 140))
    surf.blit(lv_s, (cx - lv_s.get_width() // 2, py + 70))

    # time + score
    secs = elapsed_ticks // 60
    ms   = (elapsed_ticks % 60) * 100 // 60
    ti_s = sf2.render(f"Tiempo:  {secs:02d}:{ms:02d}   |   Puntos: {score:,}", True, GREEN)
    surf.blit(ti_s, (cx - ti_s.get_width() // 2, py + 92))

    # separator
    pygame.draw.line(surf, (0, 80, 40), (px + 24, py + 116), (px + pw - 24, py + 116), 1)
    sep_w = int((pw - 48) * min(1.0, tick / 60))
    pygame.draw.line(surf, GREEN, (cx - sep_w // 2, py + 116), (cx + sep_w // 2, py + 116), 1)

    # prompt
    pr_s = lf2.render("Ingresa tu nombre:", True, (130, 200, 160))
    surf.blit(pr_s, (cx - pr_s.get_width() // 2, py + 130))

    # text field
    field_w, field_h = min(340, pw - 60), 40
    field_x = cx - field_w // 2
    field_y = py + 155
    field_s = pygame.Surface((field_w, field_h), pygame.SRCALPHA)
    field_s.fill((0, 50, 28, 200))
    surf.blit(field_s, (field_x, field_y))

    # blinking border
    fb_v = int(140 + 100 * (math.sin(tick * 0.15) * 0.5 + 0.5))
    pygame.draw.rect(surf, (0, fb_v, int(fb_v * 0.5)),
                     pygame.Rect(field_x, field_y, field_w, field_h), 2)

    # typed text + cursor
    cursor = "|" if (tick // 20) % 2 == 0 else " "
    display_name = name_buf + cursor
    try:
        nf = pygame.font.SysFont("consolas", 18, bold=True)
    except Exception:
        nf = ff
    ns = nf.render(display_name, True, WHITE)
    surf.blit(ns, (field_x + 10, field_y + field_h // 2 - ns.get_height() // 2))

    # char count hint
    cc_s = lf2.render(f"{len(name_buf)}/16", True, (70, 110, 90))
    surf.blit(cc_s, (field_x + field_w - cc_s.get_width() - 6,
                     field_y + field_h + 4))

    # confirm button
    confirm_rect = pygame.Rect(cx - 120, py + ph2 - 62, 240, 42)
    mpos = pygame.mouse.get_pos()
    mh   = confirm_rect.collidepoint(mpos) and len(name_buf) > 0
    pulse = math.sin(tick * 0.1) * 0.5 + 0.5
    cc   = (0, int(180 + 60 * pulse), int(80 + 30 * pulse)) if mh else \
           (0, 100, 50) if len(name_buf) > 0 else (30, 40, 35)
    cs2  = pygame.Surface((240, 42), pygame.SRCALPHA)
    cs2.fill((*cc, 220 if mh else 150))
    surf.blit(cs2, confirm_rect.topleft)
    pygame.draw.rect(surf, cc, confirm_rect, 2)
    lbl  = ">> GUARDAR RÉCORD <<" if mh else "[ GUARDAR RÉCORD ]"
    bl   = ff.render(lbl, True, WHITE if len(name_buf) > 0 else (60, 70, 65))
    surf.blit(bl, (cx - bl.get_width() // 2,
                   confirm_rect.y + confirm_rect.h // 2 - bl.get_height() // 2))

    # tip
    try: tip_f = pygame.font.SysFont("consolas", 11)
    except: tip_f = small_font
    tip = tip_f.render("Enter: guardar  |  Backspace: borrar  |  ESC: saltar", True, (50, 80, 60))
    surf.blit(tip, (cx - tip.get_width() // 2, py + ph2 - 16))

    return confirm_rect



def draw_leaderboard(surf, font, small_font, tick, LEVEL_CONFIGS, TILE,
                     BLACK, CYAN, GOLD, GREEN, DARK_CYAN,
                     lb_tab="local"):
    sw, sh = surf.get_size()
    cx = sw // 2
    surf.fill(BLACK)

    # Animated rings background
    for i in range(3):
        ph  = (tick * 1.2 + i * 120) % 360
        rad = int((ph / 360) * max(sw, sh) * 0.8)
        af  = 1.0 - ph / 360
        if rad > 0:
            pygame.draw.circle(surf, (int(200*af), int(160*af), 0), (cx, sh//2), rad, 1)
    for gx in range(0, sw, TILE): pygame.draw.line(surf, (10, 10, 4), (gx, 0), (gx, sh))
    for gy in range(0, sh, TILE): pygame.draw.line(surf, (10, 10, 4), (0, gy), (sw, gy))

    try:
        tf  = pygame.font.SysFont("consolas", 28, bold=True)
        rf  = pygame.font.SysFont("consolas", 14)
        hf  = pygame.font.SysFont("consolas", 12, bold=True)
        tf2 = pygame.font.SysFont("consolas", 15, bold=True)
        sf3 = pygame.font.SysFont("consolas", 11)
    except Exception:
        tf = rf = hf = tf2 = sf3 = font

    gv    = int(160 + 80 * (math.sin(tick * 0.05) * 0.5 + 0.5))
    title = tf.render("TABLA DE CLASIFICACION", True, (gv, int(gv*0.8), 0))
    surf.blit(title, (cx - title.get_width()//2, 14))

    #  Tab bar 
    tab_y  = 54
    tab_w  = 140
    tab_h  = 30
    mpos   = pygame.mouse.get_pos()

    local_r  = pygame.Rect(cx - tab_w - 4, tab_y, tab_w, tab_h)
    global_r = pygame.Rect(cx + 4,          tab_y, tab_w, tab_h)

    for r, label, is_active, color in [
        (local_r,  "LOCAL",   lb_tab == "local",  (0, 120, 60)),
        (global_r, "GLOBAL",  lb_tab == "global", (0, 60, 140)),
    ]:
        hov = r.collidepoint(mpos)
        bg  = (*color, 230) if is_active else (*(c//2 for c in color), 140)
        bs  = pygame.Surface((tab_w, tab_h), pygame.SRCALPHA)
        bs.fill(bg)
        surf.blit(bs, r.topleft)
        border = tuple(min(255, c + 60) for c in color) if is_active else color
        pygame.draw.rect(surf, border, r, 2)
        ls = tf2.render(label, True, (255,255,255) if is_active else (140,170,190))
        surf.blit(ls, (r.centerx - ls.get_width()//2, r.centery - ls.get_height()//2))

    #  online status badge 
    status = ol_status()
    st_colors = {
        "online":       (0, 200, 100),
        "syncing":      (200, 160, 0),
        "error":        (200, 60, 60),
        "unconfigured": (80, 90, 100),
    }
    st_col = st_colors.get(status, (80, 90, 100))
    st_lbl = {"online": "EN LINEA", "syncing": "SINCRONIZANDO...",
              "error": "SIN CONEXION", "unconfigured": "NO CONFIGURADO"}.get(status, status)
    dot_x = sw - 14
    dot_y = tab_y + tab_h//2
    pygame.draw.circle(surf, st_col, (dot_x, dot_y), 6)
    st_s = sf3.render(st_lbl, True, st_col)
    surf.blit(st_s, (dot_x - st_s.get_width() - 10, dot_y - st_s.get_height()//2))

    #  Table content 
    cw       = min(720, sw - 60)
    cx0      = cx - cw // 2
    y0       = tab_y + tab_h + 12
    ch2, gap = 56, 5

    # Header
    hs = pygame.Surface((cw, 24), pygame.SRCALPHA)
    hs.fill((0, 40, 20, 180))
    surf.blit(hs, (cx0, y0))
    cols_local  = [("NIVEL", 8),  ("NOMBRE", 150), ("TIEMPO", 360), ("PUNTOS", 500)]
    cols_global = [("#",     8),  ("NOMBRE", 60),  ("TIEMPO", 280), ("PUNTOS", 400),
                   ("NIVEL", 530)]
    header_cols = cols_local if lb_tab == "local" else cols_global
    for htxt, xoff in header_cols:
        surf.blit(hf.render(htxt, True, GOLD), (cx0 + xoff, y0 + 4))
    y0 += 28

    if lb_tab == "local":
        #  LOCAL tab: one row per level 
        data = lb_load()
        for i, cfg in enumerate(LEVEL_CONFIGS):
            key   = str(i)
            entry = data.get(key)
            cy2   = y0 + i * (ch2 + gap)
            cs    = pygame.Surface((cw, ch2), pygame.SRCALPHA)
            cs.fill((0, 30, 12, 160) if entry else (10, 10, 8, 100))
            surf.blit(cs, (cx0, cy2))
            pygame.draw.rect(surf, (0, 80, 40) if entry else (30, 30, 20),
                             pygame.Rect(cx0, cy2, cw, ch2), 1)
            surf.blit(rf.render(f"{i+1}. {cfg['name']}",
                                True, CYAN if entry else (60, 80, 70)),
                      (cx0+8, cy2+6))
            surf.blit(rf.render(cfg['subtitle'], True, (60, 100, 80)), (cx0+8, cy2+26))
            if entry:
                secs = entry['ticks'] // 60
                ms   = (entry['ticks'] % 60) * 100 // 60
                surf.blit(rf.render(entry['name'],        True, (255,255,255)), (cx0+150, cy2+18))
                surf.blit(rf.render(f"{secs:02d}:{ms:02d}", True, GREEN),      (cx0+360, cy2+18))
                surf.blit(rf.render(f"{entry['score']:,}", True, GOLD),        (cx0+500, cy2+18))
            else:
                surf.blit(rf.render("— sin registro —", True, (40,55,48)), (cx0+150, cy2+18))

    else:
        #  GLOBAL tab: top-10 across all levels merged 
        if not ol_is_configured():
            # Not configured — show setup instructions
            msg_lines = [
                "El leaderboard global no esta configurado.",
                "",
                "Para activarlo:",
                "  1. Crea un proyecto en firebase.google.com",
                "  2. Build → Realtime Database → Create Database",
                "  3.  'Start in test mode'",
                "  4. Copia la URL del proyecto",
                "  5. Pegala en eco_online_lb.py  (FIREBASE_URL = \"...\")  ",
                "",
                "Es gratis (1 GB, 10 GB/mes).",
            ]
            for li, line in enumerate(msg_lines):
                col = CYAN if li in (0,2) else (120, 180, 200)
                ls  = rf.render(line, True, col)
                surf.blit(ls, (cx0 + 20, y0 + li * 22))
        else:
            # Aggregate all level caches into one sorted list
            all_entries = []
            for i, cfg in enumerate(LEVEL_CONFIGS):
                for e in ol_get(i):
                    all_entries.append({**e, "level_idx": i, "level_name": cfg["name"]})
            all_entries.sort(key=lambda e: e.get("ticks", 9_999_999))
            top = all_entries[:10]

            if not top:
                wait_s = sf3.render(
                    "Cargando datos globales..." if ol_status() == "syncing"
                    else "No hay registros globales aun. ¡Se el primero!",
                    True, (120, 160, 180))
                surf.blit(wait_s, (cx - wait_s.get_width()//2, y0 + 40))
            else:
                for rank, e in enumerate(top):
                    cy2  = y0 + rank * (ch2 + gap)
                    gold_bg = rank == 0
                    cs   = pygame.Surface((cw, ch2), pygame.SRCALPHA)
                    cs.fill((30, 20, 0, 200) if gold_bg else (0, 20, 40, 160))
                    surf.blit(cs, (cx0, cy2))
                    border = GOLD if gold_bg else (0, 60, 120)
                    pygame.draw.rect(surf, border, pygame.Rect(cx0, cy2, cw, ch2), 2 if gold_bg else 1)

                    rank_col = GOLD if rank == 0 else (200, 200, 200) if rank == 1 else \
                               (180, 120, 60) if rank == 2 else (120, 140, 160)
                    surf.blit(rf.render(f"#{rank+1}", True, rank_col),  (cx0+8,  cy2+18))
                    surf.blit(rf.render(e["name"][:16], True, (255,255,255)), (cx0+60, cy2+18))
                    secs = e["ticks"] // 60
                    ms   = (e["ticks"] % 60) * 100 // 60
                    surf.blit(rf.render(f"{secs:02d}:{ms:02d}", True, GREEN), (cx0+280, cy2+18))
                    surf.blit(rf.render(f"{e.get('score',0):,}", True, GOLD), (cx0+400, cy2+18))
                    surf.blit(rf.render(e["level_name"], True, CYAN),         (cx0+530, cy2+18))

    # Back button
    back_rect = pygame.Rect(cx - 100, sh - 48, 200, 36)
    bh2  = back_rect.collidepoint(mpos)
    bc   = (0, 160, 80) if bh2 else (0, 80, 40)
    bs2  = pygame.Surface((200, 36), pygame.SRCALPHA)
    bs2.fill((*bc, 210 if bh2 else 140))
    surf.blit(bs2, back_rect.topleft)
    pygame.draw.rect(surf, bc, back_rect, 2)
    try: bbf = pygame.font.SysFont("consolas", 14, bold=True)
    except: bbf = font
    bl = bbf.render(">> VOLVER <<" if bh2 else "[ VOLVER ]", True, (255,255,255))
    surf.blit(bl, (cx - bl.get_width()//2, back_rect.centery - bl.get_height()//2))

    return back_rect, local_r, global_r


#  CO-OP LOCAL  —  Player 2

class Player2:
    COLOR = (255, 120, 0)
    PLAYER_RADIUS = 8
    PLAYER_SPEED  = 3
    SNEAK_SPEED   = 1.5

    def __init__(self, x, y):
        self.x      = x
        self.y      = y
        self.caught = False
        self.won    = False
        self.trail  = []

    # movement
    def move(self, dx, dy, walls, sneaking=False):
        import math as _m
        spd = self.SNEAK_SPEED if sneaking else self.PLAYER_SPEED
        self.trail.append((self.x, self.y))
        if len(self.trail) > 12:
            self.trail.pop(0)
        for axis in [(dx * spd, 0), (0, dy * spd)]:
            nx = self.x + axis[0]
            ny = self.y + axis[1]
            r  = self.PLAYER_RADIUS
            prect = pygame.Rect(nx - r, ny - r, r * 2, r * 2)
            if not any(prect.colliderect(w.rect) for w in walls):
                self.x, self.y = nx, ny

    def handle_keys(self, keys, walls):
        """Call once per frame. Returns (moved: bool, sneaking: bool)."""
        sneaking = keys[pygame.K_RSHIFT]
        dx = int(keys[pygame.K_RIGHT]) - int(keys[pygame.K_LEFT])
        dy = int(keys[pygame.K_DOWN])  - int(keys[pygame.K_UP])
        moved = False
        if dx or dy:
            d = math.hypot(dx, dy)
            self.move(dx / d, dy / d, walls, sneaking)
            moved = True
        return moved, sneaking

    # drawing
    def draw(self, surf, offset):
        BLACK = (0, 0, 0)
        for i, (tx, ty) in enumerate(self.trail):
            a   = (i + 1) / len(self.trail) if self.trail else 1
            r2  = max(1, int(self.PLAYER_RADIUS * a * 0.5))
            col = tuple(int(BLACK[k] + (self.COLOR[k] - BLACK[k]) * a * 0.5) for k in range(3))
            pygame.draw.circle(surf, col,
                               (int(tx - offset[0]), int(ty - offset[1])), r2)
        cx2 = int(self.x - offset[0])
        cy2 = int(self.y - offset[1])
        pygame.draw.circle(surf, self.COLOR, (cx2, cy2), self.PLAYER_RADIUS)
        pygame.draw.circle(surf, (255, 255, 255), (cx2, cy2), self.PLAYER_RADIUS, 1)
        try:
            lf = pygame.font.SysFont("consolas", 9, bold=True)
            ls = lf.render("2", True, (0, 0, 0))
            surf.blit(ls, (cx2 - ls.get_width() // 2, cy2 - ls.get_height() // 2))
        except Exception:
            pass


#  EDITOR DE NIVELES

EDITOR_PALETTE = [
    ("W", "Muro",    (60,  90, 110)),
    (".", "Pasillo", (20,  30,  38)),
    ("S", "Inicio",  (60, 255, 120)),
    ("E", "Salida",  (255,210,   0)),
    ("N", "Enemigo", (255, 60,  60)),
    ("B", "Murciél", (200, 30,  30)),
    ("T", "Trampa",  (180,140,   0)),
    ("X", "Borrar",  (10,  10,  10)),
]


def empty_editor_grid(COLS, ROWS):
    grid = [["#"] * COLS for _ in range(ROWS)]
    for r in range(1, ROWS - 1):
        for c in range(1, COLS - 1):
            grid[r][c] = "."
    grid[1][1]           = "S"
    grid[ROWS-2][COLS-2] = "E"
    return grid


def build_map_from_editor(grid, COLS, ROWS, TILE, Wall, BatEnemy, Enemy, SoundTrap, ExitTile,
                           MAT_NORMAL):
    """Convert editor grid → game objects. Returns same tuple as build_map."""
    walls, enemies, traps = [], [], []
    player_pos  = (TILE + TILE // 2, TILE + TILE // 2)
    exit_rect   = None
    floor_cells = []

    for row_i, row in enumerate(grid):
        for col_i, ch in enumerate(row):
            rx, ry = col_i * TILE, row_i * TILE
            if ch in ("#", "W"):
                walls.append(Wall(pygame.Rect(rx, ry, TILE, TILE), MAT_NORMAL))

            elif ch == "S":
                player_pos = (rx + TILE // 2, ry + TILE // 2)
                floor_cells.append((col_i, row_i))
            elif ch == "E":
                exit_rect = ExitTile(pygame.Rect(rx + 4, ry + 4, TILE - 8, TILE - 8))
                floor_cells.append((col_i, row_i))
            elif ch == ".":
                floor_cells.append((col_i, row_i))
            elif ch == "N":
                enemies.append(Enemy(rx + TILE // 2, ry + TILE // 2))
                floor_cells.append((col_i, row_i))
            elif ch == "B":
                enemies.append(BatEnemy(rx + TILE // 2, ry + TILE // 2))
                floor_cells.append((col_i, row_i))
            elif ch == "T":
                traps.append(SoundTrap(rx + TILE // 2, ry + TILE // 2))
                floor_cells.append((col_i, row_i))

    # Build A* wall grid
    wall_grid = [[False] * COLS for _ in range(ROWS)]
    for w in walls:
        gc = w.rect.x // TILE
        gr = w.rect.y // TILE
        if 0 <= gr < ROWS and 0 <= gc < COLS:
            wall_grid[gr][gc] = True

    # Fallback exit
    if exit_rect is None and floor_cells:
        ci, ri = floor_cells[-1]
        exit_rect = ExitTile(pygame.Rect(ci * TILE + 4, ri * TILE + 4, TILE - 8, TILE - 8))

    return walls, enemies, player_pos, exit_rect, traps, wall_grid


def draw_editor(surf, font, small_font, grid, sel_tile, tick, mouse_cell,
                TILE, COLS, ROWS, WHITE, CYAN, DARK_CYAN):
    sw, sh = surf.get_size()
    BLACK  = (0, 0, 0)
    surf.fill((5, 8, 12))

    #  Draw grid 
    for row_i, row in enumerate(grid):
        for col_i, ch in enumerate(row):
            rx = col_i * TILE
            ry = row_i * TILE + 38
            col = (10, 20, 28)
            for sym, _, c in EDITOR_PALETTE:
                if ch == sym:
                    col = c
                    break
            pygame.draw.rect(surf, col,         (rx, ry, TILE, TILE))
            pygame.draw.rect(surf, (20, 35, 45),(rx, ry, TILE, TILE), 1)
            if ch not in (".", "#"):
                try:
                    lf = pygame.font.SysFont("consolas", 10, bold=True)
                except Exception:
                    lf = small_font
                ls = lf.render(ch, True, WHITE)
                surf.blit(ls, (rx + TILE // 2 - ls.get_width() // 2,
                               ry + TILE // 2 - ls.get_height() // 2))

    # Hover highlight
    if mouse_cell:
        mc_r, mc_c = mouse_cell
        hs = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        hs.fill((0, 200, 255, 60))
        surf.blit(hs, (mc_c * TILE, mc_r * TILE + 38))

    # Top bar
    pygame.draw.rect(surf, (10, 18, 28), (0, 0, sw, 38))
    pygame.draw.line(surf, DARK_CYAN, (0, 38), (sw, 38))
    try:
        hf2 = pygame.font.SysFont("consolas", 14, bold=True)
    except Exception:
        hf2 = font
    surf.blit(hf2.render("EDITOR DE NIVELES", True, CYAN), (8, 10))

    # Palette sidebar
    pal_x0 = COLS * TILE + 6
    if pal_x0 + 82 > sw:
        pal_x0 = sw - 84
    try:
        pf = pygame.font.SysFont("consolas", 11, bold=True)
    except Exception:
        pf = small_font
    for i, (sym, label, col) in enumerate(EDITOR_PALETTE):
        pr  = pygame.Rect(pal_x0, 42 + i * 36, 80, 30)
        sel = (i == sel_tile)
        bg  = pygame.Surface((80, 30), pygame.SRCALPHA)
        bg.fill((*col, 220) if sel else (*col, 100))
        surf.blit(bg, pr.topleft)
        pygame.draw.rect(surf, (0, 200, 255) if sel else (40, 60, 70), pr, 2 if sel else 1)
        surf.blit(pf.render(f"{i+1}:{sym} {label}", True, WHITE), (pal_x0 + 3, 42 + i * 36 + 9))

    # Action buttons
    bw, bh2, bgap = 90, 28, 6
    btn_y  = sh - 36
    mpos   = pygame.mouse.get_pos()
    play_rect  = pygame.Rect(sw - (bw + bgap) * 4, btn_y, bw, bh2)
    save_rect  = pygame.Rect(sw - (bw + bgap) * 3, btn_y, bw, bh2)
    clear_rect = pygame.Rect(sw - (bw + bgap) * 2, btn_y, bw, bh2)
    back_rect  = pygame.Rect(sw - (bw + bgap) * 1, btn_y, bw, bh2)

    for rect, label, bc in [(play_rect,  "JUGAR",   (0, 140, 70)),
                             (save_rect,  "GUARDAR", (0, 80, 140)),
                             (clear_rect, "LIMPIAR", (80, 80, 0)),
                             (back_rect,  "VOLVER",  (80, 0, 0))]:
        hov = rect.collidepoint(mpos)
        bs  = pygame.Surface((bw, bh2), pygame.SRCALPHA)
        bs.fill((*bc, 210 if hov else 140))
        surf.blit(bs, rect.topleft)
        pygame.draw.rect(surf, bc, rect, 2)
        try:
            bf = pygame.font.SysFont("consolas", 12, bold=True)
        except Exception:
            bf = font
        bl = bf.render(label, True, WHITE)
        surf.blit(bl, (rect.centerx - bl.get_width() // 2,
                       rect.centery - bl.get_height() // 2))

    # Tip
    try:
        tf2 = pygame.font.SysFont("consolas", 11)
    except Exception:
        tf2 = small_font
    surf.blit(tf2.render(
        "Clic: pintar  |  Rueda ratón: cambiar tile  |  1-8: palette", True, (50, 80, 90)),
        (8, sh - 18))

    return play_rect, clear_rect, back_rect, save_rect

