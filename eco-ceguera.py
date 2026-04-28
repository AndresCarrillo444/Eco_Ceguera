class ExitTile:
    def __init__(self, rect):
        self.rect     = rect
        self.revealed = 0

import pygame
import math
import random
import sys

# ── Configuración ────────────────────────────────────────────────────────────
W, H          = 900, 700
FPS           = 60
TILE          = 40

# Colores base
BLACK         = (0, 0, 0)
WHITE         = (255, 255, 255)
CYAN          = (0, 220, 255)
RED           = (255, 60, 60)
ORANGE        = (255, 160, 40)
GOLD          = (255, 210, 0)
GREEN         = (60, 255, 120)
PURPLE        = (180, 60, 255)
DARK_CYAN     = (0, 80, 100)

# Gameplay
PLAYER_SPEED      = 3
PLAYER_RADIUS     = 8
ENEMY_RADIUS      = 10
SONAR_SPEED       = 4
SONAR_MAX_RADIUS  = 320
SONAR_THICKNESS   = 1
REVEAL_DURATION   = 90       # frames que un objeto queda visible tras el eco
ENEMY_SPEED_BASE  = 0.9
ENEMY_ALERT_SPEED = 2.2
ENEMY_ALERT_TIME  = 180      # frames en alerta antes de volver a patrullar
DECOY_COUNT       = 3        # señuelos por partida

# ── Mapa (0=pared, 1=corredor, 2=inicio, 3=salida) ──────────────────────────
RAW_MAP = [
    "####################",
    "#S.......#....#....#",
    "#.###.##.#.##.#.##.#",
    "#.#.....#....#....##",
    "#.#.###.######.##..#",
    "#...#.....#....#...#",
    "###.#.###.#.##.#.###",
    "#...#...#.#..#.....#",
    "#.#####.#.##.#####.#",
    "#.#.....#....#.....#",
    "#.#.###.######.####",
    "#.....#..........E##",
    "####################",
]

COLS = len(RAW_MAP[0])
ROWS = len(RAW_MAP)
MAP_W = COLS * TILE
MAP_H = ROWS * TILE

# ── Utilidades ───────────────────────────────────────────────────────────────

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def normalize(dx, dy):
    d = math.hypot(dx, dy)
    if d == 0:
        return 0, 0
    return dx / d, dy / d

def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

# ── Clases ───────────────────────────────────────────────────────────────────

class Wall:
    def __init__(self, rect):
        self.rect     = rect
        self.reveal   = 0    # frames restantes de visibilidad
        self.corners  = [rect.topleft, rect.topright, rect.bottomright, rect.bottomleft]

    def update(self):
        if self.reveal > 0:
            self.reveal -= 1

    def draw(self, surf, offset):
        if self.reveal <= 0:
            return
        alpha = min(1.0, self.reveal / 30)
        color = lerp_color((0, 30, 40), DARK_CYAN, alpha)
        r = pygame.Rect(self.rect.x - offset[0], self.rect.y - offset[1],
                        self.rect.w, self.rect.h)
        pygame.draw.rect(surf, color, r)
        pygame.draw.rect(surf, lerp_color(BLACK, CYAN, alpha * 0.6), r, 1)


