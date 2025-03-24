import pygame, math, random, numpy
from constants import *
from objects import *
from utils import joystick

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

clock = pygame.time.Clock()
pygame.mixer.init()

class Character(pygame.sprite.Sprite):
    """Base class for all game characters"""
    def __init__(self, x, y, image):
        super().__init__()
        self.x = int(x)
        self.y = int(y)
        self.width = 0
        self.height = 0
        self.image = pygame.image.load(image).convert_alpha()
        self.rect = self.image.get_rect(topleft=(self.x, self.y))
        self.hitbox = pygame.Rect(((self.rect.x//2) + 100),(self.rect.y +50), (self.rect.width//2), (self.rect.height * 0.8))
        
        # Sensors for ground detection
        self.left_sensor = None
        self.right_sensor = None
        self.left_sensor_mask = None
        self.right_sensor_mask = None
        self.sensor_thickness = 2  # How thick the sensor line is
        self.sensor_extension = 2  # How many pixels below the hitbox
        self.init_sensors()
        
        # Collision information
        self.grounded = False
        self.last_ground_y = 0
        self.current_ground_tile = None
        self.slope_transition = False
        
        # Rest of the original initialization code...
        self.frame = 0
        self.image_index = 0
        self.Xvel = 0
        self.Yvel = 0
        self.direction = 0
        self.groundSpeed = 0
        self.jumped = False
        self.stopping = False
        self.stopSoundPlayed = False
        self.jumpSoundPlayed = False
        self.gameover = False
        self.animation_speed = 0.1
        self.acceleration = 0.2
        self.max_acceleration = 0.3
        self.deceleration = 0.5
        self.friction = 0.46875
        self.maxSpeed = 20
        self.gravityforce = 0.5
        self.angle = 0
        self.contact_mode = FLOOR
        self.boosting = False
        self.swinging = False
        self.launched = False
        self.launch_timer = 0
        self.launch_x_vel = 0
        self.launch_y_vel = 0
        self.homing_attack_active = False
        self.homing_target = None
        self.homing_speed = 15
        self.can_home = False
        self.swing_direction = 0
        self.swing_speed = 2
        self.current_monkey_bar = None
        self.swing_animation_speed = 0.15
        self.target_angle = 0
        self.stoppingSoundPlayed = False
        self.homing_image = homing_image
        
    def init_sensors(self):
        """Initialize the ground sensors as surfaces with masks"""
        # Create left sensor surface
        self.left_sensor = pygame.Surface((self.sensor_thickness, self.hitbox.height // 2 + self.sensor_extension), pygame.SRCALPHA)
        self.left_sensor.fill((0, 0, 255, 128))  # Semi-transparent blue for debugging
        
        # Create right sensor surface
        self.right_sensor = pygame.Surface((self.sensor_thickness, self.hitbox.height // 2 + self.sensor_extension), pygame.SRCALPHA)
        self.right_sensor.fill((0, 0, 255, 128))  # Semi-transparent blue for debugging
        
        # Create masks from the sensors
        self.left_sensor_mask = pygame.mask.from_surface(self.left_sensor)
        self.right_sensor_mask = pygame.mask.from_surface(self.right_sensor)

    def update_sensors(self):
        """Update the position of the sensors based on Sonic's hitbox"""
        # Position the left sensor at the bottom-left of the hitbox
        self.left_sensor_pos = (
            self.hitbox.left, 
            self.hitbox.centery
        )
        
        # Position the right sensor at the bottom-right of the hitbox
        self.right_sensor_pos = (
            self.hitbox.right - self.sensor_thickness, 
            self.hitbox.centery
        )
    
    def check_sensor_collision(self, tile):
        """Check if either sensor collides with a tile using mask collision"""
        # Skip if the tile doesn't have a mask
        if not hasattr(tile, 'mask') or tile.mask is None:
            return False, 0
        
        # Get the relative positions for mask overlap check
        left_offset = (
            self.left_sensor_pos[0] - tile.rect.x,
            self.left_sensor_pos[1] - tile.rect.y
        )
        
        right_offset = (
            self.right_sensor_pos[0] - tile.rect.x,
            self.right_sensor_pos[1] - tile.rect.y
        )
        
        # Check for overlap with both sensors
        left_overlap = tile.mask.overlap(self.left_sensor_mask, left_offset)
        right_overlap = tile.mask.overlap(self.right_sensor_mask, right_offset)
        
        # If there's an overlap, find the highest point for adjustment
        highest_overlap_y = None
        if left_overlap:
            highest_overlap_y = left_overlap[1] + tile.rect.y
        
        if right_overlap:
            right_overlap_y = right_overlap[1] + tile.rect.y
            if highest_overlap_y is None or right_overlap_y < highest_overlap_y:
                highest_overlap_y = right_overlap_y
        
        return (left_overlap is not None or right_overlap is not None), highest_overlap_y
    
    def adjust_position_to_ground(self, highest_point):
        """Adjust the character's position to rest on the ground"""
        if highest_point is not None:
            # Adjust Y position to rest exactly on the ground
            # Accounting for the sensor extension below the hitbox
            target_y = highest_point - (self.hitbox.height + self.sensor_extension)
            
            # Don't adjust if we're above the ground
            if self.hitbox.bottom <= highest_point:
                # Move smoothly to the target position when on a slope
                if abs(self.hitbox.bottom - highest_point) <= 5:  # Small step threshold
                    # For gentle slopes, adjust pixel by pixel
                    self.y += (target_y - self.y) * 0.3  # Smooth factor
                else:
                    # For larger steps, snap directly
                    self.y = target_y
                
                # Update rectangles
                self.rect.y = self.y
                self.hitbox.y = (self.rect.y + 50)
                
                # Set grounded state
                self.grounded = True
                self.jumped = False
                
                # Store last ground position for reference
                self.last_ground_y = self.y
            
            # Calculate angle based on left and right sensor heights
            # (simplified for now)
            self.angle = 0  # Will be calculated based on sensor data
        else:
            # Not grounded
            self.grounded = False

    def update_contact_mode(self):
        """Update character's contact mode based on the current angle."""
        if 316 <= self.angle <= 360 or 0 <= self.angle <= 44:
            self.contact_mode = FLOOR
        elif 45 <= self.angle <= 135:
            self.contact_mode = RIGHT_WALL
        elif 136 <= self.angle <= 224:
            self.contact_mode = CEILING
        elif 225 <= self.angle <= 315:
            self.contact_mode = LEFT_WALL
            
    def find_homing_target(self, enemies, springs):
        """Scans for the closest enemy or spring when character jumps."""
        homing_range = 200
        nearest_target = None
        min_distance = homing_range

        all_targets = list(enemies) + list(springs)
        for target in all_targets:
            distance = math.sqrt((target.rect.centerx - self.hitbox.centerx) ** 2 +
                                 (target.rect.centery - self.hitbox.centery) ** 2)
            if distance < min_distance:
                min_distance = distance
                nearest_target = target

        self.homing_target = nearest_target

    def start_homing_attack(self):
        """Begins the homing attack by calculating the vector towards the target."""
        if not self.homing_target:
            return

        target_x, target_y = self.homing_target.rect.center
        dx, dy = target_x - self.rect.centerx, target_y - self.rect.centery

        # **Create a normalized direction vector**
        direction = pygame.math.Vector2(dx, dy).normalize()

        # **Set movement velocity along this vector**
        self.homing_vector = direction * self.homing_speed
        self.homing_attack_active = True 
        
    def perform_homing_attack(self):
        """Moves character along the homing vector until the target is reached."""
        if not self.homing_attack_active or not self.homing_target:
            return

        # **Move character in the direction of the homing vector**
        self.Xvel = self.homing_vector.x
        self.Yvel = self.homing_vector.y

        # **Check if character reaches the target**
        target_x, target_y = self.homing_target.rect.center
        distance = math.sqrt((target_x - self.rect.centerx) ** 2 + 
                             (target_y - self.rect.centery) ** 2)

        if distance < 10:  # **Close enough to hit**
            if isinstance(self.homing_target, Enemy):
                self.Yvel = -8  # Bounce slightly upwards after hitting an enemy
            elif isinstance(self.homing_target, Spring):
                self.activate_spring(self.homing_target.angle, self.homing_target.force)

            self.homing_attack_active = False
            self.homing_target = None
            self.can_home = False  # Reset homing ability until another jump
            
    def reset_homing_target(self):
        """Cancels the homing attack if character lands or stops jumping."""
        self.homing_target = None
        self.homing_attack_active = False
        self.can_home = False
        
    def grab_monkey_bar(self, monkey_bar_tile):
        """Set character to swinging state and position on the monkey bar."""
        self.swinging = True
        self.current_monkey_bar = monkey_bar_tile
        self.x = monkey_bar_tile.rect.centerx  # Align to center of the bar
        self.hitbox.top = monkey_bar_tile.rect.bottom  # Adjust position to grab the bar
        self.Yvel = 0  # Prevent gravity from pulling character down
        self.Xvel = 0
        self.groundSpeed = 0
        self.frame = 0
        
    def release_monkey_bar(self, jump=False):
        """Release from monkey bar and optionally jump."""
        self.swinging = False
        self.current_monkey_bar = None
        # If jumping off
        if jump:
            self.Yvel = -5  # Jump upward
            self.jumped = True
            if not self.jumpSoundPlayed:
                pygame.mixer.Sound.play(jumpSound)
                self.jumpSoundPlayed = True
        else:
            # Just drop down
            self.Yvel += self.gravityforce # Increase gravity effect
            self.Yvel = min(self.Yvel, 15)  # Increase fall speed cap
            self.jumped = False
        
        # Reset animation
        self.frame = 0
        
    def activate_spring(self, angle, force):
        """Launches character based on spring angle with proper physics transition."""
        self.launched = True
        # Longer launch time for a more noticeable launch effect
        self.launch_timer = 30
        
        # Convert angle to velocity using trigonometry
        radians = math.radians(angle)
        self.Xvel = math.cos(radians) * force
        self.Yvel = -math.sin(radians) * force  # Negative Y goes UP
        
        # Store original velocities to maintain consistent speed during launch
        self.launch_x_vel = self.Xvel
        self.launch_y_vel = self.Yvel
        
        # Reset these states
        self.grounded = False
        self.jumped = True  # Set to true so jump sound doesn't play
        
        # Force immediate position update to get away from the spring
        self.x += self.Xvel
        self.y += self.Yvel
        
    def update(self):
        keys = pygame.key.get_pressed()
        # Check if joystick is available
        if joystick:
            left_stick_x = joystick.get_axis(0)  # Left stick horizontal movement
            left_stick_y = joystick.get_axis(1)  # Left stick vertical movement
            dpad_x = joystick.get_hat(0)[0]  # D-pad horizontal movement
            dpad_y = joystick.get_hat(0)[1]  # D-pad vertical movement
            boost_button = joystick.get_axis(5)  # R2 / RT
            jump_button = joystick.get_button(0)  # A / Cross
        else:
            left_stick_x = 0
            left_stick_y = 0
            dpad_x = 0
            dpad_y = 0
            boost_button = False
            jump_button = False

        # Handle launched state (from springs)
        if self.launched:
            # While launching, maintain constant velocity in the launch direction
            self.Xvel = self.launch_x_vel
            self.Yvel = self.launch_y_vel
            
            # Update position
            self.x += self.Xvel
            self.rect.x = self.x
            self.y += self.Yvel
            self.rect.y = self.y
            self.hitbox.centerx = self.rect.centerx
            self.hitbox.centery = self.rect.centery
            
            # Update animation
            self.update_animation()
            self.update_contact_mode()
            
            # Decrease timer
            self.launch_timer -= 1
            if self.launch_timer <= 0:
                # When launch ends, preserve velocity for smooth transition
                self.launched = False
                self.groundSpeed = self.Xvel  # Transfer X velocity to ground speed
                
            # Exit early to prevent any other code from running during launch
            return

        # **Cancel homing target if Sonic lands**
        if self.grounded or not self.jumped:
            self.reset_homing_target()

        if not keys[pygame.K_SPACE] and not jump_button:
            self.can_home = True

        # **Only trigger homing attack if SPACE is pressed and a target exists**
        if self.homing_target and keys[pygame.K_SPACE] and not self.homing_attack_active and self.can_home:
            self.start_homing_attack()
        
        # Special handling for swinging on monkey bars
        if self.swinging:
            # Handle left/right movement on monkey bars
            if keys[pygame.K_LEFT] or keys[pygame.K_a] or left_stick_x < -0.5 or dpad_x == -1:
                self.swing_direction = -1
                self.Xvel = -self.swing_speed
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d] or left_stick_x > 0.5 or dpad_x == 1:
                self.swing_direction = 1
                self.Xvel = self.swing_speed
            else:
                self.Xvel = 0
                self.swing_direction = 0
            
            # Dropping or jumping off the monkey bar
            if (keys[pygame.K_DOWN] or keys[pygame.K_s] or left_stick_y > 0.5 or dpad_y == -1):
                self.release_monkey_bar(jump=False)  # Just drop down
            elif (keys[pygame.K_SPACE] or jump_button):
                self.release_monkey_bar(jump=True)   # Jump off
            
            # No gravity when swinging
            self.Yvel = 0
        
        if self.homing_attack_active:
            self.perform_homing_attack()
            self.homing_attack_active = False  # Reset after one frame

        else:
            # Regular movement when not swinging
            boost_max_speed = 32
            normal_max_speed = 20
            
            # Boosting logic - works both on ground and in air
            if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] or boost_button > 0.5:
                self.current_max_speed = boost_max_speed
                if not self.boosting:
                    # Only set this when first starting the boost
                    if abs(self.groundSpeed) < boost_max_speed:
                        # Preserve direction but set to max boost speed
                        direction = 1 if self.groundSpeed >= 0 else -1
                        self.groundSpeed = boost_max_speed * direction
                    self.boosting = True
            else:
                # When not boosting, gradually return to normal max speed
                self.current_max_speed = normal_max_speed
                self.boosting = False

            # Jump logic (adjust for contact mode)
            if (keys[pygame.K_SPACE] or jump_button) and not self.jumped:
                self.Yvel = -15
                self.jumped = True
                self.grounded = False
                self.can_home = False
                if not self.jumpSoundPlayed:
                    pygame.mixer.Sound.play(jumpSound)
                    self.jumpSoundPlayed = True
                self.jumpSoundPlayed = False

            # Apply gravity if not on the ground
            if not self.grounded:
                # Apply gravity
                self.Yvel += self.gravityforce  # Increase gravity effect
                self.Yvel = min(self.Yvel, 15)  # Cap fall speed
                
                # Air control - full control for X direction
                if keys[pygame.K_LEFT] or keys[pygame.K_a] or left_stick_x < -0.5 or dpad_x == -1:
                    self.direction = 1
                    if self.groundSpeed > 0:
                        self.groundSpeed -= self.deceleration
                        if self.groundSpeed <= 0:
                            self.groundSpeed = -0.5
                    elif self.groundSpeed > -self.current_max_speed:
                        if self.acceleration < self.max_acceleration:
                            self.acceleration += 0.001
                        if self.acceleration > self.max_acceleration:
                            self.acceleration = self.max_acceleration
                        self.groundSpeed -= self.acceleration
                        if self.groundSpeed <= -self.current_max_speed:
                            self.groundSpeed = -self.current_max_speed
                
                elif keys[pygame.K_RIGHT] or keys[pygame.K_d] or left_stick_x > 0.5 or dpad_x == 1:
                    self.direction = -1
                    if self.groundSpeed < 0:
                        self.groundSpeed += self.deceleration
                        if self.groundSpeed >= 0:
                            self.groundSpeed = 0.5
                    elif self.groundSpeed < self.current_max_speed:
                        if self.acceleration < self.max_acceleration:
                            self.acceleration += 0.001
                        if self.acceleration > self.max_acceleration:
                            self.acceleration = self.max_acceleration
                        self.groundSpeed += self.acceleration
                        if self.groundSpeed >= self.current_max_speed:
                            self.groundSpeed = self.current_max_speed
                else:
                    # Apply air friction (less than ground friction)
                    air_friction = self.friction * 0.5
                    if abs(self.groundSpeed) > air_friction:
                        self.groundSpeed -= air_friction * (self.groundSpeed / abs(self.groundSpeed))
                    else:
                        self.groundSpeed = 0
                
                # Transfer ground speed to X velocity for air movement
                self.Xvel = self.groundSpeed
            else:
                # Ground movement
                if keys[pygame.K_LEFT] or keys[pygame.K_a] or left_stick_x < -0.5 or dpad_x == -1:
                    self.direction = 1
                    if self.groundSpeed > 0:
                        self.groundSpeed -= self.deceleration
                        self.stopping = True
                        if self.groundSpeed <= 0:
                            self.groundSpeed = -0.5
                            self.stopping = False
                    elif self.groundSpeed > -self.current_max_speed:
                        if self.acceleration < self.max_acceleration:
                            self.acceleration += 0.001
                        if self.acceleration > self.max_acceleration:
                            self.acceleration = self.max_acceleration
                        self.groundSpeed -= self.acceleration
                        if self.groundSpeed <= -self.current_max_speed:
                            self.groundSpeed = -self.current_max_speed
                
                elif keys[pygame.K_RIGHT] or keys[pygame.K_d] or left_stick_x > 0.5 or dpad_x == 1:
                    self.direction = -1
                    if self.groundSpeed < 0:
                        self.groundSpeed += self.deceleration
                        self.stopping = True
                        if self.groundSpeed >= 0:
                            self.groundSpeed = 0.5
                            self.stopping = False
                    elif self.groundSpeed < self.current_max_speed:
                        if self.acceleration < self.max_acceleration:
                            self.acceleration += 0.001
                        if self.acceleration > self.max_acceleration:
                            self.acceleration = self.max_acceleration
                        self.groundSpeed += self.acceleration
                        if self.groundSpeed >= self.current_max_speed:
                            self.groundSpeed = self.current_max_speed
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
                    
                # Create a movement vector based on ground speed
                movement_vector = pygame.math.Vector2(self.groundSpeed, 0)
                movement_vector = movement_vector.rotate(-self.angle)  # Rotate along the slope

                self.Xvel = movement_vector.x
                self.Yvel = movement_vector.y


        # Update Sonic's position
        self.x += self.Xvel
        self.rect.x = self.x
        self.y += self.Yvel
        self.rect.y = self.y
        self.hitbox.x = ((self.rect.x//2) + 100)
        self.hitbox.y = (self.rect.y + 50)
        self.hitbox.center = self.rect.center
        self.hitbox.bottom = self.rect.bottom

        # Update animation
        self.update_animation()
        if not self.swinging:  # Only update contact mode when not swinging
            self.update_contact_mode()

    def update_animation(self):
        # Calculate animation speed based on Sonic's state
        if self.swinging:
            # Use a constant animation speed for swinging
            self.animation_speed = self.swing_animation_speed
        else:
            # Regular animation speed based on ground speed
            self.animation_speed = min(0.1 + abs(self.groundSpeed) * 0.01, 0.5)

        # Update animation frame based on animation speed
        self.frame += self.animation_speed
        
        # Handle swinging animation separately
        if self.swinging:
            self.image_index = int(self.frame) % len(self.swinging_images)
            if self.swing_direction >= 0:  # Right or idle
                self.image = self.swinging_images[self.image_index]
            else:  # Left
                self.image = pygame.transform.flip(self.swinging_images[self.image_index], True, False)
            return

        # Regular animations when not swinging
        self.image_index = int(self.frame) % len(self.run_images)

        # Update Sonic's image
        if self.groundSpeed > 0 and not self.jumped and not self.stopping:
            if self.groundSpeed > 30:
                self.image = self.boosting_images[self.image_index]
            elif self.groundSpeed > 15:
                self.image = self.sprint_images[self.image_index]
            elif self.groundSpeed < 15:
                self.image = self.run_images[self.image_index]
        elif self.groundSpeed < 0 and not self.jumped and not self.stopping:
            if self.groundSpeed < -30:
                self.image = pygame.transform.flip(self.boosting_images[self.image_index], True, False)
            elif self.groundSpeed < -15:
                self.image = pygame.transform.flip(self.sprint_images[self.image_index], True, False)
            elif self.groundSpeed > -15:
                self.image = pygame.transform.flip(self.run_images[self.image_index], True, False)
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
        
        # Only rotate if not swinging
        if not self.swinging:
            self.image = pygame.transform.rotate(self.image, self.angle)

class Sonic(Character):
    def __init__(self, x, y):
        super().__init__(x, y, image=os.path.join("assets", "sprites", "Sonic", "SonicIdle1.png"))
        self.width = 40 
        self.height = 40
        self.run_images = [pygame.image.load(os.path.join("assets", "sprites", "Sonic", f"SonicRun{i}.png")).convert_alpha() for i in range(1, 9)]
        self.sprint_images = [pygame.image.load(os.path.join("assets", "sprites", "Sonic", f"SonicSprint{i}.png")).convert_alpha() for i in range(1, 9)]
        self.boosting_images = [pygame.image.load(os.path.join("assets", "sprites", "Sonic", f"SonicBoost{i}.png")).convert_alpha() for i in range(1, 9)]
        self.idle_images = [pygame.image.load(os.path.join("assets", "sprites", "Sonic", f"SonicIdle{i}.png")).convert_alpha() for i in range(1, 6)]
        self.jump_images = [pygame.image.load(os.path.join("assets", "sprites", "Sonic", f"SonicJump{i}.png")).convert_alpha() for i in range(1, 5)]
        self.stopping_images = [pygame.image.load(os.path.join("assets", "sprites", "Sonic", f"SonicStopping{i}.png")).convert_alpha() for i in range(1, 3)]
        self.boost_overlay_images = [pygame.image.load(os.path.join("assets", "sprites", "Sonic", f"boost{i}.png")).convert_alpha() for i in range(1, 4)]
        # Add swinging animation frames
        self.swinging_images = [pygame.image.load(os.path.join("assets", "sprites", "Sonic", f"swing{i}.png")).convert_alpha() for i in range(1, 12)]
        
    def update(self):
        super().update()

    def update_animation(self):
        super().update_animation()

class Tails(Character):
    def __init__(self, x, y):
        super().__init__(x, y, image=os.path.join("assets", "sprites", "Tails", "tailsIdle1.png"))
        self.width = 30
        self.height = 30
        self.run_images = [pygame.image.load(os.path.join("assets", "sprites", "Tails", f"tailsRun{i}.png")).convert_alpha() for i in range(1, 10)]
        self.sprint_images = [pygame.image.load(os.path.join("assets", "sprites", "Tails", f"tailsSprint{i}.png")).convert_alpha() for i in range(1, 10)]
        self.idle_images = [pygame.image.load(os.path.join("assets", "sprites", "Tails", f"tailsIdle{i}.png")).convert_alpha() for i in range(1, 16)]
        # Load jump images and resize them to 50%
        self.jump_images = []
        for i in range(1, 9):
            original = pygame.image.load(os.path.join("assets", "sprites", "Tails", f"tailsJump{i}.png")).convert_alpha()
            width = original.get_width() // 1.5
            height = original.get_height() // 1.5
            self.jump_images.append(pygame.transform.scale(original, (width, height)))
        self.stopping_images = [pygame.image.load(os.path.join("assets", "sprites", "Tails", f"tailsStop{i}.png")).convert_alpha() for i in range(1, 5)]

    def update(self):
        super().update()

    def update_animation(self):
        # Calculate animation speed based on character's state
        if self.swinging:
            # Use a constant animation speed for swinging
            self.animation_speed = self.swing_animation_speed
        else:
            # Regular animation speed based on ground speed
            self.animation_speed = min(0.1 + abs(self.groundSpeed) * 0.01, 0.5)

        # Update animation frame based on animation speed
        self.frame += self.animation_speed
        
        if self.groundSpeed > 0 and not self.jumped and not self.stopping:
            # Calculate image index for running animations
            if self.groundSpeed > 15:
                self.image_index = int(self.frame) % len(self.sprint_images)
                self.image = pygame.transform.flip(self.sprint_images[self.image_index], True, False)
            else:
                self.image_index = int(self.frame) % len(self.run_images)
                self.image = pygame.transform.flip(self.run_images[self.image_index], True, False)
                
        elif self.groundSpeed < 0 and not self.jumped and not self.stopping:
            if self.groundSpeed < -15:
                self.image_index = int(self.frame) % len(self.sprint_images)
                self.image = self.sprint_images[self.image_index]
            else:
                self.image_index = int(self.frame) % len(self.run_images)
                self.image = self.run_images[self.image_index]
                
        elif self.groundSpeed == 0 and not self.jumped and not self.stopping:
            self.image_index = int(self.frame) % len(self.idle_images)
            if self.direction == -1:
                self.image = pygame.transform.flip(self.idle_images[self.image_index], True, False)
            elif self.direction == 1:
                self.image = self.idle_images[self.image_index]

        if self.jumped:
            self.image_index = int(self.frame) % len(self.jump_images)
            if self.groundSpeed > 0:
                self.image = pygame.transform.flip(self.jump_images[self.image_index], True, False)
            elif self.groundSpeed < 0:
                self.image = self.jump_images[self.image_index]
            else:
                if self.direction == -1:
                    self.image = pygame.transform.flip(self.jump_images[self.image_index], True, False)
                elif self.direction == 1:
                    self.image = self.jump_images[self.image_index]

        if self.stopping and not self.jumped:
            self.image_index = int(self.frame) % len(self.stopping_images)
            if self.direction == -1:
                self.image = self.stopping_images[self.image_index]
            elif self.direction == 1:
                self.image = pygame.transform.flip(self.stopping_images[self.image_index], True, False)
        
        # Only rotate if not swinging
        if not self.swinging:
            self.image = pygame.transform.rotate(self.image, self.angle)
            self.rect = self.image.get_rect(center=self.rect.center)  # Maintain center position