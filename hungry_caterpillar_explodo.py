# hungry_caterpillar_explodo.py
# A hungry-caterpillar-inspired Snake spinoff with explosive food and debris obstacles.
# Requires: pygame (pip install pygame)

import math
import random
import sys
from dataclasses import dataclass, field
from typing import Deque, List, Optional, Tuple
from collections import deque

import pygame

# ----------------------------
# Config
# ----------------------------
GRID_W, GRID_H = 28, 20         # grid size
TILE = 28                       # pixel size per cell
MARGIN = 24                     # pixels margin around playfield
FPS = 14                        # base frames per second (snake tick speed)
SCREEN_W = GRID_W * TILE + MARGIN * 2
SCREEN_H = GRID_H * TILE + MARGIN * 2
FONT_NAME = "freesansbold.ttf"

SAFE_LEAF_COLOR = (90, 200, 90)
NITRO_COLOR = (255, 150, 60)
NITRO_SPARK = (255, 220, 120)
ROCK_COLOR = (110, 110, 130)
HEAD_COLOR = (80, 230, 170)
BODY_COLOR = (50, 170, 130)
BG_COLOR = (20, 24, 28)
GRID_COLOR = (32, 38, 44)
TEXT_COLOR = (240, 240, 245)
SHADOW = (0, 0, 0)

# Nitro (explosive fruit) tuning
NITRO_MIN_FUSE = 6.0  # seconds
NITRO_MAX_FUSE = 10.0
NITRO_BLAST_RADIUS = 2.4   # in grid tiles (Euclidean)
NITRO_DEBRIS_MIN = 6
NITRO_DEBRIS_MAX = 12
NITRO_SPAWN_CHANCE = 0.40  # chance next food is nitro instead of leaf

# Screen shake tuning
SHAKE_DECAY = 0.85
SHAKE_POWER = 10

random.seed()


# ----------------------------
# Utility
# ----------------------------
def grid_to_px(cell: Tuple[int, int]) -> Tuple[int, int]:
    x, y = cell
    return (MARGIN + x * TILE, MARGIN + y * TILE)

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

def within_bounds(x, y):
    return 0 <= x < GRID_W and 0 <= y < GRID_H


# ----------------------------
# Entities
# ----------------------------
@dataclass
class Explosion:
    center: Tuple[int, int]
    radius_tiles: float
    t: float = 0.0          # elapsed time (sec)
    duration: float = 0.45  # seconds

    def alive(self):
        return self.t < self.duration


@dataclass
class Food:
    pos: Tuple[int, int]
    kind: str  # "leaf" or "nitro"
    # Nitro fields
    fuse: float = 0.0       # seconds left (for nitro only)
    fuse_total: float = 0.0 # initial fuse (for bar)

@dataclass
class GameState:
    snake: Deque[Tuple[int, int]] = field(default_factory=deque)
    dir: Tuple[int, int] = (1, 0)
    grow: int = 0
    rocks: set = field(default_factory=set)
    food: Optional[Food] = None
    score: int = 0
    best: int = 0
    alive: bool = True
    paused: bool = False
    explosions: List[Explosion] = field(default_factory=list)
    particles: List[Tuple[float, float, float, float, float]] = field(default_factory=list)  # x,y,vx,vy,life
    shake: float = 0.0


# ----------------------------
# Game logic
# ----------------------------
def spawn_snake(gs: GameState):
    gs.snake.clear()
    cx, cy = GRID_W // 3, GRID_H // 2
    for i in range(4, -1, -1):  # head last append (rightmost)
        gs.snake.append((cx - i, cy))
    gs.dir = (1, 0)
    gs.grow = 0

def empty_cells(gs: GameState) -> List[Tuple[int, int]]:
    occ = set(gs.snake) | gs.rocks
    if gs.food:
        occ.add(gs.food.pos)
    return [(x, y) for y in range(GRID_H) for x in range(GRID_W) if (x, y) not in occ]

def rand_empty(gs: GameState) -> Optional[Tuple[int, int]]:
    cells = empty_cells(gs)
    return random.choice(cells) if cells else None

def spawn_food(gs: GameState, force_leaf: bool = False):
    pos = rand_empty(gs)
    if not pos:
        return
    if not force_leaf and random.random() < NITRO_SPAWN_CHANCE:
        fuse = random.uniform(NITRO_MIN_FUSE, NITRO_MAX_FUSE)
        gs.food = Food(pos=pos, kind="nitro", fuse=fuse, fuse_total=fuse)
    else:
        gs.food = Food(pos=pos, kind="leaf")

