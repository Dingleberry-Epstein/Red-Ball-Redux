import pygame, os, math, random, pymunk

from constants import *

class GameObject(pygame.sprite.Sprite):
    """Base class for all game objects"""
    def __init__(self, x, y):
        super().__init__()
        self._x = int(x)
        self._y = int(y)
        self._rect = None
        self._image = None
        self._mask = None
    
    @property
    def x(self):
        """Get the x coordinate"""
        return self._x
    
    @x.setter
    def x(self, value):
        """Set the x coordinate"""
        self._x = int(value)
        if self._rect:
            self._rect.x = self._x
    
    @property
    def y(self):
        """Get the y coordinate"""
        return self._y
    
    @y.setter
    def y(self, value):
        """Set the y coordinate"""
        self._y = int(value)
        if self._rect:
            self._rect.y = self._y
    
    @property
    def rect(self):
        """Get the rectangle"""
        return self._rect
    
    @rect.setter
    def rect(self, value):
        """Set the rectangle"""
        self._rect = value
    
    @property
    def image(self):
        """Get the image"""
        return self._image
    
    @image.setter
    def image(self, value):
        """Set the image"""
        self._image = value
        # Update mask when image changes
        if self._image and hasattr(self, '_update_mask_on_image_change') and self._update_mask_on_image_change:
            self._mask = pygame.mask.from_surface(self._image)
    
    @property
    def mask(self):
        """Get the mask"""
        return self._mask
    
    @mask.setter
    def mask(self, value):
        """Set the mask"""
        self._mask = value
    
    def update(self):
        """Update method to be overridden by child classes"""
        pass

class Tile(GameObject):
    """Tile class for level building"""
    def __init__(self, image, position, angle=0, collideable=True):
        super().__init__(position[0], position[1])
        self._angle = angle  # Store the tile's angle
        self._collideable = collideable  # Whether the tile is collideable
        self._update_mask_on_image_change = collideable
        
        # Set image and update rect
        self.image = image.convert_alpha()  # This will call the setter
        self.rect = self.image.get_rect(topleft=position)  # This will call the setter

        # Only create a mask if the tile is collideable
        if self._collideable:
            self._mask = pygame.mask.from_surface(self.image)
        else:
            self._mask = None  # No collision for non-collideable tiles
    
    @property
    def angle(self):
        """Get the tile's angle"""
        return self._angle
    
    @property
    def collideable(self):
        """Get whether the tile is collideable"""
        return self._collideable

class AnimatedGameObject(GameObject):
    """Base class for animated game objects"""
    def __init__(self, x, y):
        super().__init__(x, y)
        self._frame = 0
        self._animation_speed = 0.1
        self._images = []
        self._current_frame = 0
    
    @property
    def frame(self):
        return self._frame
    
    @frame.setter
    def frame(self, value):
        self._frame = value
    
    @property
    def animation_speed(self):
        return self._animation_speed
    
    @animation_speed.setter
    def animation_speed(self, value):
        self._animation_speed = value
    
    @property
    def images(self):
        return self._images
    
    @images.setter
    def images(self, value):
        self._images = value
    
    @property
    def current_frame(self):
        return self._current_frame
    
    @current_frame.setter
    def current_frame(self, value):
        self._current_frame = value
    
    def update_animation(self):
        """Update animation frame based on animation speed"""
        self._frame += self._animation_speed
        self._current_frame = int(self._frame) % len(self._images)
        self.image = self._images[self._current_frame]

