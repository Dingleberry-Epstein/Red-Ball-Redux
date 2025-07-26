import pygame, pymunk, os, math, random
from enum import Enum

class PurePymunkBall(pygame.sprite.Sprite):
    """Ball character using velocity changes for direct control, with pure Pymunk physics"""

    def __init__(self, physics_manager, x, y, radius=20):
        super().__init__()

        # Reference to physics space
        self._physics = physics_manager

        # Create the body with proper mass
        self._mass = 5.0
        self._moment = pymunk.moment_for_circle(self._mass, 0, radius)
        self._body = pymunk.Body(self._mass, self._moment)
        self._body.position = (x, y)

        # Create shape with moderate friction
        self._shape = pymunk.Circle(self._body, radius)
        self._shape.elasticity = 0.0
        self._shape.friction = 0.5
        self._shape.collision_type = self._physics.collision_types["ball"]
        
        # Add moderate damping
        self._body.damping = 0.1
        
        # Track previous velocity for bounce detection
        self._prev_velocity_y = 0
        
        # Add velocity callback to dampen only true bounces
        self._physics.space.on_collision(
            self._physics.collision_types["ball"], 
            self._physics.collision_types["ground"],
            self._physics.collision_types["switch"]
        )
        
        self._jumped = False

        self._physics.space.add(self._body, self._shape)

        # Visual properties
        self._radius = radius
        self._original_image = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(self._original_image, (0, 0, 0), (radius, radius), radius)
        pygame.draw.circle(self._original_image, (255, 0, 0), (radius, radius), radius-1)
        pygame.draw.line(self._original_image, (0, 0, 0), (radius, radius), (radius * 2, radius), 1)

        self._image = self._original_image.copy()
        self._rect = self._image.get_rect(center=(x, y))

        # Movement parameters
        self._move_speed = 20.0
        self._jump_speed = 500.0
        self._max_speed = 1000

        # Optimization: Track last angle to avoid unnecessary rotations
        self._last_angle = 0

        # Load sounds
        self._load_sounds()

        # Explosion animation
        self._setup_explosion_animation()
        self._is_dead = False
        self._death_timer = 0
        self._explosion_duration = 1.25 # Total desired duration in seconds
        self._death_frame_duration = self._explosion_duration / len(self._explosion_images) # Calculate frame duration
        self._is_exploding = False # add is_exploding flag.

    def _load_sounds(self):
        """Load sound effects for the ball"""
        self._jump_sound = pygame.mixer.Sound(os.path.join("assets", "sounds", "jump.mp3"))
        self._jump_sound.set_volume(0.5)
        self._jump_sound_played = False
        self._death_sound_played = False
        self._death_sound = pygame.mixer.Sound(os.path.join("assets", "sounds", "explosion.mp3"))
        self._death_sound.set_volume(0.5)
    
    def _setup_explosion_animation(self):
        """Setup explosion animation frames"""
        og_explosion_images = [pygame.image.load(os.path.join("assets", "sprites", "kaboom", f"frame{i}.png")).convert_alpha() for i in range(1, 8)]
        self._explosion_images = [pygame.transform.scale(image, (image.width * 2, image.height * 2)) for image in og_explosion_images]
        self._explosion_frame = 0

    def _handle_collision(self, arbiter, space, data):
        """Smart damping that differentiates between bounces and slope traversal"""
        # Get the collision normal
        normal = arbiter.contact_point_set.normal
        
        # Detect true bounce vs slope traversal
        # A true bounce happens when:
        # 1. Ball was moving down (positive y velocity)
        # 2. Then suddenly starts moving up (negative y velocity)
        # 3. The collision normal is pointing mostly upward
        
        is_bounce = (self._prev_velocity_y > 50 and    # Was moving down significantly
                     self._body.velocity.y < 0 and     # Now moving up
                     normal.y < -0.7 and              # Collision from below
                     not self._jumped)                 # Not from player jump
        
        if is_bounce:
            # Only dampen true bounces
            self._body.velocity = (self._body.velocity.x, self._body.velocity.y * 0.3)
            
        return True

    @property
    def image(self):
        return self._image
    
    @image.setter
    def image(self, value):
        self._image = value
    
    @property
    def rect(self):
        return self._rect
    
    @rect.setter
    def rect(self, value):
        self._rect = value
    
    @property
    def body(self):
        return self._body
    
    @property
    def shape(self):
        return self._shape
    
    @property
    def radius(self):
        return self._radius
    
    @property
    def is_dead(self):
        return self._is_dead
    
    @property
    def original_image(self):
        return self._original_image
    
    @property
    def is_exploding(self):
        return self._is_exploding

    def update(self):
        """Update based on input, using velocity changes"""
        # Store current vertical velocity for next frame's bounce detection
        self._prev_velocity_y = self._body.velocity.y
        
        if self._is_exploding:
            self._update_explosion_animation()
            return # stop all normal updates.

        # Get keyboard input
        keys = pygame.key.get_pressed()

        # Optimize: Cache max speed based on shift key
        self._max_speed = 2000 if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else 1000

        # Apply velocity changes for movement
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            if self._body.velocity.x > -self._max_speed:
                self._body.velocity = (self._body.velocity.x - self._move_speed, self._body.velocity.y)
            else:
                self._body.velocity = (-self._max_speed, self._body.velocity.y)
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            if self._body.velocity.x < self._max_speed:
                self._body.velocity = (self._body.velocity.x + self._move_speed, self._body.velocity.y)
            else:
                self._body.velocity = (self._max_speed, self._body.velocity.y)

        # Jump with velocity change when on ground
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and not self._jumped:
            self._body.velocity = (self._body.velocity.x, -self._jump_speed)
            self._jumped = True
            if not self._jump_sound_played:
                self._jump_sound.play()
                self._jump_sound_played = True
        if self._body.velocity.y == 0:
            self._jumped = False
            self._jump_sound_played = False

        # Update sprite position
        self._rect.center = self._body.position

        # Optimization: Only update rotation when needed
        current_angle = self._body.angle
        if abs(current_angle - self._last_angle) > 0.01:
            self.update_rotation()
            self._last_angle = current_angle
    
    def _update_explosion_animation(self):
        """Update the explosion animation frames"""
        self._death_timer += 1 / 60
        if self._death_timer >= self._death_frame_duration:
            self._death_timer = 0
            self._explosion_frame += 1
            if self._explosion_frame < len(self._explosion_images):
                self._image = self._explosion_images[self._explosion_frame]
                self._rect = self._image.get_rect(center=self._rect.center)
            else:
                self._is_dead = True # Set is_dead after explosion finishes.
                self._is_exploding = False # reset the exploding flag.
                self.kill() # remove the sprite after the animation.

    def update_rotation(self):
        """Update sprite rotation to match physics body"""
        angle_degrees = self._body.angle * 57.29578
        self._image = pygame.transform.rotate(self._original_image, -angle_degrees)
        self._rect = self._image.get_rect(center=self._rect.center)

    def death(self):
        """Handle death animation and sound"""
        if self._is_exploding:
            return # don't restart the explosion if already exploding.
        self._is_exploding = True
        self._explosion_frame = 0
        self._death_timer = 0
        if not self._death_sound_played:
            self._death_sound.play()
            self._death_sound_played = True
        self._body.velocity = (0, 0)
        self._body.angular_velocity = 0
        if self._body in self._physics.space.bodies: # add this check.
            try:
                self._physics.space.remove(self._body, self._shape)
            except (ValueError, AttributeError):
                pass # ignore if it has already been removed.

