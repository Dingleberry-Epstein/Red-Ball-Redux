import pygame
import pymunk

class PurePymunkBall(pygame.sprite.Sprite):
    """Ball character using velocity changes for direct control, with pure Pymunk physics"""

    def __init__(self, physics_manager, x, y, radius=20):
        super().__init__()

        # Reference to physics space
        self.physics = physics_manager

        # Create the body with proper mass
        mass = 5.0
        moment = pymunk.moment_for_circle(mass, 0, radius)
        self.body = pymunk.Body(mass, moment)
        self.body.position = (x, y)

        # Create shape with moderate friction
        self.shape = pymunk.Circle(self.body, radius)
        self.shape.elasticity = 0.0
        self.shape.friction = 0.5
        self.shape.collision_type = self.physics.collision_types["ball"]
        self.jumped = False

        self.physics.space.add(self.body, self.shape)

        # Visual properties
        self.radius = radius
        self.original_image = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.original_image, (255, 0, 0), (radius, radius), radius)
        pygame.draw.line(self.original_image, (0, 0, 0),
                         (radius, radius), (radius * 2, radius), 1)

        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=(x, y))

        # Movement parameters
        self.move_speed = 20.0
        self.jump_speed = 500.0
        self.max_speed = 1000
        
        # Optimization: Track last angle to avoid unnecessary rotations
        self.last_angle = 0

    def update(self):
        """Update based on input, using velocity changes"""
        # Get keyboard input
        keys = pygame.key.get_pressed()

        # Optimize: Cache max speed based on shift key
        self.max_speed = 2000 if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else 1000

        # Apply velocity changes for movement
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            if self.body.velocity.x > -self.max_speed:
                self.body.velocity = (self.body.velocity.x - self.move_speed, self.body.velocity.y)
            else:
                self.body.velocity = (-self.max_speed, self.body.velocity.y)
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            if self.body.velocity.x < self.max_speed:
                self.body.velocity = (self.body.velocity.x + self.move_speed, self.body.velocity.y)
            else:
                self.body.velocity = (self.max_speed, self.body.velocity.y)

        # Jump with velocity change when on ground
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and not self.jumped:
            self.body.velocity = (self.body.velocity.x, -self.jump_speed)
            self.jumped = True
        if self.body.velocity.y == 0:
            self.jumped = False

        # Update sprite position
        self.rect.center = self.body.position
        
        # Optimization: Only update rotation when needed
        current_angle = self.body.angle
        if abs(current_angle - self.last_angle) > 0.01:  # Only rotate if angle changed significantly
            self.update_rotation()
            self.last_angle = current_angle

    def update_rotation(self):
        """Update sprite rotation to match physics body"""
        angle_degrees = self.body.angle * 57.29578  # Convert radians to degrees
        self.image = pygame.transform.rotate(self.original_image, -angle_degrees)
        self.rect = self.image.get_rect(center=self.rect.center)