def spawn_rocks(gs: GameState, n: int):
    for _ in range(n):
        p = rand_empty(gs)
        if p:
            gs.rocks.add(p)

def step_snake(gs: GameState):
    if not gs.alive or gs.paused:
        return
    hx, hy = gs.snake[-1]
    dx, dy = gs.dir
    nx, ny = hx + dx, hy + dy
    if not within_bounds(nx, ny):
        gs.alive = False
        return
    new_head = (nx, ny)

    # self-collision
    if new_head in gs.snake:
        gs.alive = False
        return

    # rock collision
    if new_head in gs.rocks:
        gs.alive = False
        return

    gs.snake.append(new_head)
    if gs.grow > 0:
        gs.grow -= 1
    else:
        gs.snake.popleft()

    # food check
    if gs.food and new_head == gs.food.pos:
        if gs.food.kind == "leaf":
            gs.grow += 1
            gs.score += 10
            burst_particles(gs, new_head, count=10, speed=120, color=SAFE_LEAF_COLOR)
            spawn_food(gs)
        else:  # nitro eaten
            gs.grow += 2
            gs.score += 25
            burst_particles(gs, new_head, count=14, speed=150, color=NITRO_SPARK)
            trigger_explosion(gs, new_head, player_trigger=True)
            spawn_food(gs)

def trigger_explosion(gs: GameState, center: Tuple[int, int], player_trigger=False):
    # Screen shake
    gs.shake = max(gs.shake, SHAKE_POWER)
    # Explosion anim
    gs.explosions.append(Explosion(center=center, radius_tiles=NITRO_BLAST_RADIUS))
    # Debris ring
    debris_n = random.randint(NITRO_DEBRIS_MIN, NITRO_DEBRIS_MAX)
    ring_positions = ring_cells(center, radius=NITRO_BLAST_RADIUS)
    random.shuffle(ring_positions)
    for p in ring_positions[:debris_n]:
        if p not in gs.snake and p not in gs.rocks and within_bounds(*p):
            gs.rocks.add(p)

    # Player too close? (blast = Euclidean radius)
    hx, hy = gs.snake[-1]
    if dist(center, (hx, hy)) <= NITRO_BLAST_RADIUS:
        gs.alive = False