class NPCCharacter(pygame.sprite.Sprite):
    """An NPC character that can interact with the player through dialogue"""
    
    def __init__(self, physics_manager, x, y, name="NPC", radius=20, color=(0, 128, 255)):
        """Initialize the NPC character"""
        super().__init__()
        
        # Reference to physics space
        self._physics = physics_manager
        
        # Set NPC name
        self._name = name
        
        # Create physics body (kinematic, not affected by physics)
        self._body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self._body.position = (x, y)
        
        # Create shape
        self._shape = pymunk.Circle(self._body, radius)
        self._shape.collision_type = self._physics.collision_types.get("npc", 4)  # Use a specific collision type
        
        # Add to physics space
        self._physics.space.add(self._body, self._shape)
        
        # Visual properties
        self._radius = radius
        self._original_image = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(self._original_image, (0, 0, 0), (radius, radius), radius)  # Black outline
        pygame.draw.circle(self._original_image, color, (radius, radius), radius - 1)  # NPC color
        
        # Update image and rect
        self._image = self._original_image.copy()
        self._rect = self._image.get_rect(center=(x, y))
        
        # Dialogue properties
        self._dialogues = self.get_default_dialogues()
        self._current_dialogue_index = 0
        self._is_talking = False
        self._player_choices = None  # Store current choices
        self._dialogue_history = []  # Track choices made
        
        # Interaction properties
        self._interaction_radius = radius * 5  # Player needs to be this close to interact
        self._interaction_indicator = None
        self._show_indicator = False
        self._indicator_timer = 0
        self._is_active = False  # For performance optimization
        
        # Font for interaction indicator
        self._setup_font()
        
        # Create interaction indicator
        self._interaction_indicator = self._font.render("E", True, (255, 255, 255))
        
        # For ground placement
        self._ground_check_distance = 100  # How far to check for ground below
        self._should_align_to_ground = True  # Set to True to enable ground alignment
        
    def _setup_font(self):
        """Set up font for the interaction indicator"""
        try:
            self._font = pygame.font.Font(os.path.join("assets", "Daydream.ttf"), 18)
        except:
            self._font = pygame.font.SysFont(None, 24)
    
    @property
    def name(self):
        return self._name
    
    @property
    def body(self):
        return self._body
    
    @property
    def rect(self):
        return self._rect
    
    @rect.setter
    def rect(self, value):
        self._rect = value
    
    @property
    def image(self):
        return self._image
    
    @image.setter
    def image(self, value):
        self._image = value
    
    @property
    def is_active(self):
        return self._is_active
    
    @property
    def show_indicator(self):
        return self._show_indicator
    
    @property
    def current_dialogue_index(self):
        return self._current_dialogue_index
    
    @current_dialogue_index.setter
    def current_dialogue_index(self, value):
        self._current_dialogue_index = value
        
    def align_to_ground(self, level):
        """Align the NPC to the ground below them"""
        if not self._should_align_to_ground:
            return
            
        # Get NPC's current position
        x, y = self._body.position
        
        # Check for ground tiles below the NPC
        ground_found = False
        test_distance = self._ground_check_distance
        
        # Simple raycast downward
        for check_y in range(int(y), int(y + test_distance), 10):
            test_point = (x, check_y)
            
            # Check if there's any static shape at this point
            for shape in level.static_shapes:
                if shape.point_query(test_point).distance < 0:
                    # Found ground, adjust position to just above it
                    self._body.position = (x, check_y - self._radius - 2)  # -2 for small clearance
                    self._rect.center = self._body.position
                    ground_found = True
                    break
                    
            if ground_found:
                break
                
        if not ground_found:
            print(f"Warning: No ground found below NPC {self._name} at ({x}, {y})")
        
    def update(self, player=None, distance_threshold=500):
        """Update NPC state - optimized to only update when near player"""
        # Skip update if player is too far away and NPC isn't active
        if player:
            dx = player.body.position.x - self._body.position.x
            dy = player.body.position.y - self._body.position.y
            distance = (dx**2 + dy**2)**0.5
            
            # Set active state based on distance
            self._is_active = distance <= distance_threshold
            
            # Show indicator if player is within interaction range
            self._show_indicator = distance <= self._interaction_radius
        
        # If not active, don't continue with updates
        if not self._is_active:
            return
            
        # Update rect position to match physics body
        self._rect.center = self._body.position
        
        # Animate interaction indicator
        if self._show_indicator:
            self._indicator_timer += 1/60
            if self._indicator_timer >= 0.5:  # Flash every half second
                self._indicator_timer = 0
        
    def can_interact(self, player):
        """Check if player is close enough to interact with this NPC"""
        # Calculate distance between NPC and player
        dx = player.body.position.x - self._body.position.x
        dy = player.body.position.y - self._body.position.y
        distance = (dx**2 + dy**2)**0.5
        
        return distance <= self._interaction_radius
    
    def start_dialogue(self):
        """Start or continue dialogue sequence"""
        self._is_talking = True
        self._current_dialogue_index = 0
        return self.get_current_dialogue()
    
    def advance_dialogue(self):
        """Move to the next dialogue line"""
        if self._current_dialogue_index < len(self._dialogues) - 1:
            self._current_dialogue_index += 1
            return self.get_current_dialogue()
        else:
            self._is_talking = False
            return None
    
    def get_current_dialogue(self):
        """Get the current dialogue text"""
        if 0 <= self._current_dialogue_index < len(self._dialogues):
            return self._dialogues[self._current_dialogue_index]
        return None
    
    def get_default_dialogues(self):
        """Get default dialogues - this should be overridden by specific NPCs"""
        return [
            {
                "text": f"Hello! I'm {self._name}.",
                "choices": [
                    {"text": "Hello! Nice to meet you.", "next_index": 1},
                    {"text": "Who are you again?", "next_index": 1},
                    {"text": "I don't have time for this.", "next_index": 2}
                ]
            },
            {
                "text": "I don't have much to say yet.",
                "choices": [
                    {"text": "That's okay.", "next_index": 2},
                    {"text": "Tell me more about yourself.", "next_index": 2},
                    {"text": "I'll come back later then.", "next_index": 2}
                ]
            },
            {
                "text": "Come back when I've been programmed with more dialogue!",
                "choices": [
                    {"text": "Sure, I'll check in later.", "next_index": None},
                    {"text": "Can't wait to hear what you have to say!", "next_index": None},
                    {"text": "Maybe I'll try talking to someone else.", "next_index": None}
                ]
            }
        ]
    
    def handle_choice(self, choice_index):
        """Handle a dialogue choice selection"""
        current_dialogue = self.get_current_dialogue()
        if current_dialogue and current_dialogue.get("choices"):
            choices = current_dialogue["choices"]
            if 0 <= choice_index < len(choices):
                choice = choices[choice_index]
                # Record the choice made
                self._dialogue_history.append({
                    "npc_text": current_dialogue["text"],
                    "player_choice": choice["text"]
                })
                
                # If the choice has a next_index, jump to that dialogue
                if "next_index" in choice and choice["next_index"] is not None:
                    self._current_dialogue_index = choice["next_index"]
                    return self.get_current_dialogue()
                # Otherwise end the dialogue
                else:
                    self._is_talking = False
                    return None
        return None
    
    def draw_indicator(self, screen, camera):
        """Draw the interaction indicator if player is close enough"""
        if self._show_indicator and self._indicator_timer < 0.25:  # Only show for half the blink cycle
            # Position indicator above NPC
            indicator_x = self._rect.centerx
            indicator_y = self._rect.top - 30
            
            # Create small background for better visibility
            bg_rect = pygame.Rect(0, 0, 30, 30)
            bg_rect.center = (indicator_x, indicator_y)
            
            # Apply camera offset
            bg_rect = camera.apply_rect(bg_rect)
            
            # Draw background circle
            pygame.draw.circle(screen, (0, 0, 0), bg_rect.center, 15)
            pygame.draw.circle(screen, (200, 200, 200), bg_rect.center, 14)
            
            # Draw "E" text
            text_rect = self._interaction_indicator.get_rect(center=bg_rect.center)
            screen.blit(self._interaction_indicator, text_rect)
    
    def print_dialogue(self):
        """Print current dialogue for debugging/testing"""
        current = self.get_current_dialogue()
        if not current:
            print("No dialogue available.")
            return
            
        # Print NPC dialogue
        print(f"\n{self._name}: {current['text']}")
        
        # Print player choices if available
        if current.get("choices"):
            print("\nYour options:")
            for i, choice in enumerate(current["choices"]):
                print(f"{i+1}. {choice['text']}")
        else:
            print("\nPress any key to continue...")