class SonarPulse:
    def __init__(self, x, y, color=CYAN, is_decoy=False):
        self.x        = x
        self.y        = y
        self.radius   = 0
        self.color    = color
        self.dead     = False
        self.is_decoy = is_decoy
        self.revealed = set()    # ids de objetos ya revelados

    def update(self, walls, enemies, exit_rect, player):
        self.radius += SONAR_SPEED
        if self.radius > SONAR_MAX_RADIUS:
            self.dead = True
            return

        # Revelar paredes tocadas por el frente de onda
        for w in walls:
            if id(w) in self.revealed:
                continue
            cx = max(w.rect.left, min(self.x, w.rect.right))
            cy = max(w.rect.top,  min(self.y, w.rect.bottom))
            if abs(dist((self.x, self.y), (cx, cy)) - self.radius) < SONAR_SPEED + 2:
                w.reveal = REVEAL_DURATION
                self.revealed.add(id(w))

        # Revelar enemigos
        for e in enemies:
            if id(e) in self.revealed:
                continue
            d = dist((self.x, self.y), (e.x, e.y))
            if abs(d - self.radius) < SONAR_SPEED + 4:
                e.reveal = REVEAL_DURATION
                self.revealed.add(id(e))
                # Alertar al enemigo si el sonar viene del jugador
                if not self.is_decoy:
                    e.alert(player.x, player.y)

        # Revelar salida
        if exit_rect:
            cx = max(exit_rect.rect.left, min(self.x, exit_rect.rect.right))
            cy = max(exit_rect.rect.top,  min(self.y, exit_rect.rect.bottom))
            if abs(dist((self.x, self.y), (cx, cy)) - self.radius) < SONAR_SPEED + 2:
                exit_rect.revealed = REVEAL_DURATION


    def draw(self, surf, offset):
        if self.dead:
            return
        alpha_f = 1.0 - (self.radius / SONAR_MAX_RADIUS)
        color = lerp_color(BLACK, self.color, alpha_f * 0.9)
        cx = int(self.x - offset[0])
        cy = int(self.y - offset[1])
        if 0 < self.radius:
            pygame.draw.circle(surf, color, (cx, cy), int(self.radius), SONAR_THICKNESS)


class Enemy:
    def __init__(self, x, y):
        self.x        = x
        self.y        = y
        self.reveal   = 0
        self.alert_t  = 0
        self.target_x = x
        self.target_y = y
        self.patrol_timer = 0
        self.speed    = ENEMY_SPEED_BASE
        self.dead     = False
        self._pick_patrol()

    def _pick_patrol(self):
        angle = random.uniform(0, 2 * math.pi)
        dist_r = random.uniform(40, 120)
        self.target_x = self.x + math.cos(angle) * dist_r
        self.target_y = self.y + math.sin(angle) * dist_r
        self.patrol_timer = random.randint(90, 200)

    def alert(self, tx, ty):
        self.target_x = tx
        self.target_y = ty
        self.alert_t  = ENEMY_ALERT_TIME
        self.speed    = ENEMY_ALERT_SPEED

    def update(self, walls, player):
        if self.reveal > 0:
            self.reveal -= 1
        if self.alert_t > 0:
            self.alert_t -= 1
            if self.alert_t == 0:
                self.speed = ENEMY_SPEED_BASE
                self._pick_patrol()
        else:
            self.patrol_timer -= 1
            if self.patrol_timer <= 0:
                self._pick_patrol()

        dx, dy = self.target_x - self.x, self.target_y - self.y
        d = math.hypot(dx, dy)
        if d > 2:
            nx, ny = dx / d, dy / d
            new_x = self.x + nx * self.speed
            new_y = self.y + ny * self.speed
            # Colisión simple con paredes
            r = ENEMY_RADIUS
            ex_rect = pygame.Rect(new_x - r, new_y - r, r * 2, r * 2)
            hit = False
            for w in walls:
                if ex_rect.colliderect(w.rect):
                    hit = True
                    break
            if not hit:
                self.x, self.y = new_x, new_y
            else:
                self._pick_patrol()

        # Detectar jugador (vista corta sin sonar)
        if dist((self.x, self.y), (player.x, player.y)) < 36:
            player.caught = True

    def draw(self, surf, offset):
        if self.reveal <= 0:
            return
        alpha = min(1.0, self.reveal / 20)
        col = lerp_color(BLACK, RED, alpha)
        cx = int(self.x - offset[0])
        cy = int(self.y - offset[1])
        # Dibujar como triángulo amenazante
        angle = math.atan2(self.target_y - self.y, self.target_x - self.x)
        pts = [
            (cx + math.cos(angle) * ENEMY_RADIUS,          cy + math.sin(angle) * ENEMY_RADIUS),
            (cx + math.cos(angle + 2.4) * ENEMY_RADIUS,    cy + math.sin(angle + 2.4) * ENEMY_RADIUS),
            (cx + math.cos(angle - 2.4) * ENEMY_RADIUS,    cy + math.sin(angle - 2.4) * ENEMY_RADIUS),
        ]
        pygame.draw.polygon(surf, col, pts)
        if self.alert_t > 0:
            pygame.draw.circle(surf, ORANGE, (cx, cy - ENEMY_RADIUS - 6), 4)


