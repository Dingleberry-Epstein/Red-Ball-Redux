import pygame, os, math, time, pytmx

from constants import *
from utils import Button

# Platform and background test rectangles
platX = 10
platY = 500
platW = 5000
platH = 47
testbgX = 0
testbgY = 0
testbgW = 1728
testbgH = 1080
test_platform = pygame.Rect(platX, platY, platW, platH)
testbg_rect = pygame.Rect(testbgX, testbgY, testbgW, testbgH)

# Load TMX file
Windmill_Isle_TMX = pytmx.load_pygame(os.path.join("assets", "world building", "Tiled Worlds", "sonic test world.tmx"))

class GameObject(pygame.sprite.Sprite):
    """Base class for all game objects"""
    def __init__(self, x, y):
        super().__init__()
        self.x = int(x)
        self.y = int(y)
        self.rect = None
        self.image = None
        self.mask = None
    
    def update(self):
        """Update method to be overridden by child classes"""
        pass

class Tile(GameObject):
    """Tile class for level building"""
    def __init__(self, image, position, angle=0, collideable=True):
        super().__init__(position[0], position[1])
        self.image = image.convert_alpha()  # Ensure the image has alpha transparency
        self.rect = self.image.get_rect(topleft=position)
        self.angle = angle  # Store the tile's angle
        self.collideable = collideable  # Whether the tile is collideable

        # Only create a mask if the tile is collideable
        if self.collideable:
            self.mask = pygame.mask.from_surface(self.image)
        else:
            self.mask = None  # No collision for non-collideable tiles

class AnimatedGameObject(GameObject):
    """Base class for animated game objects"""
    def __init__(self, x, y):
        super().__init__(x, y)
        self.frame = 0
        self.animation_speed = 0.1
        self.images = []
        self.current_frame = 0
    
    def update_animation(self):
        """Update animation frame based on animation speed"""
        self.frame += self.animation_speed
        self.current_frame = int(self.frame) % len(self.images)
        self.image = self.images[self.current_frame]

class Ring(AnimatedGameObject):
    """Ring collectible class - Optimized version"""
    def __init__(self, x, y):
        super().__init__(x, y)
        # Class-level shared resources (move these to be static class variables)
        if not hasattr(Ring, 'images_loaded'):
            Ring.images_loaded = [pygame.image.load(os.path.join("assets", "sprites", "ring", f"ring{i}.png")).convert_alpha() for i in range(1, 9)]
            Ring.images = [pygame.transform.scale(image, (50, 50)) for image in Ring.images_loaded]
            Ring.collect_sound = pygame.mixer.Sound(os.path.join("assets", "sounds", "collectring.mp3"))
        
        self.rect = Ring.images[0].get_rect()
        self.rect.topleft = (x, y)
        self.collectSound = Ring.collect_sound
        self.image = Ring.images[0]
        self.animation_speed = 0.2  # Slow down animation to improve performance

    def update(self):
        """Update ring animation - optimized"""
        # Update animation frame based on animation speed
        self.frame += self.animation_speed
        self.frame %= len(Ring.images)
        self.image = Ring.images[int(self.frame)]
        
class Enemy(AnimatedGameObject):
    """Enemy class with different types and behaviors"""
    def __init__(self, x, y, enemy_type):
        super().__init__(x, y)
        self.enemy_type = enemy_type
        self.width = 40
        self.height = 40
        self.animation_speed = 200  # milliseconds
        self.explosion_animation_speed = 75
        self.current_frame = 0
        self.animation_frames = [pygame.image.load(os.path.join("assets", "sprites", "Badniks", f"badnikroller{i}.png")).convert_alpha() for i in range(1, 5)]
        self.image = self.animation_frames[self.current_frame]
        self.rect = self.image.get_rect(topleft=(self.x, self.y))
        self.velocity = 1  # Velocity for moving enemies
        self.gravity = 5
        self.last_update = pygame.time.get_ticks()
        self.death_sound = pygame.mixer.Sound(os.path.join("assets", "sounds", "explosion.mp3"))
        self.death_sound_played = False
        self.explosion_frames = [pygame.transform.scale(pygame.image.load(os.path.join("assets", "sprites", "Badniks", f"explosion{i}.png")).convert_alpha(), (160, 160)) for i in range(1, 18)]
        self.alive = True
        self.mask = pygame.mask.from_surface(self.image)
        self.direction = 1

    def update(self, player_rect):
        """Update enemy behavior based on type and player position"""
        if self.enemy_type == "roller":
            if self.alive:
                if self.rect.x < player_rect.x:
                    self.rect.x += self.velocity
                    self.direction = -1
                elif self.rect.x > player_rect.x:
                    self.rect.x -= self.velocity
                    self.direction = 1
                now = pygame.time.get_ticks()
                if now - self.last_update > self.animation_speed:
                    self.last_update = now
                    self.current_frame = (self.current_frame + 1) % len(self.animation_frames)
                    if self.direction == 1:
                        self.image = self.animation_frames[self.current_frame]
                    elif self.direction == -1:
                        self.image = pygame.transform.flip(self.animation_frames[self.current_frame], True, False)
            else:
                now = pygame.time.get_ticks()
                if now - self.last_update > self.explosion_animation_speed:
                    self.last_update = now
                    self.current_frame = (self.current_frame + 1) % len(self.explosion_frames)
                    if self.direction == 1:
                        self.image = self.explosion_frames[self.current_frame]
                    elif self.direction == -1:
                        self.image = pygame.transform.flip(self.explosion_frames[self.current_frame], True, False)
                self.rect.y = 350

        if hasattr(self, 'explosion_start_time'):
            if pygame.time.get_ticks() - self.explosion_start_time >= 1000:
                self.kill()

    def explode(self):
        """Handle enemy explosion animation and sound"""
        self.alive = False
        if not self.death_sound_played:
            self.death_sound.play()
            self.death_sound_played = True
        self.explosion_start_time = pygame.time.get_ticks()  # Record the start time of the explosion

