import pygame
import random
import math
import colorsys

# ─── Constants & Data ────────────────────────────────────────
BLOCK_SIZE = 80
OBSTACLE_SPEED = 10
SPAWN_INTERVAL = 125
GROUND_LEVEL = 250
ROTATION_INTERVAL = 120

TETRIS_COLORS = [
    (0, 255, 255), (255, 255, 0), (128, 0, 128),
    (0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 165, 0)
]

TETROMINOES = {
    'I': [[(0,0),(1,0),(2,0),(3,0)], [(0,0),(0,1),(0,2),(0,3)]],
    'O': [[(0,0),(1,0),(0,1),(1,1)]],
    'T': [[(0,0),(1,0),(-1,0),(0,1)], [(0,0),(0,1),(1,1),(0,-1)],
          [(0,0),(-1,0),(1,0),(0,-1)], [(0,0),(0,-1),(-1,-1),(1,-1)]],
    'J': [[(0,0),(0,1),(0,2),(-1,2)], [(0,0),(-1,0),(-1,1),(-1,2)],
          [(0,0),(1,0),(0,1),(0,2)], [(2,0),(1,0),(0,0),(0,1)]],
    'L': [[(0,0),(0,1),(0,2),(1,0)], [(0,0),(0,1),(1,1),(2,1)],
          [(0,0),(-1,0),(0,1),(0,2)], [(0,0),(0,-1),(1,-1),(2,-1)]],
    'S': [[(0,1),(1,1),(1,0),(2,0)], [(1,-1),(1,0),(0,0),(0,1)]],
    'Z': [[(0,0),(1,0),(1,1),(2,1)], [(0,1),(0,0),(1,0),(1,-1)]]
}

# ─── Init Pygame ─────────────────────────────────────────────
pygame.init()
screen_width, screen_height = 800, 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Jumpy Blob")
clock = pygame.time.Clock()

# Pre-render 30 gradient frames (fast startup)
NUM_GRADIENT_FRAMES = 30
gradient_surfaces = []

print("CPU stretching its legs. . .")
for i in range(NUM_GRADIENT_FRAMES):
    hue = i / NUM_GRADIENT_FRAMES
    color1 = tuple(int(255 * c) for c in colorsys.hsv_to_rgb(hue, 0.4, 0.95))
    color2 = tuple(int(255 * c) for c in colorsys.hsv_to_rgb((hue + 0.12) % 1.0, 0.55, 0.75))
    
    surf = pygame.Surface((screen_width, screen_height))
    for y in range(screen_height):
        for x in range(screen_width):
            factor = (x + y) / (screen_width + screen_height)  # 45-degree diagonal
            r = int(color1[0] * (1 - factor) + color2[0] * factor)
            g = int(color1[1] * (1 - factor) + color2[1] * factor)
            b = int(color1[2] * (1 - factor) + color2[2] * factor)
            surf.set_at((x, y), (r, g, b))
    gradient_surfaces.append(surf)
print("Get Ready! Unleash the blob!")
print("Controls: SPACE to jump, R to restart game.")

# Fonts
font_large = pygame.font.SysFont(None, 96)
font_medium = pygame.font.SysFont(None, 48)
font_small = pygame.font.SysFont(None, 24)

# Blob properties
blob_x = 150
blob_y = 450
blob_radius = 40
ground_y = 450

# Blob fluid animation
current_blob_color = (128, 0, 128)
target_blob_color = current_blob_color
was_on_ground_last_frame = True
landing_frame = 0
gradient_duration = 18

blob_wobble_phase = 0.0
blob_wobble_offset_x = 0.0
blob_wobble_offset_y = 0.0
blob_squish = 1.0
blob_stretch = 1.0

WOBBLE_SMOOTH = 0.085
WOBBLE_SPEED = 0.035

# ─── Blob Particles ──────────────────────────────────────────
particles = []

PARTICLE_SPAWN_RATE = 3        # particles per frame
PARTICLE_LIFE = 28             # frames
PARTICLE_SIZE = 10
PARTICLE_DRAG = 0.92

# Physics
gravity = 0.8
velocity_y = 0
is_on_ground = True
jump_boosts_used = 0
last_space_pressed = False

FIRST_JUMP = -18.0
SECOND_JUMP = -18.0

# Game objects
obstacles = []
spawn_timer = 0
score = 0

# Game state
game_over = False

# ─── Collision Helper ────────────────────────────────────────
def circle_rect_collision(cx, cy, cr, rx, ry, rw, rh):
    closest_x = max(rx, min(cx, rx + rw))
    closest_y = max(ry, min(cy, ry + rh))
    dist_x = cx - closest_x
    dist_y = cy - closest_y
    return (dist_x**2 + dist_y**2)**0.5 <= cr

