class ExitTile:
    def __init__(self, rect):
        self.rect     = rect
        self.revealed = 0

import pygame
import math
import random
import sys
from collections import deque
import heapq
import asyncio
try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

#  Configuración 
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

# ── Configuración de niveles ────────────────────────────────────────────────
LEVEL_CONFIGS = [
    {'name': 'PRIMER CONTACTO',  'subtitle': 'Aprende a escuchar la oscuridad',
     'n_normal': 2, 'bat': False, 'heavy': False, 'n_traps': 0,
     'mat_metal': 0.10, 'mat_cork': 0.05, 'mat_mirror': 0.05,
     'reveal_dur': 110, 'sonar_radius': 320, 'micro_interval': 60, 'spd_mult': 0.8,
     'mechanic': None},
    {'name': 'ECOS ROJOS',       'subtitle': 'El murciélago ha despertado',
     'n_normal': 3, 'bat': True,  'heavy': False, 'n_traps': 2,
     'mat_metal': 0.20, 'mat_cork': 0.15, 'mat_mirror': 0.08,
     'reveal_dur': 80, 'sonar_radius': 300, 'micro_interval': 50, 'spd_mult': 1.0,
     'mechanic': None},
    {'name': 'CUENTA REGRESIVA', 'subtitle': 'La salida se cierra en 90 segundos',
     'n_normal': 3, 'bat': True,  'heavy': True,  'n_traps': 3,
     'mat_metal': 0.15, 'mat_cork': 0.30, 'mat_mirror': 0.10,
     'reveal_dur': 70, 'sonar_radius': 280, 'micro_interval': 45, 'spd_mult': 1.0,
     'mechanic': 'timer', 'timer_secs': 90},
    {'name': 'CAMPO MINADO',     'subtitle': 'Las trampas se regeneran cada 15 s',
     'n_normal': 4, 'bat': True,  'heavy': True,  'n_traps': 10,
     'mat_metal': 0.25, 'mat_cork': 0.20, 'mat_mirror': 0.10,
     'reveal_dur': 60, 'sonar_radius': 260, 'micro_interval': 40, 'spd_mult': 1.2,
     'mechanic': 'respawn_traps', 'respawn_frames': 900},
    {'name': 'EL ABISMO',        'subtitle': 'La oscuridad te consume cada 15 s',
     'n_normal': 5, 'bat': True,  'heavy': True,  'n_traps': 6,
     'mat_metal': 0.25, 'mat_cork': 0.25, 'mat_mirror': 0.12,
     'reveal_dur': 45, 'sonar_radius': 240, 'micro_interval': 35, 'spd_mult': 1.5,
     'mechanic': 'blackout', 'blackout_interval': 900},
]
N_LEVELS = len(LEVEL_CONFIGS)


# Nuevas mecánicas
PLAYER_SNEAK_SPEED   = 1.5   # velocidad al caminar (Shift)
MICRO_PULSE_INTERVAL = 50    # frames entre micropulsos al correr
BAT_RADIUS           = 7
BAT_SONAR_INTERVAL   = 80    # frames entre sonar del murciélago
BAT_SONAR_RADIUS     = 200
HEAVY_RADIUS         = 18
HEAVY_SPEED          = 0.45
HEAVY_HEAR_RADIUS    = 280
TRAP_PULSE_RADIUS    = 300

# Estados FSM de la IA
STATE_PATROL     = 0
STATE_INVESTIGATE = 1
STATE_CHASE      = 2
STATE_LOST       = 3

# Materiales de pared
MAT_NORMAL  = 'normal'
MAT_METAL   = 'metal'
MAT_CORK    = 'cork'
MAT_MIRROR  = 'mirror'
METAL_COLOR  = (90, 120, 150)   # acero azul-gris
CORK_COLOR   = (90, 60, 30)     # marrón oscuro
MIRROR_COLOR = (180, 220, 255)  # espejo plateado-frío

# Dimensiones del mapa generado proceduralmente (deben ser impares)
COLS  = 23
ROWS  = 15
MAP_W = COLS * TILE
MAP_H = ROWS * TILE

#  Utilidades 

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def normalize(dx, dy):
    d = math.hypot(dx, dy)
    if d == 0:
        return 0, 0
    return dx / d, dy / d

def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

def world_to_cell(x, y):
    return int(y) // TILE, int(x) // TILE

def cell_to_world(r, c):
    return c * TILE + TILE // 2, r * TILE + TILE // 2

def astar(wall_grid, start, goal):
    """A* sobre grilla. start/goal=(row,col). Retorna lista de (row,col)."""
    if start == goal or not wall_grid:
        return []
    rows, cols = len(wall_grid), len(wall_grid[0])
    gr, gc = goal
    def h(r, c): return abs(r - gr) + abs(c - gc)
    open_set = [(h(*start), 0, start)]
    came_from = {}
    g = {start: 0}
    while open_set:
        _, cost, cur = heapq.heappop(open_set)
        if cur == goal:
            path = []
            while cur in came_from:
                path.append(cur)
                cur = came_from[cur]
            return path[::-1]
        if cost > g.get(cur, float('inf')):
            continue
        cr, cc = cur
        for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
            nr, nc = cr+dr, cc+dc
            if 0 <= nr < rows and 0 <= nc < cols and not wall_grid[nr][nc]:
                ng = g[cur] + 1
                if ng < g.get((nr,nc), float('inf')):
                    came_from[(nr,nc)] = cur
                    g[(nr,nc)] = ng
                    heapq.heappush(open_set, (ng+h(nr,nc), ng, (nr,nc)))
    return []

# ── Sistema de sonido procedural ─────────────────────────────────────────

def _make_sound(freq=440, duration=0.08, vol=0.18, wave='sine', decay=True):
    """Genera un sonido sintético sin archivos externos. Requiere numpy."""
    if not _HAS_NUMPY:
        return None
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
        sr   = 44100
        n    = int(sr * duration)
        t    = np.linspace(0, duration, n, endpoint=False)
        if wave == 'sine':
            sig = np.sin(2 * math.pi * freq * t)
        elif wave == 'square':
            sig = np.sign(np.sin(2 * math.pi * freq * t))
        else:  # noise burst
            sig = np.random.uniform(-1, 1, n)
        if decay:
            env = np.linspace(1.0, 0.0, n) ** 1.8
            sig = sig * env
        sig  = (sig * vol * 32767).astype(np.int16)
        snd  = pygame.sndarray.make_sound(sig)
        return snd
    except Exception:
        return None

# Pre-generar sonidos al inicio (se reusan cada frame)
_snd_sonar  = None   # pulso del jugador
_snd_mirror = None   # rebote en espejo
_snd_trap   = None   # trampa activada
_snd_win    = None   # victoria
_snd_lose   = None   # derrota

def _init_sounds():
    global _snd_sonar, _snd_mirror, _snd_trap, _snd_win, _snd_lose
    _snd_sonar  = _make_sound(freq=520,  duration=0.12, vol=0.22, wave='sine')
    _snd_mirror = _make_sound(freq=900,  duration=0.07, vol=0.14, wave='sine', decay=True)
    _snd_trap   = _make_sound(freq=220,  duration=0.18, vol=0.28, wave='square')
    _snd_win    = _make_sound(freq=660,  duration=0.35, vol=0.30, wave='sine')
    _snd_lose   = _make_sound(freq=110,  duration=0.30, vol=0.30, wave='square')

def play_sound(snd):
    if snd is not None:
        try: snd.play()
        except Exception: pass

#  Clases 