class Laser(GameObject):
    """Laser projectile class"""
    def __init__(self, start_x, start_y, speed, lifespan=5):
        super().__init__(start_x, start_y)
        # Load the laser image and create a rect around it
        self.img = pygame.image.load(os.path.join("assets", "sprites", "Gamma", "laser1.png")).convert_alpha()
        self.img_rect = self.img.get_rect()
        self.image = pygame.transform.scale(self.img, (self.img_rect.width * 2, self.img_rect.height * 3))
        self.rect = self.image.get_rect(center=(start_x, start_y))
        self.speed = speed
        self.start_time = time.time()  # Record the time when the laser is launched
        self.lifespan = lifespan
        self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        """Update laser position and check lifespan"""
        # Move the laser horizontally by adding the speed to the X position
        self.rect.x -= self.speed
        # Check if the laser's lifespan (5 seconds) has passed
        if time.time() - self.start_time >= self.lifespan:
            self.kill()  # Remove the laser from the sprite group if its lifespan has passed

class HealthBar:
    """Boss health bar UI class"""
    def __init__(self, boss, screen):
        self.boss = boss
        self.screen = screen
        # Adjust the width and height as needed
        self.health_bar_width = 400  # Wider health bar
        self.health_bar_height = 50  # Taller health bar
        # Position the health bar at the top of the screen
        self.health_bar_position = (self.screen.get_width() // 2 - self.health_bar_width // 2, 10)
        self.font = RingFont
        self.current_health_width = 0
        self.health_fraction = 1
        self.current_health_color = (0, 255, 0)
        self.missing_health_color = (255, 0, 0)
        self.outline_color = (0, 0, 0)

    def update(self):
        """Update health bar based on boss health"""
        # Calculate the current health fraction
        self.health_fraction = self.boss.health / self.boss.max_health
        # Calculate the width of the current health portion
        self.current_health_width = self.health_bar_width * self.health_fraction

        # Define colors
        self.current_health_color = (0, 255, 0)  # Green for current health
        self.missing_health_color = (255, 0, 0)  # Red for missing health
        self.outline_color = (0, 0, 0)  # Black for outline
        
    def draw(self):
        """Draw the health bar on screen"""
        # Draw the missing health portion (red)
        pygame.draw.rect(
            self.screen,
            self.missing_health_color,
            (self.health_bar_position[0] + self.current_health_width, self.health_bar_position[1],
             self.health_bar_width - self.current_health_width, self.health_bar_height)
        )
        
        # Draw the current health portion (green)
        pygame.draw.rect(
            self.screen,
            self.current_health_color,
            (self.health_bar_position[0], self.health_bar_position[1],
             self.current_health_width, self.health_bar_height)
        )

        # Draw the outline of the health bar (black)
        pygame.draw.rect(
            self.screen,
            self.outline_color,
            (self.health_bar_position[0], self.health_bar_position[1],
             self.health_bar_width, self.health_bar_height),
            2  # Line width for the outline
        )

        # Draw the label "RANDOM AHH ROBOT" inside the health bar
        label_text = "RANDOM AHH ROBOT"
        label_color = (255, 255, 255)  # White color for the label text
        label_surface = self.font.render(label_text, True, label_color)
        label_position = (self.health_bar_position[0] + self.health_bar_width // 2 - label_surface.get_width() // 2, self.health_bar_position[1] + self.health_bar_height // 2 - label_surface.get_height() // 2)
        self.screen.blit(label_surface, label_position)