class BlueBall(NPCCharacter):
    """Blue Ball NPC character"""
    def __init__(self, physics_manager, x, y):
        """Initialize the Blue Ball NPC"""
        super().__init__(physics_manager, x, y, name="Blue Ball", color=(0, 0, 255))
        
        # Load sunglasses image
        self._load_sunglasses()
    
    def _load_sunglasses(self):
        """Load and apply sunglasses to the blue ball"""
        try:
            self._glasses = pygame.image.load(os.path.join("assets", "sprites", "sunglasses.png")).convert_alpha()
            
            # Resize glasses to fit the ball
            glasses_width = int(self._glasses.get_width() * 2)
            glasses_height = int(self._glasses.get_height() * 2)
            self._glasses = pygame.transform.scale(self._glasses, (glasses_width, glasses_height))
            
            # Create a copy of the original image to draw glasses on
            self._image = self._original_image.copy()
            
            # Position the glasses on the upper part of the ball's face
            glasses_x = self._radius - glasses_width // 2
            glasses_y = self._radius - int(self._radius * 1.3)  # Position slightly above center
            
            # Draw the glasses onto the ball
            self._image.blit(self._glasses, (glasses_x, glasses_y))
            
        except Exception as e:
            print(f"Error adding sunglasses to BlueBall: {e}")
            # Keep the original image if there's an error
            self._image = self._original_image.copy()
            
            # Create simple portrait
            self._create_portrait()
    
    def _create_portrait(self):
        """Create a simple portrait for the dialogue system"""
        self.portrait = pygame.Surface((84, 84), pygame.SRCALPHA)
        pygame.draw.circle(self.portrait, (0, 0, 255), (42, 42), 38)
        pygame.draw.circle(self.portrait, (0, 0, 0), (42, 42), 38, 2)  # Black outline

    def get_default_dialogues(self):
        """Get default dialogues for Blue Ball with multiple player choices"""
        return [
            {
                "text": "Yo? Wasn't expecting any visitors up here. What's poppin?",
                "choices": [
                    {"text": "Who are you?", "next_index": 3},
                    {"text": "What is this place?", "next_index": 1}
                ]
            },
            {
                "text": "Hah, didn't mean to fall down here, eh? This is just some old cave, kid. Don't sweat it. The end's not far from here.",
                "choices": [
                    {"text": "Who are you, anyway?", "next_index": 3},
                    {"text": "A cave?", "next_index": 2},
                    {"text": "Where is this so called 'exit'? ", "next_index": 4}
                ]
            },
            {
                "text": "Yeah, you heard me right brotha, this is a cave. I don't know what tomfoolery caused you to fall down here, but it ain't of any use now. I'd suggest you find the exit and get out of here.",
                "choices": [
                    {"text": "Who are you, anyway?", "next_index": 3},
                    {"text": "Please dude, I am so lost right now.", "next_index": 6},
                    {"text": "Fine.", "next_index": 7}
                ]
            },
            {
                "text": "I'm Barthelemy Bluschev Ball, but you can call me Blue Ball. I don't think we're related man, but I'd help out a brotha. Seems like you'll need it.",
                "choices": [
                    {"text": "You can help? What do I need from you?", "next_index": 6},
                    {"text": "Why would I need help?", "next_index": 5},
                    {"text": "I can manage on my own, thanks.", "next_index": 7}
                ]
            },
            {
                "text": "Just to your right somewhere, dude. It ain't an easy task, but I know you can do it. Just keep your head up and don't let the vastness of this space get to you.",
                "choices": [
                    {"text": "Who are you, anyway?", "next_index": 3},
                    {"text": "Man, that ain't gonna help! I'm already so lost..", "next_index": 6},
                    {"text": "Bet. I'll catch you later man.", "next_index": 7}
                ]
            },
            {
                "text": "Trust me on this man, the levels finna get wackier an wackier from here. You can beat them, sure, but it ain't no easy task.",
                "choices": [
                    {"text": "Any tips for navigating them?", "next_index": 6},
                    {"text": "I'm up for the challenge!", "next_index": 7}
                ]
            },
            {
                "text": "What you need is a map! Dont'chu worry man, I got one here for you. Press M at any time in a level to open and close it. Use WASD, Arrows or drag the map around to reposition it. You can use scroll wheel to zoom in and out as well.",
                "choices": [
                    {"text": "Thanks for the map!", "next_index": 7},
                    {"text": "That's really helpful.", "next_index": 7},
                    {"text": "I'll definitely use that.", "next_index": 7}
                ]
            },
            {
                "text": "Good luck man, I'll be waiting on the other side.",
                "choices": [
                    {"text": "See you there!", "next_index": None},
                    {"text": "Thanks for the help.", "next_index": None},
                    {"text": "Until we meet again.", "next_index": None}
                ]
            }
        ]

