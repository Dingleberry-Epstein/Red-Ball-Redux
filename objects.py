import pygame, os, math, time

from constants import *
from utils import Button
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

platform_img1 = pygame.image.load(os.path.join("assets", "world building", "HUBGround.png"))

class Tile(pygame.sprite.Sprite):
    def __init__(self, image, position, angle=0):  # Default angle to 0 if not provided
        super().__init__()
        self.image = image.convert_alpha()  
        self.rect = self.image.get_rect(topleft=position)
        self.mask = pygame.mask.from_surface(self.image)  
        self.angle = angle  # Store the angle

class Ring(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.x = int(x)
        self.y = int(y)
        self.imageLoad = [pygame.image.load(os.path.join("assets", "sprites", "ring", f"ring{i}.png")).convert_alpha() for i in range(1, 9)]
        self.images = [pygame.transform.scale(image, (50, 50)) for image in self.imageLoad]
        self.rect = self.images[0].get_rect()
        self.rect.topleft = (x, y)
        self.collectSound = pygame.mixer.Sound(os.path.join("assets", "sounds", "collectring.mp3"))
        self.frame = 0
        self.animation_speed = 0.1

    def update(self):
        # Update animation frame based on animation speed
        self.frame += self.animation_speed
        self.frame %= len(self.images)
        self.image = self.images[int(self.frame)]

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, enemy_type):
        super().__init__()
        self.x = int(x)
        self.y = int(y)
        self.enemy_type = enemy_type
        self.width = 40
        self.height = 40
        self.animation_speed = 200
        self.explosion_animation_speed = 75
        self.current_frame = 0
        self.animation_frames = [pygame.image.load(os.path.join("assets", "sprites", "Badniks", f"badnikroller{i}.png")).convert_alpha() for i in range(1, 5)]  # Load animation frames here
        self.image = self.animation_frames[self.current_frame]  # Placeholder image
        self.rect = self.image.get_rect(topleft=(self.x, self.y))
        self.velocity = 1  # Velocity for moving enemies
        self.gravity = 5
        self.last_update = pygame.time.get_ticks()
        self.death_sound = pygame.mixer.Sound(os.path.join("assets", "sounds", "explosion.mp3"))
        self.death_sound_played = False
        self.explosion_frames = [pygame.transform.scale(pygame.image.load(os.path.join("assets", "sprites", "Badniks", f"explosion{i}.png")).convert_alpha(), (160, 160)) for i in range(1, 18)]
        self.alive = True
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, player_rect):
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

        # Check for collision with player

    def explode(self):
        self.alive = False
        if not self.death_sound_played:
            self.death_sound.play()
            self.death_sound_played = True
        self.explosion_start_time = pygame.time.get_ticks()  # Record the start time of the explosion

class Laser(pygame.sprite.Sprite):
    def __init__(self, start_x, start_y, speed, lifespan=5):
        super().__init__()
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
        # Move the laser horizontally by adding the speed to the X position
        self.rect.x -= self.speed
        # Check if the laser's lifespan (5 seconds) has passed
        if time.time() - self.start_time >= self.lifespan:
            self.kill()  # Remove the laser from the sprite group if its lifespan has passed

class HealthBar:
    def __init__(self, boss, screen):
        self.boss = boss
        self.screen = screen
        # Adjust the width and height as needed
        self.health_bar_width = 400  # Wider health bar
        self.health_bar_height = 50  # Taller health bar
        # Position the health bar at the top of the screen
        self.health_bar_position = (self.screen.get_width() // 2 - self.health_bar_width // 2, 10)
        self.font = RingFont

    def update(self):
        # Calculate the current health fraction
        health_fraction = self.boss.health / self.boss.max_health
        # Calculate the width of the current health portion
        current_health_width = self.health_bar_width * health_fraction

        # Define colors
        current_health_color = (0, 255, 0)  # Green for current health
        missing_health_color = (255, 0, 0)  # Red for missing health
        outline_color = (0, 0, 0)  # Black for outline

        # Store information for later use in the draw method
        self.current_health_width = current_health_width
        self.health_fraction = health_fraction
        self.current_health_color = current_health_color
        self.missing_health_color = missing_health_color
        self.outline_color = outline_color
        
    def draw(self):
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