class Player:
    def __init__(self, x, y):
        self.x      = x
        self.y      = y
        self.caught = False
        self.won    = False
        self.trail  = []

    def move(self, dx, dy, walls):
        spd = PLAYER_SPEED
        self.trail.append((self.x, self.y))
        if len(self.trail) > 12:
            self.trail.pop(0)

        for axis in [(dx * spd, 0), (0, dy * spd)]:
            nx = self.x + axis[0]
            ny = self.y + axis[1]
            r = PLAYER_RADIUS
            prect = pygame.Rect(nx - r, ny - r, r * 2, r * 2)
            blocked = any(prect.colliderect(w.rect) for w in walls)
            if not blocked:
                self.x, self.y = nx, ny

    def draw(self, surf, offset):
        # Estela
        for i, (tx, ty) in enumerate(self.trail):
            a = (i + 1) / len(self.trail) if self.trail else 1
            col = lerp_color(BLACK, GREEN, a * 0.5)
            r = max(1, int(PLAYER_RADIUS * a * 0.5))
            pygame.draw.circle(surf, col, (int(tx - offset[0]), int(ty - offset[1])), r)
        # Cuerpo
        cx = int(self.x - offset[0])
        cy = int(self.y - offset[1])
        pygame.draw.circle(surf, GREEN, (cx, cy), PLAYER_RADIUS)
        pygame.draw.circle(surf, WHITE, (cx, cy), PLAYER_RADIUS, 1)


# ── Construcción del mapa ─────────────────────────────────────────────────────