class SignNPC(pygame.sprite.Sprite):
    """A sign that displays information when interacted with.
    Similar to NPCCharacter but simplified for one-way communication."""

    def __init__(self, physics, x, y, name="Sign", message="Read this sign for information."):
        """Initialize the sign NPC with a specific message."""
        pygame.sprite.Sprite.__init__(self)

        self._name = name
        self._message = message

        self._dialogues = [
            {
                "text": self._message,
                "choices": None
            }
        ]
        self._current_dialogue_index = 0
        self._dialogue_finished = False  # Add a flag to track dialogue completion

        self._load_image()
        self._setup_physics(physics, x, y)

        self._interaction_distance = 80
        self._show_indicator = False
        self._is_active = True

        self.portrait = self._create_sign_portrait()

        self._animation_timer = 0
        self._bounce_height = 0
        self._rotation_angle = 0

        print(f"Created sign '{name}' at position ({x}, {y})")

    def _load_image(self):
        """Load sign image or create a fallback if image not found"""
        try:
            self._image = pygame.image.load(os.path.join("assets", "sprites", "sign.png")).convert_alpha()
            self._original_image = self._image.copy()
        except:
            self._image = pygame.Surface((48, 48), pygame.SRCALPHA)
            pygame.draw.rect(self._image, (139, 69, 19), (10, 24, 28, 24))
            pygame.draw.rect(self._image, (160, 82, 45), (4, 4, 40, 20))
            pygame.draw.rect(self._image, (80, 41, 22), (4, 4, 40, 20), 2)
            self._original_image = self._image.copy()
            print(f"Created fallback sign sprite for {self._name}")

        self._image = pygame.transform.scale(self._image, (48, 48))
        self._original_image = self._image.copy()

    def _setup_physics(self, physics, x, y):
        """Setup physics body and shape for the sign"""
        self._body = pymunk.Body(body_type=pymunk.Body.STATIC)
        self._body.position = (x, y)

        radius = 12
        self._shape = pymunk.Circle(self._body, radius)
        if hasattr(physics, 'collision_types') and 'ground' in physics.collision_types:
            self._shape.collision_type = physics.collision_types["ground"]
        self._shape.sensor = True

        physics.space.add(self._body, self._shape)
        self._rect = pygame.Rect(x - 24, y - 24, 48, 48)

    def _create_sign_portrait(self):
        """Create a portrait image for the dialogue system"""
        try:
            portrait = pygame.image.load(os.path.join("assets", "sprites", "sign_portrait.png")).convert_alpha()
            return pygame.transform.scale(portrait, (84, 84))
        except:
            portrait = pygame.Surface((84, 84), pygame.SRCALPHA)

            bg_color = (160, 82, 45)
            border_color = (80, 41, 22)

            pygame.draw.rect(portrait, bg_color, (10, 10, 64, 50))
            pygame.draw.rect(portrait, border_color, (10, 10, 64, 50), 2)

            pygame.draw.rect(portrait, border_color, (32, 60, 20, 24))

            pygame.draw.line(portrait, border_color, (20, 25), (64, 25), 2)
            pygame.draw.line(portrait, border_color, (20, 35), (64, 35), 2)
            pygame.draw.line(portrait, border_color, (20, 45), (54, 45), 2)

            print(f"Created fallback sign portrait for {self._name}")
            return portrait

    @property
    def name(self):
        return self._name
    
    @property
    def message(self):
        return self._message
    
    @property
    def body(self):
        return self._body
    
    @property
    def rect(self):
        return self._rect
    
    @rect.setter
    def rect(self, value):
        self._rect = value
    
    @property
    def image(self):
        return self._image
    
    @image.setter
    def image(self, value):
        self._image = value
    
    @property
    def show_indicator(self):
        return self._show_indicator
    
    @show_indicator.setter
    def show_indicator(self, value):
        self._show_indicator = value
    
    @property
    def is_active(self):
        return self._is_active
    
    @property
    def current_dialogue_index(self):
        return self._current_dialogue_index
    
    @current_dialogue_index.setter
    def current_dialogue_index(self, value):
        self._current_dialogue_index = value

    def update(self, ball=None):
        """Update sign state and check for proximity to ball"""
        self._rect.center = (int(self._body.position.x), int(self._body.position.y))

        self._animation_timer += 0.01
        self._bounce_height = math.sin(self._animation_timer) * 2

        if self._show_indicator:
            self._rotation_angle = math.sin(self._animation_timer * 3) * 3
        else:
            self._rotation_angle = 0

        rotated_image = pygame.transform.rotate(self._original_image, self._rotation_angle)
        self._image = rotated_image

        if ball and hasattr(ball, 'body'):
            dx = self._body.position.x - ball.body.position.x
            dy = self._body.position.y - ball.body.position.y
            distance = (dx**2 + dy**2)**0.5

            if distance < self._interaction_distance:
                self._show_indicator = True
            else:
                self._show_indicator = False

    def draw_indicator(self, screen, camera):
        """Draw an interaction indicator above the sign"""
        if not self._show_indicator:
            return

        indicator_pos = (self._rect.centerx, self._rect.top - 20)
        indicator_rect = pygame.Rect(0, 0, 20, 20)
        indicator_rect.center = indicator_pos

        screen_rect = camera.apply_rect(indicator_rect)

        pulse = (math.sin(self._animation_timer * 4) + 1) * 0.5
        glow_size = 4 + int(pulse * 4)

        glow_color = (255, 255, 150, int(100 + 100 * pulse))
        glow_surf = pygame.Surface((screen_rect.width + glow_size*2, screen_rect.height + glow_size*2), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, glow_color,
                         (0, 0, screen_rect.width + glow_size*2, screen_rect.height + glow_size*2),
                         0, 5 + glow_size)

        screen.blit(glow_surf, (screen_rect.x - glow_size, screen_rect.y - glow_size))

        pygame.draw.rect(screen, (50, 50, 50), screen_rect.inflate(10, 10), 0, 5)
        pygame.draw.rect(screen, (200, 200, 200), screen_rect.inflate(10, 10), 2, 5)

        try:
            font = pygame.font.Font(os.path.join("assets", "Daydream.ttf"), 14)
        except:
            font = pygame.font.SysFont(None, 20)

        text = font.render("E", True, (255, 255, 255))
        text_rect = text.get_rect(center=screen_rect.center)
        screen.blit(text, text_rect)

    def align_to_ground(self, level):
        """Align the sign to the ground to prevent floating"""
        if not hasattr(level, 'physics') or not level.physics:
            return

        x, y = self._body.position

        ground_found = False
        test_distance = 200

        for distance in range(10, test_distance, 10):
            test_point = (x, y + distance)

            sensor_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            sensor_body.position = test_point
            sensor_shape = pymunk.Circle(sensor_body, 5)
            sensor_shape.sensor = True

            hits = level.physics.space.shape_query(sensor_shape)

            for hit in hits:
                if hasattr(hit.shape, 'collision_type') and hit.shape.collision_type == level.physics.collision_types.get("ground", 0):
                    self._body.position = (x, y + distance - 24)
                    self._rect.center = (int(x), int(y + distance - 24))
                    ground_found = True
                    break

            if ground_found:
                break

    def can_interact(self, ball):
        """Check if the player can interact with this sign"""
        if not ball or not hasattr(ball, 'body'):
            return False

        dx = self._body.position.x - ball.body.position.x
        dy = self._body.position.y - ball.body.position.y
        distance = (dx**2 + dy**2)**0.5

        return distance < self._interaction_distance

    def get_current_dialogue(self):
        """Get the current dialogue object"""
        if 0 <= self._current_dialogue_index < len(self._dialogues):
            return self._dialogues[self._current_dialogue_index]
        return None

    def start_dialogue(self):
        """Start dialogue with the sign"""
        self._current_dialogue_index = 0
        self._dialogue_finished = False  # Reset the finished flag
        print(f"Starting dialogue with sign: {self._name}")
        return self.get_current_dialogue()

    def handle_choice(self, choice_index):
        """Handle player's dialogue choice - for signs, there are no choices"""
        self._dialogue_finished = True  # Set the dialogue finished flag
        return None  # Return None to indicate that there are no more dialogues

    def print_dialogue(self):
        """Print the current dialogue (for debugging)"""
        current = self.get_current_dialogue()
        if current:
            print(f"[{self._name}]: {current['text']}")

