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

        center_x = self.rect.centerx
        center_y = self.rect.centery
        self.hitbox = pygame.Rect(center_x - (self.rect.width // 4), center_y - (self.rect.height * 0.4), self.rect.width // 2, self.rect.height * 0.8)
        self.target_angle = 0
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
        self.last_key_pressed = None
        self.contact_mode = FLOOR

        # Sensors for slope detection
        self.sensor_front = pygame.Rect(self.hitbox.centerx + 10, self.hitbox.bottom, 5, 5)
        self.sensor_back = pygame.Rect(self.hitbox.centerx - 10, self.hitbox.bottom, 5, 5)

    def update_contact_mode(self):
        """Update Sonic's contact mode based on the current angle."""
        if 316 <= self.angle <= 360 or 0 <= self.angle <= 44:
            self.contact_mode = FLOOR
        elif 45 <= self.angle <= 135:
            self.contact_mode = RIGHT_WALL
        elif 136 <= self.angle <= 224:
            self.contact_mode = CEILING
        elif 225 <= self.angle <= 315:
            self.contact_mode = LEFT_WALL

    def update(self):
        keys = pygame.key.get_pressed()

        # Jump logic (adjust for contact mode)
        if keys[pygame.K_SPACE] and not self.jumped:
            self.Yvel = -15
            self.jumped = True
            self.grounded = False
            if not self.jumpSoundPlayed:
                pygame.mixer.Sound.play(jumpSound)
                self.jumpSoundPlayed = True
            self.jumpSoundPlayed = False  

        # Movement logic remains the same
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.direction = 1
            if self.groundSpeed > 0:
                self.groundSpeed -= self.deceleration
                self.stopping = True
                if self.groundSpeed <= 0:
                    self.groundSpeed = -0.5
                    self.stopping = False
            elif self.groundSpeed > -self.maxSpeed:
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
        
        if self.stopping:
            if not self.stoppingSoundPlayed:
                pygame.mixer.Sound.play(stoppingSound)
                self.stoppingSoundPlayed = True
        else:
            self.stoppingSoundPlayed = False

        # Apply gravity if not on the ground
        if not self.grounded:
            self.Yvel += self.gravityforce # Increase gravity effect
            self.Yvel = min(self.Yvel, 15)  # Increase fall speed cap
            self.Xvel = self.groundSpeed

        else:
            # Adjust movement vector based on angle
            speed_vector = pygame.math.Vector2(self.groundSpeed, 0)
            speed_vector = speed_vector.rotate(-self.angle)
            self.Xvel = speed_vector.x
            self.Yvel = speed_vector.y

        # Update Sonic's position
        self.x += self.Xvel
        self.rect.x = self.x
        self.y += self.Yvel
        self.rect.y = self.y
        self.hitbox.x = self.x
        self.hitbox.y = self.y

        # Update sensors' position
        self.sensor_front.midbottom = (self.hitbox.centerx + 10, self.hitbox.bottom)
        self.sensor_back.midbottom = (self.hitbox.centerx - 10, self.hitbox.bottom)

        # Update animation
        self.update_animation()
        self.update_contact_mode()

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