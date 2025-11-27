#!/usr/bin/env python3
"""
Ultra Mario 2D Bros - Python Port (TRUE FIXED VERSION)
By Catsan / Team Flames

CRITICAL FIX: Ensures perfect pixel alignment between tiles and window
- Window height: 384px (exactly 12 tiles * 32px)
- Ground positioned at exact pixel boundaries
- No gaps or misalignment at screen edges
"""

import pygame
import math
import random
import time
from enum import IntEnum

# Initialize Pygame
pygame.init()

# ==================== CONSTANTS ====================
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 384  # EXACTLY 12 tiles * 32 pixels
TILE_SIZE = 16
SCALE = 2
SCALED_TILE = TILE_SIZE * SCALE  # 32 pixels
GRAVITY = 0.5
JUMP_FORCE = -10.0
MOVE_SPEED = 4.0
MAX_FALL_SPEED = 12.0
FPS = 60

# Ensure pixel-perfect rendering
TILES_WIDE = WINDOW_WIDTH // SCALED_TILE  # 18.75 tiles
TILES_HIGH = WINDOW_HEIGHT // SCALED_TILE  # Exactly 12 tiles

# Game States
class GameState(IntEnum):
    TITLE = 0
    PLAYING = 1
    PAUSED = 2
    GAME_OVER = 3
    LEVEL_COMPLETE = 4
    WORLD_INTRO = 5
    VICTORY = 6

# Power States
class PowerState(IntEnum):
    SMALL = 0
    BIG = 1
    FIRE = 2
    STAR = 3

# Tile Types
class TileType(IntEnum):
    AIR = 0
    GROUND = 1
    BRICK = 2
    QUESTION = 3
    USED = 4
    PIPE_TL = 5
    PIPE_TR = 6
    PIPE_BL = 7
    PIPE_BR = 8
    HARD = 9
    CASTLE = 10
    FLAG_POLE = 11
    FLAG_TOP = 12
    LAVA = 13
    BRIDGE = 14
    AXE = 15
    CLOUD = 16
    BUSH = 17
    HILL = 18
    WATER = 19
    CORAL = 20