class Rocket(GameObject):
    """Tracking rocket that homes in on Cubodeez"""
    def __init__(self, x, y, target):
        super().__init__(x, y)
        # Load rocket image
        try:
            self._original_image = pygame.image.load(os.path.join('assets', "sprites", "gun", 'rocket.png')).convert_alpha()
            self.image = self._original_image.copy()
        except:
            # Fallback if image can't be loaded
            self._create_fallback_image()
            print("Could not load rocket image")
            
        self.rect = self.image.get_rect(center=(x, y))
        self._target = target
        
        # Physics properties
        self._position = pygame.math.Vector2(x, y)
        self._velocity = pygame.math.Vector2(0, 0)
        self._acceleration = pygame.math.Vector2(0, 0)
        self._max_speed = 24
        self._max_force = 0.5
        
        # Tracking characteristics
        self._seek_weight = 1.0
        self._hit_distance = 50  # Distance at which the rocket explodes on the target
        
        # Load sound effect
        self._load_sound()
    
    def _create_fallback_image(self):
        """Create a fallback image if the rocket image can't be loaded"""
        self._original_image = pygame.Surface((30, 10), pygame.SRCALPHA)
        pygame.draw.rect(self._original_image, (200, 100, 50), (0, 0, 30, 10))
        pygame.draw.polygon(self._original_image, (200, 50, 0), [(30, 0), (40, 5), (30, 10)])
        self.image = self._original_image.copy()
    
    def _load_sound(self):
        """Load the rocket sound effect"""
        try:
            self._rocket_sound = pygame.mixer.Sound(os.path.join('assets', 'sounds', 'rocket_sound.mp3'))
            self._rocket_sound.set_volume(0.4)
            self._rocket_sound.play()  # Loop the sound until explosion
        except:
            self._rocket_sound = None
            print("Could not load rocket sound")
    
    @property
    def position(self):
        return self._position
    
    @position.setter
    def position(self, value):
        self._position = value
    
    @property
    def velocity(self):
        return self._velocity
    
    @velocity.setter
    def velocity(self, value):
        self._velocity = value
    
    @property
    def acceleration(self):
        return self._acceleration
    
    @acceleration.setter
    def acceleration(self, value):
        self._acceleration = value
    
    def update(self):
        # Apply steering behaviors for tracking
        if self._target:
            # Get desired direction to target
            target_pos = pygame.math.Vector2(self._target.rect.center)
            desired = target_pos - self._position
            
            # Print debugging info about distance to target
            distance = desired.length()
            if random.random() < 0.01:  # Only print occasionally to avoid spam
                print(f"Rocket distance to target: {distance:.1f}, hit distance: {self._hit_distance}")
            
            # If we're close enough to the target, explode!
            if distance < self._hit_distance:
                print("Rocket hit target!")
                return True  # Signal to create explosion and delete rocket
            
            # If we're close enough to the target, explode!
            if desired.length() < self._hit_distance:
                return True  # Signal to create explosion and delete rocket
            
            # Continue tracking
            if desired.length() > 0:
                desired.normalize_ip()
                desired *= self._max_speed
                
                # Calculate steering force
                steer = desired - self._velocity
                if steer.length() > self._max_force:
                    steer.scale_to_length(self._max_force)
                
                # Apply force with weight
                steer *= self._seek_weight
                self._acceleration += steer
        
        # Update physics
        self._velocity += self._acceleration
        if self._velocity.length() > self._max_speed:
            self._velocity.scale_to_length(self._max_speed)
        
        self._position += self._velocity
        self._acceleration *= 0
        
        # Update rectangle position
        self.rect.centerx = int(self._position.x)
        self.rect.centery = int(self._position.y)
        
        # Update rocket rotation to face movement direction
        if self._velocity.length() > 0:
            angle = math.degrees(math.atan2(self._velocity.y, self._velocity.x))
            self.image = pygame.transform.rotate(self._original_image, -angle)
            self.rect = self.image.get_rect(center=self.rect.center)
        
        return False  # Rocket continues flying
    
    def kill(self):
        # Stop sound when rocket is destroyed
        if hasattr(self, '_rocket_sound') and self._rocket_sound:
            self._rocket_sound.stop()
        Explosion(self.rect.centerx, self.rect.centery)  # Create explosion at the rocket's position
        super().kill()

