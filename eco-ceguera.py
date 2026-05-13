class ExitTile:
    def __init__(self, rect):
        self.rect     = rect
        self.revealed = 0

import pygame
import math
import random
import sys
import json
import os
import socket
import threading
from collections import deque
import heapq
import asyncio

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

#  Feature modules (leaderboard, co-op, editor)
from eco_features import (
    lb_submit, lb_is_record, draw_leaderboard, draw_name_input,
    draw_pause_menu,
    Player2,
    EDITOR_PALETTE, empty_editor_grid, build_map_from_editor, draw_editor,
)
from eco_settings import (
    settings_load, settings_save, draw_settings_menu,
    custom_level_save, custom_level_load, custom_levels_list, custom_level_delete,
    draw_save_level_dialog,
)
try:
    from eco_online_lb import ol_submit, ol_fetch_all, ol_fetch
except Exception:
    def ol_submit(*a, **kw): pass
    def ol_fetch_all(*a, **kw): pass
    def ol_fetch(*a, **kw): pass

try:
    from eco_audio import (
        audio_init, play_sfx, music_set_state, music_tick,
        music_set_volume, sfx_set_volume,
    )
    _HAS_AUDIO = True
except Exception:
    def audio_init(): pass
    def play_sfx(n): pass
    def music_set_state(s): pass
    def music_tick(): pass
    def music_set_volume(v): pass
    def sfx_set_volume(v): pass
    _HAS_AUDIO = False


#  Configuración 
W, H          = 900, 700
FPS           = 60
TILE          = 40

# Colores base
BLACK         = (0, 0, 0)
WHITE         = (255, 255, 255)
cfg_settings  = {}

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
REVEAL_DURATION   = 90       
ENEMY_SPEED_BASE  = 0.9
ENEMY_ALERT_SPEED = 2.2
ENEMY_ALERT_TIME  = 180        
DECOY_COUNT       = 3        

#  Configuración de niveles 
LEVEL_CONFIGS = [
    {'name': 'PRIMER CONTACTO',  'subtitle': 'Aprende a escuchar la oscuridad',
     'n_normal': 2, 'bat': False, 'heavy': False, 'n_traps': 0,
     'mat_metal': 0.10, 'mat_cork': 0.05, 'mat_mirror': 0.05,
     'reveal_dur': 110, 'sonar_radius': 320, 'micro_interval': 60, 'spd_mult': 0.8,
     'mechanic': None,
     'n_mimic': 0, 'n_stalker': 0, 'n_water': 2, 'n_glass': 1, 'n_noise': 1, 'n_orbs': 3},
    {'name': 'ECOS ROJOS',       'subtitle': 'El murciélago ha despertado',
     'n_normal': 3, 'bat': True,  'heavy': False, 'n_traps': 2,
     'mat_metal': 0.20, 'mat_cork': 0.15, 'mat_mirror': 0.08,
     'reveal_dur': 80, 'sonar_radius': 300, 'micro_interval': 50, 'spd_mult': 1.0,
     'mechanic': None,
     'n_mimic': 1, 'n_stalker': 0, 'n_water': 3, 'n_glass': 2, 'n_noise': 1, 'n_orbs': 2},
    {'name': 'CUENTA REGRESIVA', 'subtitle': 'La salida se cierra en 90 segundos',
     'n_normal': 3, 'bat': True,  'heavy': True,  'n_traps': 3,
     'mat_metal': 0.15, 'mat_cork': 0.30, 'mat_mirror': 0.10,
     'reveal_dur': 70, 'sonar_radius': 280, 'micro_interval': 45, 'spd_mult': 1.0,
     'mechanic': 'timer', 'timer_secs': 90,
     'n_mimic': 1, 'n_stalker': 1, 'n_water': 3, 'n_glass': 2, 'n_noise': 2, 'n_orbs': 2},
    {'name': 'CAMPO MINADO',     'subtitle': 'Las trampas se regeneran cada 15 s',
     'n_normal': 4, 'bat': True,  'heavy': True,  'n_traps': 10,
     'mat_metal': 0.25, 'mat_cork': 0.20, 'mat_mirror': 0.10,
     'reveal_dur': 60, 'sonar_radius': 260, 'micro_interval': 40, 'spd_mult': 1.2,
     'mechanic': 'respawn_traps', 'respawn_frames': 900,
     'n_mimic': 2, 'n_stalker': 1, 'n_water': 4, 'n_glass': 3, 'n_noise': 2, 'n_orbs': 1},
    {'name': 'EL ABISMO',        'subtitle': 'La oscuridad te consume cada 15 s',
     'n_normal': 5, 'bat': True,  'heavy': True,  'n_traps': 6,
     'mat_metal': 0.25, 'mat_cork': 0.25, 'mat_mirror': 0.12,
     'reveal_dur': 45, 'sonar_radius': 240, 'micro_interval': 35, 'spd_mult': 1.5,
     'mechanic': 'blackout', 'blackout_interval': 900,
     'n_mimic': 2, 'n_stalker': 2, 'n_water': 5, 'n_glass': 3, 'n_noise': 3, 'n_orbs': 1},
    # ── NEW LEVELS (showcasing new features) ────────────────────────────────
    {'name': 'EL ESPEJO ROTO',   'subtitle': 'El suelo traiciona cada paso',
     'n_normal': 3, 'bat': False, 'heavy': False, 'n_traps': 2,
     'mat_metal': 0.05, 'mat_cork': 0.05, 'mat_mirror': 0.30,
     'reveal_dur': 90, 'sonar_radius': 310, 'micro_interval': 55, 'spd_mult': 0.9,
     'mechanic': None,
     'n_mimic': 0, 'n_stalker': 0, 'n_water': 6, 'n_glass': 5, 'n_noise': 3, 'n_orbs': 2},
    {'name': 'SOMBRA SILENCIOSA','subtitle': 'No lo escucharás venir',
     'n_normal': 2, 'bat': False, 'heavy': False, 'n_traps': 1,
     'mat_metal': 0.15, 'mat_cork': 0.10, 'mat_mirror': 0.05,
     'reveal_dur': 85, 'sonar_radius': 290, 'micro_interval': 50, 'spd_mult': 1.0,
     'mechanic': None,
     'n_mimic': 0, 'n_stalker': 3, 'n_water': 2, 'n_glass': 2, 'n_noise': 2, 'n_orbs': 2},
    {'name': 'EL IMPOSTOR',      'subtitle': 'La salida no es lo que parece',
     'n_normal': 2, 'bat': True,  'heavy': False, 'n_traps': 2,
     'mat_metal': 0.15, 'mat_cork': 0.10, 'mat_mirror': 0.08,
     'reveal_dur': 75, 'sonar_radius': 280, 'micro_interval': 48, 'spd_mult': 1.1,
     'mechanic': None,
     'n_mimic': 4, 'n_stalker': 1, 'n_water': 2, 'n_glass': 2, 'n_noise': 1, 'n_orbs': 2},
    {'name': 'LA GALERIA',       'subtitle': 'Recoge los ecos antes de escapar',
     'n_normal': 4, 'bat': True,  'heavy': True,  'n_traps': 4,
     'mat_metal': 0.20, 'mat_cork': 0.20, 'mat_mirror': 0.10,
     'reveal_dur': 65, 'sonar_radius': 270, 'micro_interval': 42, 'spd_mult': 1.3,
     'mechanic': 'timer', 'timer_secs': 120,
     'n_mimic': 2, 'n_stalker': 2, 'n_water': 4, 'n_glass': 3, 'n_noise': 3, 'n_orbs': 8},
]
N_LEVELS = len(LEVEL_CONFIGS)


# Nuevas mecánicas
PLAYER_SNEAK_SPEED   = 1.5   
MICRO_PULSE_INTERVAL = 50    
BAT_RADIUS           = 7
BAT_SONAR_INTERVAL   = 80    
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
METAL_COLOR  = (90, 120, 150)  
CORK_COLOR   = (90, 60, 30)     
MIRROR_COLOR = (180, 220, 255) 

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

#  Sistema de sonido procedural 

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
_snd_sonar  = None   
_snd_mirror = None   
_snd_trap   = None   
_snd_win    = None   
_snd_lose   = None   

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
                    if abs(dx_hit) >= abs(dy_hit):  
                        nx_r, ny_r = -1.0, 0.0
                    else:                            
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
                        play_sfx("mirror")
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
        hc = cfg_settings.get("high_contrast", False)
        color = lerp_color(BLACK, self.color, min(1.0, alpha_f * (1.5 if hc else 0.9)))
        cx = int(self.x - offset[0])
        cy = int(self.y - offset[1])
        if 0 < self.radius:
            th = SONAR_THICKNESS + (1 if hc else 0)
            pygame.draw.circle(surf, color, (cx, cy), int(self.radius), th)


class Enemy:
    def __init__(self, x, y, patrol_route=None):
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
        # Fixed patrol route: list of (world_x, world_y) or None for random
        self.patrol_route     = patrol_route  
        self.patrol_route_idx = 0
        # FSM
        self.state       = STATE_PATROL
        self.path        = []      
        self.path_idx    = 0
        self.path_dirty  = False
        self.lost_timer  = 0
        self.sound_x     = x
        self.sound_y     = y
        self.chase_timer = 0        
        self._pick_patrol()

    def _pick_patrol(self):
        if self.patrol_route:
            # Advance to next waypoint in the fixed route
            wp = self.patrol_route[self.patrol_route_idx % len(self.patrol_route)]
            self.target_x, self.target_y = wp
            self.patrol_route_idx += 1
            self.patrol_timer = 30   
        else:
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
        self.path_dirty = True     

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

        #  FSM 
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

        #  Flocking (PATROL sólo) 
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

        #  Movimiento 
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
        for i, (tx, ty) in (enumerate(self.trail) if cfg_settings.get("show_trail", True) else []):
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
        for i, (tx, ty) in (enumerate(self.trail) if cfg_settings.get("show_trail", True) else []):
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
        for i, (tx, ty) in (enumerate(self.trail) if cfg_settings.get("show_trail", True) else []):
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



