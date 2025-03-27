import pygame, math, random, numpy
from constants import *
from objects import *
from utils import joystick, Mask

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

clock = pygame.time.Clock()
pygame.mixer.init()

class Character(pygame.sprite.Sprite):
    """Base class for all game characters, incorporating a detailed hitbox and multiple collision sensors 
    for precise, pixel-perfect collision handling (including angled movement)."""
    def __init__(self, x, y, image):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        
        # Load sprite image with transparency
        self.image = pygame.image.load(image).convert_alpha()
        self.rect = self.image.get_rect(topleft=(self.x, self.y))
        
        # Refined hitbox: this hitbox is configured for more accurate collision detection.
        # Adjust the offsets as necessary to match your sprite and level design.
        self.hitbox = pygame.Rect(
            ((self.rect.x // 2) + 100),   # X offset (may be adjusted)
            (self.rect.y + 50),           # Y offset (may be adjusted)
            (self.rect.width // 2),       # Width
            int(self.rect.height * 0.8)    # Height
        )
        
        # --- Create Collision Sensors ---
        # Define sensor rectangles based on the hitbox dimensions. Each sensor returns a sensor list:
        # [mask, shifted_rect, original_rect] as per the Mask class design.
        
        # Left sensor: placed along the left side of the hitbox.
        left_sensor_rect = (
            self.hitbox.x,  # Far left of hitbox
            self.hitbox.y,  
            2,  # Thin 2-pixel wide sensor
            self.hitbox.height
        )
        right_sensor_rect = (
            self.hitbox.right - 2,  # Far right of hitbox, 2 pixels wide
            self.hitbox.y,  
            2,  
            self.hitbox.height
        )
        top_sensor_rect = (
            self.hitbox.x,
            self.hitbox.y,
            self.hitbox.width,
            2  # Thin 2-pixel high sensor
        )
        bottom_sensor_rect = (
            self.hitbox.x,
            self.hitbox.bottom - 2,  # Bottom of hitbox, 2 pixels high
            self.hitbox.width,
            2
        )
        
        # Create sensors using Mask class
        # Center point is the middle of the sensor's width/height
        self.left_sensor = Mask.newSensor(
            left_sensor_rect, 
            (1, self.hitbox.height // 2)
        )
        self.right_sensor = Mask.newSensor(
            right_sensor_rect, 
            (1, self.hitbox.height // 2)
        )
        self.top_sensor = Mask.newSensor(
            top_sensor_rect,
            (self.hitbox.width // 2, 1)
        )
        self.bottom_sensor = Mask.newSensor(
            bottom_sensor_rect,
            (self.hitbox.width // 2, 1)
        )
        
        # --- Collision State Attributes ---
        # These flags and properties let you handle collision outcomes based on sensor data.
        self.grounded = False           # Is the player on the ground?
        self.left_grounded = False      # Is the player's left side in contact?
        self.right_grounded = False     # Is the player's right side in contact?
        self.last_ground_y = 0          # Previous ground contact Y, used to calculate slopes.
        self.current_ground_tile = None # Stores the current tile (from Tiled) the player is on.
        self.slope_transition = False   # Indicates if the character is transitioning between slopes.
        
        # --- Movement and Physics Properties (Sonic-style) ---
        self.frame = 0
        self.image_index = 0
        self.Xvel = 0              # Horizontal velocity
        self.Yvel = 0              # Vertical velocity
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
        
        # --- Angular Collision Handling ---
        # Angle (in degrees or arbitrary units) represents the slope of the ground.
        self.angle = 0
        # contact_mode can be FLOOR, CEILING, LEFT, or RIGHT.
        # This value, used with sensor rotation methods, defines which side is in contact.
        self.contact_mode = FLOOR
        
        # --- Advanced Movement States ---
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
        
        # Homing image – used when performing a homing attack (assumed to be loaded elsewhere)
        self.homing_image = homing_image

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

    def update_sensors(self):
        """Create precise bottom-edge sensors for ground detection"""
        # Very short, precise sensors
        sensor_thickness = 1
        sensor_height = 2  # Just enough to detect the ground
        
        # Position sensors at the bottom corners of the hitbox
        left_sensor_rect = (
            self.hitbox.left,
            self.hitbox.bottom - sensor_height,
            sensor_thickness,
            sensor_height
        )
        
        right_sensor_rect = (
            self.hitbox.right - sensor_thickness,
            self.hitbox.bottom - sensor_height,
            sensor_thickness,
            sensor_height
        )
        
        # Create sensors with precise positioning
        self.left_sensor = Mask.newSensor(
            left_sensor_rect, 
            (0, sensor_height - 1)  # Center point at the very bottom
        )
        
        self.right_sensor = Mask.newSensor(
            right_sensor_rect, 
            (0, sensor_height - 1)  # Center point at the very bottom
        )

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
        """Calculate velocity and animation state but don't update position"""
        keys = pygame.key.get_pressed()
        # Controller input handling
        if joystick:
            left_stick_x = joystick.get_axis(0)
            left_stick_y = joystick.get_axis(1)
            dpad_x = joystick.get_hat(0)[0]
            dpad_y = joystick.get_hat(0)[1]
            boost_button = joystick.get_axis(5)
            jump_button = joystick.get_button(0)
        else:
            left_stick_x = left_stick_y = dpad_x = dpad_y = 0
            boost_button = jump_button = False

        # Handle launched state (from springs)
        if self.launched:
            self.Xvel = self.launch_x_vel
            self.Yvel = self.launch_y_vel
            
            # Just update animation and decrease timer
            self.update_animation()
            self.update_contact_mode()
            
            self.launch_timer -= 1
            if self.launch_timer <= 0:
                self.launched = False
                self.groundSpeed = self.Xvel
            return

        # Homing attack logic
        if self.grounded or not self.jumped:
            self.reset_homing_target()

        if not keys[pygame.K_SPACE] and not jump_button:
            self.can_home = True

        if self.homing_target and keys[pygame.K_SPACE] and not self.homing_attack_active and self.can_home:
            self.start_homing_attack()
        
        # Monkey bar swinging
        if self.swinging:
            # Handle movement on bars
            if keys[pygame.K_LEFT] or keys[pygame.K_a] or left_stick_x < -0.5 or dpad_x == -1:
                self.swing_direction = -1
                self.Xvel = -self.swing_speed
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d] or left_stick_x > 0.5 or dpad_x == 1:
                self.swing_direction = 1
                self.Xvel = self.swing_speed
            else:
                self.Xvel = 0
                self.swing_direction = 0
            
            # Dropping or jumping off
            if (keys[pygame.K_DOWN] or keys[pygame.K_s] or left_stick_y > 0.5 or dpad_y == -1):
                self.release_monkey_bar(jump=False)
            elif (keys[pygame.K_SPACE] or jump_button):
                self.release_monkey_bar(jump=True)
            
            self.Yvel = 0
            
        elif self.homing_attack_active:
            self.perform_homing_attack()
            self.homing_attack_active = False
        else:
            # Regular movement
            boost_max_speed = 32
            normal_max_speed = 20
            
            # Boosting logic
            if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] or boost_button > 0.5:
                self.current_max_speed = boost_max_speed
                if not self.boosting:
                    if abs(self.groundSpeed) < boost_max_speed:
                        direction = 1 if self.groundSpeed >= 0 else -1
                        self.groundSpeed = boost_max_speed * direction
                    self.boosting = True
            else:
                self.current_max_speed = normal_max_speed
                self.boosting = False

            # Jump logic
            if (keys[pygame.K_SPACE] or jump_button) and not self.jumped:
                self.Yvel = -15
                self.jumped = True
                self.grounded = False
                self.can_home = False
                if not self.jumpSoundPlayed:
                    pygame.mixer.Sound.play(jumpSound)
                    self.jumpSoundPlayed = True
                self.jumpSoundPlayed = False

            # Apply gravity when not on ground
            if not self.grounded:
                # Apply gravity
                self.Yvel += self.gravityforce 
                
                # Air control
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
                    # Air friction
                    air_friction = self.friction * 0.5
                    if abs(self.groundSpeed) > air_friction:
                        self.groundSpeed -= air_friction * (self.groundSpeed / abs(self.groundSpeed))
                    else:
                        self.groundSpeed = 0
                
                # Transfer ground speed to X velocity
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
                
                # Handle stopping sound
                if self.stopping:
                    if not self.stoppingSoundPlayed:
                        pygame.mixer.Sound.play(stoppingSound)
                        self.stoppingSoundPlayed = True
                else:
                    self.stoppingSoundPlayed = False
                
                # Handle movement on angled ground
                if self.angle != 0:
                    # Apply slope influence on speed
                    angle_rad = math.radians(self.angle)
                    slope_factor = math.sin(angle_rad) * 0.2
                    
                    # Create a movement vector based on ground speed and angle
                    movement_vector = pygame.math.Vector2(self.groundSpeed, 0)
                    movement_vector = movement_vector.rotate(-self.angle)
                    
                    self.Xvel = movement_vector.x
                    self.Yvel = movement_vector.y
                else:
                    # Flat ground
                    self.Xvel = self.groundSpeed
                    self.Yvel = 0

        # IMPORTANT: Don't update position here! Only update animation
        self.update_animation()
        self.update_sensors()
        if not self.swinging:
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