class RocketLauncher(GameObject):
    """Class for the rocket launcher that targets Cubodeez"""
    def __init__(self, x, y, target, explosion_group=None):
        super().__init__(x, y)
        try:
            self.image = pygame.image.load(os.path.join('assets', "sprites", "gun", 'rocket launcher.png')).convert_alpha()
        except:
            # Fallback image if file not found
            self._create_fallback_image()
            print("Could not load rocket launcher image")

        self._key_was_pressed_last_frame = False  # Track previous frame's key state
        self._firing_in_progress = False  # Flag to prevent multiple firings in a single press
        self._firing_delay = 0  # Short delay to prevent double-firing
        self._uses_left = 2
        self.rect = self.image.get_rect(center=(x, y))
        self._target = target  # Reference to Cubodeez
        self._explosion_group = explosion_group
        self._rockets = pygame.sprite.Group()  # Group to track active rockets
        
        # Timing parameters
        self._last_launch_time = 0
        self._launch_delay = 2000  # milliseconds
        self._active = False
        
        # Player interaction parameters
        self._interaction_range = 150  # Distance in pixels for player to interact
        self._show_prompt = False
        self._e_key_pressed = False  # Track E key state to detect when first pressed
        
        # UI elements
        self._setup_ui()
        
        # Load launch sound
        self._load_sound()
        
        # Add physics body
        self._setup_physics(target)
    
    def _create_fallback_image(self):
        """Create a fallback image if the rocket launcher image can't be loaded"""
        self.image = pygame.Surface((40, 60), pygame.SRCALPHA)
        pygame.draw.rect(self.image, (80, 80, 80), (0, 0, 40, 60))
        pygame.draw.rect(self.image, (120, 120, 120), (10, 0, 20, 20))
    
    def _setup_ui(self):
        """Set up UI elements for the rocket launcher"""
        # Load E prompt font and create text
        self._font = pygame.font.Font(None, 36)  # Default font if custom font fails
        try:
            self._font = pygame.font.Font(daFont, 18)
        except:
            print("Could not load custom font, using default")
        
        self._prompt_text = self._font.render("E", True, (255, 255, 255))
        self._prompt_bg = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(self._prompt_bg, (0, 0, 0, 180), (20, 20), 20)
    
    def _load_sound(self):
        """Load the rocket launch sound"""
        try:
            self._launch_sound = pygame.mixer.Sound(os.path.join('assets', 'sounds', 'rocket.mp3'))
            self._launch_sound.set_volume(0.5)
        except:
            self._launch_sound = None
            print("Could not load rocket launch sound")
    
    def _setup_physics(self, target):
        """Set up physics body and shape for the rocket launcher"""
        self.body = pymunk.Body(body_type=pymunk.Body.STATIC)
        self.body.position = (self.x, self.y)
        self.shape = pymunk.Circle(self.body, 20)  # Adjust radius as needed
        self.shape.collision_type = target.physics.collision_types["switch"]
        self.shape.launcher = self  # Reference to the launcher object
        target.physics.space.add(self.body, self.shape)
    
    @property
    def show_prompt(self):
        return self._show_prompt
    
    @show_prompt.setter
    def show_prompt(self, value):
        self._show_prompt = value
    
    @property
    def rockets(self):
        return self._rockets
    
    @property
    def uses_left(self):
        return self._uses_left
    
    def check_player_proximity(self, player):
        """Check if player is close enough to interact with launcher using world coordinates"""
        if not player or not hasattr(player, 'rect'):
            self._show_prompt = False
            return False
            
        # Calculate distance between player and launcher in world coordinates
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        distance = (dx**2 + dy**2)**0.5
        
        # Update prompt visibility based on distance
        in_range = distance <= self._interaction_range
        self._show_prompt = in_range
        return in_range
    
    def handle_interaction(self, keys, player):
        """Handle player interaction with the launcher"""
        # Check if E was just pressed (not held)
        e_key_just_pressed = keys[pygame.K_e] and not self._e_key_pressed
        self._e_key_pressed = keys[pygame.K_e]  # Update key state
        
        if not self._show_prompt or not e_key_just_pressed:
            return None
            
        print("E key pressed while in range of rocket launcher")
        
        # Check if there's a valid target
        if not self._target or not hasattr(self._target, 'rect'):
            print("No valid boss target")
            return None
            
        # Activate the launcher if player presses E while in range
        return self.activate()
    
    def activate(self):
        """Activate the launcher to fire a rocket if there's a valid target"""
        if not self._target or not hasattr(self._target, 'vulnerable'):
            print("Cannot activate: no valid target or boss state")
            return None

        # Check if the boss is in cooldown (vulnerable)
        if not self._target.vulnerable:
            print("Cannot activate: boss is not in cooldown")
            return None

        # Check if the launcher has uses left
        if self._uses_left <= 0:
            print("Cannot activate: launcher has no uses left")
            return None

        self._active = True
        self._uses_left -= 1  # Decrement the uses counter
        print(f"Launcher activated, uses left: {self._uses_left}")

        # Force launch immediately when activated
        current_time = pygame.time.get_ticks()
        self._last_launch_time = current_time - self._launch_delay - 100  # Ensure cooldown is over
        result = self.launch_rocket()
        print(f"Rocket launcher activated, rocket created: {result is not None}")
        return result
    
    def launch_rocket(self):
        """Launch a rocket if conditions are met"""
        current_time = pygame.time.get_ticks()
        if not self._active or current_time - self._last_launch_time <= self._launch_delay:
            print(f"Cannot launch: active={self._active}, time since last launch={current_time - self._last_launch_time}ms")
            return None
            
        if not self._target or not hasattr(self._target, 'rect'):
            print("Cannot launch: no valid target")
            return None
            
        # Update launch timer
        self._last_launch_time = current_time
        
        # Create and return a new rocket
        try:
            # Create the rocket with proper parameters
            rocket = Rocket(
                self.rect.centerx,  # Start from the center of the launcher
                self.rect.top,      # Start from the top of the launcher
                self._target           # Target is the boss
            )
            
            # Add to the rockets group
            self._rockets.add(rocket)
            print(f"Rocket created and added to group. Target: {self._target.rect.center}")
            
            # Play launch sound
            if self._launch_sound:
                self._launch_sound.play()
                
            # Create a small launch explosion effect
            if self._explosion_group:
                # Make sure Explosion class is available
                launch_explosion = Explosion(self.rect.centerx, self.rect.top - 10)
                self._explosion_group.add(launch_explosion)
                print("Launch explosion created")
                
            return rocket
        except Exception as e:
            print(f"Error creating rocket: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def update(self, dt=1/60, player=None, keys=None):
        """Update rockets, check for hits, and handle player interaction"""
        current_time = pygame.time.get_ticks()
        
        # Check player proximity to show/hide the E prompt
        in_range = False
        if player:
            in_range = self.check_player_proximity(player)
            
        # Handle player interaction if keys are provided
        if keys and in_range:
            self.handle_interaction(keys, player)
        
        # Update all rockets
        for rocket in list(self._rockets):
            # Update the rocket and check if it hit the target
            hit = False
            try:
                if hasattr(rocket, 'update'):
                    hit = rocket.update()
                else:
                    print("Rocket has no update method")
                    hit = True  # Remove invalid rockets
            except Exception as e:
                print(f"Error updating rocket: {e}")
                hit = True  # Remove problematic rockets
                
            if hit:
                # Rocket hit the target, create explosion
                try:
                    if self._explosion_group:
                        explosion = Explosion(rocket.rect.centerx, rocket.rect.centery)
                        self._explosion_group.add(explosion)
                        print(f"Hit explosion created at {rocket.rect.center}")
                    
                    # Damage the boss if it's vulnerable
                    if self._target and hasattr(self._target, 'vulnerable') and self._target.vulnerable:
                        if hasattr(self._target, 'take_damage') and callable(self._target.take_damage):
                            self._target.take_damage(10)  # Higher damage than regular switches
                            print(f"Dealt 10 damage to boss")
                except Exception as e:
                    print(f"Error handling rocket hit: {e}")
                
                # Remove the rocket
                try:
                    rocket.kill()
                    if rocket in self._rockets:
                        self._rockets.remove(rocket)
                    print("Rocket removed")
                except Exception as e:
                    print(f"Error removing rocket: {e}")
                
        # Reset active state after firing
        if self._active and len(self._rockets) == 0 and current_time - self._last_launch_time > self._launch_delay:
            self._active = False
            print("Launcher reset to inactive state")
    
    def draw(self, surface, camera):
        """Draw the launcher and the E prompt with camera offsets applied"""
        # Get the camera-adjusted position for drawing
        camera_rect = camera.apply(self)
        
        # Draw the launcher itself at the camera-adjusted position
        surface.blit(self.image, camera_rect)
        
        # Draw the E prompt if player is in range, also with camera offset
        if self._show_prompt:
            # Position the prompt above the launcher (in screen coordinates)
            prompt_x = camera_rect.centerx - 20
            prompt_y = camera_rect.top - 50
            
            # Draw prompt background
            surface.blit(self._prompt_bg, (prompt_x, prompt_y))
            
            # Draw prompt text (centered on background)
            text_rect = self._prompt_text.get_rect(center=(prompt_x + 20, prompt_y + 20))
            surface.blit(self._prompt_text, text_rect)

class Explosion(GameObject):
    """Explosion animation class"""
    def __init__(self, x, y):
        super().__init__(x, y)
        # Load explosion frames
        self._explosion_frames = []
        self._load_frames()
        self.rect = self.image.get_rect(center=(x, y))
        self._frame_index = 0
        self._animation_speed = 0.2
        self._animation_timer = 0
        self._load_sound()
    
    def _load_frames(self):
        """Load explosion animation frames"""
        try:
            for i in range(1, 8):  # Assuming 7 frames for explosion animation
                frame = pygame.image.load(os.path.join('assets', 'sprites', 'kaboom', f'frame{i}.png')).convert_alpha()
                frame = pygame.transform.scale(frame, (frame.get_width() * 2, frame.get_height() * 2))
                self._explosion_frames.append(frame)
            self.image = self._explosion_frames[0]
        except Exception as e:
            # Fallback if images can't be loaded
            self._create_fallback_image()
            print(f"Could not load explosion frames: {e}")
    
    def _create_fallback_image(self):
        """Create a fallback image if explosion frames can't be loaded"""
        self.image = pygame.Surface((100, 100), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (255, 100, 0), (50, 50), 50)
        self._explosion_frames = [self.image] * 7
    
    def _load_sound(self):
        """Load explosion sound effect"""
        try:
            self._explosion_sound = pygame.mixer.Sound(os.path.join('assets', 'sounds', 'explosion.mp3'))
            self._explosion_sound.set_volume(0.7)
            self._explosion_sound.play()
        except:
            self._explosion_sound = None
            print("Could not load explosion sound")
    
    @property
    def explosion_frames(self):
        return self._explosion_frames
    
    @property
    def frame_index(self):
        return self._frame_index
    
    @frame_index.setter
    def frame_index(self, value):
        self._frame_index = value
    
    @property
    def explosion_sound(self):
        return self._explosion_sound
    
    def update(self, dt=1/60):
        # Update animation timer
        self._animation_timer += dt
        
        # Advance to next frame when timer exceeds animation speed
        if self._animation_timer >= self._animation_speed:
            self._animation_timer = 0
            self._frame_index += 1
            
            # If we've reached the end of the animation, destroy the explosion
            if self._frame_index >= len(self._explosion_frames):
                self.kill()
                return
            
            # Update image to current frame
            self.image = self._explosion_frames[self._frame_index]
            self.rect = self.image.get_rect(center=self.rect.center)

class Credits:
    """
    Displays scrolling credits from a single image, plays background music, and fades out the music.
    """
    def __init__(self, screen, width, height):
        """
        Initializes the Credits object.

        Args:
            screen: The Pygame screen surface.
            width: The width of the screen.
            height: The height of the screen.
        """
        self._screen = screen
        self._width = width
        self._height = height + 100
        print(f"Credits initialized with screen size: {width}x{height}")
        
        # Create fallback credits surface before loading the image
        self._credits_image = self._create_fallback_credits()
        self._has_loaded_image = False
        
        # Try to load the actual credits image (after fallback is ready)
        try:
            loaded_image = pygame.image.load(os.path.join("assets", "credits.png")).convert_alpha()
            self._credits_image = loaded_image
            self._has_loaded_image = True
            print("Successfully loaded credits.png")
        except Exception as e:
            print(f"Using fallback credits - couldn't load credits.png: {e}")
        
        # Set up initial positioning and timing
        self._y_position = height  # Start position below the screen
        self._scroll_speed = 1.5  # Pixels per frame (increased for better visibility)
        self._music_playing = False
        self._fade_out_started = False
        self.start_time = pygame.time.get_ticks()
        self._credits_height = self._credits_image.get_height()
        print(f"Credits image height: {self._credits_height}")
        
        # Try to load the credits music immediately
        self._start_music()
        
        # Debug print to verify initialization
        print("Credits sequence fully initialized")

    def _create_fallback_credits(self):
        """Creates a fallback credits image with text."""
        print("Creating fallback credits image")
        # Create a surface with enough height for scrolling
        surface = pygame.Surface((self._width, self._height * 3))
        surface.fill((0, 0, 0))  # Black background
        
        # Try to use the game's font
        try:
            font_large = pygame.font.Font(os.path.join("assets", "Daydream.ttf"), 36)
            font_medium = pygame.font.Font(os.path.join("assets", "Daydream.ttf"), 24)
            font_small = pygame.font.Font(os.path.join("assets", "Daydream.ttf"), 18)
            print("Using game fonts for credits")
        except Exception as e:
            print(f"Using system fonts for credits: {e}")
            font_large = pygame.font.SysFont(None, 48)
            font_medium = pygame.font.SysFont(None, 36)
            font_small = pygame.font.SysFont(None, 24)
        
        # Add title
        title = font_large.render("GAME CREDITS", True, (255, 255, 255))
        surface.blit(title, (self._width // 2 - title.get_width() // 2, 100))
        
        # Add sections with credits text
        credits_texts = [
            ("PROGRAMMING", 200),
            ("Game Developer", 240),
            ("Physics Engine", 280),
            ("", 320),
            ("ART & DESIGN", 380),
            ("Character Design", 420),
            ("Level Design", 460),
            ("UI Design", 500),
            ("", 540),
            ("MUSIC & SOUND", 600),
            ("Music Composer", 640),
            ("Sound Effects", 680),
            ("", 720),
            ("SPECIAL THANKS", 780),
            ("Beta Testers", 820),
            ("Family & Friends", 860),
            ("", 900),
            ("CUBODEEZ WAS DEFEATED", 1000),
            ("THE END", 1080),
            ("", 1140),
            ("THANKS FOR PLAYING!", 1200)
        ]
        
        for text, y_pos in credits_texts:
            # Use large font for headers, medium for content
            if text and text.isupper():
                text_surface = font_medium.render(text, True, (255, 220, 100))
            elif text:
                text_surface = font_small.render(text, True, (200, 200, 200))
            else:
                continue
            
            surface.blit(text_surface, (self._width // 2 - text_surface.get_width() // 2, y_pos))
            
        print(f"Created fallback credits with height: {surface.get_height()}")
        return surface

    def _start_music(self):
        """Starts playing the credits music."""
        try:
            # First try to load credits-specific music
            pygame.mixer.music.load(os.path.join("assets", "music", "credits.mp3"))
            pygame.mixer.music.play()
            self._music_playing = True
            print("Credits music started")
        except Exception as e:
            print(f"Failed to play credits music: {e}")
            # Try to use an alternative music file
            try:
                pygame.mixer.music.load(os.path.join("assets", "music", "theme.mp3"))
                pygame.mixer.music.play()
                self._music_playing = True
                print("Using theme music for credits")
            except Exception as e:
                print(f"Could not load any music for credits: {e}")

    @property
    def y_position(self):
        return self._y_position
    
    @property
    def credits_height(self):
        return self._credits_height
    
    @property
    def credits_image(self):
        return self._credits_image
    
    def update(self):
        """Updates the credits scrolling and music."""
        # Start music if not already playing
        if not self._music_playing:
            self._start_music()

        # Update scroll position
        self._y_position -= self._scroll_speed
        
        # Debug output for tracking credits position
        if pygame.time.get_ticks() % 120 == 0:  # Print position every ~2 seconds
            print(f"Credits position: {self._y_position}, Credits height: {self._credits_height}")

    def draw(self):
        """Draws the credits on the screen."""
        # Fill the screen with black background
        self._screen.fill((0, 0, 0))
        
        # Center the image horizontally
        x_position = self._width // 2 - self._credits_image.get_width() // 2
        
        # Draw the credits image
        self._screen.blit(self._credits_image, (x_position, self._y_position))
        
        # Draw a debug indicator
        if pygame.time.get_ticks() % 60 < 30:  # Flash every half second
            # Simple indicator in the corner to show credits are active
            pygame.draw.circle(self._screen, (255, 0, 0), (20, 20), 5)

class Coin(pygame.sprite.Sprite):
    """Collectible coin that follows the same pattern as NPCs"""
    
    def __init__(self, physics, x, y, coin_type='gold', value=10):
        super().__init__()
        self._physics = physics
        self.coin_type = coin_type.lower()
        self.value = value
        self.collected = False
        
        # Animation properties
        self.animation_time = 0
        self.bob_speed = 3.0  # Speed of bobbing animation
        self.bob_height = 5   # Height of bobbing in pixels
        self.rotation_speed = 2.0  # Speed of rotation
        self.current_rotation = 0
        self.collect_sound = pygame.mixer.Sound(os.path.join('assets', 'sounds', 'ring.mp3'))
        self.collect_sound.set_volume(0.5)
        self.collect_sound_played = False
        
        # Create coin surface based on type
        self.original_image = self._create_coin_image()
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect()
        
        # Position
        self.start_x = x
        self.start_y = y
        self.rect.centerx = x
        self.rect.centery = y
        
        # Collection animation
        self.collection_animation_time = 0
        self.collection_duration = 0.5  # seconds
        self.is_being_collected = False
        
    def _create_coin_image(self):
        """Create the coin image based on coin type"""
        size = 50 if self.coin_type == 'gold' else 30
        
        # Create surface with transparency
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        
        if self.coin_type == 'gold':
            # Gold coin - yellow with darker border
            pygame.draw.circle(surface, (255, 215, 0), (size//2, size//2), size//2)
            pygame.draw.circle(surface, (218, 165, 32), (size//2, size//2), size//2, 2)
            # Add inner circle for detail
            pygame.draw.circle(surface, (255, 255, 0), (size//2, size//2), size//3, 1)
        elif self.coin_type == 'silver':
            # Silver coin - light gray with darker border
            pygame.draw.circle(surface, (192, 192, 192), (size//2, size//2), size//2)
            pygame.draw.circle(surface, (128, 128, 128), (size//2, size//2), size//2, 2)
            pygame.draw.circle(surface, (220, 220, 220), (size//2, size//2), size//3, 1)
        else:  # copper or default
            # Copper coin - bronze color
            pygame.draw.circle(surface, (184, 115, 51), (size//2, size//2), size//2)
            pygame.draw.circle(surface, (138, 75, 31), (size//2, size//2), size//2, 2)
            pygame.draw.circle(surface, (205, 127, 50), (size//2, size//2), size//3, 1)
        
        return surface
    
    def update(self, dt):
        """Update coin logic and animation state"""
        if self.collected:
            return
            
        if self.is_being_collected:
            self._update_collection_animation(dt)
            if not self.collect_sound_played:
                self.collect_sound.play()
                self.collect_sound_played = True
        else:
            self._update_idle_animation(dt)
        
        # Update the visual image for sprite group drawing
        self._update_visual()
    
    def _update_idle_animation(self, dt):
        """Update the floating/bobbing animation"""
        self.animation_time += dt
        
        # Bobbing motion
        bob_offset = math.sin(self.animation_time * self.bob_speed) * self.bob_height
        self.rect.centery = self.start_y + bob_offset
        
        # Rotation effect (simulate 3D rotation by scaling horizontally)
        self.current_rotation += self.rotation_speed * dt
    
    def _update_collection_animation(self, dt):
        """Update the collection animation (coin flies up and fades)"""
        self.collection_animation_time += dt
        
        progress = self.collection_animation_time / self.collection_duration
        
        if progress >= 1.0:
            self.collected = True
            return
        
        # Move up during collection
        rise_distance = 30
        self.rect.centery = self.start_y - (rise_distance * progress)
    
    def _update_visual(self):
        """Update the visual appearance of the coin"""
        if self.is_being_collected:
            # Collection animation - fade out
            progress = self.collection_animation_time / self.collection_duration
            alpha = int(255 * (1 - progress))
            self.image = self.original_image.copy()
            self.image.set_alpha(alpha)
        else:
            # Idle animation - rotation effect
            scale_factor = abs(math.cos(self.current_rotation))
            
            if scale_factor > 0.1:  # Avoid division by very small numbers
                original_width = self.original_image.get_width()
                new_width = max(1, int(original_width * scale_factor))
                self.image = pygame.transform.scale(self.original_image, 
                                                  (new_width, self.original_image.get_height()))
                
                # Keep the coin centered
                old_center = self.rect.center
                self.rect = self.image.get_rect()
                self.rect.center = old_center
            else:
                # Very thin, just use a 1-pixel wide version
                self.image = pygame.transform.scale(self.original_image, (1, self.original_image.get_height()))
                old_center = self.rect.center
                self.rect = self.image.get_rect()
                self.rect.center = old_center
    
    def draw(self, screen):
        """Draw the coin to the screen"""
        if not self.collected:
            screen.blit(self.image, self.rect)
    
    def collect(self):
        """Start the collection animation"""
        if not self.collected and not self.is_being_collected:
            self.is_being_collected = True
            return self.value
        return 0
    
    def align_to_ground(self, level):
        """Align coin to ground level, similar to NPCs"""
        if hasattr(level, 'collision_tiles'):
            # Find the ground below the coin
            test_rect = pygame.Rect(self.rect.centerx - 5, self.rect.bottom, 10, 200)
            
            for tile in level.collision_tiles:
                if test_rect.colliderect(tile.rect):
                    # Position coin slightly above the ground
                    self.start_y = tile.rect.top - self.rect.height // 2 - 5
                    self.rect.centery = self.start_y
                    break