# ─── NEW MECHANICS CONSTANTS ─────────────────────────────────────────────────
HAZARD_WATER  = 'water'    # emit loud pulse when running through
HAZARD_GLASS  = 'glass'    # one-time loud pulse, then disappears
HEARTBEAT_MIN = 180        # frames between heartbeat at low alert
HEARTBEAT_MAX = 40         # frames between heartbeat at full chase
CONE_ANGLE    = 40         # degrees half-angle for focused sonar
CONE_RANGE    = 500        # max range of focused sonar
ROCK_RANGE    = 350        # max throw range for rocks
ABSORBER_DURATION = 180    # frames sound absorber is active


class FloorHazard:
    """Water puddle or broken glass on the floor.
    Water: if player runs through, emits a medium sonar pulse.
    Glass: one-time loud pulse, then disappears."""
    def __init__(self, cx, cy, htype=HAZARD_WATER):
        self.cx    = cx
        self.cy    = cy
        self.htype = htype
        r = TILE // 2 - 4
        self.rect  = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
        self.gone  = False
        self.ripple_timer = 0   # visual ripple for water

    def check(self, player, sneaking=False):
        """Returns SonarPulse or None. sneaking suppresses water noise."""
        if self.gone:
            return None
        pr = pygame.Rect(player.x - PLAYER_RADIUS, player.y - PLAYER_RADIUS,
                         PLAYER_RADIUS * 2, PLAYER_RADIUS * 2)
        if pr.colliderect(self.rect):
            if self.htype == HAZARD_GLASS:
                self.gone = True
                return SonarPulse(self.cx, self.cy, color=(200, 220, 255),
                                  is_decoy=True, max_radius=380)
            elif self.htype == HAZARD_WATER and not sneaking:
                return SonarPulse(self.cx, self.cy, color=(80, 160, 255),
                                  is_decoy=True, max_radius=200)
        return None

    def update(self):
        if self.htype == HAZARD_WATER:
            self.ripple_timer = (self.ripple_timer + 1) % 60

    def draw(self, surf, offset):
        if self.gone:
            return
        rx = self.cx - offset[0]
        ry = self.cy - offset[1]
        if self.htype == HAZARD_WATER:
            phase = self.ripple_timer / 60.0
            a = int(30 + 20 * math.sin(phase * 2 * math.pi))
            pygame.draw.ellipse(surf, (0, a, int(a * 2.5)),
                                (rx - 10, ry - 5, 20, 10), 1)
            pygame.draw.ellipse(surf, (0, a // 2, a),
                                (rx - 6, ry - 3, 12, 6), 1)
        else:  # glass
            c = (70, 80, 100)
            for dx2, dy2 in [(-5, -3), (5, -3), (0, 6), (-3, 3), (4, 2)]:
                pygame.draw.line(surf, c, (rx, ry), (rx + dx2, ry + dy2), 1)
            pygame.draw.circle(surf, (120, 140, 170), (rx, ry), 2)


class NoiseZone:
    """Area with background noise (fans/wind).
    Inside: player steps are muffled (sonar micro-pulses suppressed).
    The zone itself draws a faint visual shimmer."""
    def __init__(self, cx, cy, radius=70):
        self.cx     = cx
        self.cy     = cy
        self.radius = radius
        self._tick  = random.randint(0, 60)

    def contains(self, x, y):
        return math.hypot(x - self.cx, y - self.cy) < self.radius

    def update(self):
        self._tick += 1

    def draw(self, surf, offset):
        rx = int(self.cx - offset[0])
        ry = int(self.cy - offset[1])
        a = int(18 + 10 * math.sin(self._tick * 0.08))
        for i in range(1, 4):
            r2 = int(self.radius * i / 3)
            pygame.draw.circle(surf, (0, a, a // 2), (rx, ry), r2, 1)
        # Wind particles
        for i in range(3):
            ang = (self._tick * 0.04 + i * 2.1) % (2 * math.pi)
            pr2 = int(self.radius * 0.6)
            px2 = int(rx + math.cos(ang) * pr2)
            py2 = int(ry + math.sin(ang) * pr2)
            pygame.draw.circle(surf, (0, a, a), (px2, py2), 1)


class EchoOrb:
    """Collectible lore fragment. Touching it shows a brief message."""
    _LORE = [
        "El laboratorio cayó en silencio hace años...",
        "Dicen que los guardias aún patrullan sin saberlo.",
        "La oscuridad no es tu enemiga. El sonido sí.",
        "Escuché pasos donde no debía haberlos.",
        "El eco revela lo que los ojos nunca podrán.",
        "Sobrevivir es simple: no hagas ruido.",
        "Hay algo más grande moviéndose en las sombras.",
        "Mi último pulso de sonar me delató...",
    ]
    def __init__(self, cx, cy):
        self.cx       = cx
        self.cy       = cy
        self.radius   = 7
        self.collected = False
        self.message  = random.choice(EchoOrb._LORE)
        self.msg_timer = 0
        self._tick    = random.randint(0, 60)

    def check(self, player):
        if self.collected:
            return
        if math.hypot(player.x - self.cx, player.y - self.cy) < self.radius + PLAYER_RADIUS:
            self.collected = True
            self.msg_timer = 240   # show message for 4 seconds

    def update(self):
        self._tick += 1
        if self.msg_timer > 0:
            self.msg_timer -= 1

    def draw(self, surf, offset):
        if self.collected:
            return
        rx = int(self.cx - offset[0])
        ry = int(self.cy - offset[1])
        pulse = math.sin(self._tick * 0.07) * 0.5 + 0.5
        col = (int(100 + 80 * pulse), int(60 + 40 * pulse), int(200 + 55 * pulse))
        pygame.draw.circle(surf, col, (rx, ry), self.radius, 2)
        pygame.draw.circle(surf, (180, 120, 255), (rx, ry), 3)

    def draw_message(self, surf, font):
        if self.msg_timer <= 0:
            return
        try:
            mf = pygame.font.SysFont("consolas", 14)
        except Exception:
            mf = font
        alpha = min(1.0, self.msg_timer / 30.0)
        col = (int(180 * alpha), int(120 * alpha), int(255 * alpha))
        sw = surf.get_width()
        sh = surf.get_height()
        ms = mf.render(f'"{self.message}"', True, col)
        surf.blit(ms, (sw // 2 - ms.get_width() // 2, sh - 60))


class SoundAbsorber:
    """One-use consumable. Activated with E key.
    Silences all sonar pulses within radius for ABSORBER_DURATION frames."""
    def __init__(self):
        self.count    = 1       # player starts with 1
        self.active   = False
        self.timer    = 0
        self.radius   = 120

    def activate(self):
        if self.count > 0 and not self.active:
            self.count   -= 1
            self.active  = True
            self.timer   = ABSORBER_DURATION

    def update(self):
        if self.active:
            self.timer -= 1
            if self.timer <= 0:
                self.active = False

    def cancels(self, px, py, pulse_x, pulse_y):
        """Returns True if a pulse at (pulse_x, pulse_y) is cancelled."""
        if not self.active:
            return False
        return math.hypot(px - pulse_x, py - pulse_y) < self.radius

    def draw_hud(self, surf, x, y, font):
        try:
            sf = pygame.font.SysFont("consolas", 13)
        except Exception:
            sf = font
        col = (100, 220, 180) if self.count > 0 else (50, 60, 70)
        label = f"Absorb[E]: {self.count}"
        if self.active:
            label += f" ●{self.timer // 60 + 1}s"
            col = (0, 255, 200)
        s = sf.render(label, True, col)
        surf.blit(s, (x, y))


class ThrowableRock:
    """Thrown via Q + left-click on target. Creates a noise pulse on impact."""
    def __init__(self, sx, sy, tx, ty):
        self.x     = float(sx)
        self.y     = float(sy)
        angle      = math.atan2(ty - sy, tx - sx)
        speed      = 8.0
        self.vx    = math.cos(angle) * speed
        self.vy    = math.sin(angle) * speed
        self.tx    = tx
        self.ty    = ty
        self.dead  = False
        self.trail = []

    def update(self, walls):
        if self.dead:
            return None
        self.trail.append((self.x, self.y))
        if len(self.trail) > 8:
            self.trail.pop(0)
        self.x += self.vx
        self.y += self.vy
        # Wall collision or near target
        r = pygame.Rect(self.x - 3, self.y - 3, 6, 6)
        if any(r.colliderect(w.rect) for w in walls):
            self.dead = True
            return SonarPulse(self.x, self.y, color=(255, 200, 80),
                              is_decoy=True, max_radius=300)
        if math.hypot(self.x - self.tx, self.y - self.ty) < 10:
            self.dead = True
            return SonarPulse(self.x, self.y, color=(255, 200, 80),
                              is_decoy=True, max_radius=300)
        return None

    def draw(self, surf, offset):
        if self.dead:
            return
        for i, (tx2, ty2) in enumerate(self.trail):
            a = (i + 1) / max(len(self.trail), 1)
            c = (int(180 * a), int(130 * a), 0)
            pygame.draw.circle(surf, c,
                               (int(tx2 - offset[0]), int(ty2 - offset[1])), 2)
        rx = int(self.x - offset[0])
        ry = int(self.y - offset[1])
        pygame.draw.circle(surf, (200, 160, 80), (rx, ry), 3)


class MimicEnemy:
    """Stationary enemy that pretends to be the exit tile.
    If hit by a player sonar pulse, briefly reveals its true form."""
    def __init__(self, cx, cy):
        self.cx      = cx
        self.cy      = cy
        r            = TILE // 2 - 4
        self.rect    = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
        self.revealed = 0
        self.dead    = False   # dies when player escapes past it (not used for win)
        self._tick   = 0
        self.x       = float(cx)   # for dist checks
        self.y       = float(cy)

    def update(self, player):
        self._tick += 1
        if self.revealed > 0:
            self.revealed -= 1
        # If player walks into it while unrevealed → caught
        if math.hypot(player.x - self.cx, player.y - self.cy) < PLAYER_RADIUS + 12:
            player.caught = True

    def on_sonar_hit(self):
        self.revealed = REVEAL_DURATION

    def draw(self, surf, offset):
        rx = int(self.cx - offset[0])
        ry = int(self.cy - offset[1])
        if self.revealed > 0:
            alpha = min(1.0, self.revealed / 20)
            # Show true form: pulsing magenta diamond
            col = lerp_color(BLACK, (255, 0, 200), alpha)
            r2 = int(TILE // 2 - 4)
            pts = [(rx, ry - r2), (rx + r2, ry), (rx, ry + r2), (rx - r2, ry)]
            pygame.draw.polygon(surf, col, pts)
            pygame.draw.polygon(surf, (255, 100, 255), pts, 2)
        else:
            # Disguise as exit tile (gold blinking square)
            blink = (math.sin(self._tick * 0.12) + 1) / 2
            col = lerp_color(BLACK, GOLD, blink * 0.6)
            er = pygame.Rect(rx - 14, ry - 14, 28, 28)
            pygame.draw.rect(surf, col, er)
            pygame.draw.rect(surf, GOLD, er, 2)


class StalkerEnemy(Enemy):
    """Invisible enemy - emits NO sonar of its own.
    Extremely fast when it detects the player's sonar origin."""
    def __init__(self, x, y):
        super().__init__(x, y)
        self.speed    = 0.3   # slow by default
        self.reveal   = 0     # stays 0 unless sonar hits it
        self._stalk_t = 0

    def on_sonar_detected(self, px, py):
        """Called when player fires a sonar pulse - stalker heard the origin."""
        self.speed = ENEMY_ALERT_SPEED * 1.4
        self.alert(px, py)
        self._stalk_t = 300

    def update(self, walls, player, all_enemies=None, wall_grid=None):
        super().update(walls, player, all_enemies, wall_grid)
        if self._stalk_t > 0:
            self._stalk_t -= 1
            if self._stalk_t <= 0:
                self.speed = 0.3

    def draw(self, surf, offset):
        # Draw a very faint dark distortion trail only
        for i, (tx, ty) in (enumerate(self.trail) if cfg_settings.get("show_trail", True) else []):
            t = (i + 1) / max(len(self.trail), 1)
            b = int(t * 30)
            if b > 3:
                pygame.draw.circle(surf, (b // 2, 0, b),
                                   (int(tx - offset[0]), int(ty - offset[1])),
                                   max(1, int(t * 2)))
        if self.reveal > 0:
            alpha = min(1.0, self.reveal / 20)
            col = lerp_color(BLACK, PURPLE, alpha)
            cx2 = int(self.x - offset[0])
            cy2 = int(self.y - offset[1])
            pygame.draw.circle(surf, col, (cx2, cy2), ENEMY_RADIUS)
            pygame.draw.circle(surf, (200, 100, 255), (cx2, cy2), ENEMY_RADIUS, 1)


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
        # 1) ESTELA ROJA RÁPIDA
        for i, (tx2, ty2) in (enumerate(self.trail) if cfg_settings.get("show_trail", True) else []):
            a = (i + 1) / len(self.trail) if self.trail else 1
            col = lerp_color(BLACK, GREEN, a * 0.5)
            r = max(1, int(PLAYER_RADIUS * a * 0.5))
            pygame.draw.circle(surf, col, (int(tx2 - offset[0]), int(ty2 - offset[1])), r)
        # Cuerpo
        cx = int(self.x - offset[0])
        cy = int(self.y - offset[1])
        c = WHITE if cfg_settings.get("high_contrast", False) else GREEN
        pygame.draw.circle(surf, c, (cx, cy), PLAYER_RADIUS)
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
        col_i, row_i = floor_cells[idx]; idx += 1
        enemies.append(HeavyEnemy(col_i * TILE + TILE // 2, row_i * TILE + TILE // 2))

    # NEW: Mimic enemies
    for _ in range(cfg.get('n_mimic', 0)):
        if idx < len(floor_cells):
            col_i, row_i = floor_cells[idx]; idx += 1
            enemies.append(MimicEnemy(col_i * TILE + TILE // 2, row_i * TILE + TILE // 2))

    # NEW: Stalker enemies
    for _ in range(cfg.get('n_stalker', 0)):
        if idx < len(floor_cells):
            col_i, row_i = floor_cells[idx]; idx += 1
            enemies.append(StalkerEnemy(col_i * TILE + TILE // 2, row_i * TILE + TILE // 2))

    # NEW: Floor hazards
    floor_hazards = []
    for col_i, row_i in floor_cells[idx:idx + cfg.get('n_water', 2)]:
        floor_hazards.append(FloorHazard(col_i * TILE + TILE // 2,
                                          row_i * TILE + TILE // 2, HAZARD_WATER))
    idx += cfg.get('n_water', 2)
    for col_i, row_i in floor_cells[idx:idx + cfg.get('n_glass', 1)]:
        floor_hazards.append(FloorHazard(col_i * TILE + TILE // 2,
                                          row_i * TILE + TILE // 2, HAZARD_GLASS))
    idx += cfg.get('n_glass', 1)

    # NEW: Noise zones
    noise_zones = []
    for col_i, row_i in floor_cells[idx:idx + cfg.get('n_noise', 1)]:
        noise_zones.append(NoiseZone(col_i * TILE + TILE // 2,
                                      row_i * TILE + TILE // 2,
                                      radius=random.randint(55, 90)))
    idx += cfg.get('n_noise', 1)

    # NEW: Echo orbs
    echo_orbs = []
    for col_i, row_i in floor_cells[idx:idx + cfg.get('n_orbs', 2)]:
        echo_orbs.append(EchoOrb(col_i * TILE + TILE // 2,
                                  row_i * TILE + TILE // 2))

    # Build wall grid for A* pathfinding
    wall_grid = [[False] * COLS for _ in range(ROWS)]
    for w in walls:
        gc = w.rect.x // TILE
        gr = w.rect.y // TILE
        if 0 <= gr < ROWS and 0 <= gc < COLS:
            wall_grid[gr][gc] = True

    return walls, enemies, player_pos, exit_rect, traps, wall_grid, \
           floor_hazards, noise_zones, echo_orbs



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

#  Partículas flotantes del menú 
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

    #  Fondo: grid + partículas sonar 
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

    #  Scanlines decorativas 
    for sy in range(0, H, 4):
        pygame.draw.line(surf, (0, 5, 8), (0, sy), (W, sy))

    #  Panel principal 
    panel_w = min(560, W - 60)
    panel_h = 500          # taller to fit 7 menu buttons
    panel_x = cx - panel_w // 2
    panel_y = max(8, cy - panel_h // 2)   # clamp so it never goes above screen

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

    #  Título con efecto glitch 
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

    #  Botones del menú 
    mouse_pos = pygame.mouse.get_pos()
    btn_defs = [
        ("JUGAR",          "Comenzar partida"),
        ("NIVELES",        "Seleccionar nivel"),
        ("EDITOR",         "Crear laberinto"),
        ("CLASIFICACION",  "Mejores tiempos"),
        ("CONTROLES",      "Ver controles"),
        ("CONFIGURACION",  "Ajustes del juego"),
        ("SALIR",          "Cerrar el juego"),
    ]
    btn_w, btn_h, btn_gap = min(320, panel_w - 80), 36, 5
    btn_start_y = title_y + 104
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

    #  Panel créditos (si está activo) 
    if show_credits:
        cr_w, cr_h = min(680, W - 40), 260
        cr_x = cx - cr_w // 2
        cr_y_below = panel_y + panel_h + 10
        if cr_y_below + cr_h <= H - 6:
            cr_y = cr_y_below
        else:
            cr_y = panel_y + (panel_h - cr_h) // 2
        crs = pygame.Surface((cr_w, cr_h), pygame.SRCALPHA)
        crs.fill((0, 15, 25, 235))
        surf.blit(crs, (cr_x, cr_y))
        pygame.draw.rect(surf, (0, 80, 120), (cr_x, cr_y, cr_w, cr_h), 2)
        try: hf = pygame.font.SysFont("consolas", 15, bold=True)
        except: hf = small_font
        ht = hf.render("CONTROLES", True, CYAN)
        surf.blit(ht, (cx - ht.get_width() // 2, cr_y + 12))
        pygame.draw.line(surf, DARK_CYAN, (cr_x + 20, cr_y + 34), (cr_x + cr_w - 20, cr_y + 34), 1)
        # Player 1 controls
        try: hf2 = pygame.font.SysFont("consolas", 12, bold=True)
        except: hf2 = small_font
        p1_lbl = hf2.render("Jugador 1", True, (60, 200, 120))
        surf.blit(p1_lbl, (cr_x + 20, cr_y + 40))
        ctrl_lines = [
            ("WASD",           "Mover"),
            ("Shift",          "Sigilo (sin micro-pulsos)"),
            ("Clic Izq",       "Pulso sonar 360°"),
            ("F",              "Sonar en cono (direccional)"),
            ("Q + Clic",       "Lanzar piedra (ruido a distancia)"),
            ("E",              "Absorb. de sonido (3 seg)"),
            ("Clic Der",       "Señuelo sónico"),
            ("R",              "Reiniciar nivel"),
            ("ESC",            "Pausa / Menú"),
        ]
        try: cf2 = pygame.font.SysFont("consolas", 11)
        except: cf2 = small_font
        for j, (k, v) in enumerate(ctrl_lines):
            ky = cr_y + 54 + j * 20
            ks = cf2.render(k, True, (0, 180, 220))
            vs = cf2.render(v, True, (150, 200, 220))
            surf.blit(ks, (cr_x + 20, ky))
            surf.blit(vs, (cr_x + 110, ky))
        # ── Nuevas mecánicas column ──────────────────────────────────────────
        try: hf3 = pygame.font.SysFont("consolas", 11, bold=True)
        except: hf3 = small_font
        mech_lbl = hf3.render("Nuevas mecánicas", True, (180, 120, 255))
        surf.blit(mech_lbl, (cr_x + cr_w // 2 + 10, cr_y + 40))
        mech_lines = [
            ("Charcos",        "Ruido moderado al correr"),
            ("Vidrio roto",    "Ruido masivo al pisar"),
            ("Zona viento",    "Silencia micro-pulsos"),
            ("Orbe eco",       "Recolectar lore"),
            ("Mímico",         "Enemigo oculto en salida"),
            ("Rastreador",     "Te persigue al oír sonar"),
            ("Corazón",        "Late si hay alertas"),
        ]
        try: mf2 = pygame.font.SysFont("consolas", 11)
        except: mf2 = small_font
        for j, (k, v) in enumerate(mech_lines):
            ky = cr_y + 54 + j * 20
            ks = mf2.render(k, True, (180, 100, 255))
            vs = mf2.render(v, True, (160, 140, 200))
            surf.blit(ks, (cr_x + cr_w // 2 + 10, ky))
            surf.blit(vs, (cr_x + cr_w // 2 + 110, ky))
        # Co-op footer 
        try: cf3 = pygame.font.SysFont("consolas", 11)
        except: cf3 = small_font
        tip_c = cf3.render("Jugador 2 (co-op): Flechas + RShift  |  C en nivel: activar co-op", True, (80, 130, 100))
        surf.blit(tip_c, (cr_x + 20, cr_y + cr_h - 22))

    #  Recuadro de créditos (esquina inferior izquierda) 
    try:
        cr_lbl_f = pygame.font.SysFont("consolas", 11, bold=True)
        cr_val_f = pygame.font.SysFont("consolas", 11)
    except:
        cr_lbl_f = cr_val_f = small_font

    credits_lines = [
        ("Diseño y código",  "Andres Carrillo"),
        ("Github",            "AndresCarrillo444"),
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

    # Tip inferior 
    try: tip_f = pygame.font.SysFont("consolas", 12)
    except: tip_f = small_font
    tip = tip_f.render("Flechas: navegar  |  Enter: seleccionar  |  ESC: salir", True, (40, 65, 80))
    surf.blit(tip, (cx - tip.get_width() // 2, H - 18))

    #  Versión 
    ver = tip_f.render("v2.0  |  ECO-CEGUERA", True, (25, 45, 60))
    surf.blit(ver, (panel_x + panel_w - ver.get_width() - 6, panel_y + panel_h - 18))

    # Returns 7 rects (jugar, niveles, editor, clasificacion, controles, config, salir)
    while len(btn_rects) < 7:
        btn_rects.append(pygame.Rect(0, 0, 0, 0))
    return tuple(btn_rects[:7])


#  Pantalla de selección de nivel 
def draw_level_select(surf, tick, sel, max_unlocked, font, small_font,
                      ls_tab="normal", custom_sel=0, custom_names=None,
                      coop_enabled=False):
    if custom_names is None:
        custom_names = []

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

    try:  tf = pygame.font.SysFont("consolas", 28, bold=True)
    except: tf = font
    gv = int(160 + 80*(math.sin(tick*0.05)*0.5+0.5))
    ts = tf.render("SELECCIONAR NIVEL", True, (0, gv, gv))
    surf.blit(ts, (cx - ts.get_width()//2, 14))

    # Tab bar
    tab_y, tab_w2, tab_h2 = 50, 160, 28
    mouse = pygame.mouse.get_pos()
    tab_normal_r = pygame.Rect(cx - tab_w2 - 4, tab_y, tab_w2, tab_h2)
    tab_custom_r = pygame.Rect(cx + 4,           tab_y, tab_w2, tab_h2)

    try:  tf2 = pygame.font.SysFont("consolas", 13, bold=True)
    except: tf2 = small_font

    for r, label, active, col in [
        (tab_normal_r, "NIVELES",     ls_tab == "normal", (0, 100, 50)),
        (tab_custom_r, "MIS NIVELES", ls_tab == "custom", (0, 50, 130)),
    ]:
        bg = (*col, 230) if active else (*(c//2 for c in col), 140)
        bst = pygame.Surface((tab_w2, tab_h2), pygame.SRCALPHA)
        bst.fill(bg)
        surf.blit(bst, r.topleft)
        border = tuple(min(255, c + 60) for c in col) if active else col
        pygame.draw.rect(surf, border, r, 2)
        ls2 = tf2.render(label, True, WHITE if active else (140,170,190))
        surf.blit(ls2, (r.centerx - ls2.get_width()//2, r.centery - ls2.get_height()//2))

    card_y0 = tab_y + tab_h2 + 10

    # CO-OP status badge 
    try: cof = pygame.font.SysFont("consolas", 12, bold=True)
    except: cof = small_font
    co_on  = coop_enabled
    co_txt = "[ CO-OP: ON  ]" if co_on else "[ CO-OP: OFF ]"
    co_col = (0, 200, 100) if co_on else (80, 90, 100)
    co_bg  = (0, 60, 30, 200) if co_on else (20, 25, 30, 160)
    co_s   = cof.render(co_txt, True, co_col)
    co_bw, co_bh = co_s.get_width() + 14, 22
    co_bx, co_by = cx + tab_w2 + 14, tab_y + (tab_h2 - co_bh) // 2
    cobs = pygame.Surface((co_bw, co_bh), pygame.SRCALPHA)
    cobs.fill(co_bg)
    surf.blit(cobs, (co_bx, co_by))
    pygame.draw.rect(surf, co_col, (co_bx, co_by, co_bw, co_bh), 1)
    surf.blit(co_s, (co_bx + 7, co_by + co_bh//2 - co_s.get_height()//2))
    key_hint = cof.render("C: activar/desactivar", True, (50, 80, 60) if not co_on else (40, 120, 70))
    surf.blit(key_hint, (co_bx, co_by + co_bh + 3))


    # Placeholders so return tuple is always complete
    card_rects        = []
    play_rect         = pygame.Rect(0,0,0,0)
    custom_card_rects = []
    custom_play_r     = pygame.Rect(0,0,0,0)
    custom_del_r      = pygame.Rect(0,0,0,0)

    if ls_tab == "normal":
        # Built-in levels 
        card_w, card_h2, gap = 780, 46, 4
        card_x = cx - card_w // 2
        mech_labels = {'timer':'CRONOMETRO','respawn_traps':'TRAMPAS VIVAS','blackout':'APAGON'}

        for i, cfg in enumerate(LEVEL_CONFIGS):
            cy2   = card_y0 + i * (card_h2 + gap)
            rect  = pygame.Rect(card_x, cy2, card_w, card_h2)
            card_rects.append(rect)
            locked   = i > max_unlocked
            hovered  = rect.collidepoint(mouse) and not locked
            selected = (i == sel)

            cs = pygame.Surface((card_w, card_h2), pygame.SRCALPHA)
            cs.fill((0,40,60,200) if selected else (5,20,30,160) if not locked else (5,10,15,80))
            surf.blit(cs, (card_x, cy2))

            if selected and not locked:
                bv = int(130 + 110*(math.sin(tick*0.1)*0.5+0.5))
                border = (0, bv, 255)
            elif hovered: border = (0,110,170)
            elif locked:  border = (25,35,45)
            else:         border = (0,55,75)
            pygame.draw.rect(surf, border, rect, 2)

            bc = (0,80,110) if selected and not locked else (40,50,60) if locked else (0,50,70)
            pygame.draw.rect(surf, bc, (card_x+6, cy2+6, 50, card_h2-12))
            ns = font.render(f"{i+1}", True, (70,80,90) if locked else CYAN)
            surf.blit(ns, (card_x+6+25-ns.get_width()//2, cy2+card_h2//2-ns.get_height()//2))

            nc = (35,45,55) if locked else (WHITE if selected else (170,205,225))
            try: nf = pygame.font.SysFont("consolas",15,bold=True)
            except: nf = small_font
            nm = nf.render(("[BLOQUEADO]  " if locked else "") + cfg['name'], True, nc)
            surf.blit(nm, (card_x+64, cy2+6))
            ss = small_font.render(cfg['subtitle'], True, (25,35,45) if locked else (100,145,165))
            surf.blit(ss, (card_x+64, cy2+24))

            mech = cfg.get('mechanic')
            if mech and not locked:
                ml = small_font.render(mech_labels.get(mech,''), True, ORANGE)
                surf.blit(ml, (card_x+card_w-ml.get_width()-8, cy2+card_h2//2-ml.get_height()//2))

        py0 = card_y0 + N_LEVELS*(card_h2+gap) + 8
        play_rect = pygame.Rect(cx-110, py0, 220, 40)
        can_play  = sel <= max_unlocked
        ph = play_rect.collidepoint(mouse) and can_play
        pc = (0,210,255) if ph else ((0,140,180) if can_play else (40,50,60))
        ps2 = pygame.Surface((220,40), pygame.SRCALPHA)
        ps2.fill((*pc, 210 if ph else 140))
        surf.blit(ps2, play_rect.topleft)
        pygame.draw.rect(surf, pc, play_rect, 2)
        try: bf = pygame.font.SysFont("consolas",16,bold=True)
        except: bf = font
        bl = bf.render(">> JUGAR <<" if ph else "[ JUGAR ]", True, WHITE if can_play else (60,70,80))
        surf.blit(bl, (cx-bl.get_width()//2, py0+20-bl.get_height()//2))

        try: cf3 = pygame.font.SysFont("consolas",11)
        except: cf3 = small_font
        surf.blit(cf3.render("C: co-op ON/OFF", True, (50,90,60)), (cx-60, py0+46))

    else:
        # Custom levels tab 
        card_w, card_h2, gap = 780, 46, 4
        card_x = cx - card_w // 2

        if not custom_names:
            try: ef = pygame.font.SysFont("consolas",14)
            except: ef = small_font
            surf.blit(ef.render("No tienes niveles guardados todavía.", True, (80,110,130)),
                      (cx - ef.size("No tienes niveles guardados todavía.")[0]//2, card_y0+30))
            surf.blit(ef.render("Ve al EDITOR → pinta tu laberinto → GUARDAR", True, (60,90,110)),
                      (cx - ef.size("Ve al EDITOR → pinta tu laberinto → GUARDAR")[0]//2, card_y0+56))
        else:
            for i, name in enumerate(custom_names):
                cy2  = card_y0 + i * (card_h2 + gap)
                rect = pygame.Rect(card_x, cy2, card_w - 60, card_h2)
                custom_card_rects.append(rect)
                selected = (i == custom_sel)
                hovered  = rect.collidepoint(mouse)

                cs = pygame.Surface((card_w-60, card_h2), pygame.SRCALPHA)
                cs.fill((0,25,50,200) if selected else (5,15,30,160))
                surf.blit(cs, (card_x, cy2))
                if selected:
                    bv = int(100+130*(math.sin(tick*0.1)*0.5+0.5))
                    border = (0, bv, min(255,bv+80))
                elif hovered: border = (0,80,150)
                else:         border = (0,40,80)
                pygame.draw.rect(surf, border, rect, 2)

                pygame.draw.rect(surf, (0,40,80), (card_x+6, cy2+6, 40, card_h2-12))
                try: nf2 = pygame.font.SysFont("consolas",12,bold=True)
                except: nf2 = small_font
                ns2 = nf2.render(str(i+1), True, (0,160,220))
                surf.blit(ns2, (card_x+6+20-ns2.get_width()//2, cy2+card_h2//2-ns2.get_height()//2))

                try: cnf = pygame.font.SysFont("consolas",14,bold=True)
                except: cnf = small_font
                cn_s = cnf.render(name, True, WHITE if selected else (160,200,230))
                surf.blit(cn_s, (card_x+54, cy2+card_h2//2-cn_s.get_height()//2))

                del_r = pygame.Rect(card_x+card_w-54, cy2+(card_h2-24)//2, 50, 24)
                dh = del_r.collidepoint(mouse)
                ds = pygame.Surface((50,24), pygame.SRCALPHA)
                ds.fill((120,0,0,200) if dh else (60,0,0,140))
                surf.blit(ds, del_r.topleft)
                pygame.draw.rect(surf, (200,0,0) if dh else (80,0,0), del_r, 1)
                try: df = pygame.font.SysFont("consolas",11,bold=True)
                except: df = small_font
                dl = df.render("DEL", True, (255,80,80))
                surf.blit(dl, (del_r.centerx-dl.get_width()//2, del_r.centery-dl.get_height()//2))
                if selected:
                    custom_del_r = del_r

            py0 = card_y0 + len(custom_names)*(card_h2+gap) + 8
            custom_play_r = pygame.Rect(cx-110, py0, 220, 40)
            can_p = 0 <= custom_sel < len(custom_names)
            ph2 = custom_play_r.collidepoint(mouse) and can_p
            pc2 = (0,160,255) if ph2 else ((0,90,180) if can_p else (40,50,60))
            ps3 = pygame.Surface((220,40), pygame.SRCALPHA)
            ps3.fill((*pc2, 210 if ph2 else 140))
            surf.blit(ps3, custom_play_r.topleft)
            pygame.draw.rect(surf, pc2, custom_play_r, 2)
            try: bf2 = pygame.font.SysFont("consolas",16,bold=True)
            except: bf2 = font
            bl2 = bf2.render(">> JUGAR <<" if ph2 else "[ JUGAR ]",
                              True, WHITE if can_p else (60,70,80))
            surf.blit(bl2, (cx-bl2.get_width()//2, py0+20-bl2.get_height()//2))

    surf.blit(small_font.render("Click: seleccionar  |  ESC: menu principal", True, (55,80,95)),
              (cx - small_font.size("Click: seleccionar  |  ESC: menu principal")[0]//2, H-18))
    return (card_rects, play_rect, tab_normal_r, tab_custom_r,
            custom_card_rects, custom_play_r, custom_del_r)


def draw_level_complete(surf, tick, font, level_idx, score=0, pulse_count=0, elapsed_ticks=0):
    """Overlay shown when the player escapes. Returns continue_rect."""
    cx, cy = W//2, H//2

    ov = pygame.Surface((W, H), pygame.SRCALPHA)
    ov.fill((0, 20, 8, 200))
    surf.blit(ov, (0, 0))

    for i in range(6):
        phase = (tick * 1.2 + i * 52) % 360
        rad = int((phase / 360) * max(W, H) * 0.75)
        af  = 1.0 - phase / 360
        col = (0, int(220 * af), int(90 * af))
        if rad > 0:
            pygame.draw.circle(surf, col, (cx, cy), rad, 1)

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

    try: tf = pygame.font.SysFont("consolas", 40, bold=True)
    except: tf = font
    gv = int(150 + 100*(math.sin(tick*0.08)*0.5+0.5))
    sh = tf.render("NIVEL COMPLETADO", True, (0, gv//4, gv//8))
    surf.blit(sh, (cx - sh.get_width()//2 + 3, py2 + 22 + 3))
    t1 = tf.render("NIVEL COMPLETADO", True, (0, gv, int(gv*0.45)))
    surf.blit(t1, (cx - t1.get_width()//2, py2 + 22))

    pygame.draw.line(surf, (0, 80, 40), (px2+24, py2+82), (px2+pw-24, py2+82), 1)
    sep_w = int((pw-48) * min(1.0, tick/60))
    pygame.draw.line(surf, GREEN, (cx - sep_w//2, py2+82), (cx + sep_w//2, py2+82), 1)

    cfg = LEVEL_CONFIGS[level_idx]
    try: sf = pygame.font.SysFont("consolas", 15)
    except: sf = font

    n2 = sf.render(f"Nivel {level_idx+1}  —  {cfg['name']}", True, (120, 220, 150))
    surf.blit(n2, (cx - n2.get_width()//2, py2 + 98))

    is_last = level_idx >= N_LEVELS - 1
    next_txt = "¡Has completado el juego!" if is_last else f"Siguiente:  {LEVEL_CONFIGS[level_idx+1]['name']}"
    nx_col = GOLD if is_last else (100, 180, 130)
    nx = sf.render(next_txt, True, nx_col)
    surf.blit(nx, (cx - nx.get_width()//2, py2 + 112))

    time_bonus = max(0, 3000 - elapsed_ticks // 2)
    pulse_pen  = pulse_count * 80
    lvl_bonus  = level_idx * 500
    try: bf2 = pygame.font.SysFont("consolas", 13)
    except: bf2 = sf
    score_lines = [
        ("Base",      5000,      CYAN),
        ("Velocidad", time_bonus, GREEN),
        ("Pulsos  -", pulse_pen,  ORANGE),
        ("Nivel   +", lvl_bonus,  GOLD),
        ("TOTAL",     score,      WHITE),
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

    controls = small_font.render(
        "WASD:mover  Shift:sigilo  Clic:sonar  F:cono  Q:roca  E:absorb  Clic-Der:señuelo  R:reset",
        True, (80, 120, 140))
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
    audio_init()
    clock = pygame.time.Clock()
    pygame.display.set_caption("Eco-Ceguera")
    IS_WEB = sys.platform == 'emscripten'

    try:
        font       = pygame.font.SysFont("consolas", 20, bold=True)
        small_font = pygame.font.SysFont("consolas", 14)
    except Exception:
        font       = pygame.font.Font(None, 24)
        small_font = pygame.font.Font(None, 16)

    # Resolution setup 
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

    #  Progression 
    current_level = 0
    max_unlocked  = 0

    #  Game state placeholders 
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

    #  New feature state
    lb_tick       = 0                               # leaderboard animation tick
    editor_grid   = empty_editor_grid(COLS, ROWS)  # level editor grid
    editor_sel    = 0                               # selected palette index
    editor_tick   = 0
    player2       = None                            # co-op second player
    coop_enabled  = False                           # toggle in level select (C key)
    # name-input state (shown only on new record)
    name_buf      = ""    # text typed by the player
    ni_tick       = 0     # animation tick for name-input screen
    lb_tab        = "local"   # leaderboard tab: 'local' or 'global'
    ls_tab        = "normal"  # level-select tab: 'normal' or 'custom'
    custom_sel    = 0         # selected index in custom levels list
    custom_names  = custom_levels_list()  # names of saved custom levels
    # pause state
    paused        = False         # True while pause menu is open
    pause_tick    = 0             # animation tick inside the pause menu
    pause_origin  = 'ls'          # 'ls' or 'editor' — where to go on "exit"
    # Progreso y Settings
    global cfg_settings
    cfg_settings  = settings_load()
    settings_open = False
    settings_tick = 0
    # fog-of-war memory surface (persistent dim wall outlines)
    fog_surf      = None          # created per-level in new_game helper
    # particle death burst
    death_particles = []          # list of dicts {x,y,vx,vy,life,max_life,color}
    # level transition fade
    fade_alpha    = 0             # 0=fully visible, 255=black; negative triggers fade-in
    fade_dir      = 0             # +1=fade out, -1=fade in, 0=idle
    fade_target   = None          # state to switch to after fade-out
    # editor save dialog
    editor_save_open  = False
    editor_save_buf   = ""
    editor_save_tick  = 0
    micro_pulse_timer2 = 0   # co-op player2 movement sonar throttle
    # NEW feature state
    floor_hazards  = []        # FloorHazard list
    noise_zones    = []        # NoiseZone list
    echo_orbs      = []        # EchoOrb list
    rocks          = []        # ThrowableRock list in flight
    absorber       = SoundAbsorber()
    rock_mode      = False     # True while Q held — next click throws rock
    heartbeat_t    = 0         # frames until next heartbeat visual
    mimics         = []        # MimicEnemy list (subset of enemies list for sonar checks)
    stalkers       = []        # StalkerEnemy list (for sonar-heard notification)

    def new_game(level):
        global REVEAL_DURATION, SONAR_MAX_RADIUS, MICRO_PULSE_INTERVAL
        global ENEMY_SPEED_BASE, ENEMY_ALERT_SPEED
        cfg = LEVEL_CONFIGS[level]
        REVEAL_DURATION      = cfg['reveal_dur']
        SONAR_MAX_RADIUS     = cfg['sonar_radius']
        MICRO_PULSE_INTERVAL = cfg['micro_interval']
        ENEMY_SPEED_BASE     = round(cfg['spd_mult'] * 0.9, 2)
        ENEMY_ALERT_SPEED    = round(cfg['spd_mult'] * 2.2, 2)
        w2, e2, ppos, ex, tr, wg, fh, nz, eo = build_map(cfg)
        m   = cfg.get('mechanic')
        lt  = cfg.get('timer_secs', 0) * FPS if m == 'timer' else 0
        trc = cfg.get('respawn_frames', 900) if m == 'respawn_traps' else 0
        bc  = cfg.get('blackout_interval', 900) if m == 'blackout' else 0
        return (w2, e2, Player(*ppos), [], DECOY_COUNT, 0, ex, tr, 0, wg,
                lt, trc, bc, m, cfg, fh, nz, eo, SoundAbsorber())

    def calc_score(elapsed_ticks, pulses_used, level):
        """Calcula la puntuación al completar un nivel."""
        base        = 5000
        time_bonus  = max(0, 3000 - elapsed_ticks // 2)  # hasta 3000 pts por velocidad
        pulse_pen   = pulses_used * 80                    # -80 pts por pulso usado
        level_bonus = level * 500
        return max(0, base + time_bonus - pulse_pen + level_bonus)

    #  Main async loop 
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

        # RESOLUTION PICKER 
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

        # INTRO
        if state == 'intro':
            intro_tick += 1
            _MENU_OPTS = 7  # Jugar, Niveles, Editor, Clasificacion, Controles, Config, Salir
            for ev in events:
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        if settings_open:
                            settings_save(cfg_settings)
                            sfx_set_volume(cfg_settings.get('sfx_volume', 0.55))
                            music_set_volume(cfg_settings.get('music_volume', 0.45))
                            settings_open = False
                        else:
                            pygame.quit(); sys.exit()
                    if not settings_open:
                        if ev.key == pygame.K_UP:
                            menu_sel = (menu_sel - 1) % _MENU_OPTS
                            show_credits = False
                        if ev.key == pygame.K_DOWN:
                            menu_sel = (menu_sel + 1) % _MENU_OPTS
                            show_credits = False
                        if ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                            if menu_sel == 0:   state = 'ls'
                            elif menu_sel == 1: state = 'ls'
                            elif menu_sel == 2: state = 'editor'
                            elif menu_sel == 3: state = 'lb'; lb_tick = 0
                            elif menu_sel == 4: show_credits = not show_credits
                            elif menu_sel == 5: settings_open = True; settings_tick = 0
                            elif menu_sel == 6: pygame.quit(); sys.exit()
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if settings_open:
                        s_rects = draw_settings_menu(screen, font, small_font, settings_tick,
                                                     cfg_settings, BLACK=BLACK, CYAN=CYAN,
                                                     WHITE=WHITE, GREEN=GREEN, GOLD=GOLD)
                        if s_rects['sfx_up'].collidepoint(ev.pos):
                            cfg_settings['sfx_volume'] = min(1.0, round(cfg_settings['sfx_volume'] + 0.1, 1))
                        elif s_rects['sfx_down'].collidepoint(ev.pos):
                            cfg_settings['sfx_volume'] = max(0.0, round(cfg_settings['sfx_volume'] - 0.1, 1))
                        elif s_rects['hc_toggle'].collidepoint(ev.pos):
                            cfg_settings['high_contrast'] = not cfg_settings['high_contrast']
                        elif s_rects['trail_toggle'].collidepoint(ev.pos):
                            cfg_settings['show_trail'] = not cfg_settings['show_trail']
                        elif s_rects['back'].collidepoint(ev.pos):
                            settings_save(cfg_settings)
                            sfx_set_volume(cfg_settings.get('sfx_volume', 0.55))
                            music_set_volume(cfg_settings.get('music_volume', 0.45))
                            settings_open = False
                    else:
                        rects = draw_start_screen(screen, font, small_font, intro_tick, menu_sel, show_credits)
                        if   rects[0].collidepoint(ev.pos): state = 'ls'
                        elif rects[1].collidepoint(ev.pos): state = 'ls'
                        elif rects[2].collidepoint(ev.pos): state = 'editor'
                        elif rects[3].collidepoint(ev.pos): state = 'lb'; lb_tick = 0
                        elif rects[4].collidepoint(ev.pos): show_credits = not show_credits
                        elif rects[5].collidepoint(ev.pos): settings_open = True; settings_tick = 0
                        elif rects[6].collidepoint(ev.pos): pygame.quit(); sys.exit()
                        else:
                            for i, r in enumerate(rects):
                                if r.collidepoint(ev.pos):
                                    menu_sel = i
                if ev.type == pygame.FINGERDOWN:
                    sx, sy = int(ev.x * W), int(ev.y * H)
                    rects = draw_start_screen(screen, font, small_font, intro_tick, menu_sel, show_credits)
                    if   rects[0].collidepoint((sx,sy)): state = 'ls'
                    elif rects[1].collidepoint((sx,sy)): state = 'ls'
                    elif rects[2].collidepoint((sx,sy)): state = 'editor'
                    elif rects[3].collidepoint((sx,sy)): state = 'lb'; lb_tick = 0
                    elif rects[4].collidepoint((sx,sy)): show_credits = not show_credits
                    elif rects[5].collidepoint((sx,sy)): settings_open = True; settings_tick = 0
                    elif rects[6].collidepoint((sx,sy)): pygame.quit(); sys.exit()
            draw_start_screen(screen, font, small_font, intro_tick, menu_sel, show_credits)
            if settings_open:
                settings_tick += 1
                draw_settings_menu(screen, font, small_font, settings_tick, cfg_settings,
                                   BLACK=BLACK, CYAN=CYAN, WHITE=WHITE, GREEN=GREEN, GOLD=GOLD)
            music_set_state('menu')
            pygame.display.flip()
            await asyncio.sleep(0); continue

        #  LEVEL SELECT
        if state == 'ls':
            ls_tick += 1

            def _ls_draw():
                return draw_level_select(screen, ls_tick, current_level, max_unlocked,
                                         font, small_font,
                                         ls_tab=ls_tab, custom_sel=custom_sel,
                                         custom_names=custom_names,
                                         coop_enabled=coop_enabled)

            def _launch_normal():
                nonlocal walls, enemies, player, pulses, decoys, tick, exit_rect
                nonlocal traps, micro_pulse_timer, wall_grid
                nonlocal lv_timer, trap_respawn_cd, blackout_cd, mech, active_cfg
                nonlocal score, pulse_count, game_ticks, sfx_played, player2, paused
                nonlocal pause_origin, state
                nonlocal floor_hazards, noise_zones, echo_orbs, rocks, absorber
                nonlocal rock_mode, heartbeat_t, mimics, stalkers
                (walls, enemies, player, pulses, decoys, tick, exit_rect,
                 traps, micro_pulse_timer, wall_grid,
                 lv_timer, trap_respawn_cd, blackout_cd, mech, active_cfg,
                 floor_hazards, noise_zones, echo_orbs, absorber) = new_game(current_level)
                mimics   = [e for e in enemies if isinstance(e, MimicEnemy)]
                stalkers = [e for e in enemies if isinstance(e, StalkerEnemy)]
                rocks = []; rock_mode = False; heartbeat_t = 0
                score = 0; pulse_count = 0; game_ticks = 0; sfx_played = False
                player2 = Player2(player.x + TILE, player.y) if coop_enabled else None
                paused = False; pause_origin = 'ls'; state = 'play'
                play_sfx('start'); music_set_state('play')

            def _launch_custom(idx):
                nonlocal walls, enemies, player, pulses, decoys, tick, exit_rect
                nonlocal traps, micro_pulse_timer, wall_grid
                nonlocal lv_timer, trap_respawn_cd, blackout_cd, mech, active_cfg
                nonlocal score, pulse_count, game_ticks, sfx_played, player2, paused
                nonlocal pause_origin, state
                nonlocal floor_hazards, noise_zones, echo_orbs, rocks, absorber
                nonlocal rock_mode, heartbeat_t, mimics, stalkers
                data = custom_level_load(custom_names[idx])
                if not data:
                    return
                grid = data
                w2, e2, ppos2, ex2, tr2, wg2 = build_map_from_editor(
                    grid, COLS, ROWS, TILE,
                    Wall, BatEnemy, Enemy, SoundTrap, ExitTile, MAT_NORMAL)
                walls, enemies, exit_rect, traps, wall_grid = w2, e2, ex2, tr2, wg2
                player = Player(*ppos2)
                pulses = []; decoys = DECOY_COUNT; tick = 0
                micro_pulse_timer = lv_timer = trap_respawn_cd = blackout_cd = 0
                mech = None; active_cfg = {}
                floor_hazards = []; noise_zones = []; echo_orbs = []
                rocks = []; absorber = SoundAbsorber(); rock_mode = False; heartbeat_t = 0
                mimics = []; stalkers = []
                score = 0; pulse_count = 0; game_ticks = 0; sfx_played = False
                player2 = Player2(player.x + TILE, player.y) if coop_enabled else None
                paused = False; pause_origin = 'ls'; state = 'play'
                play_sfx('start'); music_set_state('play')

            for ev in events:
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        state = 'intro'; show_credits = False
                    elif ev.key == pygame.K_c:
                        coop_enabled = not coop_enabled
                    elif ls_tab == "normal":
                        if ev.key == pygame.K_UP:
                            current_level = max(0, current_level - 1)
                        elif ev.key == pygame.K_DOWN:
                            current_level = min(max_unlocked, current_level + 1)
                        elif ev.key in (pygame.K_RETURN, pygame.K_SPACE) and current_level <= max_unlocked:
                            _launch_normal()
                    else:
                        if ev.key == pygame.K_UP:
                            custom_sel = max(0, custom_sel - 1)
                        elif ev.key == pygame.K_DOWN:
                            custom_sel = min(max(0, len(custom_names)-1), custom_sel + 1)
                        elif ev.key in (pygame.K_RETURN, pygame.K_SPACE) and custom_names:
                            _launch_custom(custom_sel)

                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    (crects, play_r, tab_nr, tab_cr,
                     c_crects, c_play_r, c_del_r) = _ls_draw()

                    if tab_nr.collidepoint(ev.pos):
                        ls_tab = "normal"
                    elif tab_cr.collidepoint(ev.pos):
                        ls_tab = "custom"
                        custom_names = custom_levels_list()
                    elif ls_tab == "normal":
                        for i, r in enumerate(crects):
                            if r.collidepoint(ev.pos) and i <= max_unlocked:
                                current_level = i
                        if play_r.collidepoint(ev.pos) and current_level <= max_unlocked:
                            _launch_normal()
                    else:
                        for i, r in enumerate(c_crects):
                            if r.collidepoint(ev.pos):
                                custom_sel = i
                        if c_del_r.width > 0 and c_del_r.collidepoint(ev.pos) and custom_names:
                            custom_level_delete(custom_names[custom_sel])
                            custom_names = custom_levels_list()
                            custom_sel = max(0, min(custom_sel, len(custom_names)-1))
                        elif c_play_r.collidepoint(ev.pos) and custom_names:
                            _launch_custom(custom_sel)

            music_set_state('menu')
            _ls_draw()
            pygame.display.flip()
            await asyncio.sleep(0); continue

        # LEVEL COMPLETE 
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

        # LEADERBOARD
        if state == 'lb':
            lb_tick += 1
            music_set_state('none')
            for ev in events:
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    state = 'intro'
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    back_r, local_r, global_r = draw_leaderboard(
                        screen, font, small_font, lb_tick,
                        LEVEL_CONFIGS, TILE, BLACK, CYAN, GOLD, GREEN, DARK_CYAN,
                        lb_tab=lb_tab)
                    if back_r.collidepoint(ev.pos):
                        state = 'intro'
                    elif local_r.collidepoint(ev.pos):
                        lb_tab = 'local'
                    elif global_r.collidepoint(ev.pos):
                        lb_tab = 'global'
                        ol_fetch_all(N_LEVELS, force=False)
            # Trigger a background fetch when first entering global tab
            if lb_tab == 'global' and lb_tick == 1:
                ol_fetch_all(N_LEVELS, force=False)
            draw_leaderboard(screen, font, small_font, lb_tick,
                             LEVEL_CONFIGS, TILE, BLACK, CYAN, GOLD, GREEN, DARK_CYAN,
                             lb_tab=lb_tab)
            pygame.display.flip()
            await asyncio.sleep(0); continue

        # NAME INPUT  (shown only on new record)
        if state == 'name_input':
            ni_tick += 1
            for ev in events:
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        # Skip saving name — save with placeholder and continue
                        lb_submit(current_level, "---", game_ticks, score)
                        ol_submit(current_level, "---", game_ticks, score)
                        state = 'comp'; comp_tick = 0
                    elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        final_name = name_buf.strip() or "---"
                        lb_submit(current_level, final_name, game_ticks, score)
                        ol_submit(current_level, final_name, game_ticks, score)
                        state = 'comp'; comp_tick = 0
                    elif ev.key == pygame.K_BACKSPACE:
                        name_buf = name_buf[:-1]
                    else:
                        ch = ev.unicode
                        if ch and ch.isprintable() and len(name_buf) < 16:
                            name_buf += ch
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    conf_r = draw_name_input(
                        screen, font, small_font, ni_tick, name_buf,
                        current_level, score, game_ticks,
                        LEVEL_CONFIGS, TILE, BLACK, CYAN, GOLD, GREEN, WHITE)
                    if conf_r.collidepoint(ev.pos) and name_buf.strip():
                        final_name = name_buf.strip()
                        lb_submit(current_level, final_name, game_ticks, score)
                        ol_submit(current_level, final_name, game_ticks, score)
                        state = 'comp'; comp_tick = 0
            draw_name_input(
                screen, font, small_font, ni_tick, name_buf,
                current_level, score, game_ticks,
                LEVEL_CONFIGS, TILE, BLACK, CYAN, GOLD, GREEN, WHITE)
            pygame.display.flip()
            await asyncio.sleep(0); continue

        # LEVEL EDITOR

        if state == 'editor':
            editor_tick += 1
            mpos = pygame.mouse.get_pos()
            # Compute which grid cell the mouse is over
            if mpos[1] >= 38:
                mc_r = (mpos[1] - 38) // TILE
                mc_c = mpos[0] // TILE
                if 0 <= mc_r < ROWS and 0 <= mc_c < COLS:
                    mouse_cell = (mc_r, mc_c)
                else:
                    mouse_cell = None
            else:
                mouse_cell = None

            for ev in events:
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        state = 'intro'
                    # Number keys 1-8 select palette
                    if pygame.K_1 <= ev.key <= pygame.K_8:
                        editor_sel = ev.key - pygame.K_1
                if ev.type == pygame.MOUSEWHEEL:
                    editor_sel = (editor_sel - ev.y) % len(EDITOR_PALETTE)
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    # Check action buttons first
                    pr, cr, br, sr = draw_editor(screen, font, small_font, editor_grid,
                                                 editor_sel, editor_tick, mouse_cell,
                                                 TILE, COLS, ROWS, WHITE, CYAN, DARK_CYAN)
                    if pr.collidepoint(mpos):
                        # Launch the custom map
                        w2, e2, ppos2, ex2, tr2, wg2 = build_map_from_editor(
                            editor_grid, COLS, ROWS, TILE,
                            Wall, BatEnemy, Enemy, SoundTrap, ExitTile, MAT_NORMAL)
                        walls, enemies, exit_rect, traps, wall_grid = w2, e2, ex2, tr2, wg2
                        player = Player(*ppos2)
                        pulses = []; decoys = DECOY_COUNT; tick = 0
                        micro_pulse_timer = lv_timer = trap_respawn_cd = blackout_cd = 0
                        mech = None; active_cfg = {}
                        score = 0; pulse_count = 0; game_ticks = 0; sfx_played = False
                        player2 = None
                        paused = False; pause_origin = 'editor'
                        state = 'play'
                    elif sr.collidepoint(mpos):
                        editor_save_open = True
                        editor_save_buf  = ""
                        editor_save_tick = 0
                    elif cr.collidepoint(mpos):
                        editor_grid = empty_editor_grid(COLS, ROWS)
                    elif br.collidepoint(mpos):
                        state = 'intro'
                    elif mouse_cell:
                        sym = EDITOR_PALETTE[editor_sel][0]
                        r2, c2 = mouse_cell
                        editor_grid[r2][c2] = '.' if sym == 'X' else sym

            # Save dialog keyboard handling
            if editor_save_open:
                for ev in events:
                    if ev.type == pygame.KEYDOWN:
                        if ev.key == pygame.K_ESCAPE:
                            editor_save_open = False
                        elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            if editor_save_buf.strip():
                                custom_level_save(editor_save_buf.strip(), editor_grid)
                                editor_save_open = False
                        elif ev.key == pygame.K_BACKSPACE:
                            editor_save_buf = editor_save_buf[:-1]
                        else:
                            ch = ev.unicode
                            if ch and ch.isprintable() and len(editor_save_buf) < 20:
                                editor_save_buf += ch

            # Drag-paint on hold (skip when save dialog open)
            if not editor_save_open and pygame.mouse.get_pressed()[0] and mouse_cell:
                sym = EDITOR_PALETTE[editor_sel][0]
                r2, c2 = mouse_cell
                editor_grid[r2][c2] = '.' if sym == 'X' else sym

            pr, cr, br, sr = draw_editor(screen, font, small_font, editor_grid,
                                         editor_sel, editor_tick, mouse_cell,
                                         TILE, COLS, ROWS, WHITE, CYAN, DARK_CYAN)
            if editor_save_open:
                editor_save_tick += 1
                existing = custom_levels_list()
                ok_r2, canc_r2 = draw_save_level_dialog(
                    screen, font, small_font, editor_save_tick,
                    editor_save_buf, existing, BLACK=BLACK, CYAN=CYAN, WHITE=WHITE)
                for ev in events:
                    if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                        if ok_r2.collidepoint(ev.pos) and editor_save_buf.strip():
                            custom_level_save(editor_save_buf.strip(), editor_grid)
                            editor_save_open = False
                        elif canc_r2.collidepoint(ev.pos):
                            editor_save_open = False
            pygame.display.flip()
            await asyncio.sleep(0); continue


        # GAMEPLAY
        if not paused:
            tick += 1

        for ev in events:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if not player.caught and not player.won:
                        paused = not paused
                        pause_tick = 0
                if ev.key == pygame.K_r and not paused:
                    if pause_origin == 'ls':
                        (walls, enemies, player, pulses, decoys, tick, exit_rect,
                         traps, micro_pulse_timer, wall_grid,
                         lv_timer, trap_respawn_cd, blackout_cd, mech, active_cfg,
                         floor_hazards, noise_zones, echo_orbs, absorber) = new_game(current_level)
                        mimics   = [e for e in enemies if isinstance(e, MimicEnemy)]
                        stalkers = [e for e in enemies if isinstance(e, StalkerEnemy)]
                        rocks = []; rock_mode = False; heartbeat_t = 0
                    else:
                        w2, e2, ppos2, ex2, tr2, wg2 = build_map_from_editor(
                            editor_grid, COLS, ROWS, TILE,
                            Wall, BatEnemy, Enemy, SoundTrap, ExitTile, MAT_NORMAL)
                        walls, enemies, exit_rect, traps, wall_grid = w2, e2, ex2, tr2, wg2
                        player = Player(*ppos2)
                        floor_hazards = []; noise_zones = []; echo_orbs = []
                        rocks = []; absorber = SoundAbsorber(); rock_mode = False
                        mimics = []; stalkers = []
                    pulses = []; decoys = DECOY_COUNT; tick = 0
                    score = 0; pulse_count = 0; game_ticks = 0; sfx_played = False
                    paused = False
                # New: Q toggles rock-throw mode
                if ev.key == pygame.K_q and not paused:
                    rock_mode = not rock_mode
                # New: E activates sound absorber
                if ev.key == pygame.K_e and not paused and not player.caught and not player.won:
                    absorber.activate()
                # New: F fires focused cone sonar
                if ev.key == pygame.K_f and not paused and not player.caught and not player.won:
                    mx, my = pygame.mouse.get_pos()
                    ox2 = int(max(0, min(player.x - VIEW_W//2, MAP_W - VIEW_W)))
                    oy2 = int(max(0, min(player.y - VIEW_H//2, MAP_H - VIEW_H)))
                    wx2 = mx + ox2; wy2 = (my - HUD_TOP) + oy2
                    ang = math.atan2(wy2 - player.y, wx2 - player.x)
                    # fire 5 thin rays in the cone
                    for da in [-2, -1, 0, 1, 2]:
                        ra = ang + math.radians(da * (CONE_ANGLE / 2))
                        p_cone = SonarPulse(player.x, player.y, (0, 255, 180),
                                            max_radius=CONE_RANGE)
                        pulses.append(p_cone)
                    pulse_count += 1
                    play_sfx("sonar")
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
                     lv_timer, trap_respawn_cd, blackout_cd, mech, active_cfg,
                     floor_hazards, noise_zones, echo_orbs, absorber) = new_game(current_level)
                    mimics   = [e for e in enemies if isinstance(e, MimicEnemy)]
                    stalkers = [e for e in enemies if isinstance(e, StalkerEnemy)]
                    rocks = []; rock_mode = False; heartbeat_t = 0
                    score = 0; pulse_count = 0; game_ticks = 0
                elif m_rect_d.collidepoint(ev.pos):  # Menú
                    state = 'ls'; ls_tick = 0
            # Mouse: sonar / decoy / rock
            if ev.type == pygame.MOUSEBUTTONDOWN and not player.caught and not player.won:
                ox = int(max(0, min(player.x - VIEW_W//2, MAP_W - VIEW_W)))
                oy = int(max(0, min(player.y - VIEW_H//2, MAP_H - VIEW_H)))
                wx = ev.pos[0] + ox
                wy = (ev.pos[1] - HUD_TOP) + oy
                if ev.button == 1:
                    if rock_mode:
                        if math.hypot(wx - player.x, wy - player.y) <= ROCK_RANGE:
                            rocks.append(ThrowableRock(player.x, player.y, wx, wy))
                        rock_mode = False
                    else:
                        new_p = SonarPulse(player.x, player.y, CYAN)
                        pulses.append(new_p)
                        pulse_count += 1
                        play_sfx("sonar")
                        for st in stalkers:
                            st.on_sonar_detected(player.x, player.y)
                        for mc2 in mimics:
                            if dist((mc2.x, mc2.y), (player.x, player.y)) < SONAR_MAX_RADIUS:
                                mc2.on_sonar_hit()
                elif ev.button == 3 and decoys > 0:
                    pulses.append(SonarPulse(wx, wy, PURPLE, is_decoy=True))
                    for e in enemies:
                        if dist((e.x,e.y),(wx,wy)) < SONAR_MAX_RADIUS: e.alert(wx, wy)
                    decoys -= 1
                    play_sfx("sonar")


        # Movement (keyboard)
        if not player.caught and not player.won:
            keys     = pygame.key.get_pressed()
            sneaking = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
            in_noise = any(nz.contains(player.x, player.y) for nz in noise_zones)
            # P1 uses WASD only — arrow keys reserved for Player 2 (co-op)
            dx = int(keys[pygame.K_d]) - int(keys[pygame.K_a])
            dy = int(keys[pygame.K_s]) - int(keys[pygame.K_w])
            if dx or dy:
                ndx, ndy = normalize(dx, dy)
                player.move(ndx, ndy, walls, sneaking)
                if not sneaking and not in_noise:
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
            # Co-op: player 2 exit check
            if player2 and exit_rect and pygame.Rect(
                    player2.x - PLAYER_RADIUS, player2.y - PLAYER_RADIUS,
                    PLAYER_RADIUS*2, PLAYER_RADIUS*2).colliderect(exit_rect.rect):
                player.won = True   # both players win together

        # Co-op: move player 2
        if player2 and not player.caught and not player.won:
            keys2 = pygame.key.get_pressed()
            moved2, sneak2 = player2.handle_keys(keys2, walls)
            if moved2 and not sneak2:
                micro_pulse_timer2 += 1
                if micro_pulse_timer2 >= MICRO_PULSE_INTERVAL:
                    micro_pulse_timer2 = 0
                    pulses.append(SonarPulse(player2.x, player2.y, (0,100,130), max_radius=60))
            else:
                micro_pulse_timer2 = 0
            # Enemy proximity for player2
            for e in enemies:
                if dist((e.x, e.y), (player2.x, player2.y)) < 36:
                    player.caught = True

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
                play_sfx("win")
                sfx_played = True
                music_set_state("win")
            # Check record BEFORE saving
            is_normal_level = active_cfg in LEVEL_CONFIGS
            if is_normal_level and lb_is_record(current_level, game_ticks):
                # New record! Ask for name first
                name_buf = ""
                ni_tick  = 0
                state    = 'name_input'
            else:
                # Not a record (or editor level) — go straight to result screen
                if is_normal_level:
                    lb_submit(current_level, "---", game_ticks, score)
                state = 'comp'; comp_tick = 0
            await asyncio.sleep(0); continue

        if player.caught and not sfx_played:
            play_sfx("lose")
            sfx_played = True
            music_set_state("lose")

        if not paused:
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
                        play_sfx("trap")

                # NEW: floor hazards
                sneaking_now = pygame.key.get_pressed()[pygame.K_LSHIFT] or \
                               pygame.key.get_pressed()[pygame.K_RSHIFT]
                for fh in floor_hazards:
                    fh.update()
                    fhp = fh.check(player, sneaking=sneaking_now)
                    if fhp:
                        pulses.append(fhp)
                        for e in enemies: e.alert(fh.cx, fh.cy)
                floor_hazards = [fh for fh in floor_hazards if not fh.gone or fh.htype == HAZARD_WATER]

                # NEW: noise zones
                for nz in noise_zones:
                    nz.update()

                # NEW: echo orbs
                for orb in echo_orbs:
                    orb.update()
                    orb.check(player)

                # NEW: rocks in flight
                new_rocks = []
                for rock in rocks:
                    rp = rock.update(walls)
                    if rp:
                        pulses.append(rp)
                        for e in enemies: e.alert(rock.x, rock.y)
                    if not rock.dead:
                        new_rocks.append(rock)
                rocks = new_rocks

                # NEW: absorber update
                absorber.update()

                # NEW: mimic update
                for mc2 in mimics:
                    mc2.update(player)

                # NEW: heartbeat based on alert level
                if not player.caught and not player.won:
                    n_alert = sum(1 for e in enemies
                                  if hasattr(e, 'alert_t') and e.alert_t > 0)
                    if n_alert > 0:
                        ratio = min(1.0, n_alert / max(len(enemies), 1))
                        hb_interval = int(HEARTBEAT_MIN - ratio * (HEARTBEAT_MIN - HEARTBEAT_MAX))
                        heartbeat_t -= 1


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
        for fh in floor_hazards: fh.draw(game_surf, offset)
        for nz in noise_zones:   nz.draw(game_surf, offset)
        for orb in echo_orbs:    orb.draw(game_surf, offset)
        for rock in rocks:       rock.draw(game_surf, offset)
        for mc2 in mimics:       mc2.draw(game_surf, offset)
        for p in pulses:         p.draw(game_surf, offset)
        for e in enemies:        e.draw(game_surf, offset)
        player.draw(game_surf, offset)
        if player2:
            player2.draw(game_surf, offset)


        screen.blit(game_surf, (0, HUD_TOP))

        alert_count = sum(1 for e in enemies if e.alert_t > 0)

        # Adaptive music state (drives alert vs. play) 
        if state == 'play' and not player.caught and not player.won:
            if alert_count > 0:
                music_set_state('alert')
            else:
                music_set_state('play')
        music_tick()

        draw_hud(screen, font, small_font, decoys, alert_count,
                 player.caught, player.won, current_level, lv_timer, mech, tick,
                 score, pulse_count)
        # Extra HUD elements for new features
        absorber.draw_hud(screen, W - 200, H - 22, small_font)
        if rock_mode:
            try: rm_f = pygame.font.SysFont("consolas", 13, bold=True)
            except: rm_f = small_font
            rm_s = rm_f.render("[ROCA] Clic para lanzar", True, (255, 200, 80))
            screen.blit(rm_s, (W//2 - rm_s.get_width()//2, H - 40))
        # Echo orb messages (draw on screen overlay)
        for orb in echo_orbs:
            orb.draw_message(screen, small_font)
        # Heartbeat vignette
        n_alert2 = sum(1 for e in enemies if hasattr(e, 'alert_t') and e.alert_t > 0)
        if n_alert2 > 0 and not player.caught and not player.won:
            ratio2 = min(1.0, n_alert2 / max(len(enemies), 1))
            hb_alpha = int(40 * ratio2 * (math.sin(tick * 0.15 * (1 + ratio2)) * 0.5 + 0.5))
            if hb_alpha > 2:
                vign = pygame.Surface((W, H), pygame.SRCALPHA)
                vign.fill((80, 0, 0, hb_alpha))
                screen.blit(vign, (0, 0))

        # Pause menu overlay 
        if paused:
            pause_tick += 1
            # freeze game progression
            p_rects = draw_pause_menu(screen, font, small_font, pause_tick,
                                      from_editor=(pause_origin == 'editor'),
                                      BLACK=BLACK, CYAN=CYAN, WHITE=WHITE)
            # handle pause button clicks
            for ev in events:
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if p_rects['resume'].collidepoint(ev.pos):
                        paused = False
                    elif 'editor' in p_rects and p_rects['editor'].collidepoint(ev.pos):
                        paused = False; state = 'editor'
                    elif p_rects['menu'].collidepoint(ev.pos):
                        paused = False; state = 'intro'; show_credits = False

        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    asyncio.run(main())

