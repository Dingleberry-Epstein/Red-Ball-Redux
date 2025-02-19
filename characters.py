import pygame, math, random
from constants import *
from objects import *

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

clock = pygame.time.Clock()
pygame.mixer.init()

class Sonic(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.x = int(x)
        self.y = int(y)
        self.frame = 0
        self.width = 40 
        self.height = 40
        self.run_images = [pygame.image.load(os.path.join("assets", "sprites", "Sonic", f"SonicRun{i}.png")).convert_alpha() for i in range(1, 9)]
        self.sprint_images = [pygame.image.load(os.path.join("assets", "sprites", "Sonic", f"SonicSprint{i}.png")).convert_alpha() for i in range(1, 9)]
        self.boosting_images = [pygame.image.load(os.path.join("assets", "sprites", "Sonic", f"SonicBoost{i}.png")).convert_alpha() for i in range(1, 9)]
        self.idle_images = [pygame.image.load(os.path.join("assets", "sprites", "Sonic", f"SonicIdle{i}.png")).convert_alpha() for i in range(1, 6)]
        self.jump_images = [pygame.image.load(os.path.join("assets", "sprites", "Sonic", f"SonicJump{i}.png")).convert_alpha() for i in range(1, 5)]
        self.stopping_images = [pygame.image.load(os.path.join("assets", "sprites", "Sonic", f"SonicStopping{i}.png")).convert_alpha() for i in range(1, 3)]
        self.image_index = 0
        self.image = self.idle_images[self.image_index]
        self.rect = self.image.get_rect(topleft=(self.x, self.y))
        # Calculate the center of the rectangle
        center_x = self.rect.centerx
        center_y = self.rect.centery
        # Create the hitbox centered on the rectangle
        self.hitbox = pygame.Rect(center_x - (self.rect.width // 4), center_y - (self.rect.height * 0.4), self.rect.width // 2, self.rect.height * 0.8)

        self.animation_speed = 0.1
        self.acceleration = 0.2
        self.max_acceleration = 0.3
        self.deceleration = 0.5
        self.friction = 0.46875
        self.maxSpeed = 20
        self.groundSpeed = 0
        self.gravityforce = 0.5
        self.angle = 0
        self.jumped = False
        self.direction = 0
        self.Xvel = 0
        self.Yvel = 0
        self.jumpSoundPlayed = False
        self.gameover = False
        self.grounded = False
        self.stopping = False
        self.stoppingSoundPlayed = False
        self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE] and not self.jumped:  # Check if Space key is pressed and Sonic hasn't jumped yet
            self.Yvel = -15
            self.jumped = True
            self.grounded = False
            if not self.jumpSoundPlayed:
                pygame.mixer.Sound.play(jumpSound)
                self.jumpSoundPlayed = True
            self.jumpSoundPlayed = False  # Update the flag to indicate that the jump sound has been played
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.direction = 1
            if self.groundSpeed > 0:
                self.groundSpeed -= self.deceleration
                self.stopping = True
                if self.groundSpeed <= 0:
                    self.groundSpeed = -0.5
                    self.stopping = False
            elif self.groundSpeed > -self.maxSpeed:
                # Gradually increase acceleration up to maximum
                if self.acceleration < self.max_acceleration:
                    self.acceleration += 0.001
                if self.acceleration > self.max_acceleration:
                    self.acceleration = self.max_acceleration
                self.groundSpeed -= self.acceleration
                if self.groundSpeed <= -self.maxSpeed:
                    self.groundSpeed = -self.maxSpeed
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.direction = -1
            if self.groundSpeed < 0:
                self.groundSpeed += self.deceleration
                self.stopping = True
                if self.groundSpeed >= 0:
                    self.groundSpeed = 0.5
                    self.stopping = False
            elif self.groundSpeed < self.maxSpeed:
                # Gradually increase acceleration up to maximum
                if self.acceleration < self.max_acceleration:
                    self.acceleration += 0.001
                if self.acceleration > self.max_acceleration:
                    self.acceleration = self.max_acceleration
                self.groundSpeed += self.acceleration
                if self.groundSpeed >= self.maxSpeed:
                    self.groundSpeed = self.maxSpeed
        else:
            if self.acceleration > 0.05:
                self.acceleration -= 0.001
            self.groundSpeed -= min(abs(self.groundSpeed), self.friction) * (self.groundSpeed / abs(self.groundSpeed) if self.groundSpeed != 0 else 0)
            self.stopping = False
        if self.stopping and not self.jumped:
            if not self.stoppingSoundPlayed:
                stoppingSound.play()
                self.stoppingSoundPlayed = True
        if self.stoppingSoundPlayed == True and not self.stopping:
            self.stoppingSoundPlayed = False

        if not self.grounded:
            self.Yvel += self.gravityforce  # Apply gravity
            self.Yvel = min(self.Yvel, 10)  # Cap max fall speed
            self.Xvel = self.groundSpeed
        else:
            self.Yvel = self.groundSpeed * math.sin(self.angle * -1)
            self.Xvel = self.groundSpeed * math.cos(self.angle)    

        self.x += self.Xvel
        self.rect.x = self.x  # Update self.rect with the new x coordinate
        self.y += self.Yvel
        self.rect.y = self.y
        self.hitbox.x = self.x
        self.hitbox.y = self.y
        # Update animation speed and direction
        self.update_animation()

    def update_animation(self):
        # Calculate animation speed based on Sonic's ground speed
        self.animation_speed = min(0.1 + abs(self.groundSpeed) * 0.01, 0.5)

        # Update animation frame based on animation speed
        self.frame += self.animation_speed
        self.image_index = int(self.frame) % len(self.run_images)

        # Update Sonic's image
        if self.groundSpeed > 0 and not self.jumped and not self.stopping:
            if self.groundSpeed < 15:
                self.image = self.run_images[self.image_index]
            elif self.groundSpeed > 15:
                self.image = self.sprint_images[self.image_index]
            elif self.groundSpeed > 30:
                self.image = self.boosting_images[self.image_index]
        elif self.groundSpeed < 0 and not self.jumped and not self.stopping:
            if self.groundSpeed > -15:
                self.image = pygame.transform.flip(self.run_images[self.image_index], True, False)
            elif self.groundSpeed < -15:
                self.image = pygame.transform.flip(self.sprint_images[self.image_index], True, False)
            elif self.groundSpeed < -30:
                self.image = pygame.transform.flip(self.boosting_images[self.image_index], True, False)
        elif self.groundSpeed == 0 and not self.jumped and not self.stopping:
            self.image_index = int(self.frame) % len(self.idle_images)
            if self.direction == -1:
                self.image = self.idle_images[self.image_index]
            elif self.direction == 1:
                self.image = pygame.transform.flip(self.idle_images[self.image_index], True, False)

        if self.jumped:
            jump_image_count = len(self.jump_images)
            self.image_index = int(self.frame) % jump_image_count
            if self.groundSpeed > 0:
                self.image = self.jump_images[self.image_index]
            elif self.groundSpeed < 0:
                self.image = pygame.transform.flip(self.jump_images[self.image_index], True, False)
            else:
                if self.direction == -1:
                    self.image = self.jump_images[self.image_index]
                elif self.direction == 1:
                    self.image = pygame.transform.flip(self.jump_images[self.image_index], True, False)

        if self.stopping and not self.jumped:
            stopping_image_count = len(self.stopping_images)
            self.image_index = int(self.frame) % stopping_image_count
            if self.direction == 1:
                self.image = self.stopping_images[self.image_index]
            elif self.direction == -1:
                self.image = pygame.transform.flip(self.stopping_images[self.image_index], True, False)
        
        self.image = pygame.transform.rotate(self.image, self.angle)