class Wall:
    def __init__(self, rect, material=MAT_NORMAL):
        self.rect     = rect
        self.reveal   = 0
        self.material = material
        self.corners  = [rect.topleft, rect.topright, rect.bottomright, rect.bottomleft]

    def update(self):
        if self.reveal > 0:
            self.reveal -= 1

    def draw(self, surf, offset):
        if self.reveal <= 0:
            return
        alpha = min(1.0, self.reveal / 30)
        r = pygame.Rect(self.rect.x - offset[0], self.rect.y - offset[1],
                        self.rect.w, self.rect.h)
        if self.material == MAT_METAL:
            base_col, edge_col = METAL_COLOR, (180, 210, 240)
        elif self.material == MAT_CORK:
            base_col, edge_col = CORK_COLOR, (150, 100, 60)
        elif self.material == MAT_MIRROR:
            base_col, edge_col = (160, 200, 240), (220, 240, 255)
        else:
            base_col, edge_col = (0, 30, 40), CYAN
        if alpha > 0.35:
            pygame.draw.rect(surf, lerp_color(BLACK, base_col, alpha), r)
            pygame.draw.rect(surf, lerp_color(BLACK, edge_col, alpha * 0.6), r, 1)
            # Espejo: línea diagonal brillante
            if self.material == MAT_MIRROR:
                shine = lerp_color(BLACK, (255, 255, 255), alpha * 0.7)
                pygame.draw.line(surf, shine, r.topleft, r.bottomright, 1)
                pygame.draw.line(surf, shine, r.topright, r.bottomleft, 1)
        else:
            density = alpha / 0.35
            n_dots = int(TILE * TILE * density * 0.22)
            bc = tuple(int(c * density) for c in base_col)
            sw, sh = surf.get_size()
            for _ in range(n_dots):
                px = r.x + random.randint(0, TILE - 1)
                py = r.y + random.randint(0, TILE - 1)
                if 0 <= px < sw and 0 <= py < sh:
                    v = random.randint(0, 55)
                    surf.set_at((px, py), (min(255, bc[0]+v//4),
                                           min(255, bc[1]+v//4),
                                           min(255, bc[2]+v//4)))


class SonarPulse:
    def __init__(self, x, y, color=CYAN, is_decoy=False, catches_player=False, max_radius=SONAR_MAX_RADIUS):
        self.x              = x
        self.y              = y
        self.radius         = 0
        self.color          = color
        self.dead           = False
        self.is_decoy       = is_decoy
        self.catches_player = catches_player
        self.max_radius     = max_radius
        self.revealed       = set()

    def update(self, walls, enemies, exit_rect, player):
        self.radius += SONAR_SPEED
        if self.radius > self.max_radius:
            self.dead = True
            return []

        new_pulses = []

        # Revelar paredes tocadas por el frente de onda
        for w in walls:
            if id(w) in self.revealed:
                continue
            cx = max(w.rect.left, min(self.x, w.rect.right))
            cy = max(w.rect.top,  min(self.y, w.rect.bottom))
            if abs(dist((self.x, self.y), (cx, cy)) - self.radius) < SONAR_SPEED + 2:
                self.revealed.add(id(w))
                if w.material == MAT_CORK:
                    w.reveal = max(w.reveal, REVEAL_DURATION // 4)
                    self.max_radius = min(self.max_radius, self.radius + 55)
                elif w.material == MAT_MIRROR:
                    w.reveal = max(w.reveal, REVEAL_DURATION)
                    # Calcular punto de impacto y normal de la cara
                    hit_x = max(w.rect.left, min(self.x, w.rect.right))
                    hit_y = max(w.rect.top,  min(self.y, w.rect.bottom))
                    # Determinar cuál cara fue impactada
                    dx_hit = self.x - w.rect.centerx
                    dy_hit = self.y - w.rect.centery
                    if abs(dx_hit) >= abs(dy_hit):  # cara izq/der → refleja X
                        nx_r, ny_r = -1.0, 0.0
                    else:                            # cara arriba/abajo → refleja Y
                        nx_r, ny_r = 0.0, -1.0
                    # Dirección incidente del pulso (desde centro hacia pared)
                    idx_ = hit_x - self.x; idy_ = hit_y - self.y
                    ld = math.hypot(idx_, idy_)
                    if ld > 0: idx_, idy_ = idx_/ld, idy_/ld
                    # Reflexión: r = d - 2(d·n)n
                    dot = idx_*nx_r + idy_*ny_r
                    rx_ = idx_ - 2*dot*nx_r
                    ry_ = idy_ - 2*dot*ny_r
                    rem = max(0, self.max_radius - self.radius) * 0.7
                    if rem > 30 and not self.is_decoy:
                        ref = SonarPulse(hit_x + rx_*4, hit_y + ry_*4,
                                         color=MIRROR_COLOR,
                                         is_decoy=False,
                                         catches_player=self.catches_player,
                                         max_radius=rem)
                        ref.revealed.add(id(w))
                        new_pulses.append(ref)
                        play_sound(_snd_mirror)
                else:
                    w.reveal = max(w.reveal, REVEAL_DURATION)

        # Revelar enemigos
        for e in enemies:
            if id(e) in self.revealed:
                continue
            d = dist((self.x, self.y), (e.x, e.y))
            if abs(d - self.radius) < SONAR_SPEED + 4:
                e.reveal = REVEAL_DURATION
                self.revealed.add(id(e))
                if not self.is_decoy:
                    e.alert(player.x, player.y)

        # Revelar salida
        if exit_rect:
            cx = max(exit_rect.rect.left, min(self.x, exit_rect.rect.right))
            cy = max(exit_rect.rect.top,  min(self.y, exit_rect.rect.bottom))
            if abs(dist((self.x, self.y), (cx, cy)) - self.radius) < SONAR_SPEED + 2:
                exit_rect.revealed = REVEAL_DURATION

        # Murciélago: detectar si el pulso toca al jugador
        if self.catches_player:
            dp = dist((self.x, self.y), (player.x, player.y))
            if abs(dp - self.radius) < SONAR_SPEED + 6:
                player.caught = True

        return new_pulses


    def draw(self, surf, offset):
        if self.dead:
            return
        alpha_f = 1.0 - (self.radius / max(self.max_radius, 1))
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
        self.trail    = []
        # FSM
        self.state       = STATE_PATROL
        self.path        = []       # A* waypoints [(row, col)]
        self.path_idx    = 0
        self.path_dirty  = False
        self.lost_timer  = 0
        self.sound_x     = x
        self.sound_y     = y
        self.chase_timer = 0        # countdown to refresh chase path
        self._pick_patrol()

    def _pick_patrol(self):
        angle = random.uniform(0, 2 * math.pi)
        dist_r = random.uniform(40, 120)
        self.target_x = self.x + math.cos(angle) * dist_r
        self.target_y = self.y + math.sin(angle) * dist_r
        self.patrol_timer = random.randint(90, 200)

    def alert(self, tx, ty):
        self.sound_x    = tx
        self.sound_y    = ty
        self.alert_t    = ENEMY_ALERT_TIME
        self.speed      = ENEMY_ALERT_SPEED
        self.state      = STATE_INVESTIGATE
        self.path_dirty = True      # recompute A* next update

    def _follow_path(self):
        """Steer target_x/y toward next waypoint in self.path."""
        if self.path and self.path_idx < len(self.path):
            pr, pc = self.path[self.path_idx]
            wx, wy = cell_to_world(pr, pc)
            if math.hypot(self.x - wx, self.y - wy) < TILE // 2:
                self.path_idx += 1
            else:
                self.target_x, self.target_y = wx, wy
                return True
        return False

    def update(self, walls, player, all_enemies=None, wall_grid=None):
        if self.reveal > 0:
            self.reveal -= 1

        # Recompute A* path if flagged
        if self.path_dirty and wall_grid is not None:
            start = world_to_cell(self.x, self.y)
            goal  = world_to_cell(self.sound_x, self.sound_y)
            self.path     = astar(wall_grid, start, goal)
            self.path_idx = 0
            self.path_dirty = False

        # ── FSM ──────────────────────────────────────────────────────────
        if self.state == STATE_PATROL:
            self.speed = ENEMY_SPEED_BASE
            self.patrol_timer -= 1
            if self.patrol_timer <= 0:
                self._pick_patrol()

        elif self.state == STATE_INVESTIGATE:
            self.alert_t -= 1
            if self.alert_t <= 0:
                self.state = STATE_LOST
                self.lost_timer = 180
                self.speed = ENEMY_SPEED_BASE * 0.7
            if not self._follow_path():
                # No more waypoints: reached destination
                self.target_x, self.target_y = self.sound_x, self.sound_y
                if math.hypot(self.x - self.sound_x, self.y - self.sound_y) < TILE:
                    self.state = STATE_LOST
                    self.lost_timer = 180
                    self.speed = ENEMY_SPEED_BASE * 0.7
            # Transition to CHASE if player is very close
            if dist((self.x, self.y), (player.x, player.y)) < 80:
                self.state = STATE_CHASE
                self.alert_t = ENEMY_ALERT_TIME
                self.speed   = ENEMY_ALERT_SPEED
                self.chase_timer = 0

        elif self.state == STATE_CHASE:
            self.alert_t -= 1
            if self.alert_t <= 0:
                self.state = STATE_LOST
                self.lost_timer = 180
                self.speed = ENEMY_SPEED_BASE * 0.7
            else:
                self.chase_timer -= 1
                if self.chase_timer <= 0 and wall_grid is not None:
                    self.chase_timer = 20
                    start = world_to_cell(self.x, self.y)
                    goal  = world_to_cell(player.x, player.y)
                    self.path     = astar(wall_grid, start, goal)
                    self.path_idx = 0
                if not self._follow_path():
                    self.target_x, self.target_y = player.x, player.y

        elif self.state == STATE_LOST:
            self.lost_timer -= 1
            if self.lost_timer <= 0:
                self.state = STATE_PATROL
                self.speed = ENEMY_SPEED_BASE
                self._pick_patrol()
            else:
                if math.hypot(self.x - self.target_x, self.y - self.target_y) < TILE:
                    ang = random.uniform(0, 2 * math.pi)
                    r2  = random.uniform(20, 80)
                    self.target_x = self.sound_x + math.cos(ang) * r2
                    self.target_y = self.sound_y + math.sin(ang) * r2

        # ── Flocking (PATROL sólo) ────────────────────────────────────────
        flock_dx = flock_dy = 0.0
        if self.state == STATE_PATROL and all_enemies:
            sep_x = sep_y = coh_x = coh_y = ali_x = ali_y = 0.0
            count = 0
            for other in all_enemies:
                if other is self:
                    continue
                d = math.hypot(self.x - other.x, self.y - other.y)
                if 0 < d < 80:
                    count += 1
                    sep_x += (self.x - other.x) / d
                    sep_y += (self.y - other.y) / d
                    coh_x += other.x
                    coh_y += other.y
                    if other.trail:
                        ox, oy = other.trail[-1]
                        ali_x += other.x - ox
                        ali_y += other.y - oy
            if count > 0:
                coh_x = (coh_x / count - self.x) * 0.01
                coh_y = (coh_y / count - self.y) * 0.01
                sep_x *= 0.4;  sep_y *= 0.4
                ali_x = (ali_x / count) * 0.1
                ali_y = (ali_y / count) * 0.1
                flock_dx = sep_x + coh_x + ali_x
                flock_dy = sep_y + coh_y + ali_y

        # ── Movimiento ────────────────────────────────────────────────────
        dx = self.target_x - self.x + flock_dx
        dy = self.target_y - self.y + flock_dy
        d  = math.hypot(dx, dy)
        if d > 2:
            nx, ny = dx / d, dy / d
            new_x = self.x + nx * self.speed
            new_y = self.y + ny * self.speed
            r = ENEMY_RADIUS
            ex_rect = pygame.Rect(new_x - r, new_y - r, r * 2, r * 2)
            hit = any(ex_rect.colliderect(w.rect) for w in walls)
            if not hit:
                if not self.trail or math.hypot(self.x - self.trail[-1][0], self.y - self.trail[-1][1]) > 6:
                    self.trail.append((self.x, self.y))
                    if len(self.trail) > 20:
                        self.trail.pop(0)
                self.x, self.y = new_x, new_y
            else:
                if self.state in (STATE_INVESTIGATE, STATE_CHASE) and wall_grid:
                    self.path_dirty = True   # recalculate around obstacle
                else:
                    self._pick_patrol()

        # Detectar jugador por proximidad física
        if dist((self.x, self.y), (player.x, player.y)) < 36:
            player.caught = True


    def draw(self, surf, offset):
        # Subtle darkness-distortion trail — always drawn, no sonar needed
        for i, (tx, ty) in enumerate(self.trail):
            t = (i + 1) / max(len(self.trail), 1)
            tcx = int(tx - offset[0])
            tcy = int(ty - offset[1])
            brightness = int(t * 48)   # max ~48/255 — very dark teal
            if brightness > 5:
                radius = max(1, int(t * 2.5))
                pygame.draw.circle(surf, (brightness // 4, brightness // 2, brightness),
                                   (tcx, tcy), radius)

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


class BatEnemy(Enemy):
    """Emite sonar rojo. Si el frente de onda toca al jugador, lo atrapa."""
    def __init__(self, x, y):
        super().__init__(x, y)
        self.sonar_timer = random.randint(0, BAT_SONAR_INTERVAL)

    def update(self, walls, player, all_enemies=None, wall_grid=None):
        super().update(walls, player, all_enemies, wall_grid)
        self.sonar_timer -= 1
        if self.sonar_timer <= 0:
            self.sonar_timer = BAT_SONAR_INTERVAL
            return SonarPulse(self.x, self.y, color=(220, 30, 30),
                              is_decoy=True, catches_player=True,
                              max_radius=BAT_SONAR_RADIUS)
        return None

    def draw(self, surf, offset):
        for i, (tx, ty) in enumerate(self.trail):
            t = (i + 1) / max(len(self.trail), 1)
            b = int(t * 48)
            if b > 5:
                pygame.draw.circle(surf, (b, b // 5, b // 5),
                                   (int(tx - offset[0]), int(ty - offset[1])),
                                   max(1, int(t * 2.5)))
        if self.reveal <= 0:
            return
        alpha = min(1.0, self.reveal / 20)
        col = lerp_color(BLACK, (255, 40, 40), alpha)
        cx, cy = int(self.x - offset[0]), int(self.y - offset[1])
        r = BAT_RADIUS
        pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
        pygame.draw.polygon(surf, col, pts)
        pygame.draw.polygon(surf, lerp_color(BLACK, (255, 100, 100), alpha), pts, 1)
        if self.alert_t > 0:
            pygame.draw.circle(surf, RED, (cx, cy - r - 6), 4)


class HeavyEnemy(Enemy):
    """Lento y grande. Escucha sonar a enorme distancia."""
    def __init__(self, x, y):
        super().__init__(x, y)
        self.speed = HEAVY_SPEED

    def draw(self, surf, offset):
        for i, (tx, ty) in enumerate(self.trail):
            t = (i + 1) / max(len(self.trail), 1)
            b = int(t * 48)
            if b > 5:
                pygame.draw.circle(surf, (b, b // 3, 0),
                                   (int(tx - offset[0]), int(ty - offset[1])),
                                   max(1, int(t * 3)))
        if self.reveal <= 0:
            return
        alpha = min(1.0, self.reveal / 20)
        cx, cy = int(self.x - offset[0]), int(self.y - offset[1])
        pygame.draw.circle(surf, lerp_color(BLACK, ORANGE, alpha), (cx, cy), HEAVY_RADIUS)
        pygame.draw.circle(surf, lerp_color(BLACK, (255, 200, 80), alpha), (cx, cy), HEAVY_RADIUS, 2)
        if self.alert_t > 0:
            pygame.draw.circle(surf, ORANGE, (cx, cy - HEAVY_RADIUS - 6), 6)


class SoundTrap:
    """Baldosa trampa. Al pisarla, emite un pulso que alerta a todos los enemigos."""
    def __init__(self, cx, cy):
        r = TILE // 2 - 6
        self.rect      = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
        self.triggered = False
        self.cx        = cx
        self.cy        = cy

    def check(self, player):
        if self.triggered:
            return None
        pr = pygame.Rect(player.x - PLAYER_RADIUS, player.y - PLAYER_RADIUS,
                         PLAYER_RADIUS * 2, PLAYER_RADIUS * 2)
        if pr.colliderect(self.rect):
            self.triggered = True
            return SonarPulse(self.cx, self.cy, color=GOLD,
                              is_decoy=True, max_radius=TRAP_PULSE_RADIUS)
        return None

    def draw(self, surf, offset):
        if self.triggered:
            return
        rx = self.cx - offset[0]
        ry = self.cy - offset[1]
        c = (55, 38, 8)   # dark amber — barely visible
        pygame.draw.line(surf, c, (rx, ry - 6), (rx - 5, ry + 4), 1)
        pygame.draw.line(surf, c, (rx, ry - 6), (rx + 4, ry + 5), 1)
        pygame.draw.line(surf, c, (rx - 5, ry + 4), (rx - 2, ry + 9), 1)
        pygame.draw.line(surf, c, (rx + 4, ry + 5), (rx + 1, ry + 9), 1)
        pygame.draw.circle(surf, c, (rx, ry), 2)


class Player:
    def __init__(self, x, y):
        self.x      = x
        self.y      = y
        self.caught = False
        self.won    = False
        self.trail  = []

    def move(self, dx, dy, walls, sneaking=False):
        spd = PLAYER_SNEAK_SPEED if sneaking else PLAYER_SPEED
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


#  Generación Procedimental del Mapa 

def generate_map():
    """Iterative DFS maze (perfect maze) + extra loops + BFS exit placement."""
    cols, rows = COLS, ROWS
    grid = [['#'] * cols for _ in range(rows)]

    # Carve maze from (1,1) visiting only odd-indexed cells
    grid[1][1] = '.'
    stack = [(1, 1)]
    visited = {(1, 1)}
    while stack:
        r, c = stack[-1]
        dirs = [(0, 2), (0, -2), (2, 0), (-2, 0)]
        random.shuffle(dirs)
        moved = False
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if 1 <= nr < rows - 1 and 1 <= nc < cols - 1 and (nr, nc) not in visited:
                grid[nr][nc] = '.'
                grid[r + dr // 2][c + dc // 2] = '.'   # knock wall between
                visited.add((nr, nc))
                stack.append((nr, nc))
                moved = True
                break
        if not moved:
            stack.pop()

    # Add extra openings so it feels like corridors, not a perfect maze
    for _ in range((cols * rows) // 8):
        r = random.randint(1, rows - 2)
        c = random.randint(1, cols - 2)
        if grid[r][c] == '#':
            adj = sum(1 for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]
                      if 0 <= r+dr < rows and 0 <= c+dc < cols
                      and grid[r+dr][c+dc] != '#')
            if adj >= 2:
                grid[r][c] = '.'

    # Place start at (1,1)
    grid[1][1] = 'S'

    # BFS from start to find the farthest reachable open cell → exit
    dist_g = [[-1] * cols for _ in range(rows)]
    dist_g[1][1] = 0
    q = deque([(1, 1)])
    farthest = (1, 1)
    while q:
        cr, cc = q.popleft()
        for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
            nr, nc = cr + dr, cc + dc
            if 0 <= nr < rows and 0 <= nc < cols and dist_g[nr][nc] == -1 and grid[nr][nc] != '#':
                dist_g[nr][nc] = dist_g[cr][cc] + 1
                q.append((nr, nc))
                if dist_g[nr][nc] > dist_g[farthest[0]][farthest[1]]:
                    farthest = (nr, nc)
    grid[farthest[0]][farthest[1]] = 'E'

    return [''.join(row) for row in grid]


#  Construcción del mapa 

def build_map(cfg=None):
    if cfg is None:
        cfg = LEVEL_CONFIGS[0]
    raw        = generate_map()
    walls      = []
    enemies    = []
    traps      = []
    floor_cells = []
    player_pos = (TILE + TILE // 2, TILE + TILE // 2)
    exit_rect  = None
    mm = cfg.get('mat_metal', 0.25)
    mc = cfg.get('mat_cork',  0.15)

    for row_i, row in enumerate(raw):
        for col_i, ch in enumerate(row):
            rx = col_i * TILE
            ry = row_i * TILE
            if ch == '#':
                roll = random.random()
                mi   = cfg.get('mat_mirror', 0.08)
                if roll < mm:
                    mat = MAT_METAL
                elif roll < mm + mc:
                    mat = MAT_CORK
                elif roll < mm + mc + mi:
                    mat = MAT_MIRROR
                else:
                    mat = MAT_NORMAL
                walls.append(Wall(pygame.Rect(rx, ry, TILE, TILE), mat))
            elif ch == 'S':
                player_pos = (rx + TILE // 2, ry + TILE // 2)
            elif ch == 'E':
                exit_rect = ExitTile(pygame.Rect(rx + 4, ry + 4, TILE - 8, TILE - 8))
            elif ch == '.':
                floor_cells.append((col_i, row_i))

    random.shuffle(floor_cells)
    n_base  = cfg.get('n_normal', 2)
    n_traps = cfg.get('n_traps',  2)
    idx = 0
    for col_i, row_i in floor_cells[idx:idx + n_base]:
        enemies.append(Enemy(col_i * TILE + TILE // 2, row_i * TILE + TILE // 2))
    idx += n_base
    for col_i, row_i in floor_cells[idx:idx + n_traps]:
        traps.append(SoundTrap(col_i * TILE + TILE // 2, row_i * TILE + TILE // 2))
    idx += n_traps

    if cfg.get('bat', False) and idx < len(floor_cells):
        col_i, row_i = floor_cells[idx]; idx += 1
        enemies.append(BatEnemy(col_i * TILE + TILE // 2, row_i * TILE + TILE // 2))
    if cfg.get('heavy', False) and idx < len(floor_cells):
        col_i, row_i = floor_cells[idx]
        enemies.append(HeavyEnemy(col_i * TILE + TILE // 2, row_i * TILE + TILE // 2))

    # Build wall grid for A* pathfinding
    wall_grid = [[False] * COLS for _ in range(ROWS)]
    for w in walls:
        gc = w.rect.x // TILE
        gr = w.rect.y // TILE
        if 0 <= gr < ROWS and 0 <= gc < COLS:
            wall_grid[gr][gc] = True

    return walls, enemies, player_pos, exit_rect, traps, wall_grid



#  Pantalla de resolución 

def draw_resolution_select(surf, tick, sel, resolutions, font, small_font):
    """Resolution picker. Returns (card_rects, confirm_rect)."""
    sw, sh = surf.get_size()
    cx = sw // 2
    surf.fill(BLACK)
    for i in range(4):
        phase = (tick * 1.5 + i * 90) % 360
        rad = int((phase / 360) * max(sw, sh) * 0.85)
        af  = 1.0 - phase / 360
        if rad > 0:
            pygame.draw.circle(surf, (0, int(180*af), int(220*af)), (cx, sh//2), rad, 1)
    for gx in range(0, sw, TILE): pygame.draw.line(surf, (8,15,20), (gx,0), (gx,sh))
    for gy in range(0, sh, TILE): pygame.draw.line(surf, (8,15,20), (0,gy), (sw,gy))

    gv = int(160 + 80*(math.sin(tick*0.05)*0.5+0.5))
    try: tf = pygame.font.SysFont("consolas", 26, bold=True)
    except: tf = font
    ts = tf.render("TAMAÑO DE PANTALLA", True, (0, gv, gv))
    surf.blit(ts, (cx - ts.get_width()//2, 16))

    card_w = min(660, sw - 40)
    card_h, gap = 58, 7
    card_x = cx - card_w // 2
    card_y0 = 58
    mouse = pygame.mouse.get_pos()
    card_rects = []

    for i, (rw, rh, lbl) in enumerate(resolutions):
        cy2  = card_y0 + i * (card_h + gap)
        rect = pygame.Rect(card_x, cy2, card_w, card_h)
        card_rects.append(rect)
        selected = (i == sel)
        hovered  = rect.collidepoint(mouse)
        cs = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        cs.fill((0,40,60,200) if selected else (5,20,30,150))
        surf.blit(cs, (card_x, cy2))
        if selected:
            bv = int(130 + 110*(math.sin(tick*0.1)*0.5+0.5))
            border = (0, bv, 255)
        elif hovered: border = (0,110,170)
        else:         border = (0,55,75)
        pygame.draw.rect(surf, border, rect, 2)
        nc = WHITE if selected else (170,205,225)
        try: nf = pygame.font.SysFont("consolas", 17, bold=True)
        except: nf = small_font
        nm = nf.render(lbl, True, nc)
        surf.blit(nm, (card_x+20, cy2+card_h//2-nm.get_height()//2))
        if selected:
            ar = small_font.render("◄", True, CYAN)
            surf.blit(ar, (card_x+card_w-28, cy2+card_h//2-ar.get_height()//2))

    by = card_y0 + len(resolutions)*(card_h+gap) + 10
    ok_rect = pygame.Rect(cx-120, by, 240, 42)
    ph = ok_rect.collidepoint(mouse)
    pc = (0,210,255) if ph else (0,140,180)
    ps = pygame.Surface((240,42), pygame.SRCALPHA)
    ps.fill((*pc, 210 if ph else 140))
    surf.blit(ps, ok_rect.topleft)
    pygame.draw.rect(surf, pc, ok_rect, 2)
    try: bf = pygame.font.SysFont("consolas",16,bold=True)
    except: bf = font
    bl = bf.render(">> CONFIRMAR <<" if ph else "[ CONFIRMAR ]", True, WHITE)
    surf.blit(bl, (cx-bl.get_width()//2, by+21-bl.get_height()//2))
    tip = small_font.render("Flechas: navegar  |  Enter: confirmar  |  ESC: salir", True, (55,80,95))
    surf.blit(tip, (cx-tip.get_width()//2, sh-20))
    return card_rects, ok_rect


#  Pantalla de inicio 

# ── Partículas flotantes del menú ──────────────────────────────────────────
_menu_particles = []
def _init_menu_particles():
    global _menu_particles
    _menu_particles = [
        {'x': random.uniform(0, W), 'y': random.uniform(0, H),
         'r': 0, 'max_r': random.randint(60, 220),
         'speed': random.uniform(0.4, 1.1),
         'phase': random.uniform(0, math.pi * 2),
         'drift_x': random.uniform(-0.3, 0.3),
         'drift_y': random.uniform(-0.3, 0.3)}
        for _ in range(12)
    ]

_init_menu_particles()

def _update_menu_particles(tick):
    for p in _menu_particles:
        p['r'] += p['speed']
        p['x'] = (p['x'] + p['drift_x']) % W
        p['y'] = (p['y'] + p['drift_y']) % H
        if p['r'] >= p['max_r']:
            p['r'] = 0
            p['max_r'] = random.randint(60, 220)
            p['speed'] = random.uniform(0.4, 1.1)

def draw_start_screen(surf, font, small_font, tick, menu_sel=0, show_credits=False):
    """Renders animated main menu. Returns (play_rect, levels_rect, credits_rect, exit_rect)."""
    surf.fill(BLACK)
    cx, cy = W // 2, H // 2

    # ── Fondo: grid + partículas sonar ────────────────────────────────────
    for gx in range(0, W, TILE):
        pygame.draw.line(surf, (6, 12, 18), (gx, 0), (gx, H))
    for gy in range(0, H, TILE):
        pygame.draw.line(surf, (6, 12, 18), (0, gy), (W, gy))

    _update_menu_particles(tick)
    for p in _menu_particles:
        if p['r'] > 0:
            af = max(0.0, 1.0 - p['r'] / p['max_r'])
            col = (0, int(180 * af), int(220 * af))
            pygame.draw.circle(surf, col, (int(p['x']), int(p['y'])), int(p['r']), 1)

    # ── Scanlines decorativas ──────────────────────────────────────────────
    for sy in range(0, H, 4):
        pygame.draw.line(surf, (0, 5, 8), (0, sy), (W, sy))

    # ── Panel principal ───────────────────────────────────────────────────
    panel_w = min(560, W - 60)
    panel_h = 420
    panel_x = cx - panel_w // 2
    panel_y = cy - panel_h // 2

    # Sombra del panel
    shadow_s = pygame.Surface((panel_w + 12, panel_h + 12), pygame.SRCALPHA)
    shadow_s.fill((0, 200, 255, 18))
    surf.blit(shadow_s, (panel_x - 6, panel_y - 6))

    ps = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    ps.fill((0, 18, 30, 210))
    surf.blit(ps, (panel_x, panel_y))

    # Borde animado
    bv = int(100 + 120 * (math.sin(tick * 0.045) * 0.5 + 0.5))
    pygame.draw.rect(surf, (0, bv, min(255, bv + 60)), (panel_x, panel_y, panel_w, panel_h), 2)

    # Esquinas brillantes
    csz = 14
    cv = int(160 + 80 * (math.sin(tick * 0.07) * 0.5 + 0.5))
    for px2, py2 in [(panel_x, panel_y),
                     (panel_x + panel_w - csz, panel_y),
                     (panel_x, panel_y + panel_h - csz),
                     (panel_x + panel_w - csz, panel_y + panel_h - csz)]:
        pygame.draw.rect(surf, (0, cv, 255), (px2, py2, csz, csz), 2)

    # ── Título con efecto glitch ──────────────────────────────────────────
    try:
        title_font = pygame.font.SysFont("consolas", 50, bold=True)
        sub_font   = pygame.font.SysFont("consolas", 14)
        btn_font   = pygame.font.SysFont("consolas", 18, bold=True)
        tiny_font  = pygame.font.SysFont("consolas", 12)
    except Exception:
        title_font = sub_font = btn_font = tiny_font = font

    glow_val = int(170 + 85 * (math.sin(tick * 0.055) * 0.5 + 0.5))
    title_text = "ECO-CEGUERA"
    title_y = panel_y + 32

    # Glitch: desplazamiento aleatorio cada ~90 frames
    glitch_on = (tick % 90 < 4)
    gx_off = random.randint(-4, 4) if glitch_on else 0

    # Capa roja (glitch)
    if glitch_on:
        gl_r = title_font.render(title_text, True, (200, 0, 60))
        surf.blit(gl_r, (cx - gl_r.get_width() // 2 + gx_off + 2, title_y + 2))
    # Sombra
    sh_t = title_font.render(title_text, True, (0, glow_val // 5, glow_val // 4))
    surf.blit(sh_t, (cx - sh_t.get_width() // 2 + 3, title_y + 3))
    # Principal
    t_surf = title_font.render(title_text, True, (0, glow_val, 255))
    surf.blit(t_surf, (cx - t_surf.get_width() // 2 + (gx_off if glitch_on else 0), title_y))

    # Subtítulo parpadeante
    sub_alpha = int(140 + 80 * (math.sin(tick * 0.03) * 0.5 + 0.5))
    sub = sub_font.render("Sigilo sónico  ·  Sonar  ·  Supervivencia", True, (0, sub_alpha, int(sub_alpha * 1.1)))
    surf.blit(sub, (cx - sub.get_width() // 2, title_y + 62))

    # Línea separadora animada
    sep_w = int((panel_w - 60) * min(1.0, tick / 80))
    pygame.draw.line(surf, (0, 60, 90), (cx - (panel_w - 60) // 2, title_y + 88),
                     (cx + (panel_w - 60) // 2, title_y + 88), 1)
    pygame.draw.line(surf, CYAN, (cx - sep_w // 2, title_y + 88),
                     (cx + sep_w // 2, title_y + 88), 1)

    # ── Botones del menú ──────────────────────────────────────────────────
    mouse_pos = pygame.mouse.get_pos()
    btn_defs = [
        ("JUGAR",    "Comenzar partida"),
        ("NIVELES",  "Seleccionar nivel"),
        ("CONTROLES","Ver controles"),
        ("SALIR",    "Cerrar el juego"),
    ]
    btn_w, btn_h, btn_gap = min(320, panel_w - 80), 46, 10
    btns_total_h = len(btn_defs) * (btn_h + btn_gap) - btn_gap
    btn_start_y = title_y + 108
    btn_x = cx - btn_w // 2
    btn_rects = []

    for i, (label, hint) in enumerate(btn_defs):
        by = btn_start_y + i * (btn_h + btn_gap)
        brect = pygame.Rect(btn_x, by, btn_w, btn_h)
        btn_rects.append(brect)
        hovered  = brect.collidepoint(mouse_pos)
        selected = (i == menu_sel)
        pulse = math.sin(tick * 0.1 + i * 0.8) * 0.5 + 0.5

        # Fondo del botón
        if hovered or selected:
            bc = (0, int(160 + 60 * pulse), int(200 + 55 * pulse))
            ba = int(190 + 40 * pulse)
        else:
            bc = (0, 55, 80)
            ba = 120
        bs = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
        bs.fill((*bc, ba))
        surf.blit(bs, (btn_x, by))

        # Borde
        if hovered or selected:
            brd = (0, int(180 + 70 * pulse), 255)
            pygame.draw.rect(surf, brd, brect, 2)
            # Línea interior izquierda
            pygame.draw.line(surf, brd, (btn_x + 4, by + 6), (btn_x + 4, by + btn_h - 6), 2)
        else:
            pygame.draw.rect(surf, (0, 45, 65), brect, 1)

        # Indicador de selección (triángulo)
        if selected:
            tri_x = btn_x - 16
            tri_cy = by + btn_h // 2
            tri_sz = int(6 + 3 * pulse)
            pygame.draw.polygon(surf, (0, 220, 255),
                [(tri_x, tri_cy),
                 (tri_x - tri_sz, tri_cy - tri_sz),
                 (tri_x - tri_sz, tri_cy + tri_sz)])

        # Texto
        tc = WHITE if (hovered or selected) else (120, 180, 210)
        prefix = ">> " if (hovered or selected) else "   "
        lbl_s = btn_font.render(prefix + label, True, tc)
        surf.blit(lbl_s, (btn_x + 18, by + btn_h // 2 - lbl_s.get_height() // 2))

        # Hint a la derecha
        hint_s = tiny_font.render(hint, True, (50, 90, 120) if not (hovered or selected) else (80, 150, 180))
        surf.blit(hint_s, (btn_x + btn_w - hint_s.get_width() - 10,
                            by + btn_h // 2 - hint_s.get_height() // 2))

    # ── Panel créditos (si está activo) ──────────────────────────────────
    if show_credits:
        cr_w, cr_h = min(480, W - 80), 220
        cr_x, cr_y = cx - cr_w // 2, panel_y + panel_h + 14
        if cr_y + cr_h > H - 10:
            cr_y = panel_y - cr_h - 14
        crs = pygame.Surface((cr_w, cr_h), pygame.SRCALPHA)
        crs.fill((0, 15, 25, 220))
        surf.blit(crs, (cr_x, cr_y))
        pygame.draw.rect(surf, (0, 80, 120), (cr_x, cr_y, cr_w, cr_h), 2)
        try: hf = pygame.font.SysFont("consolas", 15, bold=True)
        except: hf = small_font
        ht = hf.render("CONTROLES", True, CYAN)
        surf.blit(ht, (cx - ht.get_width() // 2, cr_y + 12))
        pygame.draw.line(surf, DARK_CYAN, (cr_x + 20, cr_y + 34), (cr_x + cr_w - 20, cr_y + 34), 1)
        ctrl_lines = [
            ("WASD / Flechas", "Mover"),
            ("Shift",          "Caminar en sigilo"),
            ("Clic Izq",       "Pulso sonar"),
            ("Clic Der",       "Lanzar señuelo"),
            ("R",              "Reiniciar"),
            ("ESC",            "Volver al menú"),
        ]
        try: cf2 = pygame.font.SysFont("consolas", 13)
        except: cf2 = small_font
        for j, (k, v) in enumerate(ctrl_lines):
            ky = cr_y + 44 + j * 26
            ks = cf2.render(k, True, (0, 180, 220))
            vs = cf2.render(v, True, (150, 200, 220))
            surf.blit(ks, (cr_x + 20, ky))
            surf.blit(vs, (cr_x + 180, ky))

    # ── Recuadro de créditos (esquina inferior izquierda) ─────────────────
    try:
        cr_lbl_f = pygame.font.SysFont("consolas", 11, bold=True)
        cr_val_f = pygame.font.SysFont("consolas", 11)
    except:
        cr_lbl_f = cr_val_f = small_font

    credits_lines = [
        ("Diseño y código",  "Andres Carrillo"),
        ("Motor",            "Pygame 2 / Python 3"),
        ("Género",           "Sigilo · Sonar"),
        ("Versión",          "1.0  —  2026"),
    ]
    cr_pad = 10
    cr_line_h = 18
    cr_w = 230
    cr_h = cr_pad * 2 + 20 + len(credits_lines) * cr_line_h
    cr_margin = 14
    cr_x = cr_margin
    cr_y = H - cr_h - cr_margin

    # Fondo semitransparente
    cr_surf = pygame.Surface((cr_w, cr_h), pygame.SRCALPHA)
    cr_surf.fill((0, 12, 20, 200))
    surf.blit(cr_surf, (cr_x, cr_y))

    # Borde animado (mismo ritmo que el panel principal)
    cr_bv = int(60 + 80 * (math.sin(tick * 0.045 + 1.2) * 0.5 + 0.5))
    pygame.draw.rect(surf, (0, cr_bv, min(255, cr_bv + 50)), (cr_x, cr_y, cr_w, cr_h), 1)

    # Esquinas pequeñas
    cr_csz = 6
    cr_cv = int(100 + 100 * (math.sin(tick * 0.07 + 0.5) * 0.5 + 0.5))
    for qx, qy in [(cr_x, cr_y), (cr_x + cr_w - cr_csz, cr_y),
                   (cr_x, cr_y + cr_h - cr_csz), (cr_x + cr_w - cr_csz, cr_y + cr_h - cr_csz)]:
        pygame.draw.rect(surf, (0, cr_cv, 200), (qx, qy, cr_csz, cr_csz), 1)

    # Encabezado con ícono de sonar
    sonar_cx = cr_x + 14
    sonar_cy = cr_y + cr_pad + 6
    sonar_r = int(4 + 2 * (math.sin(tick * 0.08) * 0.5 + 0.5))
    pygame.draw.circle(surf, (0, cr_cv, 200), (sonar_cx, sonar_cy), sonar_r, 1)
    pygame.draw.circle(surf, (0, cr_cv // 2, 120), (sonar_cx, sonar_cy), sonar_r + 3, 1)

    hdr = cr_lbl_f.render("CRÉDITOS", True, (0, cr_cv, 200))
    surf.blit(hdr, (sonar_cx + 12, cr_y + cr_pad))

    # Línea separadora
    pygame.draw.line(surf, (0, cr_bv // 2, cr_bv // 2),
                     (cr_x + 8, cr_y + cr_pad + 17),
                     (cr_x + cr_w - 8, cr_y + cr_pad + 17), 1)

    # Líneas de créditos
    for j, (lbl, val) in enumerate(credits_lines):
        ly = cr_y + cr_pad + 22 + j * cr_line_h
        ls = cr_lbl_f.render(lbl + ":", True, (0, 140, 180))
        vs = cr_val_f.render(val, True, (130, 190, 210))
        surf.blit(ls, (cr_x + 10, ly))
        surf.blit(vs, (cr_x + 10 + ls.get_width() + 4, ly))

    # ── Tip inferior ─────────────────────────────────────────────────────
    try: tip_f = pygame.font.SysFont("consolas", 12)
    except: tip_f = small_font
    tip = tip_f.render("Flechas: navegar  |  Enter: seleccionar  |  ESC: salir", True, (40, 65, 80))
    surf.blit(tip, (cx - tip.get_width() // 2, H - 18))

    # ── Versión ───────────────────────────────────────────────────────────
    ver = tip_f.render("v2.0  |  ECO-CEGUERA", True, (25, 45, 60))
    surf.blit(ver, (panel_x + panel_w - ver.get_width() - 6, panel_y + panel_h - 18))

    # Retorna los 4 rects (jugar, niveles, controles, salir)
    while len(btn_rects) < 4:
        btn_rects.append(pygame.Rect(0, 0, 0, 0))
    return tuple(btn_rects[:4])


#  Pantalla de selección de nivel 

def draw_level_select(surf, tick, sel, max_unlocked, font, small_font):
    """Renders level select. Returns (card_rects, play_rect)."""
    surf.fill(BLACK)
    cx = W // 2
    for i in range(4):
        phase = (tick * 1.5 + i * 90) % 360
        rad = int((phase / 360) * max(W, H) * 0.9)
        af  = 1.0 - phase / 360
        if rad > 0:
            pygame.draw.circle(surf, (0, int(220*af), int(255*af)), (cx, H//2), rad, 1)
    for gx in range(0, W, TILE): pygame.draw.line(surf, (8,15,20), (gx,0), (gx,H))
    for gy in range(0, H, TILE): pygame.draw.line(surf, (8,15,20), (0,gy), (W,gy))

    try:  tf = pygame.font.SysFont("consolas", 30, bold=True)
    except: tf = font
    gv = int(160 + 80*(math.sin(tick*0.05)*0.5+0.5))
    ts = tf.render("SELECCIONAR NIVEL", True, (0, gv, gv))
    surf.blit(ts, (cx - ts.get_width()//2, 18))

    card_w, card_h, gap = 780, 72, 8
    card_x = cx - card_w // 2
    card_y0 = 66
    mouse   = pygame.mouse.get_pos()
    card_rects = []
    mech_labels = {'timer':'CRONOMETRO', 'respawn_traps':'TRAMPAS VIVAS', 'blackout':'APAGON'}

    for i, cfg in enumerate(LEVEL_CONFIGS):
        cy2  = card_y0 + i * (card_h + gap)
        rect = pygame.Rect(card_x, cy2, card_w, card_h)
        card_rects.append(rect)
        locked   = i > max_unlocked
        hovered  = rect.collidepoint(mouse) and not locked
        selected = (i == sel)

        bg_a = 200 if selected else 160
        bg_r, bg_g, bg_b = (0,40,60) if selected else (5,20,30)
        cs = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        cs.fill((bg_r, bg_g, bg_b, bg_a if not locked else 80))
        surf.blit(cs, (card_x, cy2))

        if selected and not locked:
            bv = int(130 + 110*(math.sin(tick*0.1)*0.5+0.5))
            border = (0, bv, 255)
        elif hovered: border = (0,110,170)
        elif locked:  border = (25,35,45)
        else:         border = (0,55,75)
        pygame.draw.rect(surf, border, rect, 2)

        # Badge number
        bc = (0,80,110) if selected and not locked else (40,50,60) if locked else (0,50,70)
        pygame.draw.rect(surf, bc, (card_x+6, cy2+6, 54, card_h-12))
        ns = font.render(f"{i+1}", True, (70,80,90) if locked else CYAN)
        surf.blit(ns, (card_x+6+27-ns.get_width()//2, cy2+card_h//2-ns.get_height()//2))

        # Name
        nc = (35,45,55) if locked else (WHITE if selected else (170,205,225))
        try: nf = pygame.font.SysFont("consolas",17,bold=True)
        except: nf = small_font
        nm = nf.render(("[BLOQUEADO]  " if locked else "") + cfg['name'], True, nc)
        surf.blit(nm, (card_x+70, cy2+9))
        sc = (25,35,45) if locked else (100,145,165)
        ss = small_font.render(cfg['subtitle'], True, sc)
        surf.blit(ss, (card_x+70, cy2+34))

        mech = cfg.get('mechanic')
        if mech and not locked:
            ml = small_font.render(mech_labels.get(mech,''), True, ORANGE)
            surf.blit(ml, (card_x+card_w-ml.get_width()-10, cy2+card_h//2-ml.get_height()//2))

    # PLAY button
    py0 = card_y0 + N_LEVELS*(card_h+gap) + 10
    play_rect = pygame.Rect(cx-110, py0, 220, 44)
    can_play  = sel <= max_unlocked
    ph = play_rect.collidepoint(mouse) and can_play
    pc = (0,210,255) if ph else ((0,140,180) if can_play else (40,50,60))
    ps = pygame.Surface((220,44), pygame.SRCALPHA)
    ps.fill((*pc, 210 if ph else 140))
    surf.blit(ps, (cx-110, py0))
    pygame.draw.rect(surf, pc, play_rect, 2)
    try: bf = pygame.font.SysFont("consolas",18,bold=True)
    except: bf = font
    bl = bf.render(">> JUGAR <<" if ph else "[ JUGAR ]", True, WHITE if can_play else (60,70,80))
    surf.blit(bl, (cx-bl.get_width()//2, py0+22-bl.get_height()//2))

    tip = small_font.render("Click en un nivel para seleccionar  |  ESC: menu principal", True, (55,80,95))
    surf.blit(tip, (cx-tip.get_width()//2, H-22))
    return card_rects, play_rect


def draw_level_complete(surf, tick, font, level_idx, score=0, pulse_count=0, elapsed_ticks=0):
    """Overlay shown when the player escapes. Returns continue_rect."""
    cx, cy = W//2, H//2

    # Fondo oscuro verde
    ov = pygame.Surface((W, H), pygame.SRCALPHA)
    ov.fill((0, 20, 8, 200))
    surf.blit(ov, (0, 0))

    # Anillos expansivos de victoria
    for i in range(6):
        phase = (tick * 1.2 + i * 52) % 360
        rad = int((phase / 360) * max(W, H) * 0.75)
        af  = 1.0 - phase / 360
        col = (0, int(220 * af), int(90 * af))
        if rad > 0:
            pygame.draw.circle(surf, col, (cx, cy), rad, 1)

    # Panel glassmorphism
    pw, ph2 = min(540, W - 60), 300
    px2, py2 = cx - pw//2, cy - ph2//2
    ps = pygame.Surface((pw, ph2), pygame.SRCALPHA)
    ps.fill((0, 30, 15, 215))
    surf.blit(ps, (px2, py2))
    bv = int(120 + 110*(math.sin(tick*0.07)*0.5+0.5))
    pygame.draw.rect(surf, (0, bv, int(bv*0.45)), (px2, py2, pw, ph2), 2)
    csz = 12
    for qx, qy in [(px2, py2), (px2+pw-csz, py2), (px2, py2+ph2-csz), (px2+pw-csz, py2+ph2-csz)]:
        pygame.draw.rect(surf, (0, 220, 100), (qx, qy, csz, csz), 2)

    # Título
    try: tf = pygame.font.SysFont("consolas", 40, bold=True)
    except: tf = font
    gv = int(150 + 100*(math.sin(tick*0.08)*0.5+0.5))
    sh = tf.render("NIVEL COMPLETADO", True, (0, gv//4, gv//8))
    surf.blit(sh, (cx - sh.get_width()//2 + 3, py2 + 22 + 3))
    t1 = tf.render("NIVEL COMPLETADO", True, (0, gv, int(gv*0.45)))
    surf.blit(t1, (cx - t1.get_width()//2, py2 + 22))

    # Separador
    pygame.draw.line(surf, (0, 80, 40), (px2+24, py2+82), (px2+pw-24, py2+82), 1)
    sep_w = int((pw-48) * min(1.0, tick/60))
    pygame.draw.line(surf, GREEN, (cx - sep_w//2, py2+82), (cx + sep_w//2, py2+82), 1)

    cfg = LEVEL_CONFIGS[level_idx]
    try: sf = pygame.font.SysFont("consolas", 15)
    except: sf = font

    # Nombre del nivel
    n2 = sf.render(f"Nivel {level_idx+1}  —  {cfg['name']}", True, (120, 220, 150))
    surf.blit(n2, (cx - n2.get_width()//2, py2 + 98))

    # Siguiente nivel
    is_last = level_idx >= N_LEVELS - 1
    next_txt = "¡Has completado el juego!" if is_last else f"Siguiente:  {LEVEL_CONFIGS[level_idx+1]['name']}"
    nx_col = GOLD if is_last else (100, 180, 130)
    nx = sf.render(next_txt, True, nx_col)
    surf.blit(nx, (cx - nx.get_width()//2, py2 + 112))

    # Desglose de puntuación
    time_bonus = max(0, 3000 - elapsed_ticks // 2)
    pulse_pen  = pulse_count * 80
    lvl_bonus  = level_idx * 500
    try: bf2 = pygame.font.SysFont("consolas", 13)
    except: bf2 = sf
    score_lines = [
        ("Base",         5000,       CYAN),
        ("Velocidad",    time_bonus, GREEN),
        ("Pulsos  -",    pulse_pen,  ORANGE),
        ("Nivel   +",    lvl_bonus,  GOLD),
        ("TOTAL",        score,      WHITE),
    ]
    sc_y = py2 + 140
    pygame.draw.line(surf, (0,60,40), (px2+24, sc_y-4), (px2+pw-24, sc_y-4), 1)
    for label, val, col in score_lines:
        lbl_s = bf2.render(label, True, (80, 140, 110))
        val_s = bf2.render(f"{val:,}", True, col)
        surf.blit(lbl_s, (cx - 120, sc_y))
        surf.blit(val_s, (cx + 40,  sc_y))
        sc_y += 18
    pygame.draw.line(surf, (0,60,40), (px2+24, sc_y-2), (px2+pw-24, sc_y-2), 1)

    # Botón CONTINUAR
    mouse = pygame.mouse.get_pos()
    cont = pygame.Rect(cx - 140, py2 + ph2 - 68, 280, 46)
    mh   = cont.collidepoint(mouse)
    pulse = math.sin(tick * 0.1) * 0.5 + 0.5
    cc   = (0, int(180+60*pulse), int(80+30*pulse)) if mh else (0, 140, 60)
    cs2  = pygame.Surface((280, 46), pygame.SRCALPHA)
    cs2.fill((*cc, 210 if mh else 150))
    surf.blit(cs2, cont.topleft)
    pygame.draw.rect(surf, cc, cont, 2)
    if mh:
        pygame.draw.line(surf, cc, (cont.x+4, cont.y+6), (cont.x+4, cont.y+cont.h-6), 2)
    try: bf = pygame.font.SysFont("consolas", 17, bold=True)
    except: bf = font
    lbl = ">> CONTINUAR <<" if mh else "[ CONTINUAR ]"
    bl = bf.render(lbl, True, WHITE)
    surf.blit(bl, (cx - bl.get_width()//2, cont.y + cont.h//2 - bl.get_height()//2))

    try: tip_f = pygame.font.SysFont("consolas", 12)
    except: tip_f = font
    tip = tip_f.render("Enter / Espacio para continuar", True, (40, 80, 50))
    surf.blit(tip, (cx - tip.get_width()//2, py2 + ph2 - 16))
    return cont


#  HUD 

def draw_hud(surf, font, small_font, decoys, alert_count, caught, won, level_idx=0, level_timer=0, mech=None, tick=0, score=0, pulse_count=0):

    # Panel superior
    pygame.draw.rect(surf, (10, 20, 30), (0, 0, W, 36))
    pygame.draw.line(surf, DARK_CYAN, (0, 36), (W, 36), 1)

    lbl = font.render(f"ECO-CEGUERA  N{level_idx+1}", True, CYAN)
    surf.blit(lbl, (12, 8))

    decoy_txt = small_font.render(f"Señuelos: {'[ ]' * decoys}  (clic der)", True, PURPLE)
    surf.blit(decoy_txt, (lbl.get_width() + 24, 10))

    # Puntuación en la esquina derecha del HUD
    try: sc_f = pygame.font.SysFont("consolas", 13, bold=True)
    except: sc_f = small_font
    sc_col = GOLD
    sc_txt = sc_f.render(f"SCORE {score:,}  |  PULSOS {pulse_count}", True, sc_col)
    surf.blit(sc_txt, (W - sc_txt.get_width() - 12, 10))

    if mech == 'timer' and level_timer > 0:
        secs = level_timer // FPS
        tcol = RED if secs < 20 else ORANGE if secs < 40 else GOLD
        tt = font.render(f"TIEMPO: {secs:02d}s", True, tcol)
        surf.blit(tt, (W//2 - tt.get_width()//2, 8))
    elif alert_count > 0:
        alert_txt = small_font.render(f"! {alert_count} enemigo(s) en alerta !", True, ORANGE)
        surf.blit(alert_txt, (W//2 - alert_txt.get_width()//2, 8))

    controls = small_font.render("WASD: mover  |  Shift: sigilo  |  Clic Izq: sonar  |  R: reiniciar  |  ESC: menu", True, (80, 120, 140))
    surf.blit(controls, (12, H - 22))

    if caught:
        cx2, cy2 = W // 2, H // 2
        # Fondo rojo oscuro pulsante
        pulse2 = math.sin(tick * 0.07 if tick else 0) * 0.5 + 0.5
        ov2 = pygame.Surface((W, H), pygame.SRCALPHA)
        ov2.fill((int(160 + 40*pulse2), 0, 0, 160))
        surf.blit(ov2, (0, 0))

        # Panel glassmorphism rojo
        pw3, ph3 = min(500, W - 60), 230
        px3, py3 = cx2 - pw3//2, cy2 - ph3//2
        ps3 = pygame.Surface((pw3, ph3), pygame.SRCALPHA)
        ps3.fill((40, 0, 0, 220))
        surf.blit(ps3, (px3, py3))
        rv = int(140 + 100*pulse2)
        pygame.draw.rect(surf, (rv, 0, 0), (px3, py3, pw3, ph3), 2)
        csz2 = 10
        for qx, qy in [(px3, py3), (px3+pw3-csz2, py3), (px3, py3+ph3-csz2), (px3+pw3-csz2, py3+ph3-csz2)]:
            pygame.draw.rect(surf, (220, 0, 0), (qx, qy, csz2, csz2), 2)

        # Título
        try: df = pygame.font.SysFont("consolas", 38, bold=True)
        except: df = font
        tv = int(180 + 70*pulse2)
        sh2 = df.render("ATRAPADO", True, (tv//4, 0, 0))
        surf.blit(sh2, (cx2 - sh2.get_width()//2 + 3, py3 + 24 + 3))
        t2 = df.render("ATRAPADO", True, (tv, 0, 0))
        surf.blit(t2, (cx2 - t2.get_width()//2, py3 + 24))

        pygame.draw.line(surf, (80, 0, 0), (px3+20, py3+78), (px3+pw3-20, py3+78), 1)

        try: sf2 = pygame.font.SysFont("consolas", 14)
        except: sf2 = font
        sub2 = sf2.render("Los enemigos te han detectado", True, (200, 80, 80))
        surf.blit(sub2, (cx2 - sub2.get_width()//2, py3 + 92))

        # Botones: Reintentar | Menú
        mouse2 = pygame.mouse.get_pos()
        bw, bh, bgap = 180, 42, 14
        total = bw*2 + bgap
        by3 = py3 + ph3 - 64

        r_rect = pygame.Rect(cx2 - total//2, by3, bw, bh)
        m_rect = pygame.Rect(cx2 - total//2 + bw + bgap, by3, bw, bh)

        for brect, label in [(r_rect, "REINTENTAR"), (m_rect, "MENU")]:
            hov = brect.collidepoint(mouse2)
            bc2 = (rv, int(rv*0.3), 0) if (hov and label=="REINTENTAR") else \
                  (int(rv*0.5), int(rv*0.5), int(rv*0.5)) if hov else \
                  (100, 20, 0) if label=="REINTENTAR" else (40, 40, 50)
            bs2 = pygame.Surface((bw, bh), pygame.SRCALPHA)
            bs2.fill((*bc2, 200 if hov else 140))
            surf.blit(bs2, brect.topleft)
            pygame.draw.rect(surf, bc2, brect, 2)
            try: bf2 = pygame.font.SysFont("consolas", 14, bold=True)
            except: bf2 = font
            lbl2 = (">> " if hov else "[ ") + label + (" <<" if hov else " ]")
            lb2 = bf2.render(lbl2, True, WHITE)
            surf.blit(lb2, (brect.centerx - lb2.get_width()//2,
                            brect.centery - lb2.get_height()//2))

        try: tip_f2 = pygame.font.SysFont("consolas", 12)
        except: tip_f2 = font
        tip2 = tip_f2.render("R: reintentar  |  ESC: menú", True, (100, 30, 30))
        surf.blit(tip2, (cx2 - tip2.get_width()//2, py3 + ph3 - 14))



#  Loop principal 

async def main():
    global W, H
    pygame.init()
    _init_sounds()
    clock = pygame.time.Clock()
    pygame.display.set_caption("Eco-Ceguera")
    IS_WEB = sys.platform == 'emscripten'

    try:
        font       = pygame.font.SysFont("consolas", 20, bold=True)
        small_font = pygame.font.SysFont("consolas", 14)
    except Exception:
        font       = pygame.font.Font(None, 24)
        small_font = pygame.font.Font(None, 16)

    # ── Resolution setup ──────────────────────────────────────────────────
    if IS_WEB:
        try:
            info = pygame.display.Info()
            W, H = max(800, info.current_w), max(500, info.current_h)
        except Exception:
            W, H = 900, 600
        screen    = pygame.display.set_mode((W, H))
        state     = 'intro'
        valid_res = []; sel_res = 0; native_w = native_h = 0
    else:
        try:
            desktop = pygame.display.get_desktop_sizes()
            native_w, native_h = desktop[0]
        except Exception:
            native_w, native_h = 1920, 1080
        _res_list = [
            (800,  500,  "800 × 500    Pequeño"),
            (1024, 640,  "1024 × 640   Mediano"),
            (1280, 720,  "1280 × 720   HD"),
            (1600, 900,  "1600 × 900   HD+"),
            (1920, 1080, "1920 × 1080  Full HD"),
            (native_w, native_h, f"Pantalla completa  ({native_w}×{native_h})"),
        ]
        seen = set(); valid_res = []
        for r in _res_list:
            k = (r[0], r[1])
            if k not in seen and r[0] <= native_w and r[1] <= native_h:
                seen.add(k); valid_res.append(r)
        sel_res = min(2, len(valid_res) - 1)
        screen  = pygame.display.set_mode((900, 580))
        state   = 'res'

    HUD_TOP = 38
    VIEW_W  = W
    VIEW_H  = H - HUD_TOP - 24

    # ── Progression ───────────────────────────────────────────────────────
    current_level = 0
    max_unlocked  = 0

    # ── Game state placeholders ───────────────────────────────────────────
    walls = enemies = player = pulses = exit_rect = traps = wall_grid = None
    decoys = micro_pulse_timer = tick = 0
    lv_timer = trap_respawn_cd = blackout_cd = 0
    mech = active_cfg = None
    intro_tick = res_tick = ls_tick = comp_tick = 0
    menu_sel = 0
    show_credits = False
    score = 0
    pulse_count = 0
    game_ticks = 0
    sfx_played = False   # evita repetir el sonido de victoria/derrota

    def new_game(level):
        global REVEAL_DURATION, SONAR_MAX_RADIUS, MICRO_PULSE_INTERVAL
        global ENEMY_SPEED_BASE, ENEMY_ALERT_SPEED
        cfg = LEVEL_CONFIGS[level]
        REVEAL_DURATION      = cfg['reveal_dur']
        SONAR_MAX_RADIUS     = cfg['sonar_radius']
        MICRO_PULSE_INTERVAL = cfg['micro_interval']
        ENEMY_SPEED_BASE     = round(cfg['spd_mult'] * 0.9, 2)
        ENEMY_ALERT_SPEED    = round(cfg['spd_mult'] * 2.2, 2)
        w2, e2, ppos, ex, tr, wg = build_map(cfg)
        m   = cfg.get('mechanic')
        lt  = cfg.get('timer_secs', 0) * FPS if m == 'timer' else 0
        trc = cfg.get('respawn_frames', 900) if m == 'respawn_traps' else 0
        bc  = cfg.get('blackout_interval', 900) if m == 'blackout' else 0
        return (w2, e2, Player(*ppos), [], DECOY_COUNT, 0, ex, tr, 0, wg, lt, trc, bc, m, cfg)

    def calc_score(elapsed_ticks, pulses_used, level):
        """Calcula la puntuación al completar un nivel."""
        base        = 5000
        time_bonus  = max(0, 3000 - elapsed_ticks // 2)  # hasta 3000 pts por velocidad
        pulse_pen   = pulses_used * 80                    # -80 pts por pulso usado
        level_bonus = level * 500
        return max(0, base + time_bonus - pulse_pen + level_bonus)

    # ── Main async loop ───────────────────────────────────────────────────
    running = True
    while running:
        clock.tick(FPS)
        events = pygame.event.get()

        # global quit
        for ev in events:
            if ev.type == pygame.QUIT:
                running = False

        if not running:
            break

        # ════ RESOLUTION PICKER ══════════════════════════════════════════
        if state == 'res':
            res_tick += 1
            for ev in events:
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
                    if ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                        rw, rh, _ = valid_res[sel_res]
                        W, H = rw, rh
                        flags = pygame.FULLSCREEN if (rw == native_w and rh == native_h) else 0
                        screen = pygame.display.set_mode((W, H), flags)
                        VIEW_W = W; VIEW_H = H - HUD_TOP - 24
                        state = 'intro'
                    if ev.key == pygame.K_UP:   sel_res = max(0, sel_res - 1)
                    if ev.key == pygame.K_DOWN: sel_res = min(len(valid_res)-1, sel_res+1)
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    crects, ok_r = draw_resolution_select(screen, res_tick, sel_res, valid_res, font, small_font)
                    for i, r in enumerate(crects):
                        if r.collidepoint(ev.pos): sel_res = i
                    if ok_r.collidepoint(ev.pos):
                        rw, rh, _ = valid_res[sel_res]
                        W, H = rw, rh
                        flags = pygame.FULLSCREEN if (rw == native_w and rh == native_h) else 0
                        screen = pygame.display.set_mode((W, H), flags)
                        VIEW_W = W; VIEW_H = H - HUD_TOP - 24
                        state = 'intro'
                if ev.type == pygame.FINGERDOWN:
                    sx, sy = int(ev.x * 900), int(ev.y * 580)
                    crects, ok_r = draw_resolution_select(screen, res_tick, sel_res, valid_res, font, small_font)
                    for i, r in enumerate(crects):
                        if r.collidepoint((sx, sy)): sel_res = i
                    if ok_r.collidepoint((sx, sy)):
                        rw, rh, _ = valid_res[sel_res]
                        W, H = rw, rh; screen = pygame.display.set_mode((W, H))
                        VIEW_W = W; VIEW_H = H - HUD_TOP - 24
                        state = 'intro'
            draw_resolution_select(screen, res_tick, sel_res, valid_res, font, small_font)
            pygame.display.flip()
            await asyncio.sleep(0); continue

        # ════ INTRO ══════════════════════════════════════════════════════
        if state == 'intro':
            intro_tick += 1
            _MENU_OPTS = 4  # Jugar, Niveles, Controles, Salir
            for ev in events:
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        pygame.quit(); sys.exit()
                    if ev.key == pygame.K_UP:
                        menu_sel = (menu_sel - 1) % _MENU_OPTS
                        show_credits = False
                    if ev.key == pygame.K_DOWN:
                        menu_sel = (menu_sel + 1) % _MENU_OPTS
                        show_credits = False
                    if ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if menu_sel == 0:   # Jugar
                            state = 'ls'
                        elif menu_sel == 1: # Niveles
                            state = 'ls'
                        elif menu_sel == 2: # Controles
                            show_credits = not show_credits
                        elif menu_sel == 3: # Salir
                            pygame.quit(); sys.exit()
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    rects = draw_start_screen(screen, font, small_font, intro_tick, menu_sel, show_credits)
                    if rects[0].collidepoint(ev.pos):   # Jugar
                        state = 'ls'
                    elif rects[1].collidepoint(ev.pos): # Niveles
                        state = 'ls'
                    elif rects[2].collidepoint(ev.pos): # Controles
                        show_credits = not show_credits
                    elif rects[3].collidepoint(ev.pos): # Salir
                        pygame.quit(); sys.exit()
                    else:
                        for i, r in enumerate(rects):
                            if r.collidepoint(ev.pos):
                                menu_sel = i
                if ev.type == pygame.FINGERDOWN:
                    sx, sy = int(ev.x * W), int(ev.y * H)
                    rects = draw_start_screen(screen, font, small_font, intro_tick, menu_sel, show_credits)
                    if rects[0].collidepoint((sx,sy)): state = 'ls'
                    elif rects[1].collidepoint((sx,sy)): state = 'ls'
                    elif rects[2].collidepoint((sx,sy)): show_credits = not show_credits
                    elif rects[3].collidepoint((sx,sy)): pygame.quit(); sys.exit()
            draw_start_screen(screen, font, small_font, intro_tick, menu_sel, show_credits)
            pygame.display.flip()
            await asyncio.sleep(0); continue

        # ════ LEVEL SELECT ════════════════════════════════════════════════
        if state == 'ls':
            ls_tick += 1
            for ev in events:
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE: state = 'intro'; show_credits = False
                    if ev.key == pygame.K_UP:   current_level = max(0, current_level - 1)
                    if ev.key == pygame.K_DOWN: current_level = min(max_unlocked, current_level + 1)
                    if ev.key in (pygame.K_RETURN, pygame.K_SPACE) and current_level <= max_unlocked:
                        (walls, enemies, player, pulses, decoys, tick, exit_rect,
                         traps, micro_pulse_timer, wall_grid,
                         lv_timer, trap_respawn_cd, blackout_cd, mech, active_cfg) = new_game(current_level)
                        score = 0; pulse_count = 0; game_ticks = 0
                        state = 'play'
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    crects, play_r = draw_level_select(screen, ls_tick, current_level, max_unlocked, font, small_font)
                    for i, r in enumerate(crects):
                        if r.collidepoint(ev.pos) and i <= max_unlocked: current_level = i
                    if play_r.collidepoint(ev.pos) and current_level <= max_unlocked:
                        (walls, enemies, player, pulses, decoys, tick, exit_rect,
                         traps, micro_pulse_timer, wall_grid,
                         lv_timer, trap_respawn_cd, blackout_cd, mech, active_cfg) = new_game(current_level)
                        score = 0; pulse_count = 0; game_ticks = 0
                        state = 'play'
                if ev.type == pygame.FINGERDOWN:
                    sx, sy = int(ev.x * W), int(ev.y * H)
                    crects, play_r = draw_level_select(screen, ls_tick, current_level, max_unlocked, font, small_font)
                    for i, r in enumerate(crects):
                        if r.collidepoint((sx, sy)) and i <= max_unlocked: current_level = i
                    if play_r.collidepoint((sx, sy)) and current_level <= max_unlocked:
                        (walls, enemies, player, pulses, decoys, tick, exit_rect,
                         traps, micro_pulse_timer, wall_grid,
                         lv_timer, trap_respawn_cd, blackout_cd, mech, active_cfg) = new_game(current_level)
                        state = 'play'
            draw_level_select(screen, ls_tick, current_level, max_unlocked, font, small_font)
            pygame.display.flip()
            await asyncio.sleep(0); continue

        # ════ LEVEL COMPLETE ══════════════════════════════════════════════
        if state == 'comp':
            comp_tick += 1
            for ev in events:
                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                        current_level = min(current_level + 1, N_LEVELS - 1)
                        state = 'ls'; ls_tick = 0
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    cont = draw_level_complete(screen, comp_tick, font, current_level,
                                               score, pulse_count, game_ticks)
                    if cont.collidepoint(ev.pos):
                        current_level = min(current_level + 1, N_LEVELS - 1)
                        state = 'ls'; ls_tick = 0
            draw_level_complete(screen, comp_tick, font, current_level,
                                score, pulse_count, game_ticks)
            pygame.display.flip()
            await asyncio.sleep(0); continue

        # ════ GAMEPLAY ════════════════════════════════════════════════════
        tick += 1

        for ev in events:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: state = 'ls'; ls_tick = 0
                if ev.key == pygame.K_r:
                    (walls, enemies, player, pulses, decoys, tick, exit_rect,
                     traps, micro_pulse_timer, wall_grid,
                     lv_timer, trap_respawn_cd, blackout_cd, mech, active_cfg) = new_game(current_level)
                    score = 0; pulse_count = 0; game_ticks = 0
            # Mouse: clic en botones de derrota
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and player.caught:
                cx_d, cy_d = W // 2, H // 2
                pw3d, ph3d = min(500, W - 60), 230
                py3d = cy_d - ph3d // 2
                bw_d, bh_d, bgap_d = 180, 42, 14
                total_d = bw_d * 2 + bgap_d
                by3d = py3d + ph3d - 64
                r_rect_d = pygame.Rect(cx_d - total_d//2, by3d, bw_d, bh_d)
                m_rect_d = pygame.Rect(cx_d - total_d//2 + bw_d + bgap_d, by3d, bw_d, bh_d)
                if r_rect_d.collidepoint(ev.pos):  # Reintentar
                    (walls, enemies, player, pulses, decoys, tick, exit_rect,
                     traps, micro_pulse_timer, wall_grid,
                     lv_timer, trap_respawn_cd, blackout_cd, mech, active_cfg) = new_game(current_level)
                    score = 0; pulse_count = 0; game_ticks = 0
                elif m_rect_d.collidepoint(ev.pos):  # Menú
                    state = 'ls'; ls_tick = 0
            # Mouse: sonar / decoy
            if ev.type == pygame.MOUSEBUTTONDOWN and not player.caught and not player.won:
                ox = int(max(0, min(player.x - VIEW_W//2, MAP_W - VIEW_W)))
                oy = int(max(0, min(player.y - VIEW_H//2, MAP_H - VIEW_H)))
                wx = ev.pos[0] + ox
                wy = (ev.pos[1] - HUD_TOP) + oy
                if ev.button == 1:
                    pulses.append(SonarPulse(player.x, player.y, CYAN))
                    pulse_count += 1
                    play_sound(_snd_sonar)
                elif ev.button == 3 and decoys > 0:
                    pulses.append(SonarPulse(wx, wy, PURPLE, is_decoy=True))
                    for e in enemies:
                        if dist((e.x,e.y),(wx,wy)) < SONAR_MAX_RADIUS: e.alert(wx, wy)
                    decoys -= 1
                    play_sound(_snd_sonar)


        # Movement (keyboard)
        if not player.caught and not player.won:
            keys     = pygame.key.get_pressed()
            sneaking = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
            dx = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - \
                 int(keys[pygame.K_a] or keys[pygame.K_LEFT])
            dy = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - \
                 int(keys[pygame.K_w] or keys[pygame.K_UP])
            if dx or dy:
                ndx, ndy = normalize(dx, dy)
                player.move(ndx, ndy, walls, sneaking)
                if not sneaking:
                    micro_pulse_timer += 1
                    if micro_pulse_timer >= MICRO_PULSE_INTERVAL:
                        micro_pulse_timer = 0
                        pulses.append(SonarPulse(player.x, player.y, (0,100,130), max_radius=60))
                else:
                    micro_pulse_timer = 0
            else:
                micro_pulse_timer = 0

            if exit_rect and pygame.Rect(player.x-PLAYER_RADIUS, player.y-PLAYER_RADIUS,
                                         PLAYER_RADIUS*2, PLAYER_RADIUS*2).colliderect(exit_rect.rect):
                player.won = True

        # Level mechanics
        if not player.caught and not player.won:
            if mech == 'timer' and lv_timer > 0:
                lv_timer -= 1
                if lv_timer <= 0: player.caught = True
            elif mech == 'respawn_traps' and trap_respawn_cd > 0:
                trap_respawn_cd -= 1
                if trap_respawn_cd <= 0:
                    trap_respawn_cd = active_cfg.get('respawn_frames', 900)
                    for trap in traps: trap.triggered = False
            elif mech == 'blackout' and blackout_cd > 0:
                blackout_cd -= 1
                if blackout_cd <= 0:
                    blackout_cd = active_cfg.get('blackout_interval', 900)
                    for w in walls: w.reveal = 0
                    for e in enemies: e.reveal = 0
                    if exit_rect: exit_rect.revealed = 0

        if not player.caught and not player.won:
            game_ticks += 1

        if player.won and state == 'play':
            max_unlocked = max(max_unlocked, current_level + 1)
            score = calc_score(game_ticks, pulse_count, current_level)
            if not sfx_played:
                play_sound(_snd_win)
                sfx_played = True
            state = 'comp'; comp_tick = 0
            await asyncio.sleep(0); continue

        if player.caught and not sfx_played:
            play_sound(_snd_lose)
            sfx_played = True

        # Pulses
        new_from = []
        for p in pulses:
            ex2 = p.update(walls, enemies, exit_rect, player)
            if ex2: new_from.extend(ex2)
        pulses = [p for p in pulses if not p.dead]
        pulses.extend(new_from)

        for w in walls: w.update()

        if not player.caught and not player.won:
            for e in enemies:
                res = e.update(walls, player, enemies, wall_grid)
                if res is not None: pulses.append(res)
            for e in enemies:
                if isinstance(e, HeavyEnemy):
                    for p in pulses:
                        if not p.is_decoy and not p.catches_player:
                            if dist((e.x,e.y),(p.x,p.y)) < HEAVY_HEAR_RADIUS:
                                e.alert(p.x,p.y); break
            for trap in traps:
                tp = trap.check(player)
                if tp is not None:
                    pulses.append(tp)
                    for e in enemies: e.alert(trap.cx, trap.cy)
                    play_sound(_snd_trap)

        # Camera
        off_x = int(max(0, min(player.x - VIEW_W//2, MAP_W - VIEW_W)))
        off_y = int(max(0, min(player.y - VIEW_H//2, MAP_H - VIEW_H)))
        offset = (off_x, off_y)

        # Draw
        screen.fill(BLACK)
        game_surf = pygame.Surface((VIEW_W, VIEW_H))
        game_surf.fill(BLACK)

        for gx in range(0, MAP_W, TILE):
            sx = gx - off_x
            if 0 <= sx <= VIEW_W: pygame.draw.line(game_surf, (8,15,20), (sx,0), (sx,VIEW_H))
        for gy in range(0, MAP_H, TILE):
            sy = gy - off_y
            if 0 <= sy <= VIEW_H: pygame.draw.line(game_surf, (8,15,20), (0,sy), (VIEW_W,sy))

        for w in walls: w.draw(game_surf, offset)

        if exit_rect and exit_rect.revealed > 0:
            exit_rect.revealed -= 1
            alpha = min(1.0, exit_rect.revealed / 20)
            blink = (math.sin(tick * 0.15) + 1) / 2
            col   = lerp_color(BLACK, GOLD, alpha * blink)
            er    = pygame.Rect(exit_rect.rect.x-off_x, exit_rect.rect.y-off_y,
                                exit_rect.rect.w, exit_rect.rect.h)
            pygame.draw.rect(game_surf, col, er)
            pygame.draw.rect(game_surf, GOLD, er, 2)

        for trap in traps: trap.draw(game_surf, offset)
        for p in pulses:   p.draw(game_surf, offset)
        for e in enemies:  e.draw(game_surf, offset)
        player.draw(game_surf, offset)

        screen.blit(game_surf, (0, HUD_TOP))

        alert_count = sum(1 for e in enemies if e.alert_t > 0)
        draw_hud(screen, font, small_font, decoys, alert_count,
                 player.caught, player.won, current_level, lv_timer, mech, tick,
                 score, pulse_count)

        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    asyncio.run(main())