# ─── Main Loop ───────────────────────────────────────────────
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r and game_over:
                obstacles.clear()
                spawn_timer = 0
                score = 0
                blob_y = ground_y
                velocity_y = 0
                is_on_ground = True
                jump_boosts_used = 0
                current_blob_color = (128, 0, 128)
                target_blob_color = current_blob_color
                blob_wobble_offset_x = 0.0
                blob_wobble_offset_y = 0.0
                blob_squish = 1.0
                blob_stretch = 1.0
                game_over = False

    if not game_over:
        keys = pygame.key.get_pressed()
        space_pressed = keys[pygame.K_SPACE]
        space_just_pressed = space_pressed and not last_space_pressed

        if space_just_pressed:
            if is_on_ground:
                velocity_y = FIRST_JUMP
                is_on_ground = False
                jump_boosts_used = 0
            elif jump_boosts_used < 1:
                velocity_y += SECOND_JUMP
                jump_boosts_used += 1

        last_space_pressed = space_pressed

        velocity_y += gravity
        blob_y += velocity_y

        if blob_y >= ground_y:
            blob_y = ground_y
            velocity_y = 0
            is_on_ground = True
            jump_boosts_used = 0

        # Detect landing → new color
        if is_on_ground and not was_on_ground_last_frame:
            target_blob_color = random.choice(TETRIS_COLORS)
            landing_frame = pygame.time.get_ticks() // 16

        was_on_ground_last_frame = is_on_ground

        # Fluid wobble update
        blob_wobble_phase += WOBBLE_SPEED

        wobble_x = (
            math.sin(blob_wobble_phase * 0.9) * 5.2 +
            math.cos(blob_wobble_phase * 2.1) * 3.1 +
            math.sin(blob_wobble_phase * 3.4 + 0.8) * 2.0 +
            math.cos(blob_wobble_phase * 5.2 + 2.1) * 1.4
        )

        wobble_y = (
            math.cos(blob_wobble_phase * 1.2) * 4.8 +
            math.sin(blob_wobble_phase * 2.6) * 2.9 +
            math.cos(blob_wobble_phase * 4.0 + 1.3) * 2.1 +
            math.sin(blob_wobble_phase * 6.1 + 3.4) * 1.2
        )

        blob_wobble_offset_x += (wobble_x - blob_wobble_offset_x) * WOBBLE_SMOOTH
        blob_wobble_offset_y += (wobble_y - blob_wobble_offset_y) * WOBBLE_SMOOTH

        # Squash & stretch
        if velocity_y > 1.2 and blob_y > ground_y - 60:
            target_squish = 0.68 + 0.32 * (1 - min(1.0, abs(velocity_y)/22))
            target_stretch = 1.0
        elif velocity_y < -6:
            target_squish = 1.0
            target_stretch = 1.22 + 0.10 * (abs(velocity_y)/25)
        else:
            target_squish = 1.0
            target_stretch = 1.0

        blob_squish += (target_squish - blob_squish) * 0.18
        blob_stretch += (target_stretch - blob_stretch) * 0.18

        # ─── Obstacles logic ─────────────────────────────────
        spawn_timer += 1
        if spawn_timer >= SPAWN_INTERVAL:
            shape_name = random.choice(list(TETROMINOES.keys()))
            rotations = TETROMINOES[shape_name]
            rot_idx = random.randint(0, len(rotations)-1)

            obstacles.append({
                'x': screen_width + 200,
                'shape_name': shape_name,
                'current_rotation_idx': rot_idx,
                'rotation_timer': 0,
                'color': random.choice(TETRIS_COLORS)
            })
            spawn_timer = 0

        for obs in obstacles[:]:
            obs['x'] -= OBSTACLE_SPEED

            obs['rotation_timer'] += 1
            if obs['rotation_timer'] >= ROTATION_INTERVAL:
                obs['rotation_timer'] = 0
                num_rot = len(TETROMINOES[obs['shape_name']])
                obs['current_rotation_idx'] = (obs['current_rotation_idx'] + 1) % num_rot

            shape = TETROMINOES[obs['shape_name']][obs['current_rotation_idx']]
            dxs = [dx for dx, _ in shape]
            min_dx, max_dx = min(dxs), max(dxs)
            width = (max_dx - min_dx + 1) * BLOCK_SIZE

            right_edge = obs['x'] + max_dx * BLOCK_SIZE
            if right_edge < blob_x - blob_radius:
                # Simple pass detection: if obstacle is fully left of blob and not yet counted
                # (we use the list index as a proxy for uniqueness)
                if 'passed' not in obs:
                    score += 1
                    obs['passed'] = True

            if obs['x'] + min_dx * BLOCK_SIZE + width < -100:
                obstacles.remove(obs)

        # Collision check
        for obs in obstacles:
            shape = TETROMINOES[obs['shape_name']][obs['current_rotation_idx']]
            min_dy = min(dy for _, dy in shape)
            py = GROUND_LEVEL - (min_dy * BLOCK_SIZE)
            for dx, dy in shape:
                bx = obs['x'] + dx * BLOCK_SIZE
                by = py + dy * BLOCK_SIZE
                if circle_rect_collision(blob_x, blob_y, blob_radius, bx, by, BLOCK_SIZE, BLOCK_SIZE):
                    game_over = True
                    break
            if game_over:
                break

    # ─── Drawing ─────────────────────────────────────────────
    # Use pre-rendered gradient frame
    frame_idx = (pygame.time.get_ticks() // 120) % NUM_GRADIENT_FRAMES  # slower cycle ~3.6 sec
    screen.blit(gradient_surfaces[frame_idx], (0, 0))

    # Ground
    for i in range(0, screen_width + 50, 50):
        pygame.draw.rect(screen, (0, 0, 0),
                         (i, ground_y + blob_radius, 50, screen_height - ground_y - blob_radius + 20))

    # Obstacles
    for obs in obstacles:
        px = obs['x']
        color = obs['color']
        shape = TETROMINOES[obs['shape_name']][obs['current_rotation_idx']]
        min_dy = min(dy for _, dy in shape)
        py = GROUND_LEVEL - (min_dy * BLOCK_SIZE)
        for dx, dy in shape:
            bx = px + dx * BLOCK_SIZE
            by = py + dy * BLOCK_SIZE
            pygame.draw.rect(screen, color, (bx, by, BLOCK_SIZE, BLOCK_SIZE))
            pygame.draw.rect(screen, (255,255,255), (bx, by, BLOCK_SIZE, BLOCK_SIZE), 3)
            pygame.draw.rect(screen, (50,50,50), (bx+4, by+4, BLOCK_SIZE-8, BLOCK_SIZE-8), 1)

    # ─── Fluid goopy blob ────────────────────────────────────
    center_x = blob_x
    center_y = int(blob_y)

    base_r, base_g, base_b = current_blob_color

    for layer in range(8, 0, -1):
        progress = layer / 8.0
        radius = blob_radius * (0.65 + progress * 0.45)
        layer_wobble_mult = progress * 1.4
        off_x = blob_wobble_offset_x * layer_wobble_mult
        off_y = blob_wobble_offset_y * layer_wobble_mult
        rx = int(radius * 1.05)
        ry = int(radius * blob_squish * blob_stretch * (0.9 + progress * 0.2))
        brightness = 0.68 + 0.42 * progress
        col = (
            max(0, min(255, int(base_r * brightness))),
            max(0, min(255, int(base_g * brightness))),
            max(0, min(255, int(base_b * brightness)))
        )
        pygame.draw.ellipse(
            screen, col,
            (center_x + off_x - rx, center_y + off_y - ry, rx * 2, ry * 2)
        )

    # Color transition update — safer clamping
    frames_since_landing = (pygame.time.get_ticks() // 16) - landing_frame
    if frames_since_landing < gradient_duration:
        t = frames_since_landing / gradient_duration
        r = int(current_blob_color[0] * (1 - t) + target_blob_color[0] * t)
        g = int(current_blob_color[1] * (1 - t) + target_blob_color[1] * t)
        b = int(current_blob_color[2] * (1 - t) + target_blob_color[2] * t)
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        current_blob_color = (r, g, b)
    else:
        current_blob_color = target_blob_color

    # Score / UI
    if not game_over:
        score_text = font_medium.render(f"{score}", True, (0, 0, 0))
        screen.blit(score_text, (screen_width // 2 - 30, 25))
    else:
        go_text = font_large.render("GAME OVER", True, (0, 0, 0))
        score_text = font_medium.render(f"FINAL SCORE: {score}", True, (0, 0, 0))
        restart_text = font_small.render("PRESS R TO RESTART", True, (0, 255, 0))
        screen.blit(go_text, go_text.get_rect(center=(screen_width//2, screen_height//2 - 80)))
        screen.blit(score_text, score_text.get_rect(center=(screen_width//2, screen_height//2)))
        screen.blit(restart_text, restart_text.get_rect(center=(screen_width//2, screen_height//2 + 80)))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()