# Colors - NES Palette
SKY_BLUE = (92, 148, 252)
UNDERGROUND_BLACK = (0, 0, 0)
CASTLE_BLACK = (0, 0, 0)
UNDERWATER_BLUE = (60, 100, 180)
GROUND_BROWN = (200, 76, 12)
BRICK_RED = (200, 76, 12)
QUESTION_YELLOW = (252, 152, 56)
PIPE_GREEN = (0, 168, 0)
MARIO_RED = (228, 0, 88)
MARIO_SKIN = (252, 152, 56)
GOOMBA_BROWN = (172, 80, 52)
KOOPA_GREEN = (0, 168, 0)
COIN_YELLOW = (252, 188, 60)
CLOUD_WHITE = (252, 252, 252)
LAVA_RED = (228, 0, 88)
WATER_BLUE = (60, 188, 252)
STAR_YELLOW = (252, 188, 60)
FIRE_ORANGE = (252, 116, 0)
CASTLE_GRAY = (120, 120, 120)
CORAL_PINK = (255, 120, 150)
AXE_SILVER = (180, 180, 200)
BOWSER_GREEN = (0, 140, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

class Entity:
    """Base entity class for all game objects"""
    def __init__(self, entity_type, x, y):
        self.type = entity_type
        self.x = x
        self.y = y
        self.vel_x = 0
        self.vel_y = 0
        self.width = SCALED_TILE
        self.height = SCALED_TILE
        self.active = True
        self.dead = False
        self.stomped = False
        self.stomp_timer = 0
        self.in_shell = False
        self.emerging = False
        self.emerge_y = 0
        
        # Set initial properties based on type
        if entity_type in ["goomba", "koopa"]:
            self.vel_x = -1
        elif entity_type == "bowser":
            self.width = SCALED_TILE * 2
            self.height = SCALED_TILE * 2
            self.vel_x = -1
        elif entity_type in ["mushroom", "fireflower", "star"]:
            self.vel_x = 2
        elif entity_type == "fireball":
            self.width = 12
            self.height = 12

    def update(self, game):
        """Update entity position and behavior"""
        if self.stomped:
            self.stomp_timer -= 1
            if self.stomp_timer <= 0:
                self.dead = True
            return
        
        if self.emerging:
            self.y -= 1
            if self.y <= self.emerge_y - SCALED_TILE:
                self.emerging = False
            return
        
        # Apply gravity
        if self.type not in ["coin"] or self.vel_y != 0:
            self.vel_y += 0.3
            if self.vel_y > 8:
                self.vel_y = 8
        
        # Special behaviors
        if self.type == "star":
            self.vel_y = -5  # Stars bounce
        
        if self.type == "coin" and self.vel_y < 0:
            self.y += self.vel_y
            self.vel_y += 0.5
            if self.vel_y >= 0:
                self.dead = True
                game.collect_coin()
            return
        
        # Movement
        self.x += self.vel_x
        
        # Collision detection
        self.handle_collision(game)
        
        # Update Y position
        self.y += self.vel_y

    def handle_collision(self, game):
        """Handle collision with tiles"""
        # Wall collision
        check_x = int((self.x + self.width) / SCALED_TILE) if self.vel_x > 0 else int(self.x / SCALED_TILE)
        check_y = int((self.y + self.height / 2) / SCALED_TILE)
        if game.is_solid_tile(check_x, check_y):
            self.vel_x = -self.vel_x
        
        # Ground collision
        ground_y = int((self.y + self.height) / SCALED_TILE)
        ground_x = int((self.x + self.width / 2) / SCALED_TILE)
        if game.is_solid_tile(ground_x, ground_y):
            self.y = ground_y * SCALED_TILE - self.height
            self.vel_y = 0
        
        # Cliff detection for walking enemies
        if self.type in ["goomba", "koopa"] and not self.in_shell:
            ahead_x = int((self.x + self.width + 4) / SCALED_TILE) if self.vel_x > 0 else int((self.x - 4) / SCALED_TILE)
            below_y = int((self.y + self.height + 4) / SCALED_TILE)
            if not game.is_solid_tile(ahead_x, below_y):
                self.vel_x = -self.vel_x

class Particle:
    """Particle effect class"""
    def __init__(self, x, y, vel_x=0, vel_y=0, color=WHITE):
        self.x = x
        self.y = y
        self.vel_x = vel_x
        self.vel_y = vel_y
        self.color = color
        self.life = 60

    def update(self):
        self.x += self.vel_x
        self.y += self.vel_y
        self.vel_y += 0.3
        self.life -= 1

class FloatingText:
    """Floating score/text display"""
    def __init__(self, text, x, y):
        self.text = text
        self.x = x
        self.y = y
        self.life = 60

    def update(self):
        self.y -= 1
        self.life -= 1

class UltraMario2D:
    def __init__(self):
        # Setup display with exact dimensions
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Ultra Mario 2D Bros - TRUE FIXED VERSION")
        
        # Ensure pixel-perfect rendering
        self.screen.set_alpha(None)  # Disable alpha blending for speed
        
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.Font(None, 16)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_large = pygame.font.Font(None, 36)
        
        # Game state
        self.game_state = GameState.TITLE
        self.current_world = 1
        self.current_level = 1
        self.lives = 3
        self.coins = 0
        self.score = 0
        self.time_remaining = 400
        self.last_time_update = time.time()
        
        # Player state
        self.player_x = 0
        self.player_y = 0
        self.player_vel_x = 0
        self.player_vel_y = 0
        self.player_power = PowerState.SMALL
        self.player_on_ground = False
        self.player_facing_right = True
        self.invincibility_frames = 0
        self.star_timer = 0
        self.anim_frame = 0
        self.anim_timer = 0
        self.player_dead = False
        self.death_timer = 0
        
        # Input state
        self.left_pressed = False
        self.right_pressed = False
        self.jump_pressed = False
        self.run_pressed = False
        self.down_pressed = False
        self.jump_held = False
        
        # Camera
        self.camera_x = 0
        
        # Level data
        self.level_width = 0
        self.level_height = 12  # EXACTLY 12 tiles for 384px height
        self.current_tiles = []
        self.entities = []
        self.particles = []
        self.floating_texts = []
        
        # Level-specific
        self.is_underground = False
        self.is_underwater = False
        self.is_castle = False
        self.flag_pole_x = -1
        self.flag_descending = False
        self.flag_y = 0
        self.level_complete_timer = 0
        self.world_intro_timer = 0
        self.victory_timer = 0
        
        # Castle-specific
        self.bridge_collapsing = False
        self.bridge_collapse_x = 0
        self.axe_x = -1
        self.axe_y = -1
        
        print("Ultra Mario 2D Bros - TRUE FIXED VERSION")
        print("By Catsan / Team Flames")
        print(f"Window: {WINDOW_WIDTH}x{WINDOW_HEIGHT} (Exactly {TILES_HIGH} tiles high)")

    def run(self):
        """Main game loop"""
        running = True
        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    self.handle_key_down(event.key)
                elif event.type == pygame.KEYUP:
                    self.handle_key_up(event.key)
            
            # Update game based on state
            if self.game_state == GameState.TITLE:
                self.update_title()
            elif self.game_state == GameState.PLAYING:
                self.update_game()
            elif self.game_state == GameState.PAUSED:
                pass  # Paused - no updates
            elif self.game_state == GameState.GAME_OVER:
                self.update_game_over()
            elif self.game_state == GameState.LEVEL_COMPLETE:
                self.update_level_complete()
            elif self.game_state == GameState.WORLD_INTRO:
                self.update_world_intro()
            elif self.game_state == GameState.VICTORY:
                self.update_victory()
            
            # Render
            self.render()
            
            # Cap framerate
            self.clock.tick(FPS)
        
        pygame.quit()

    def update_title(self):
        """Update title screen"""
        self.anim_timer += 1

    def update_game(self):
        """Update main game logic"""
        if self.player_dead:
            self.death_timer += 1
            self.player_vel_y += GRAVITY * 0.5
            self.player_y += self.player_vel_y
            if self.death_timer > 180:
                self.lose_life()
            return
        
        # Update timers
        current_time = time.time()
        if current_time - self.last_time_update >= 1.0:
            self.time_remaining -= 1
            self.last_time_update = current_time
            if self.time_remaining <= 0:
                self.kill_player()
        
        # Update animation
        self.anim_timer += 1
        if self.anim_timer >= 8:
            self.anim_timer = 0
            self.anim_frame = (self.anim_frame + 1) % 3
        
        # Update invincibility
        if self.invincibility_frames > 0:
            self.invincibility_frames -= 1
        if self.star_timer > 0:
            self.star_timer -= 1
        
        # Update player
        self.update_player()
        
        # Update entities
        self.update_entities()
        
        # Update particles
        for particle in self.particles[:]:
            particle.update()
            if particle.life <= 0:
                self.particles.remove(particle)
        
        # Update floating texts
        for text in self.floating_texts[:]:
            text.update()
            if text.life <= 0:
                self.floating_texts.remove(text)
        
        # Update camera
        self.update_camera()
        
        # Check for level completion
        if self.flag_pole_x >= 0 and not self.flag_descending and self.level_complete_timer == 0:
            player_tile_x = int(self.player_x / SCALED_TILE)
            if abs(player_tile_x - self.flag_pole_x) < 1.5:
                self.trigger_flag_sequence()
        
        # Handle flag descent
        if self.flag_descending:
            self.flag_y += 3
            self.player_y += 3
            if self.flag_y >= self.level_height * SCALED_TILE - SCALED_TILE * 3:
                self.flag_descending = False
                self.level_complete_timer = 1
        
        # Handle level complete
        if self.level_complete_timer > 0:
            self.level_complete_timer += 1
            if self.level_complete_timer > 60:
                self.player_x += 2
                self.player_facing_right = True
                if self.player_x > self.camera_x + WINDOW_WIDTH + 50:
                    self.advance_level()

    def update_player(self):
        """Update player physics and movement"""
        if self.level_complete_timer > 0:
            return
        
        # Horizontal movement
        accel = 0.4 if self.run_pressed else 0.2
        max_speed = MOVE_SPEED * 1.5 if self.run_pressed else MOVE_SPEED
        
        if self.left_pressed and not self.right_pressed:
            self.player_vel_x -= accel
            if self.player_vel_x < -max_speed:
                self.player_vel_x = -max_speed
            self.player_facing_right = False
        elif self.right_pressed and not self.left_pressed:
            self.player_vel_x += accel
            if self.player_vel_x > max_speed:
                self.player_vel_x = max_speed
            self.player_facing_right = True
        else:
            # Friction
            if self.player_vel_x > 0:
                self.player_vel_x -= 0.15
                if self.player_vel_x < 0:
                    self.player_vel_x = 0
            elif self.player_vel_x < 0:
                self.player_vel_x += 0.15
                if self.player_vel_x > 0:
                    self.player_vel_x = 0
        
        # Jumping
        if self.jump_pressed and self.player_on_ground and not self.jump_held:
            self.player_vel_y = JUMP_FORCE
            self.player_on_ground = False
            self.jump_held = True
        
        # Variable jump height
        if not self.jump_pressed and self.player_vel_y < -3:
            self.player_vel_y = -3
        
        # Gravity
        if self.is_underwater:
            self.player_vel_y += GRAVITY * 0.3
            if self.player_vel_y > 2:
                self.player_vel_y = 2
        else:
            self.player_vel_y += GRAVITY
            if self.player_vel_y > MAX_FALL_SPEED:
                self.player_vel_y = MAX_FALL_SPEED
        
        # Apply movement with collision
        self.player_x += self.player_vel_x
        self.handle_horizontal_collision()
        
        # Keep player in bounds
        if self.player_x < 0:
            self.player_x = 0
        if self.player_x < self.camera_x and self.camera_x > 0:
            self.player_x = self.camera_x
        
        # Apply vertical movement
        self.player_y += self.player_vel_y
        self.handle_vertical_collision()
        
        # Check for death by falling
        if self.player_y > self.level_height * SCALED_TILE + 50:
            self.kill_player()

    def handle_horizontal_collision(self):
        """Handle player horizontal collision with tiles"""
        player_width = SCALED_TILE - 4
        player_height = SCALED_TILE if self.player_power == PowerState.SMALL else SCALED_TILE * 2
        
        start_tile_y = int(self.player_y / SCALED_TILE)
        end_tile_y = int((self.player_y + player_height - 1) / SCALED_TILE)
        
        if self.player_vel_x > 0:  # Moving right
            tile_x = int((self.player_x + player_width) / SCALED_TILE)
            for ty in range(start_tile_y, min(end_tile_y + 1, self.level_height)):
                if self.is_solid_tile(tile_x, ty):
                    self.player_x = tile_x * SCALED_TILE - player_width - 1
                    self.player_vel_x = 0
                    break
        elif self.player_vel_x < 0:  # Moving left
            tile_x = int(self.player_x / SCALED_TILE)
            for ty in range(start_tile_y, min(end_tile_y + 1, self.level_height)):
                if self.is_solid_tile(tile_x, ty):
                    self.player_x = (tile_x + 1) * SCALED_TILE + 1
                    self.player_vel_x = 0
                    break

    def handle_vertical_collision(self):
        """Handle player vertical collision with tiles"""
        player_width = SCALED_TILE - 4
        player_height = SCALED_TILE if self.player_power == PowerState.SMALL else SCALED_TILE * 2
        
        self.player_on_ground = False
        
        start_tile_x = int((self.player_x + 2) / SCALED_TILE)
        end_tile_x = int((self.player_x + player_width - 2) / SCALED_TILE)
        
        if self.player_vel_y > 0:  # Falling
            tile_y = int((self.player_y + player_height) / SCALED_TILE)
            for tx in range(start_tile_x, min(end_tile_x + 1, self.level_width)):
                if self.is_solid_tile(tx, tile_y):
                    # CRITICAL FIX: Align player exactly to tile boundary
                    self.player_y = tile_y * SCALED_TILE - player_height
                    self.player_vel_y = 0
                    self.player_on_ground = True
                    break
        elif self.player_vel_y < 0:  # Rising
            tile_y = int(self.player_y / SCALED_TILE)
            for tx in range(start_tile_x, min(end_tile_x + 1, self.level_width)):
                if self.is_solid_tile(tx, tile_y):
                    self.player_y = (tile_y + 1) * SCALED_TILE
                    self.player_vel_y = 0
                    self.hit_block(tx, tile_y)
                    break

    def hit_block(self, tx, ty):
        """Handle block hit by player"""
        if tx < 0 or tx >= self.level_width or ty < 0 or ty >= self.level_height:
            return
        
        tile = self.current_tiles[ty][tx]
        if tile == TileType.QUESTION:
            self.current_tiles[ty][tx] = TileType.USED
            # Spawn coin or power-up
            if random.random() < 0.25 and self.player_power == PowerState.SMALL:
                self.spawn_powerup(tx * SCALED_TILE, ty * SCALED_TILE - SCALED_TILE)
            else:
                self.spawn_coin(tx * SCALED_TILE, ty * SCALED_TILE - SCALED_TILE)
            self.score += 100
        elif tile == TileType.BRICK and self.player_power != PowerState.SMALL:
            self.current_tiles[ty][tx] = TileType.AIR
            self.create_brick_particles(tx * SCALED_TILE, ty * SCALED_TILE)
            self.score += 50

    def spawn_coin(self, x, y):
        """Spawn a coin entity"""
        coin = Entity("coin", x + SCALED_TILE // 2 - 6, y)
        coin.vel_y = -10
        self.entities.append(coin)

    def spawn_powerup(self, x, y):
        """Spawn a power-up"""
        if self.player_power == PowerState.SMALL:
            powerup_type = "mushroom"
        elif random.random() < 0.33:
            powerup_type = "star"
        else:
            powerup_type = "fireflower"
        
        powerup = Entity(powerup_type, x, y + SCALED_TILE)
        powerup.emerging = True
        powerup.emerge_y = y
        self.entities.append(powerup)

    def create_brick_particles(self, x, y):
        """Create particle effects for broken bricks"""
        for i in range(4):
            px = x + (i % 2) * SCALED_TILE // 2
            py = y + (i // 2) * SCALED_TILE // 2
            vel_x = -3 if i % 2 == 0 else 3
            vel_y = -8 if i < 2 else -5
            self.particles.append(Particle(px, py, vel_x, vel_y, BRICK_RED))

    def update_entities(self):
        """Update all entities"""
        for entity in self.entities[:]:
            entity.update(self)
            
            # Remove dead or off-screen entities
            if entity.dead or entity.x < self.camera_x - 100 or entity.x > self.camera_x + WINDOW_WIDTH + 100:
                self.entities.remove(entity)
                continue
            
            # Check collision with player
            if not self.player_dead and self.invincibility_frames == 0 and entity.active:
                if self.check_entity_collision(entity):
                    self.handle_entity_collision(entity)

    def check_entity_collision(self, entity):
        """Check if player collides with entity"""
        player_width = SCALED_TILE - 4
        player_height = SCALED_TILE if self.player_power == PowerState.SMALL else SCALED_TILE * 2
        
        return (self.player_x < entity.x + entity.width and
                self.player_x + player_width > entity.x and
                self.player_y < entity.y + entity.height and
                self.player_y + player_height > entity.y)

    def handle_entity_collision(self, entity):
        """Handle collision between player and entity"""
        if entity.type in ["mushroom", "fireflower", "star"]:
            self.collect_powerup(entity)
            return
        
        if entity.type == "coin":
            self.collect_coin()
            entity.dead = True
            return
        
        # Enemy collision
        if self.star_timer > 0:
            self.kill_enemy(entity)
            return
        
        # Check if stomping
        player_height = SCALED_TILE if self.player_power == PowerState.SMALL else SCALED_TILE * 2
        if self.player_vel_y > 0 and self.player_y + player_height - 10 < entity.y + entity.height / 2:
            self.stomp_enemy(entity)
        else:
            self.damage_player()

    def collect_powerup(self, entity):
        """Collect a power-up"""
        if entity.type == "mushroom":
            if self.player_power == PowerState.SMALL:
                self.player_power = PowerState.BIG
                self.player_y -= SCALED_TILE
            self.score += 1000
            self.floating_texts.append(FloatingText("+1000", entity.x, entity.y))
        elif entity.type == "fireflower":
            if self.player_power == PowerState.SMALL:
                self.player_y -= SCALED_TILE
            self.player_power = PowerState.FIRE
            self.score += 1000
            self.floating_texts.append(FloatingText("+1000", entity.x, entity.y))
        elif entity.type == "star":
            self.star_timer = 600
            self.score += 1000
            self.floating_texts.append(FloatingText("+1000", entity.x, entity.y))
        entity.dead = True

    def stomp_enemy(self, entity):
        """Stomp on enemy"""
        if entity.type == "goomba":
            entity.stomped = True
            entity.stomp_timer = 30
            entity.active = False
            self.score += 100
            self.floating_texts.append(FloatingText("+100", entity.x, entity.y))
        elif entity.type == "koopa":
            if entity.in_shell:
                # Kick shell
                entity.vel_x = 8 if self.player_facing_right else -8
                self.score += 100
            else:
                entity.in_shell = True
                entity.vel_x = 0
                self.score += 100
            self.floating_texts.append(FloatingText("+100", entity.x, entity.y))
        self.player_vel_y = -6

    def kill_enemy(self, entity):
        """Kill enemy with star power or fireball"""
        entity.dead = True
        self.score += 200
        self.floating_texts.append(FloatingText("+200", entity.x, entity.y))
        # Create death particles
        for i in range(6):
            px = entity.x + random.randint(0, entity.width)
            py = entity.y + random.randint(0, entity.height)
            vel_x = random.uniform(-3, 3)
            vel_y = random.uniform(-8, -2)
            self.particles.append(Particle(px, py, vel_x, vel_y, WHITE))

    def damage_player(self):
        """Damage the player"""
        if self.invincibility_frames > 0 or self.star_timer > 0:
            return
        
        if self.player_power == PowerState.SMALL:
            self.kill_player()
        else:
            self.player_power = PowerState.SMALL
            self.invincibility_frames = 120

    def kill_player(self):
        """Kill the player"""
        self.player_dead = True
        self.player_vel_y = -8
        self.player_vel_x = 0
        self.death_timer = 0

    def lose_life(self):
        """Lose a life and reset or game over"""
        self.lives -= 1
        if self.lives <= 0:
            self.game_state = GameState.GAME_OVER
        else:
            self.load_level(self.current_world, self.current_level)

    def collect_coin(self):
        """Collect a coin"""
        self.coins += 1
        self.score += 200
        if self.coins >= 100:
            self.coins = 0
            self.lives += 1
            self.floating_texts.append(FloatingText("1UP!", self.player_x, self.player_y - 30))

    def update_camera(self):
        """Update camera position"""
        target_camera_x = self.player_x - WINDOW_WIDTH / 3.0
        if target_camera_x < 0:
            target_camera_x = 0
        if target_camera_x > self.level_width * SCALED_TILE - WINDOW_WIDTH:
            target_camera_x = self.level_width * SCALED_TILE - WINDOW_WIDTH
        
        # Smooth camera movement
        self.camera_x += (target_camera_x - self.camera_x) * 0.1
        
        # Camera never goes backwards
        if self.camera_x < 0:
            self.camera_x = 0

    def update_game_over(self):
        """Update game over state"""
        self.anim_timer += 1

    def update_level_complete(self):
        """Update level complete state"""
        pass

    def update_world_intro(self):
        """Update world intro screen"""
        self.world_intro_timer += 1
        if self.world_intro_timer > 180:
            self.world_intro_timer = 0
            self.game_state = GameState.PLAYING

    def update_victory(self):
        """Update victory screen"""
        self.victory_timer += 1
        self.anim_timer += 1
        
        # Create firework particles
        if self.victory_timer % 20 == 0:
            for i in range(5):
                px = random.randint(0, WINDOW_WIDTH)
                py = random.randint(0, WINDOW_HEIGHT // 2)
                vel_x = random.uniform(-2, 2)
                vel_y = random.uniform(-4, 0)
                color = (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
                self.particles.append(Particle(px, py, vel_x, vel_y, color))

    def trigger_flag_sequence(self):
        """Trigger the flag pole completion sequence"""
        self.flag_descending = True
        self.flag_y = 0
        self.player_vel_x = 0
        self.player_vel_y = 0
        self.player_x = self.flag_pole_x * SCALED_TILE - SCALED_TILE // 2
        
        # Score based on height
        height_score = int((self.level_height * SCALED_TILE - self.player_y) / SCALED_TILE) * 100
        self.score += max(100, height_score)
        self.floating_texts.append(FloatingText(f"+{max(100, height_score)}", self.player_x, self.player_y))

    def advance_level(self):
        """Advance to next level"""
        # Add time bonus
        self.score += self.time_remaining * 50
        
        self.current_level += 1
        if self.current_level > 4:
            self.current_level = 1
            self.current_world += 1
            if self.current_world > 8:
                # Game complete!
                self.game_state = GameState.VICTORY
                self.victory_timer = 0
                return
        
        self.game_state = GameState.WORLD_INTRO
        self.load_level(self.current_world, self.current_level)

    def load_level(self, world, level):
        """Load a level"""
        self.current_world = world
        self.current_level = level
        
        # Determine level type
        self.is_underground = (level == 2 and (world == 1 or world == 4))
        self.is_castle = (level == 4)
        self.is_underwater = (world == 2 and level == 2) or (world == 7 and level == 2)
        
        # Generate level
        self.generate_level(world, level)
        
        # Reset player - CRITICAL: Position exactly on ground tiles
        self.player_x = SCALED_TILE * 3
        # Ground is at row 10 (levelHeight - 2), so player stands on row 9
        self.player_y = (self.level_height - 3) * SCALED_TILE
        if self.player_power != PowerState.SMALL:
            self.player_y -= SCALED_TILE
        self.player_vel_x = 0
        self.player_vel_y = 0
        self.player_on_ground = False
        self.player_dead = False
        self.invincibility_frames = 0
        
        # Reset camera
        self.camera_x = 0
        
        # Clear entities
        self.entities.clear()
        self.particles.clear()
        self.floating_texts.clear()
        
        # Populate enemies
        self.populate_enemies(world, level)
        
        # Reset timers
        self.time_remaining = 400
        self.last_time_update = time.time()
        self.flag_descending = False
        self.flag_y = 0
        self.level_complete_timer = 0
        self.bridge_collapsing = False
        
        # Verify level height matches window
        assert self.level_height == TILES_HIGH, f"Level height mismatch! {self.level_height} != {TILES_HIGH}"

    def generate_level(self, world, level):
        """Generate level layout"""
        # Base level width
        self.level_width = 200 + (world - 1) * 20 + random.randint(0, 50)
        self.current_tiles = [[TileType.AIR for _ in range(self.level_width)] for _ in range(self.level_height)]
        self.flag_pole_x = -1
        self.axe_x = -1
        self.axe_y = -1
        
        if self.is_castle:
            self.generate_castle_level(world)
        elif self.is_underground:
            self.generate_underground_level(world)
        elif self.is_underwater:
            self.generate_underwater_level(world)
        else:
            self.generate_overworld_level(world, level)

    def generate_overworld_level(self, world, level):
        """Generate standard overworld level"""
        # CRITICAL: Place ground at EXACT bottom rows
        for x in range(self.level_width):
            self.current_tiles[self.level_height - 1][x] = TileType.GROUND  # Row 11
            self.current_tiles[self.level_height - 2][x] = TileType.GROUND  # Row 10
        
        # Add gaps
        num_gaps = 3 + world + random.randint(0, 3)
        for i in range(num_gaps):
            gap_x = 30 + i * (self.level_width // (num_gaps + 1)) + random.randint(-10, 10)
            gap_width = 2 + random.randint(0, 2 + world // 2)
            for x in range(gap_x, min(gap_x + gap_width, self.level_width)):
                self.current_tiles[self.level_height - 1][x] = TileType.AIR
                self.current_tiles[self.level_height - 2][x] = TileType.AIR
        
        # Add platforms and blocks
        for i in range(self.level_width // 15):
            x = 10 + i * 15 + random.randint(0, 8)
            y = self.level_height - 5 - random.randint(0, 3)
            
            platform_type = random.randint(0, 3)
            if platform_type == 0:
                # Question blocks
                length = 1 + random.randint(0, 4)
                for j in range(length):
                    if x + j < self.level_width:
                        self.current_tiles[y][x + j] = TileType.QUESTION if random.random() < 0.33 else TileType.BRICK
            elif platform_type == 1:
                # Brick row
                length = 3 + random.randint(0, 5)
                for j in range(length):
                    if x + j < self.level_width:
                        self.current_tiles[y][x + j] = TileType.BRICK
            elif platform_type == 2:
                # Stairs
                height = 2 + random.randint(0, 4)
                for h in range(height):
                    for w in range(h + 1):
                        ty = self.level_height - 3 - h
                        tx = x + w
                        if 0 <= ty < self.level_height and tx < self.level_width:
                            self.current_tiles[ty][tx] = TileType.HARD
        
        # Add pipes
        for i in range(self.level_width // 30):
            x = 20 + i * 30 + random.randint(0, 15)
            pipe_height = 2 + random.randint(0, 3)
            self.add_pipe(x, self.level_height - 2 - pipe_height, pipe_height)
        
        # Add flag pole at end
        self.flag_pole_x = self.level_width - 10
        
        # Add castle at end
        for y in range(self.level_height - 6, self.level_height - 2):
            for x in range(self.level_width - 6, self.level_width - 1):
                if x < self.level_width:
                    self.current_tiles[y][x] = TileType.CASTLE
        
        # Castle entrance
        self.current_tiles[self.level_height - 3][self.level_width - 4] = TileType.AIR
        self.current_tiles[self.level_height - 4][self.level_width - 4] = TileType.AIR

    def generate_underground_level(self, world):
        """Generate underground level"""
        # Ceiling
        for x in range(self.level_width):
            self.current_tiles[0][x] = TileType.BRICK
            self.current_tiles[1][x] = TileType.BRICK
        
        # Floor - EXACT bottom placement
        for x in range(self.level_width):
            self.current_tiles[self.level_height - 1][x] = TileType.HARD
            self.current_tiles[self.level_height - 2][x] = TileType.HARD
        
        # Add platforms
        for i in range(self.level_width // 20):
            x = 15 + i * 20 + random.randint(0, 10)
            y = 4 + random.randint(0, 6)
            length = 3 + random.randint(0, 6)
            for j in range(length):
                if x + j < self.level_width and y < self.level_height:
                    self.current_tiles[y][x + j] = TileType.QUESTION if random.random() < 0.25 else TileType.BRICK
        
        # Exit pipe
        self.add_pipe(self.level_width - 15, self.level_height - 6, 4)
        
        self.flag_pole_x = self.level_width - 8

    def generate_castle_level(self, world):
        """Generate castle level"""
        # Floor with lava pits - EXACT placement
        for x in range(self.level_width):
            if x % 20 < 15 or x > self.level_width - 30:
                self.current_tiles[self.level_height - 1][x] = TileType.HARD
                self.current_tiles[self.level_height - 2][x] = TileType.HARD
            else:
                self.current_tiles[self.level_height - 1][x] = TileType.LAVA
        
        # Ceiling
        for x in range(self.level_width):
            self.current_tiles[0][x] = TileType.HARD
            self.current_tiles[1][x] = TileType.HARD
        
        # Add platforms
        for i in range(self.level_width // 25):
            x = 10 + i * 25
            y = 5 + random.randint(0, 4)
            for j in range(4 + random.randint(0, 4)):
                if x + j < self.level_width and y < self.level_height:
                    self.current_tiles[y][x + j] = TileType.BRICK
        
        # Bridge at end
        bridge_start = self.level_width - 25
        for x in range(bridge_start, self.level_width - 5):
            if self.level_height - 4 >= 0:
                self.current_tiles[self.level_height - 4][x] = TileType.BRIDGE
        
        # Lava under bridge
        for x in range(bridge_start, self.level_width - 5):
            self.current_tiles[self.level_height - 1][x] = TileType.LAVA
            self.current_tiles[self.level_height - 2][x] = TileType.LAVA
            self.current_tiles[self.level_height - 3][x] = TileType.LAVA
        
        # Axe position
        self.axe_x = self.level_width - 6
        self.axe_y = self.level_height - 5
        if self.axe_y >= 0:
            self.current_tiles[self.axe_y][self.axe_x] = TileType.AXE
        
        # Floor after bridge
        for x in range(self.level_width - 5, self.level_width):
            self.current_tiles[self.level_height - 1][x] = TileType.HARD
            self.current_tiles[self.level_height - 2][x] = TileType.HARD
        
        self.flag_pole_x = -1

    def generate_underwater_level(self, world):
        """Generate underwater level"""
        # Sandy floor - EXACT placement with variation
        for x in range(self.level_width):
            floor_height = self.level_height - 2 - (random.randint(0, 1) if random.random() < 0.3 else 0)
            for y in range(floor_height, self.level_height):
                self.current_tiles[y][x] = TileType.GROUND
        
        # Add coral
        for i in range(self.level_width // 10):
            x = 5 + i * 10 + random.randint(0, 5)
            height = 1 + random.randint(0, 3)
            for y in range(self.level_height - 3, max(self.level_height - 3 - height, 0), -1):
                if x < self.level_width:
                    self.current_tiles[y][x] = TileType.CORAL
        
        # Underwater platforms
        for i in range(self.level_width // 20):
            x = 15 + i * 20 + random.randint(0, 10)
            y = 4 + random.randint(0, 6)
            length = 3 + random.randint(0, 4)
            for j in range(length):
                if x + j < self.level_width and y < self.level_height:
                    self.current_tiles[y][x + j] = TileType.HARD
        
        # Exit pipe
        self.add_pipe(self.level_width - 12, self.level_height - 6, 4)
        
        self.flag_pole_x = self.level_width - 6

    def add_pipe(self, x, y, height):
        """Add a pipe to the level"""
        if x < 0 or x + 1 >= self.level_width or y < 0 or y + height >= self.level_height:
            return
        
        # Top of pipe
        self.current_tiles[y][x] = TileType.PIPE_TL
        self.current_tiles[y][x + 1] = TileType.PIPE_TR
        
        # Body of pipe
        for h in range(1, height):
            if y + h < self.level_height:
                self.current_tiles[y + h][x] = TileType.PIPE_BL
                self.current_tiles[y + h][x + 1] = TileType.PIPE_BR

    def populate_enemies(self, world, level):
        """Populate level with enemies"""
        enemy_count = 5 + world * 2 + level
        
        for i in range(enemy_count):
            x = 100 + i * (self.level_width * SCALED_TILE // enemy_count)
            # Place enemies on ground (row 9)
            y = (self.level_height - 3) * SCALED_TILE
            
            # Skip enemies near start and end
            if x < 200 or x > (self.level_width - 15) * SCALED_TILE:
                continue
            
            # Vary enemy types
            enemy_type = "goomba" if random.random() < 0.67 else "koopa"
            
            enemy = Entity(enemy_type, x, y)
            enemy.vel_x = -1 if random.random() < 0.5 else 1
            self.entities.append(enemy)
        
        # Add Bowser in castle levels
        if self.is_castle:
            bowser = Entity("bowser", (self.level_width - 20) * SCALED_TILE, (self.level_height - 6) * SCALED_TILE)
            bowser.vel_x = -1
            self.entities.append(bowser)

    def is_solid_tile(self, tx, ty):
        """Check if a tile is solid"""
        if tx < 0 or tx >= self.level_width or ty < 0 or ty >= self.level_height:
            return False
        
        tile = self.current_tiles[ty][tx]
        return tile in [TileType.GROUND, TileType.BRICK, TileType.QUESTION, 
                       TileType.USED, TileType.HARD, TileType.PIPE_TL,
                       TileType.PIPE_TR, TileType.PIPE_BL, TileType.PIPE_BR,
                       TileType.BRIDGE, TileType.CASTLE]

    def render(self):
        """Main render function"""
        # Choose background based on level type
        if self.is_castle:
            self.screen.fill(CASTLE_BLACK)
        elif self.is_underground:
            self.screen.fill(UNDERGROUND_BLACK)
        elif self.is_underwater:
            self.screen.fill(UNDERWATER_BLUE)
        else:
            self.screen.fill(SKY_BLUE)
        
        # Render based on game state
        if self.game_state == GameState.TITLE:
            self.render_title()
        elif self.game_state == GameState.PLAYING:
            self.render_game()
        elif self.game_state == GameState.PAUSED:
            self.render_game()
            self.render_pause_overlay()
        elif self.game_state == GameState.GAME_OVER:
            self.render_game_over()
        elif self.game_state == GameState.LEVEL_COMPLETE:
            self.render_game()
            self.render_level_complete()
        elif self.game_state == GameState.WORLD_INTRO:
            self.render_world_intro()
        elif self.game_state == GameState.VICTORY:
            self.render_victory()
        
        pygame.display.flip()

    def render_title(self):
        """Render title screen"""
        # Draw decorative clouds
        for i in range(4):
            x = 50 + i * 150
            y = 40 + (i % 2) * 20
            self.draw_cloud(x, y)
        
        # Draw ground
        pygame.draw.rect(self.screen, GROUND_BROWN, (0, WINDOW_HEIGHT - 50, WINDOW_WIDTH, 50))
        
        # Title
        title = self.font_large.render("ULTRA MARIO 2D BROS", True, WHITE)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 100))
        # Shadow
        shadow = self.font_large.render("ULTRA MARIO 2D BROS", True, BLACK)
        self.screen.blit(shadow, (title_rect.x + 2, title_rect.y + 2))
        self.screen.blit(title, title_rect)
        
        # Subtitle
        subtitle = self.font_medium.render("Python Port by Catsan", True, COIN_YELLOW)
        subtitle_rect = subtitle.get_rect(center=(WINDOW_WIDTH // 2, 140))
        self.screen.blit(subtitle, subtitle_rect)
        
        # Draw Mario
        self.draw_mario(WINDOW_WIDTH // 2 - SCALED_TILE // 2, 180, True, PowerState.BIG, (self.anim_timer // 8) % 3)
        
        # Press Enter text (blinking)
        if (self.anim_timer // 30) % 2 == 0:
            text = self.font_medium.render("PRESS ENTER TO START", True, WHITE)
            text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, 300))
            self.screen.blit(text, text_rect)
        
        # Controls
        controls = [
            "Arrow Keys: Move",
            "Z or Space: Jump",
            "X: Run/Fire",
            "P: Pause",
            "ESC: Back to Title"
        ]
        y = WINDOW_HEIGHT - 100
        for control in controls:
            text = self.font_small.render(control, True, WHITE)
            self.screen.blit(text, (20, y))
            y += 15

    def render_game(self):
        """Render main game"""
        # Draw background elements if overworld
        if not self.is_underground and not self.is_castle:
            self.render_background_elements()
        
        # Draw tiles
        self.render_tiles()
        
        # Draw entities
        self.render_entities()
        
        # Draw particles
        for particle in self.particles:
            pygame.draw.rect(self.screen, particle.color, 
                           (int(particle.x - self.camera_x), int(particle.y), 8, 8))
        
        # Draw floating texts
        for text in self.floating_texts:
            rendered_text = self.font_small.render(text.text, True, WHITE)
            self.screen.blit(rendered_text, (int(text.x - self.camera_x), int(text.y)))
        
        # Draw player
        if not self.player_dead or self.death_timer < 60:
            visible = self.invincibility_frames == 0 or (self.invincibility_frames // 4) % 2 == 0
            if visible:
                star_flash = self.star_timer > 0 and (self.star_timer // 4) % 2 == 0
                self.draw_mario(int(self.player_x - self.camera_x), int(self.player_y),
                               self.player_facing_right, self.player_power, self.anim_frame, star_flash)
        
        # Draw HUD
        self.render_hud()

    def render_background_elements(self):
        """Render background decorations"""
        # Clouds (parallax)
        for i in range(self.level_width // 10):
            cloud_x = i * 200 - int(self.camera_x * 0.3)
            if -100 < cloud_x < WINDOW_WIDTH + 100:
                self.draw_cloud(cloud_x, 30 + (i % 3) * 20)
        
        # Hills
        for i in range(self.level_width // 8):
            hill_x = i * 250 - int(self.camera_x * 0.5)
            if -150 < hill_x < WINDOW_WIDTH + 150:
                self.draw_hill(hill_x, WINDOW_HEIGHT - 100)
        
        # Bushes
        for i in range(self.level_width // 5):
            bush_x = i * 180 + 80 - int(self.camera_x * 0.7)
            if -50 < bush_x < WINDOW_WIDTH + 50:
                self.draw_bush(bush_x, WINDOW_HEIGHT - 70)

    def draw_cloud(self, x, y):
        """Draw a cloud"""
        pygame.draw.ellipse(self.screen, CLOUD_WHITE, (x, y, 40, 25))
        pygame.draw.ellipse(self.screen, CLOUD_WHITE, (x + 20, y - 10, 40, 30))
        pygame.draw.ellipse(self.screen, CLOUD_WHITE, (x + 50, y, 35, 25))

    def draw_hill(self, x, y):
        """Draw a hill"""
        points = [(x, y + 60), (x + 75, y), (x + 150, y + 60)]
        pygame.draw.polygon(self.screen, (0, 200, 0), points)

    def draw_bush(self, x, y):
        """Draw a bush"""
        pygame.draw.ellipse(self.screen, (0, 180, 0), (x, y, 30, 20))
        pygame.draw.ellipse(self.screen, (0, 180, 0), (x + 15, y - 5, 25, 25))
        pygame.draw.ellipse(self.screen, (0, 180, 0), (x + 30, y, 30, 20))

    def render_tiles(self):
        """Render level tiles"""
        start_tile_x = int(self.camera_x / SCALED_TILE)
        end_tile_x = start_tile_x + WINDOW_WIDTH // SCALED_TILE + 2
        
        # CRITICAL: Render exactly to window height
        for ty in range(self.level_height):  # 0 to 11
            for tx in range(start_tile_x, min(end_tile_x, self.level_width)):
                if tx < 0:
                    continue
                
                tile = self.current_tiles[ty][tx]
                screen_x = tx * SCALED_TILE - int(self.camera_x)
                screen_y = ty * SCALED_TILE
                
                # Verify we don't render past window bounds
                if screen_y < WINDOW_HEIGHT:
                    self.draw_tile(tile, screen_x, screen_y)
        
        # Draw flag if present
        if self.flag_pole_x >= 0:
            screen_x = self.flag_pole_x * SCALED_TILE - int(self.camera_x)
            
            # Flag pole
            pygame.draw.rect(self.screen, (0, 100, 0), 
                           (screen_x + 12, SCALED_TILE * 3, 8, SCALED_TILE * (self.level_height - 6)))
            
            # Flag ball
            pygame.draw.circle(self.screen, (0, 180, 0), 
                             (screen_x + 16, SCALED_TILE * 3 - 4), 8)
            
            # Flag
            flag_offset = self.flag_y if self.flag_descending else 0
            points = [
                (screen_x + 20, SCALED_TILE * 3 + flag_offset),
                (screen_x + 52, SCALED_TILE * 4 + flag_offset),
                (screen_x + 20, SCALED_TILE * 5 + flag_offset)
            ]
            pygame.draw.polygon(self.screen, WHITE, points)

    def draw_tile(self, tile_type, x, y):
        """Draw a single tile"""
        if tile_type == TileType.AIR:
            return
        elif tile_type == TileType.GROUND:
            color = (100, 60, 20) if self.is_underground else GROUND_BROWN
            pygame.draw.rect(self.screen, color, (x, y, SCALED_TILE, SCALED_TILE))
            # Texture
            pygame.draw.rect(self.screen, (80, 40, 10) if self.is_underground else (180, 60, 10),
                           (x + 2, y + 2, SCALED_TILE - 4, SCALED_TILE - 4), 1)
        elif tile_type == TileType.BRICK:
            color = (100, 100, 100) if self.is_castle else BRICK_RED
            pygame.draw.rect(self.screen, color, (x, y, SCALED_TILE, SCALED_TILE))
            # Brick pattern
            line_color = (60, 60, 60) if self.is_castle else (160, 60, 10)
            pygame.draw.line(self.screen, line_color, (x, y + SCALED_TILE // 2), 
                           (x + SCALED_TILE, y + SCALED_TILE // 2))
            pygame.draw.line(self.screen, line_color, (x + SCALED_TILE // 2, y), 
                           (x + SCALED_TILE // 2, y + SCALED_TILE // 2))
        elif tile_type == TileType.QUESTION:
            pygame.draw.rect(self.screen, QUESTION_YELLOW, (x, y, SCALED_TILE, SCALED_TILE))
            pygame.draw.rect(self.screen, (200, 120, 40), (x + 1, y + 1, SCALED_TILE - 2, SCALED_TILE - 2), 1)
            # Question mark
            text = self.font_medium.render("?", True, WHITE)
            self.screen.blit(text, (x + 8, y + 4))
        elif tile_type == TileType.USED:
            pygame.draw.rect(self.screen, (100, 60, 20), (x, y, SCALED_TILE, SCALED_TILE))
            pygame.draw.rect(self.screen, (60, 40, 10), (x + 2, y + 2, SCALED_TILE - 4, SCALED_TILE - 4), 1)
        elif tile_type in [TileType.PIPE_TL, TileType.PIPE_TR, TileType.PIPE_BL, TileType.PIPE_BR]:
            pygame.draw.rect(self.screen, PIPE_GREEN, (x, y, SCALED_TILE, SCALED_TILE))
            # Pipe highlights
            if tile_type in [TileType.PIPE_TL, TileType.PIPE_BL]:
                pygame.draw.rect(self.screen, (0, 200, 0), (x, y, 4, SCALED_TILE))
            if tile_type in [TileType.PIPE_TR, TileType.PIPE_BR]:
                pygame.draw.rect(self.screen, (0, 200, 0), (x + SCALED_TILE - 4, y, 4, SCALED_TILE))
            if tile_type in [TileType.PIPE_TL, TileType.PIPE_TR]:
                pygame.draw.rect(self.screen, (0, 220, 0), (x, y, SCALED_TILE, 8))
        elif tile_type == TileType.HARD:
            pygame.draw.rect(self.screen, (80, 80, 80), (x, y, SCALED_TILE, SCALED_TILE))
            pygame.draw.rect(self.screen, (120, 120, 120), (x + 2, y + 2, SCALED_TILE - 4, SCALED_TILE - 4), 1)
        elif tile_type == TileType.CASTLE:
            pygame.draw.rect(self.screen, CASTLE_GRAY, (x, y, SCALED_TILE, SCALED_TILE))
            # Castle pattern
            pygame.draw.line(self.screen, (80, 80, 80), (x, y + SCALED_TILE // 2), 
                           (x + SCALED_TILE, y + SCALED_TILE // 2))
        elif tile_type == TileType.LAVA:
            pygame.draw.rect(self.screen, LAVA_RED, (x, y, SCALED_TILE, SCALED_TILE))
            pygame.draw.rect(self.screen, (255, 150, 50), (x, y, SCALED_TILE, 4))
            # Animated bubbles
            if (self.anim_timer + x // 10) % 20 < 10:
                pygame.draw.circle(self.screen, (255, 200, 100), (x + 12, y + 8), 4)
        elif tile_type == TileType.BRIDGE:
            pygame.draw.rect(self.screen, (160, 100, 60), (x, y + 4, SCALED_TILE, SCALED_TILE - 8))
            # Chain pattern
            pygame.draw.line(self.screen, (100, 60, 30), (x, y + SCALED_TILE // 2), 
                           (x + SCALED_TILE, y + SCALED_TILE // 2))
        elif tile_type == TileType.AXE:
            # Handle
            pygame.draw.rect(self.screen, (139, 69, 19), (x + 12, y + 8, 8, 24))
            # Blade
            points = [(x + 6, y + 8), (x + 20, y + 2), (x + 26, y + 12), (x + 20, y + 18)]
            pygame.draw.polygon(self.screen, AXE_SILVER, points)
            # Glint
            pygame.draw.line(self.screen, WHITE, (x + 10, y + 6), (x + 14, y + 10))
        elif tile_type == TileType.WATER:
            pygame.draw.rect(self.screen, WATER_BLUE, (x, y, SCALED_TILE, SCALED_TILE))
            # Wave animation
            wave_offset = int(math.sin((x + self.anim_timer * 2) * 0.1) * 2)
            pygame.draw.line(self.screen, (100, 200, 255), (x, y + 4 + wave_offset), 
                           (x + SCALED_TILE, y + 4 + wave_offset))
        elif tile_type == TileType.CORAL:
            # Coral branches
            pygame.draw.ellipse(self.screen, CORAL_PINK, (x + 2, y + 8, 12, 20))
            pygame.draw.ellipse(self.screen, CORAL_PINK, (x + 10, y + 4, 14, 24))
            pygame.draw.ellipse(self.screen, CORAL_PINK, (x + 20, y + 10, 10, 18))

    def render_entities(self):
        """Render all entities"""
        for entity in self.entities:
            screen_x = int(entity.x - self.camera_x)
            screen_y = int(entity.y)
            
            if screen_x < -50 or screen_x > WINDOW_WIDTH + 50:
                continue
            
            if entity.type == "goomba":
                if entity.stomped:
                    # Flat goomba
                    pygame.draw.rect(self.screen, GOOMBA_BROWN, 
                                   (screen_x, screen_y + SCALED_TILE - 8, SCALED_TILE, 8))
                else:
                    # Body
                    pygame.draw.ellipse(self.screen, GOOMBA_BROWN, 
                                      (screen_x, screen_y, SCALED_TILE, SCALED_TILE - 4))
                    pygame.draw.rect(self.screen, GOOMBA_BROWN,
                                    (screen_x + 4, screen_y + SCALED_TILE - 10, SCALED_TILE - 8, 10))
                    # Feet
                    foot_offset = 0 if self.anim_frame % 2 == 0 else 2
                    pygame.draw.ellipse(self.screen, (100, 50, 30),
                                      (screen_x + foot_offset, screen_y + SCALED_TILE - 8, 10, 8))
                    pygame.draw.ellipse(self.screen, (100, 50, 30),
                                      (screen_x + SCALED_TILE - 10 - foot_offset, screen_y + SCALED_TILE - 8, 10, 8))
                    # Eyes
                    pygame.draw.ellipse(self.screen, WHITE, (screen_x + 6, screen_y + 8, 8, 8))
                    pygame.draw.ellipse(self.screen, WHITE, (screen_x + SCALED_TILE - 14, screen_y + 8, 8, 8))
                    pygame.draw.ellipse(self.screen, BLACK, (screen_x + 8, screen_y + 10, 4, 4))
                    pygame.draw.ellipse(self.screen, BLACK, (screen_x + SCALED_TILE - 12, screen_y + 10, 4, 4))
            
            elif entity.type == "koopa":
                if entity.in_shell:
                    # Shell
                    pygame.draw.ellipse(self.screen, KOOPA_GREEN,
                                      (screen_x, screen_y + 8, SCALED_TILE, SCALED_TILE - 8))
                    pygame.draw.ellipse(self.screen, (0, 200, 0),
                                      (screen_x + 4, screen_y + 12, SCALED_TILE - 8, SCALED_TILE - 16))
                else:
                    # Walking koopa
                    pygame.draw.ellipse(self.screen, KOOPA_GREEN,
                                      (screen_x + 4, screen_y, SCALED_TILE - 8, SCALED_TILE))
                    # Head
                    pygame.draw.ellipse(self.screen, (200, 180, 100),
                                      (screen_x + 8, screen_y - 8, 16, 16))
            
            elif entity.type == "mushroom":
                # Cap
                pygame.draw.ellipse(self.screen, MARIO_RED,
                                  (screen_x, screen_y, SCALED_TILE, SCALED_TILE // 2 + 4))
                # Spots
                pygame.draw.circle(self.screen, WHITE, (screen_x + 8, screen_y + 8), 4)
                pygame.draw.circle(self.screen, WHITE, (screen_x + SCALED_TILE - 8, screen_y + 8), 4)
                # Stem
                pygame.draw.rect(self.screen, (255, 220, 180),
                               (screen_x + 6, screen_y + SCALED_TILE // 2, SCALED_TILE - 12, SCALED_TILE // 2))
            
            elif entity.type == "fireflower":
                # Stem
                pygame.draw.rect(self.screen, (0, 180, 0),
                               (screen_x + 12, screen_y + 16, 8, 16))
                # Petals
                pygame.draw.ellipse(self.screen, FIRE_ORANGE, (screen_x + 4, screen_y, 12, 12))
                pygame.draw.ellipse(self.screen, FIRE_ORANGE, (screen_x + 16, screen_y, 12, 12))
                pygame.draw.ellipse(self.screen, FIRE_ORANGE, (screen_x + 4, screen_y + 8, 12, 12))
                pygame.draw.ellipse(self.screen, FIRE_ORANGE, (screen_x + 16, screen_y + 8, 12, 12))
                # Center
                pygame.draw.ellipse(self.screen, QUESTION_YELLOW, (screen_x + 10, screen_y + 6, 12, 12))
            
            elif entity.type == "star":
                # Star power-up
                color = STAR_YELLOW if self.anim_frame % 2 == 0 else WHITE
                self.draw_star(screen_x + SCALED_TILE // 2, screen_y + SCALED_TILE // 2, 14, color)
            
            elif entity.type == "coin":
                # Animated coin
                coin_width = 8 + int(abs(math.sin(self.anim_timer * 0.2)) * 8)
                x_offset = (SCALED_TILE - coin_width) // 2
                pygame.draw.ellipse(self.screen, COIN_YELLOW,
                                  (screen_x + x_offset, screen_y, coin_width, SCALED_TILE))
                pygame.draw.ellipse(self.screen, (200, 150, 50),
                                  (screen_x + x_offset + 2, screen_y + 4, coin_width - 4, SCALED_TILE - 8), 1)

    def draw_star(self, cx, cy, size, color):
        """Draw a star shape"""
        points = []
        for i in range(10):
            angle = math.pi / 2 + i * math.pi / 5
            r = size if i % 2 == 0 else size // 2
            x = cx + int(math.cos(angle) * r)
            y = cy - int(math.sin(angle) * r)
            points.append((x, y))
        pygame.draw.polygon(self.screen, color, points)

    def draw_mario(self, x, y, facing_right, power, frame, star_flash=False):
        """Draw Mario sprite"""
        height = SCALED_TILE if power == PowerState.SMALL else SCALED_TILE * 2
        
        # Colors
        hat_color = WHITE if star_flash else MARIO_RED
        skin_color = STAR_YELLOW if star_flash else MARIO_SKIN
        overall_color = (0, 255, 255) if star_flash else (WHITE if power == PowerState.FIRE else MARIO_RED)
        
        if power == PowerState.SMALL:
            # Small Mario
            # Hat
            pygame.draw.rect(self.screen, hat_color, (x + 4, y, 24, 8))
            pygame.draw.rect(self.screen, hat_color, (x + 2, y + 4, 28, 6))
            
            # Face
            pygame.draw.rect(self.screen, skin_color, (x + 4, y + 10, 24, 10))
            
            # Eyes
            eye_offset = 18 if facing_right else 6
            pygame.draw.rect(self.screen, BLACK, (x + eye_offset, y + 12, 4, 4))
            
            # Body
            pygame.draw.rect(self.screen, overall_color, (x + 6, y + 20, 20, 12))
        else:
            # Big/Fire Mario
            # Hat
            pygame.draw.rect(self.screen, hat_color, (x + 4, y, 24, 10))
            pygame.draw.rect(self.screen, hat_color, (x + 2, y + 6, 28, 8))
            
            # Face
            pygame.draw.rect(self.screen, skin_color, (x + 4, y + 14, 24, 14))
            
            # Eyes
            eye_offset = 18 if facing_right else 6
            pygame.draw.rect(self.screen, BLACK, (x + eye_offset, y + 18, 5, 5))
            
            # Mustache
            pygame.draw.rect(self.screen, (80, 40, 20), (x + 6, y + 24, 20, 4))
            
            # Body
            pygame.draw.rect(self.screen, overall_color, (x + 4, y + 28, 24, 20))
            
            # Buttons
            pygame.draw.circle(self.screen, COIN_YELLOW, (x + 12, y + 34), 2)
            pygame.draw.circle(self.screen, COIN_YELLOW, (x + 20, y + 34), 2)
            
            # Arms
            if frame in [1, 2]:
                pygame.draw.rect(self.screen, skin_color, (x, y + 32, 6, 10))
                pygame.draw.rect(self.screen, skin_color, (x + 26, y + 32, 6, 10))
            else:
                pygame.draw.rect(self.screen, skin_color, (x, y + 34, 6, 8))
                pygame.draw.rect(self.screen, skin_color, (x + 26, y + 34, 6, 8))
            
            # Legs
            leg_offset = -2 if frame == 1 else (2 if frame == 2 else 0)
            pygame.draw.rect(self.screen, (100, 60, 40), (x + 6 + leg_offset, y + 48, 8, 16))
            pygame.draw.rect(self.screen, (100, 60, 40), (x + 18 - leg_offset, y + 48, 8, 16))

    def render_hud(self):
        """Render HUD elements"""
        # Score
        text = self.font_small.render("SCORE", True, WHITE)
        self.screen.blit(text, (20, 5))
        text = self.font_small.render(f"{self.score:06d}", True, WHITE)
        self.screen.blit(text, (20, 20))
        
        # Coins
        pygame.draw.circle(self.screen, COIN_YELLOW, (128, 18), 10)
        text = self.font_small.render(f"x{self.coins:02d}", True, WHITE)
        self.screen.blit(text, (140, 11))
        
        # World
        text = self.font_small.render("WORLD", True, WHITE)
        self.screen.blit(text, (220, 5))
        text = self.font_small.render(f"{self.current_world}-{self.current_level}", True, WHITE)
        self.screen.blit(text, (225, 20))
        
        # Time
        text = self.font_small.render("TIME", True, WHITE)
        self.screen.blit(text, (320, 5))
        color = MARIO_RED if self.time_remaining <= 100 else WHITE
        text = self.font_small.render(str(self.time_remaining), True, color)
        self.screen.blit(text, (320, 20))
        
        # Lives
        text = self.font_small.render(f"LIVES: {self.lives}", True, WHITE)
        self.screen.blit(text, (420, 11))
        
        # Power indicator
        if self.star_timer > 0:
            text = self.font_small.render("★ STAR!", True, STAR_YELLOW)
            self.screen.blit(text, (500, 11))
        elif self.player_power == PowerState.FIRE:
            text = self.font_small.render("🔥 FIRE", True, FIRE_ORANGE)
            self.screen.blit(text, (500, 11))

    def render_pause_overlay(self):
        """Render pause screen overlay"""
        # Semi-transparent overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(150)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        # Paused text
        text = self.font_large.render("PAUSED", True, WHITE)
        text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
        self.screen.blit(text, text_rect)
        
        text = self.font_medium.render("Press P to resume", True, WHITE)
        text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 40))
        self.screen.blit(text, text_rect)

    def render_game_over(self):
        """Render game over screen"""
        self.screen.fill(BLACK)
        
        text = self.font_large.render("GAME OVER", True, WHITE)
        text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 30))
        self.screen.blit(text, text_rect)
        
        text = self.font_medium.render(f"Final Score: {self.score}", True, WHITE)
        text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 20))
        self.screen.blit(text, text_rect)
        
        if (self.anim_timer // 30) % 2 == 0:
            text = self.font_small.render("Press ENTER to continue", True, WHITE)
            text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 60))
            self.screen.blit(text, text_rect)

    def render_level_complete(self):
        """Render level complete overlay"""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(100)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        text = self.font_large.render("LEVEL COMPLETE!", True, WHITE)
        text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
        self.screen.blit(text, text_rect)

    def render_world_intro(self):
        """Render world intro screen"""
        self.screen.fill(BLACK)
        
        text = self.font_large.render(f"WORLD {self.current_world}-{self.current_level}", True, WHITE)
        text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20))
        self.screen.blit(text, text_rect)
        
        # Draw Mario and lives
        self.draw_mario(WINDOW_WIDTH // 2 - 40, WINDOW_HEIGHT // 2 + 20, True, PowerState.SMALL, 0)
        text = self.font_medium.render(f"x {self.lives}", True, WHITE)
        self.screen.blit(text, (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 35))

    def render_victory(self):
        """Render victory screen"""
        # Animated background
        blue_value = int(50 + math.sin(self.victory_timer * 0.05) * 30)
        self.screen.fill((0, 0, blue_value))
        
        # Firework particles
        for particle in self.particles:
            pygame.draw.circle(self.screen, particle.color, (int(particle.x), int(particle.y)), 3)
        
        # Victory text
        text = self.font_large.render("CONGRATULATIONS!", True, COIN_YELLOW)
        text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, 100))
        self.screen.blit(text, text_rect)
        
        text = self.font_medium.render("You saved the Mushroom Kingdom!", True, WHITE)
        text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, 150))
        self.screen.blit(text, text_rect)
        
        # Mario celebration
        mario_y = WINDOW_HEIGHT // 2 + int(math.sin(self.victory_timer * 0.1) * 10)
        star_flash = (self.victory_timer // 5) % 2 == 0
        self.draw_mario(WINDOW_WIDTH // 2 - SCALED_TILE // 2, mario_y, True, 
                       PowerState.BIG, (self.victory_timer // 10) % 3, star_flash)
        
        # Final score
        text = self.font_large.render(f"FINAL SCORE: {self.score}", True, WHITE)
        text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 100))
        self.screen.blit(text, text_rect)
        
        # Credits
        text = self.font_small.render("Created by Catsan / Team Flames", True, COIN_YELLOW)
        text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 60))
        self.screen.blit(text, text_rect)
        
        # Restart prompt
        if (self.anim_timer // 30) % 2 == 0:
            text = self.font_small.render("Press ENTER to play again", True, WHITE)
            text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 30))
            self.screen.blit(text, text_rect)

    def handle_key_down(self, key):
        """Handle key press events"""
        if self.game_state == GameState.TITLE:
            if key == pygame.K_RETURN:
                self.start_game()
            return
        
        if self.game_state in [GameState.GAME_OVER, GameState.VICTORY]:
            if key == pygame.K_RETURN:
                self.reset_game()
                self.game_state = GameState.TITLE
            return
        
        if self.game_state == GameState.PLAYING:
            if key in [pygame.K_LEFT, pygame.K_a]:
                self.left_pressed = True
            elif key in [pygame.K_RIGHT, pygame.K_d]:
                self.right_pressed = True
            elif key in [pygame.K_UP, pygame.K_w, pygame.K_SPACE, pygame.K_z]:
                self.jump_pressed = True
            elif key in [pygame.K_DOWN, pygame.K_s]:
                self.down_pressed = True
            elif key in [pygame.K_x, pygame.K_LSHIFT, pygame.K_RSHIFT]:
                self.run_pressed = True
                if self.player_power == PowerState.FIRE and not self.player_dead:
                    self.shoot_fireball()
            elif key == pygame.K_p:
                self.game_state = GameState.PAUSED
            elif key == pygame.K_ESCAPE:
                self.game_state = GameState.TITLE
        elif self.game_state == GameState.PAUSED:
            if key == pygame.K_p:
                self.game_state = GameState.PLAYING
            elif key == pygame.K_ESCAPE:
                self.game_state = GameState.TITLE

    def handle_key_up(self, key):
        """Handle key release events"""
        if key in [pygame.K_LEFT, pygame.K_a]:
            self.left_pressed = False
        elif key in [pygame.K_RIGHT, pygame.K_d]:
            self.right_pressed = False
        elif key in [pygame.K_UP, pygame.K_w, pygame.K_SPACE, pygame.K_z]:
            self.jump_pressed = False
            self.jump_held = False
        elif key in [pygame.K_DOWN, pygame.K_s]:
            self.down_pressed = False
        elif key in [pygame.K_x, pygame.K_LSHIFT, pygame.K_RSHIFT]:
            self.run_pressed = False

    def shoot_fireball(self):
        """Shoot a fireball"""
        # Limit fireballs
        fireball_count = sum(1 for e in self.entities if e.type == "fireball")
        if fireball_count >= 2:
            return
        
        fireball = Entity("fireball",
                         self.player_x + (SCALED_TILE if self.player_facing_right else -8),
                         self.player_y + SCALED_TILE // 2)
        fireball.vel_x = 8 if self.player_facing_right else -8
        fireball.vel_y = 0
        self.entities.append(fireball)

    def start_game(self):
        """Start a new game"""
        self.reset_game()
        self.game_state = GameState.WORLD_INTRO

    def reset_game(self):
        """Reset game to initial state"""
        self.current_world = 1
        self.current_level = 1
        self.lives = 3
        self.coins = 0
        self.score = 0
        self.player_power = PowerState.SMALL
        self.load_level(self.current_world, self.current_level)

if __name__ == "__main__":
    print("=" * 50)
    print("ULTRA MARIO 2D BROS - TRUE FIXED VERSION")
    print("=" * 50)
    print("Controls:")
    print("- Arrow Keys: Move")
    print("- Z or Space: Jump")
    print("- X: Run/Fire")
    print("- P: Pause")
    print("- ESC: Back to Title")
    print("=" * 50)
    
    game = UltraMario2D()
    game.run()