def build_map():
    walls      = []
    enemies    = []
    player_pos = (TILE + TILE // 2, TILE + TILE // 2)
    exit_rect  = None

    for row_i, row in enumerate(RAW_MAP):
        for col_i, ch in enumerate(row):
            rx = col_i * TILE
            ry = row_i * TILE
            if ch == '#':
                r = pygame.Rect(rx, ry, TILE, TILE)
                walls.append(Wall(r))
            elif ch == 'S':
                player_pos = (rx + TILE // 2, ry + TILE // 2)
            elif ch == 'E':
                er = pygame.Rect(rx + 4, ry + 4, TILE - 8, TILE - 8)
                exit_rect = ExitTile(er)
            elif ch == '.':
                if random.random() < 0.04:
                    enemies.append(Enemy(rx + TILE // 2, ry + TILE // 2))

    # Garantizar al menos 3 enemigos
    while len(enemies) < 3:
        r = random.randint(1, ROWS - 2)
        c = random.randint(1, COLS - 2)
        if RAW_MAP[r][c] == '.':
            enemies.append(Enemy(c * TILE + TILE // 2, r * TILE + TILE // 2))

    return walls, enemies, player_pos, exit_rect


# ── Pantalla de inicio ───────────────────────────────────────────────────────

def draw_start_screen(surf, font, small_font, tick):
    """Renders an animated start screen. Returns the pygame.Rect of the play button."""
    surf.fill(BLACK)

    cx, cy = W // 2, H // 2

    # ── Fondo: anillos de sonar animados ─────────────────────────────────────
    num_rings = 5
    for i in range(num_rings):
        phase = (tick * 1.8 + i * (360 // num_rings)) % 360
        radius = int((phase / 360) * max(W, H) * 0.85)
        alpha_f = 1.0 - (phase / 360)
        r = int(0 * alpha_f)
        g = int(220 * alpha_f)
        b = int(255 * alpha_f)
        if radius > 0:
            pygame.draw.circle(surf, (r, g, b), (cx, cy), radius, 1)

    # ── Grid sutil de fondo ───────────────────────────────────────────────────
    for gx in range(0, W, TILE):
        pygame.draw.line(surf, (8, 15, 20), (gx, 0), (gx, H))
    for gy in range(0, H, TILE):
        pygame.draw.line(surf, (8, 15, 20), (0, gy), (W, gy))

    # ── Panel central (glassmorphism) ─────────────────────────────────────────
    panel_w, panel_h = 560, 380
    panel_x = cx - panel_w // 2
    panel_y = cy - panel_h // 2

    panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel_surf.fill((0, 30, 45, 180))
    surf.blit(panel_surf, (panel_x, panel_y))

    # Borde brillante
    border_alpha = int(140 + 80 * (math.sin(tick * 0.05) * 0.5 + 0.5))
    pygame.draw.rect(surf, (0, border_alpha, 180), (panel_x, panel_y, panel_w, panel_h), 2)
    # Brillo en esquinas
    corner_size = 10
    for px, py in [(panel_x, panel_y), (panel_x + panel_w - corner_size, panel_y),
                   (panel_x, panel_y + panel_h - corner_size),
                   (panel_x + panel_w - corner_size, panel_y + panel_h - corner_size)]:
        pygame.draw.rect(surf, CYAN, (px, py, corner_size, corner_size), 2)

    # ── Título ────────────────────────────────────────────────────────────────
    try:
        title_font  = pygame.font.SysFont("consolas", 46, bold=True)
        sub_font    = pygame.font.SysFont("consolas", 15)
        ctrl_font   = pygame.font.SysFont("consolas", 14)
        btn_font    = pygame.font.SysFont("consolas", 20, bold=True)
    except Exception:
        title_font = sub_font = ctrl_font = btn_font = font

    # Sombra del título
    glow_val = int(180 + 75 * (math.sin(tick * 0.06) * 0.5 + 0.5))
    shadow = title_font.render("ECO-CEGUERA", True, (0, glow_val // 4, glow_val // 3))
    surf.blit(shadow, (cx - shadow.get_width() // 2 + 3, panel_y + 36 + 3))
    title_surf = title_font.render("ECO-CEGUERA", True, (0, glow_val, int(glow_val * 1.0)))
    surf.blit(title_surf, (cx - title_surf.get_width() // 2, panel_y + 36))

    subtitle = sub_font.render("Sigilo sónico  ·  Sonar  ·  Supervivencia", True, (0, 160, 200))
    surf.blit(subtitle, (cx - subtitle.get_width() // 2, panel_y + 96))

    # Separador
    pygame.draw.line(surf, DARK_CYAN, (panel_x + 30, panel_y + 122), (panel_x + panel_w - 30, panel_y + 122), 1)

    # ── Controles ─────────────────────────────────────────────────────────────
    controls = [
        ("WASD / Flechas",  "Mover al jugador"),
        ("Clic Izquierdo",  "Emitir pulso sonar (te delata)"),
        ("Clic Derecho",    "Lanzar señuelo (distrae enemigos)"),
        ("R",               "Reiniciar partida"),
        ("ESC",             "Salir al sistema operativo"),
    ]
    label_x  = panel_x + 36
    value_x  = panel_x + 200
    ctrl_y   = panel_y + 136
    line_h   = 24
    for key, desc in controls:
        k_surf = ctrl_font.render(key, True, CYAN)
        d_surf = ctrl_font.render(desc, True, (160, 200, 220))
        surf.blit(k_surf, (label_x, ctrl_y))
        surf.blit(d_surf, (value_x, ctrl_y))
        ctrl_y += line_h

    # Separador
    pygame.draw.line(surf, DARK_CYAN, (panel_x + 30, panel_y + 300), (panel_x + panel_w - 30, panel_y + 300), 1)

    # ── Botón JUGAR ───────────────────────────────────────────────────────────
    btn_w, btn_h = 200, 44
    btn_x = cx - btn_w // 2
    btn_y = panel_y + panel_h - 66
    btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

    mouse_pos = pygame.mouse.get_pos()
    hovered = btn_rect.collidepoint(mouse_pos)

    btn_color = (0, 200, 255) if hovered else (0, 140, 180)
    btn_surf = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
    btn_surf.fill((*btn_color, 200 if hovered else 140))
    surf.blit(btn_surf, (btn_x, btn_y))
    pygame.draw.rect(surf, btn_color, btn_rect, 2)

    btn_lbl = btn_font.render("[ JUGAR ]" if not hovered else ">> JUGAR <<", True, WHITE)
    surf.blit(btn_lbl, (cx - btn_lbl.get_width() // 2, btn_y + btn_h // 2 - btn_lbl.get_height() // 2))

    # Tip teclado
    tip = ctrl_font.render("o presiona  ENTER / ESPACIO", True, (60, 100, 120))
    surf.blit(tip, (cx - tip.get_width() // 2, btn_y + btn_h + 8))

    return btn_rect


# ── HUD ───────────────────────────────────────────────────────────────────────

def draw_hud(surf, font, small_font, decoys, alert_count, caught, won):
    # Panel izquierdo
    pygame.draw.rect(surf, (10, 20, 30), (0, 0, W, 36))
    pygame.draw.line(surf, DARK_CYAN, (0, 36), (W, 36), 1)

    title = font.render("ECO-CEGUERA", True, CYAN)
    surf.blit(title, (12, 8))

    decoy_txt = small_font.render(f"Señuelos: {'[ ]' * decoys}  (clic der)", True, PURPLE)
    surf.blit(decoy_txt, (220, 10))

    if alert_count > 0:
        alert_txt = small_font.render(f"! {alert_count} enemigo(s) en alerta !", True, ORANGE)
        surf.blit(alert_txt, (W - alert_txt.get_width() - 12, 10))

    controls = small_font.render("WASD/Flechas: mover  |  Clic Izq: sonar  |  R: reiniciar  |  ESC: salir", True, (80, 120, 140))
    surf.blit(controls, (12, H - 22))

    if caught:
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((180, 0, 0, 120))
        surf.blit(overlay, (0, 0))
        msg = font.render("¡TE HAN ATRAPADO!  Pulsa R para reiniciar", True, WHITE)
        surf.blit(msg, (W // 2 - msg.get_width() // 2, H // 2 - 20))

    if won:
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 180, 60, 100))
        surf.blit(overlay, (0, 0))
        msg = font.render("¡ESCAPASTE!  Pulsa R para reiniciar", True, GOLD)
        surf.blit(msg, (W // 2 - msg.get_width() // 2, H // 2 - 20))


# ── Loop principal ────────────────────────────────────────────────────────────

def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Eco-Ceguera")
    clock  = pygame.time.Clock()

    try:
        font       = pygame.font.SysFont("consolas", 20, bold=True)
        small_font = pygame.font.SysFont("consolas", 14)
    except Exception:
        font       = pygame.font.Font(None, 24)
        small_font = pygame.font.Font(None, 16)

    # ── Pantalla de inicio ────────────────────────────────────────────────────
    intro_tick = 0
    in_intro   = True
    while in_intro:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    in_intro = False
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                btn_rect = draw_start_screen(screen, font, small_font, intro_tick)
                if btn_rect.collidepoint(event.pos):
                    in_intro = False

        btn_rect = draw_start_screen(screen, font, small_font, intro_tick)
        pygame.display.flip()
        intro_tick += 1

    def new_game():
        walls, enemies, ppos, exit_r = build_map()
        player  = Player(*ppos)
        pulses  = []
        decoys  = DECOY_COUNT
        tick    = 0
        return walls, enemies, player, pulses, decoys, tick, exit_r

    walls, enemies, player, pulses, decoys, tick, exit_rect = new_game()

    # Viewport offset para centrar al jugador
    HUD_TOP = 38
    VIEW_W  = W
    VIEW_H  = H - HUD_TOP - 24

    running = True
    while running:
        dt = clock.tick(FPS)
        tick += 1

        # ── Eventos ──────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_r:
                    walls, enemies, player, pulses, decoys, tick, exit_rect = new_game()
            if event.type == pygame.MOUSEBUTTONDOWN and not player.caught and not player.won:
                mx, my = event.pos
                # Convertir clic a coordenadas del mundo
                off_x = player.x - VIEW_W // 2
                off_y = player.y - VIEW_H // 2
                off_x = max(0, min(off_x, MAP_W - VIEW_W))
                off_y = max(0, min(off_y, MAP_H - VIEW_H))
                world_x = mx + off_x
                world_y = (my - HUD_TOP) + off_y

                if event.button == 1:   # sonar desde jugador
                    pulses.append(SonarPulse(player.x, player.y, CYAN))
                elif event.button == 3 and decoys > 0:  # señuelo
                    pulses.append(SonarPulse(world_x, world_y, PURPLE, is_decoy=True))
                    # Alertar enemigos al señuelo
                    for e in enemies:
                        if dist((e.x, e.y), (world_x, world_y)) < SONAR_MAX_RADIUS:
                            e.alert(world_x, world_y)
                    decoys -= 1

        # ── Movimiento jugador ────────────────────────────────────────────────
        if not player.caught and not player.won:
            keys = pygame.key.get_pressed()
            dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
            dy = (keys[pygame.K_s] or keys[pygame.K_DOWN])  - (keys[pygame.K_w] or keys[pygame.K_UP])
            if dx or dy:
                ndx, ndy = normalize(dx, dy)
                player.move(ndx, ndy, walls)

            # Verificar salida
            if exit_rect and pygame.Rect(player.x - PLAYER_RADIUS, player.y - PLAYER_RADIUS,
                                         PLAYER_RADIUS * 2, PLAYER_RADIUS * 2).colliderect(exit_rect.rect):
                player.won = True

        # ── Actualizar pulsos ─────────────────────────────────────────────────
        for p in pulses:
            p.update(walls, enemies, exit_rect, player)
        pulses = [p for p in pulses if not p.dead]

        # ── Actualizar paredes ────────────────────────────────────────────────
        for w in walls:
            w.update()

        # ── Actualizar enemigos ───────────────────────────────────────────────
        if not player.caught and not player.won:
            for e in enemies:
                e.update(walls, player)

        # ── Calcular offset de cámara ─────────────────────────────────────────
        off_x = int(player.x - VIEW_W // 2)
        off_y = int(player.y - VIEW_H // 2)
        off_x = max(0, min(off_x, MAP_W - VIEW_W))
        off_y = max(0, min(off_y, MAP_H - VIEW_H))
        offset = (off_x, off_y)

        # ── Dibujo ────────────────────────────────────────────────────────────
        screen.fill(BLACK)

        # Zona de juego (recorte)
        game_surf = pygame.Surface((VIEW_W, VIEW_H))
        game_surf.fill(BLACK)

        # Fondo: grid sutil
        for gx in range(0, MAP_W, TILE):
            sx = gx - off_x
            if 0 <= sx <= VIEW_W:
                pygame.draw.line(game_surf, (8, 15, 20), (sx, 0), (sx, VIEW_H))
        for gy in range(0, MAP_H, TILE):
            sy = gy - off_y
            if 0 <= sy <= VIEW_H:
                pygame.draw.line(game_surf, (8, 15, 20), (0, sy), (VIEW_W, sy))

        # Paredes
        for w in walls:
            w.draw(game_surf, offset)

        # Salida
        if exit_rect:
            if exit_rect.revealed > 0:
                exit_rect.revealed -= 1
                alpha = min(1.0, exit_rect.revealed / 20)
                blink = (math.sin(tick * 0.15) + 1) / 2
                col = lerp_color(BLACK, GOLD, alpha * blink)
                er = pygame.Rect(exit_rect.rect.x - off_x, exit_rect.rect.y - off_y,
                                 exit_rect.rect.w, exit_rect.rect.h)
                pygame.draw.rect(game_surf, col, er)
                pygame.draw.rect(game_surf, GOLD, er, 2)

        # Pulsos de sonar
        for p in pulses:
            p.draw(game_surf, offset)

        # Enemigos
        for e in enemies:
            e.draw(game_surf, offset)

        # Jugador (siempre visible)
        player.draw(game_surf, offset)

        screen.blit(game_surf, (0, HUD_TOP))

        # HUD
        alert_count = sum(1 for e in enemies if e.alert_t > 0)
        draw_hud(screen, font, small_font, decoys, alert_count, player.caught, player.won)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