def dist(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    return math.hypot(a[0]-b[0], a[1]-b[1])

def ring_cells(center: Tuple[int, int], radius: float) -> List[Tuple[int, int]]:
    cx, cy = center
    cells = []
    r2 = radius ** 2
    for y in range(cy - math.ceil(radius) - 1, cy + math.ceil(radius) + 2):
        for x in range(cx - math.ceil(radius) - 1, cx + math.ceil(radius) + 2):
            if within_bounds(x, y):
                d2 = (x - cx) ** 2 + (y - cy) ** 2
                if r2 * 0.6 <= d2 <= r2 * 1.3:
                    cells.append((x, y))
    return cells

def burst_particles(gs: GameState, cell: Tuple[int, int], count=8, speed=120, color=(255,255,255)):
    px, py = grid_to_px(cell)
    cx, cy = px + TILE/2, py + TILE/2
    for _ in range(count):
        ang = random.uniform(0, math.tau)
        v = random.uniform(speed*0.6, speed*1.2)
        vx, vy = math.cos(ang)*v, math.sin(ang)*v
        life = random.uniform(0.25, 0.6)
        gs.particles.append([cx, cy, vx, vy, life, *color])

def update_particles(gs: GameState, dt: float):
    g = 420  # gravity for a playful arc
    newp = []
    for p in gs.particles:
        x, y, vx, vy, life, r, gcol, b = p
        life -= dt
        if life > 0:
            vy += g * dt * 0.25
            x += vx * dt
            y += vy * dt
            newp.append([x, y, vx, vy, life, r, gcol, b])
    gs.particles = newp

def update_food(gs: GameState, dt: float):
    if not gs.food:
        return
    if gs.food.kind == "nitro":
        gs.food.fuse -= dt
        if gs.food.fuse <= 0:
            # BOOM where it stands
            trigger_explosion(gs, gs.food.pos, player_trigger=False)
            gs.food = None
            # After an explosion, spawn a *leaf* to give reprieve
            spawn_food(gs, force_leaf=True)

# ----------------------------
# Rendering
# ----------------------------
def draw_grid(surf):
    for y in range(GRID_H + 1):
        ypx = MARGIN + y * TILE
        pygame.draw.line(surf, GRID_COLOR, (MARGIN, ypx), (MARGIN + GRID_W * TILE, ypx), 1)
    for x in range(GRID_W + 1):
        xpx = MARGIN + x * TILE
        pygame.draw.line(surf, GRID_COLOR, (xpx, MARGIN), (xpx, MARGIN + GRID_H * TILE), 1)

def draw_cell(surf, cell, color, inset=3, border_radius=6):
    x, y = grid_to_px(cell)
    rect = pygame.Rect(x + inset, y + inset, TILE - inset*2, TILE - inset*2)
    pygame.draw.rect(surf, color, rect, border_radius=border_radius)
    return rect

def draw_food(surf, f: Food, t: float):
    if f.kind == "leaf":
        rect = draw_cell(surf, f.pos, SAFE_LEAF_COLOR, inset=4, border_radius=8)
        # Leaf vein
        pygame.draw.line(surf, (40, 140, 60), rect.midleft, rect.midright, 2)
    else:
        # Nitro berry: pulsing fill + spark
        pulse = (math.sin(t*8) * 0.5 + 0.5) * 0.35 + 0.5
        base = blend(NITRO_COLOR, (255, 100, 0), pulse)
        rect = draw_cell(surf, f.pos, base, inset=4, border_radius=8)
        # Spark glint
        cx, cy = rect.center
        pygame.draw.circle(surf, NITRO_SPARK, (cx, cy), 4)
        # Fuse bar
        if f.fuse_total > 0:
            pct = clamp(f.fuse / f.fuse_total, 0, 1)
            barw = int((TILE - 8) * pct)
            barx, bary = rect.left + 4, rect.bottom + 2
            pygame.draw.rect(surf, (40,40,40), (barx, bary, TILE-8, 5), border_radius=3)
            pygame.draw.rect(surf, (255,180,80), (barx, bary, barw, 5), border_radius=3)

def draw_rocks(surf, rocks):
    for r in rocks:
        rect = draw_cell(surf, r, ROCK_COLOR, inset=5, border_radius=6)
        # Cracks
        pygame.draw.line(surf, (80,80,95), (rect.left+4, rect.centery), (rect.centerx, rect.top+4), 2)
        pygame.draw.line(surf, (80,80,95), (rect.centerx, rect.top+4), (rect.right-4, rect.bottom-4), 2)

def draw_snake(surf, snake):
    # body
    for i, c in enumerate(list(snake)[:-1]):
        draw_cell(surf, c, BODY_COLOR, inset=5, border_radius=8)
    # head glow
    head = snake[-1]
    hx, hy = grid_to_px(head)
    center = (hx + TILE//2, hy + TILE//2)
    pygame.draw.circle(surf, (0,0,0), center, TILE//2 + 8)
    pygame.draw.circle(surf, (60, 200, 160), center, TILE//2 + 6, width=3)
    draw_cell(surf, head, HEAD_COLOR, inset=4, border_radius=9)
    # eyes
    rect = pygame.Rect(hx+6, hy+6, TILE-12, TILE-12)
    pygame.draw.circle(surf, (255,255,255), (rect.left+6, rect.centery), 3)
    pygame.draw.circle(surf, (255,255,255), (rect.right-6, rect.centery), 3)
    pygame.draw.circle(surf, (30,30,30), (rect.left+6, rect.centery), 1)
    pygame.draw.circle(surf, (30,30,30), (rect.right-6, rect.centery), 1)

def blend(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def draw_explosions(surf, explosions, dt):
    for ex in explosions:
        ex.t += dt
        if not ex.alive(): 
            continue
        px, py = grid_to_px(ex.center)
        cx, cy = px + TILE/2, py + TILE/2
        # ring expands and fades
        k = ex.t / ex.duration
        rad = (ex.radius_tiles * TILE) * (0.4 + 0.8*k)
        alpha = int(255 * (1 - k))
        color = (*NITRO_SPARK, )
        s = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 210, 120, alpha), (cx, cy), int(rad), width=8)
        pygame.draw.circle(s, (255, 140, 60, int(alpha*0.8)), (cx, cy), max(2, int(rad*0.65)), width=6)
        surf.blit(s, (0, 0))

def clean_explosions(gs: GameState):
    gs.explosions = [e for e in gs.explosions if e.alive()]

def draw_particles(surf, particles):
    for p in particles:
        x, y, vx, vy, life, r, g, b = p
        alpha = int(255 * clamp(life * 2.0, 0, 1))
        pygame.draw.circle(surf, (r, g, b, alpha), (int(x), int(y)), 3)

def draw_ui(surf, font, gs: GameState):
    score_s = font.render(f"Score: {gs.score}", True, TEXT_COLOR)
    best_s = font.render(f"Best: {gs.best}", True, TEXT_COLOR)
    surf.blit(score_s, (MARGIN, 8))
    surf.blit(best_s, (SCREEN_W - best_s.get_width() - MARGIN, 8))

def shake_offset(gs: GameState):
    if gs.shake <= 0: 
        return 0, 0
    ox = random.uniform(-gs.shake, gs.shake)
    oy = random.uniform(-gs.shake, gs.shake)
    gs.shake *= SHAKE_DECAY
    if gs.shake < 0.5:
        gs.shake = 0
    return int(ox), int(oy)

# ----------------------------
# Main
# ----------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Hungry Caterpillar: Explodo Snack")
    clock = pygame.time.Clock()
    font = pygame.font.Font(FONT_NAME, 20)
    bigfont = pygame.font.Font(FONT_NAME, 32)

    gs = GameState()
    spawn_snake(gs)
    spawn_food(gs)
    spawn_rocks(gs, n=12)

    time_accum = 0.0  # for movement step
    running = True
    t = 0.0

    while running:
        dt = clock.tick(FPS) / 1000.0
        t += dt

        # ---------------- events
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_ESCAPE,):
                    running = False
                if e.key in (pygame.K_p,):
                    gs.paused = not gs.paused
                if not gs.alive and e.key in (pygame.K_r,):
                    # restart
                    gs.best = max(gs.best, gs.score)
                    gs = GameState(best=gs.best)
                    spawn_snake(gs)
                    spawn_food(gs)
                    spawn_rocks(gs, n=12)
                if gs.alive and not gs.paused:
                    # direction change (no reverse)
                    dx, dy = gs.dir
                    if e.key in (pygame.K_LEFT, pygame.K_a) and (dx, dy) != (1, 0):
                        gs.dir = (-1, 0)
                    elif e.key in (pygame.K_RIGHT, pygame.K_d) and (dx, dy) != (-1, 0):
                        gs.dir = (1, 0)
                    elif e.key in (pygame.K_UP, pygame.K_w) and (dx, dy) != (0, 1):
                        gs.dir = (0, -1)
                    elif e.key in (pygame.K_DOWN, pygame.K_s) and (dx, dy) != (0, -1):
                        gs.dir = (0, 1)

        if gs.alive and not gs.paused:
            time_accum += dt
            # One movement step per frame (tied to FPS), simple & snappy
            if time_accum >= (1.0 / FPS):
                time_accum = 0.0
                step_snake(gs)

            update_food(gs, dt)
            update_particles(gs, dt)
            clean_explosions(gs)

        # ---------------- draw
        screen.fill(BG_COLOR)
        ox, oy = shake_offset(gs)
        # draw playfield with offset for shake
        play = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        draw_grid(play)
        draw_rocks(play, gs.rocks)
        draw_snake(play, gs.snake)
        if gs.food:
            draw_food(play, gs.food, t)
        draw_explosions(play, gs.explosions, dt)
        draw_particles(play, gs.particles)
        draw_ui(play, font, gs)

        screen.blit(play, (ox, oy))

        if gs.paused and gs.alive:
            overlay_msg(screen, bigfont, "PAUSED", sub="Press P to resume")
        if not gs.alive:
            overlay_msg(screen, bigfont, "GAME OVER",
                        sub="Press R to restart")

        pygame.display.flip()

    pygame.quit()
    sys.exit()

def overlay_msg(surf, font, title, sub=""):
    s = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    s.fill((0, 0, 0, 120))
    surf.blit(s, (0, 0))
    tt = font.render(title, True, (255, 255, 255))
    surf.blit(tt, ((SCREEN_W - tt.get_width()) // 2, SCREEN_H // 2 - 40))
    if sub:
        f2 = pygame.font.Font(FONT_NAME, 20)
        ss = f2.render(sub, True, (230, 230, 230))
        surf.blit(ss, ((SCREEN_W - ss.get_width()) // 2, SCREEN_H // 2 + 5))

if __name__ == "__main__":
    main()