class BossState(Enum):
    """Clean state enumeration for boss behavior"""
    IDLE = "idle"
    PREPARING = "preparing"
    JUMPING = "jumping"
    LANDING = "landing"
    VULNERABLE = "vulnerable"
    STUNNED = "stunned"


class Cubodeez_The_Almighty_Cube(pygame.sprite.Sprite):
    """Rebuilt Cubodeez boss with clean state management and proper Pymunk integration"""
    
    def __init__(self, physics_manager, x, y, target_ball=None, size=150):
        super().__init__()
        
        # Core references
        self.physics = physics_manager
        self.target = target_ball
        self.size = size
        
        # Position and spawn data
        self.spawn_x = x
        self.spawn_y = y
        
        # Boss stats
        self.name = "Cubodeez The Almighty Cube"
        self.max_health = 100
        self.health = self.max_health
        self.mass = 80.0
        
        # Physics setup
        self._setup_physics()
        
        # Visual setup
        self._setup_visuals()
        
        # State management
        self.state = BossState.IDLE
        self.state_timer = 0.0
        self.action_cooldown = 2.0  # Time between attacks
        
        # Jump mechanics
        self.jump_force = 1000
        self.jump_height = 600
        self.max_jump_distance = 800
        self.is_grounded = True
        self.ground_check_distance = size + 20
        
        # Target and landing system
        self.target_position = (0, 0)
        self.landing_radius = 150
        self.show_target_marker = False
        self.target_locked = False
        
        # Vulnerability system
        self.is_vulnerable = False
        self.vulnerability_duration = 3.0
        self.vulnerability_timer = 0.0
        self.damage_taken_this_cycle = False
        
        # Visual effects
        self.shake_timer = 0.0
        self.shake_intensity = 0
        self.flash_timer = 0.0
        self.eye_color = (255, 255, 0)  # Default yellow
        
        # Sound effects
        self._load_sounds()
        
        # Debug
        self.debug_mode = True
        
        print(f"Cubodeez initialized at ({x}, {y}) - State: {self.state}")

    def _setup_physics(self):
        """Initialize physics body and collision handling"""
        # Create physics body
        self.body = pymunk.Body(self.mass, pymunk.moment_for_box(self.mass, (self.size, self.size)))
        self.body.position = self.spawn_x, self.spawn_y
        
        # Create collision shape
        self.shape = pymunk.Poly.create_box(self.body, (self.size, self.size))
        self.shape.elasticity = 0.2
        self.shape.friction = 0.8
        
        # Set collision type
        self.collision_type = self.physics.collision_types.get("boss", 5)
        self.shape.collision_type = self.collision_type
        
        # Store reference for collision callbacks
        self.shape.boss_ref = self
        
        # Add to physics space
        self.physics.space.add(self.body, self.shape)
        
        # Setup collision handlers using new Pymunk API
        self._setup_collision_handlers()

    def _setup_collision_handlers(self):
        """Setup collision handlers using new Pymunk API"""
        ball_type = self.physics.collision_types.get("ball", 1)
        ground_type = self.physics.collision_types.get("ground", 2)
        
        # Boss vs Player collision
        def boss_player_collision_begin(arbiter, space, data):
            boss_shape, player_shape = arbiter.shapes
            if hasattr(boss_shape, 'boss_ref'):
                boss_shape.boss_ref._handle_player_collision()
            return True
            
        self.physics.space.on_collision(
            self.collision_type, ball_type,
            begin=boss_player_collision_begin
        )
        
        # Boss vs Ground collision
        def boss_ground_collision_begin(arbiter, space, data):
            boss_shape, ground_shape = arbiter.shapes
            if hasattr(boss_shape, 'boss_ref'):
                return boss_shape.boss_ref._handle_ground_collision(arbiter)
            return True
            
        self.physics.space.on_collision(
            self.collision_type, ground_type,
            begin=boss_ground_collision_begin
        )

    def _setup_visuals(self):
        """Setup visual appearance and animations"""
        # Create base image
        self.base_image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        
        # Draw gradient body
        for y in range(self.size):
            intensity = int(120 + (80 * (y / self.size)))
            color = (intensity, 0, 0)
            pygame.draw.line(self.base_image, color, (0, y), (self.size, y))
        
        # Add border
        pygame.draw.rect(self.base_image, (0, 0, 0), (0, 0, self.size, self.size), 3)
        
        # Setup dynamic elements (eyes, etc.) - drawn in update_visuals()
        self.image = self.base_image.copy()
        self.rect = self.image.get_rect(center=(self.spawn_x, self.spawn_y))
        
        # Target marker
        self._create_target_marker()

    def _create_target_marker(self):
        """Create the target marker visual"""
        marker_size = (self.size, self.size // 4)
        self.target_marker = pygame.Surface(marker_size, pygame.SRCALPHA)
        
        # Semi-transparent red background
        pygame.draw.rect(self.target_marker, (255, 0, 0, 128), (0, 0, *marker_size))
        pygame.draw.rect(self.target_marker, (255, 0, 0, 255), (0, 0, *marker_size), 2)
        
        # Draw X pattern
        pygame.draw.line(self.target_marker, (255, 255, 255), 
                        (10, 10), (marker_size[0]-10, marker_size[1]-10), 3)
        pygame.draw.line(self.target_marker, (255, 255, 255), 
                        (10, marker_size[1]-10), (marker_size[0]-10, 10), 3)
        
        self.marker_rect = self.target_marker.get_rect()

    def _load_sounds(self):
        """Load sound effects with fallbacks"""
        self.sounds = {}
        sound_files = {
            'jump': 'boss_jump.mp3',
            'land': 'boss_land.mp3',
            'hurt': os.path.join("assets", "sounds", "boss_hurt.mp3"),
            'squish': 'explosion.mp3'
        }
        
        for sound_name, filename in sound_files.items():
            try:
                path = os.path.join("assets", "sounds", filename)
                self.sounds[sound_name] = pygame.mixer.Sound(path)
            except (pygame.error, FileNotFoundError):
                print(f"Warning: Could not load {filename}")
                self.sounds[sound_name] = None

    def _handle_player_collision(self):
        """Handle collision with player - always lethal"""
        if not self.target or (hasattr(self.target, 'is_dead') and self.target.is_dead):
            return
            
        print("Boss squished the player!")
        
        self._add_screen_shake(0.8, 20)

    def _handle_ground_collision(self, arbiter):
        """Handle ground collision with proper state-based logic"""
        # Always allow collision when not jumping
        if self.state != BossState.JUMPING:
            self._set_grounded(True)
            return True
        
        # During jump, only land if falling and near target
        if self.body.velocity.y <= 0:  # Still ascending
            arbiter.process_collision = False
            return True
        
        # Check if we're near our intended landing spot
        contact_point = arbiter.contact_point_set.points[0].point_a if arbiter.contact_point_set.points else self.body.position
        distance_to_target = math.sqrt(
            (contact_point.x - self.target_position[0]) ** 2 + 
            (contact_point.y - self.target_position[1]) ** 2
        )
        
        # Land if close enough to target or falling too fast
        should_land = (
            distance_to_target <= self.landing_radius or
            self.body.velocity.y > 800 or  # Falling very fast
            self.state_timer > 4.0  # Been jumping too long
        )
        
        if should_land:
            self._execute_landing(contact_point)
            return True
        else:
            # Phase through ground if not at target
            arbiter.process_collision = False
            return True

    def _set_grounded(self, grounded):
        """Update grounded state with proper logging"""
        if self.is_grounded != grounded:
            self.is_grounded = grounded
            if self.debug_mode:
                print(f"Boss grounded state changed: {grounded}")

    def _execute_landing(self, landing_point):
        """Execute landing sequence with proper state transition"""
        print(f"Boss landing at {landing_point} - Distance to target: {math.sqrt((landing_point.x - self.target_position[0])**2 + (landing_point.y - self.target_position[1])**2):.1f}")
        
        # Stop all movement
        self.body.velocity = (0, 0)
        
        # Update state
        self.state = BossState.LANDING
        self.state_timer = 0.0
        self._set_grounded(True)
        
        # Effects
        self._play_sound('land')
        self._add_screen_shake(0.6, 25)
        
        # Hide target marker
        self.show_target_marker = False
        self.target_locked = False

    def _check_ground_below(self):
        """Simple ground check using ray casting"""
        if not self.is_grounded and self.state != BossState.JUMPING:
            # Cast ray downward
            start = self.body.position
            end = (start.x, start.y + self.ground_check_distance)
            
            query = self.physics.space.segment_query_first(
                start, end, 
                0, pymunk.ShapeFilter(mask=self.physics.collision_types.get("ground", 2))
            )
            
            if query and query.shape:
                self._set_grounded(True)
                # Adjust position if needed
                ground_y = query.point.y - self.size // 2
                if self.body.position.y > ground_y:
                    self.body.position = (self.body.position.x, ground_y)

    def calculate_jump_to_player(self):
        """Calculate jump trajectory to hit the player"""
        if not self.target:
            return False
        
        # Get player position
        player_pos = self.target.body.position
        boss_pos = self.body.position
        
        # Calculate target with some prediction
        player_vel = getattr(self.target.body, 'velocity', (0, 0))
        prediction_time = 1.0  # Predict 1 second ahead
        predicted_x = player_pos.x + player_vel.x * prediction_time
        predicted_y = player_pos.y
        
        # Constrain to maximum jump distance
        dx = predicted_x - boss_pos.x
        distance = abs(dx)
        
        if distance > self.max_jump_distance:
            direction = 1 if dx > 0 else -1
            predicted_x = boss_pos.x + direction * self.max_jump_distance
        
        # Set target position
        self.target_position = (predicted_x, predicted_y)
        
        return True

    def execute_jump(self):
        """Execute jump with calculated trajectory"""
        if not self.is_grounded or self.state == BossState.JUMPING:
            return False
        
        # Calculate trajectory
        start_pos = self.body.position
        target_x, target_y = self.target_position
        
        dx = target_x - start_pos.x
        dy = target_y - start_pos.y
        
        # Calculate jump timing and velocities
        gravity = abs(self.physics.space.gravity.y)
        jump_time = 2.0  # Fixed jump time for consistency
        
        # Horizontal velocity
        vel_x = dx / jump_time
        
        # Vertical velocity (accounting for desired height)
        jump_height = max(self.jump_height, abs(dy) + 200)
        vel_y = -math.sqrt(2 * gravity * jump_height)
        
        # Apply velocities
        self.body.velocity = (vel_x, vel_y)
        
        # Update state
        self.state = BossState.JUMPING
        self.state_timer = 0.0
        self._set_grounded(False)
        
        # Lock target marker
        self.target_locked = True
        self.marker_rect.center = self.target_position
        
        # Effects
        self._play_sound('jump')
        
        print(f"Jump executed: velocity=({vel_x:.1f}, {vel_y:.1f}), target={self.target_position}")
        return True

    def take_damage(self, amount=20):
        """Take damage when vulnerable"""
        if not self.is_vulnerable or self.damage_taken_this_cycle:
            return False
        
        self.health -= amount
        self.health = max(0, self.health)
        self.damage_taken_this_cycle = True
        
        # Visual feedback
        self.flash_timer = 0.5
        self._add_screen_shake(0.4, 15)
        self._play_sound('hurt')
        
        print(f"Boss took {amount} damage! Health: {self.health}/{self.max_health}")
        
        # Check for defeat
        if self.health <= 0:
            self._handle_defeat()
        
        return True

    def _handle_defeat(self):
        """Handle boss defeat"""
        print("Cubodeez has been defeated!")
        # Add defeat logic here (particle effects, score, etc.)
        # For now, just reset
        self.reset_to_spawn()

    def reset_to_spawn(self):
        """Reset boss to spawn position and state"""
        print("Resetting boss to spawn position")
        
        # Reset position and physics
        self.body.position = (self.spawn_x, self.spawn_y)
        self.body.velocity = (0, 0)
        
        # Reset state
        self.state = BossState.IDLE
        self.state_timer = 0.0
        self._set_grounded(True)

        self.is_vulnerable = False
        self.vulnerability_timer = 0.0
        self.damage_taken_this_cycle = False
        
        # Reset visual effects
        self.show_target_marker = False
        self.target_locked = False
        self.shake_timer = 0.0
        self.flash_timer = 0.0

    def _play_sound(self, sound_name):
        """Play a sound effect if available"""
        sound = self.sounds.get(sound_name)
        if sound:
            sound.play()

    def _add_screen_shake(self, duration, intensity):
        """Add screen shake effect"""
        self.shake_timer = max(self.shake_timer, duration)
        self.shake_intensity = max(self.shake_intensity, intensity)

    def update_state_machine(self, dt):
        """Update the main state machine"""
        self.state_timer += dt
        
        if self.state == BossState.IDLE:
            self._update_idle_state()
        elif self.state == BossState.PREPARING:
            self._update_preparing_state()
        elif self.state == BossState.JUMPING:
            self._update_jumping_state()
        elif self.state == BossState.LANDING:
            self._update_landing_state()
        elif self.state == BossState.VULNERABLE:
            self._update_vulnerable_state()

    def _update_idle_state(self):
        """Update idle state behavior"""
        # Show target marker
        if not self.show_target_marker:
            self.show_target_marker = True
            self.target_locked = False
        
        # Update marker position to follow player
        if not self.target_locked and self.target:
            self.marker_rect.center = self.target.rect.center
        
        # Check if ready to attack
        if self.state_timer >= self.action_cooldown and self.is_grounded:
            self.state = BossState.PREPARING
            self.state_timer = 0.0

    def _update_preparing_state(self):
        """Update preparation state"""
        preparation_time = 1.0
        
        # Visual charging effect
        progress = min(1.0, self.state_timer / preparation_time)
        red = 255
        green = int(255 * (1.0 - progress))
        self.eye_color = (red, green, 0)
        
        # Execute jump when ready
        if self.state_timer >= preparation_time:
            if self.calculate_jump_to_player() and self.execute_jump():
                # Jump successful - state changed in execute_jump()
                pass
            else:
                # Jump failed, return to idle
                self.state = BossState.IDLE
                self.state_timer = 0.0

    def _update_jumping_state(self):
        """Update jumping state"""
        # Change eye color while jumping
        self.eye_color = (255, 0, 0)  # Red eyes while jumping
        
        # Timeout check to prevent infinite jumping
        if self.state_timer > 5.0:
            print("Jump timeout - forcing landing")
            self._execute_landing(self.body.position)

    def _update_landing_state(self):
        """Update landing state"""
        landing_duration = 0.5
        
        if self.state_timer >= landing_duration:
            # Transition to vulnerable state
            self.state = BossState.VULNERABLE
            self.state_timer = 0.0
            self.vulnerability_timer = 0.0
            self.is_vulnerable = True
            self.damage_taken_this_cycle = False
            
            print("Boss is now vulnerable!")

    def _update_vulnerable_state(self):
        """Update vulnerable state"""
        self.vulnerability_timer += 1/60  # Assuming 60 FPS
        
        # Flashing effect
        flash_rate = 10  # Flashes per second
        self.flash_timer = (int(self.vulnerability_timer * flash_rate) % 2) * 0.1
        
        # End vulnerability
        if self.vulnerability_timer >= self.vulnerability_duration:
            self.is_vulnerable = False
            self.flash_timer = 0.0
            self.state = BossState.IDLE
            self.state_timer = 0.0
            self.eye_color = (255, 255, 0)  # Back to yellow
            
            print("Boss vulnerability ended")

    def update_visuals(self):
        """Update visual effects and sprite appearance"""
        # Start with base image
        self.image = self.base_image.copy()
        
        # Apply screen shake to position
        shake_x = 0
        shake_y = 0
        if self.shake_timer > 0:
            self.shake_timer -= 1/60
            shake_x = random.randint(-self.shake_intensity, self.shake_intensity)
            shake_y = random.randint(-self.shake_intensity, self.shake_intensity)
        
        # Update rect position
        self.rect.center = (
            self.body.position.x + shake_x,
            self.body.position.y + shake_y
        )
        
        # Draw eyes
        self._draw_eyes()
        
        # Apply vulnerability flash
        if self.flash_timer > 0:
            flash_surface = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
            flash_surface.fill((255, 255, 255, 100))
            self.image.blit(flash_surface, (0, 0))

    def _draw_eyes(self):
        """Draw the boss eyes with current color"""
        eye_size = self.size // 8
        eye_y = self.size // 3
        
        # Left eye
        pygame.draw.rect(self.image, self.eye_color,
                        (self.size // 4 - eye_size // 2, eye_y, eye_size, eye_size * 2))
        
        # Right eye  
        pygame.draw.rect(self.image, self.eye_color,
                        (3 * self.size // 4 - eye_size // 2, eye_y, eye_size, eye_size * 2))
        
        # Angry eyebrows
        eyebrow_thickness = max(2, self.size // 40)
        pygame.draw.line(self.image, (0, 0, 0),
                        (self.size // 4 - eye_size, eye_y - 5),
                        (self.size // 4 + eye_size, eye_y - 8),
                        eyebrow_thickness)
        pygame.draw.line(self.image, (0, 0, 0),
                        (3 * self.size // 4 - eye_size, eye_y - 8),
                        (3 * self.size // 4 + eye_size, eye_y - 5),
                        eyebrow_thickness)

    def update(self):
        """Main update method"""
        if not self.target:
            return
        
        dt = 1/60  # Assuming 60 FPS
        
        # Check for ground
        self._check_ground_below()
        
        # Update state machine
        self.update_state_machine(dt)
        
        # Update visuals
        self.update_visuals()
        
        # Check if fallen off map
        if self.body.position.y > getattr(self.physics, 'level_height', 2000) + 500:
            self.reset_to_spawn()

    def draw(self, screen, camera):
        """Draw the boss and related visual elements"""
        # Draw target marker if visible
        if self.show_target_marker:
            marker_screen_pos = camera.apply_rect(self.marker_rect)
            screen.blit(self.target_marker, marker_screen_pos)
        
        # Draw boss (sprite system handles this automatically, but included for completeness)
        boss_screen_pos = camera.apply_rect(self.rect)
        screen.blit(self.image, boss_screen_pos)
        
        # Debug information
        if self.debug_mode:
            self._draw_debug_info(screen, camera)

    def _draw_debug_info(self, screen, camera):
        """Draw debug information"""
        # Health bar
        health_bar_width = 100
        health_bar_height = 10
        health_ratio = self.health / self.max_health
        
        health_bar_pos = ((
            self.body.position.x - health_bar_width // 2,
            self.body.position.y - self.size // 2 - 20
        ))
        
        # Background
        pygame.draw.rect(screen, (255, 0, 0), 
                        (*health_bar_pos, health_bar_width, health_bar_height))
        # Health
        pygame.draw.rect(screen, (0, 255, 0),
                        (*health_bar_pos, int(health_bar_width * health_ratio), health_bar_height))
        
        # State text
        font = pygame.font.Font(None, 24)
        state_text = font.render(f"State: {self.state.value}", True, (255, 255, 255))
        state_pos = ((
            self.body.position.x - state_text.get_width() // 2,
            self.body.position.y - self.size // 2 - 40
        ))
        screen.blit(state_text, state_pos)

    # Properties for compatibility
    @property
    def vulnerable(self):
        return self.is_vulnerable
    
    @property
    def damaged_this_cycle(self):
        return self.damage_taken_this_cycle
    
    @damaged_this_cycle.setter 
    def damaged_this_cycle(self, value):
        self.damage_taken_this_cycle = value