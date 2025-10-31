import pygame
import random
import math
from enum import Enum

# Initialize Pygame
pygame.init()

# Constants
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 600
GRID_SIZE = 20
GRID_WIDTH = WINDOW_WIDTH // GRID_SIZE
GRID_HEIGHT = WINDOW_HEIGHT // GRID_SIZE

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
RED = (255, 0, 0)
GREEN = (0, 200, 0)
LIME = (150, 255, 0)
BROWN = (101, 67, 33)

# Direction enum
class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

class Caterpillar:
    def __init__(self):
        self.body = [(GRID_WIDTH // 2, GRID_HEIGHT // 2)]
        self.direction = Direction.RIGHT
        self.grow = False
    
    def move(self):
        head_x, head_y = self.body[0]
        dx, dy = self.direction.value
        new_head = (head_x + dx, head_y + dy)
        
        self.body.insert(0, new_head)
        if not self.grow:
            self.body.pop()
        else:
            self.grow = False
    
    def change_direction(self, new_direction):
        # Prevent moving in opposite direction
        dx_current, dy_current = self.direction.value
        dx_new, dy_new = new_direction.value
        if (dx_current, dy_current) != (-dx_new, -dy_new):
            self.direction = new_direction
    
    def check_collision(self):
        head_x, head_y = self.body[0]
        # Check wall collision
        if head_x < 0 or head_x >= GRID_WIDTH or head_y < 0 or head_y >= GRID_HEIGHT:
            return True
        # Check self collision
        if self.body[0] in self.body[1:]:
            return True
        return False
    
    def eat_food(self, food_pos):
        if self.body[0] == food_pos:
            self.grow = True
            return True
        return False

class Food:
    def __init__(self, caterpillar_body):
        self.position = self.generate_position(caterpillar_body)
        self.explosion_time = None
        self.exploding = False
        self.explosion_particles = []
    
    def generate_position(self, caterpillar_body):
        while True:
            pos = (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
            if pos not in caterpillar_body:
                return pos
    
    def start_explosion(self):
        self.exploding = True
        # Create explosion particles
        for _ in range(15):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 8)
            color = random.choice([RED, ORANGE, YELLOW])
            self.explosion_particles.append({
                'x': self.position[0] * GRID_SIZE + GRID_SIZE // 2,
                'y': self.position[1] * GRID_SIZE + GRID_SIZE // 2,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'color': color,
                'life': 1.0
            })
    
    def update_explosion(self):
        if self.exploding:
            for particle in self.explosion_particles:
                particle['x'] += particle['vx']
                particle['y'] += particle['vy']
                particle['life'] -= 0.05
            self.explosion_particles = [p for p in self.explosion_particles if p['life'] > 0]
            if not self.explosion_particles:
                self.exploding = False
                return True  # Explosion finished
        return False

def draw_grid(screen):
    for x in range(0, WINDOW_WIDTH, GRID_SIZE):
        pygame.draw.line(screen, (40, 40, 40), (x, 0), (x, WINDOW_HEIGHT))
    for y in range(0, WINDOW_HEIGHT, GRID_SIZE):
        pygame.draw.line(screen, (40, 40, 40), (0, y), (WINDOW_WIDTH, y))

def draw_caterpillar(screen, caterpillar):
    for i, (x, y) in enumerate(caterpillar.body):
        if i == 0:
            # Draw head with eyes
            rect = pygame.Rect(x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE, GRID_SIZE)
            pygame.draw.rect(screen, LIME, rect)
            pygame.draw.rect(screen, BLACK, rect, 1)
            # Eyes
            eye_size = 3
            eye_offset = 5
            pygame.draw.circle(screen, BLACK, (x * GRID_SIZE + eye_offset, y * GRID_SIZE + eye_offset), eye_size)
            pygame.draw.circle(screen, BLACK, (x * GRID_SIZE + GRID_SIZE - eye_offset, y * GRID_SIZE + eye_offset), eye_size)
        else:
            # Alternating segment colors for caterpillar effect
            color = GREEN if i % 2 == 0 else YELLOW
            rect = pygame.Rect(x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE, GRID_SIZE)
            pygame.draw.ellipse(screen, color, rect)
            pygame.draw.ellipse(screen, BLACK, rect, 1)

def draw_food(screen, food):
    if food.exploding:
        # Draw explosion particles
        for particle in food.explosion_particles:
            size = int(particle['life'] * 8)
            if size > 0:
                pygame.draw.circle(screen, particle['color'], 
                                 (int(particle['x']), int(particle['y'])), size)
    else:
        # Draw apple-like food
        x, y = food.position
        center_x = x * GRID_SIZE + GRID_SIZE // 2
        center_y = y * GRID_SIZE + GRID_SIZE // 2
        radius = GRID_SIZE // 2 - 2
        
        # Draw red apple
        pygame.draw.circle(screen, RED, (center_x, center_y), radius)
        # Leaf
        leaf_points = [(center_x, center_y - radius), 
                      (center_x - 3, center_y - radius - 3),
                      (center_x + 3, center_y - radius - 3)]
        pygame.draw.polygon(screen, GREEN, leaf_points)

def draw_score(screen, score, font):
    score_text = font.render(f'Score: {score}', True, WHITE)
    screen.blit(score_text, (10, 10))

def game_over_screen(screen, score, font):
    screen.fill(BLACK)
    game_over_text = font.render('Game Over!', True, RED)
    score_text = font.render(f'Final Score: {score}', True, WHITE)
    restart_text = font.render('Press SPACE to restart or ESC to quit', True, WHITE)
    
    screen.blit(game_over_text, (WINDOW_WIDTH // 2 - game_over_text.get_width() // 2, WINDOW_HEIGHT // 2 - 60))
    screen.blit(score_text, (WINDOW_WIDTH // 2 - score_text.get_width() // 2, WINDOW_HEIGHT // 2))
    screen.blit(restart_text, (WINDOW_WIDTH // 2 - restart_text.get_width() // 2, WINDOW_HEIGHT // 2 + 60))

def main():
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption('Caterpillar Game')
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)
    
    caterpillar = Caterpillar()
    food = Food(caterpillar.body)
    score = 0
    game_over = False
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            
            if event.type == pygame.KEYDOWN:
                if game_over:
                    if event.key == pygame.K_SPACE:
                        # Restart game
                        caterpillar = Caterpillar()
                        food = Food(caterpillar.body)
                        score = 0
                        game_over = False
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        return
                else:
                    # Arrow keys
                    if event.key == pygame.K_UP:
                        caterpillar.change_direction(Direction.UP)
                    elif event.key == pygame.K_DOWN:
                        caterpillar.change_direction(Direction.DOWN)
                    elif event.key == pygame.K_LEFT:
                        caterpillar.change_direction(Direction.LEFT)
                    elif event.key == pygame.K_RIGHT:
                        caterpillar.change_direction(Direction.RIGHT)
                    # WASD keys
                    elif event.key == pygame.K_w:
                        caterpillar.change_direction(Direction.UP)
                    elif event.key == pygame.K_s:
                        caterpillar.change_direction(Direction.DOWN)
                    elif event.key == pygame.K_a:
                        caterpillar.change_direction(Direction.LEFT)
                    elif event.key == pygame.K_d:
                        caterpillar.change_direction(Direction.RIGHT)
        
        if not game_over:
            # Update explosion if active
            if food.exploding:
                if food.update_explosion():
                    # Explosion finished, generate new food
                    food = Food(caterpillar.body)
            else:
                caterpillar.move()
                
                if caterpillar.check_collision():
                    game_over = True
                
                if caterpillar.eat_food(food.position):
                    score += 10
                    food.start_explosion()
            
            screen.fill(BLACK)
            draw_grid(screen)
            draw_caterpillar(screen, caterpillar)
            draw_food(screen, food)
            draw_score(screen, score, font)
        else:
            game_over_screen(screen, score, font)
        
        pygame.display.flip()
        clock.tick(10)

if __name__ == '__main__':
    main()
