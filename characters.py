import pygame, pymunk, os, math, random

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
		self._physics.space.add_collision_handler(
			self._physics.collision_types["ball"], 
			self._physics.collision_types["ground"]
		).post_solve = self._handle_collision
		
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
				"text": "Yeah, you heard me right brotha, this is a cave. I don't know what tomfoolery caused you to fall down here, but it ain't of any use now. You wanna get outta here? Just find the exit.",
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

class Cubodeez_The_Almighty_Cube(pygame.sprite.Sprite):
	"""The all-powerful square boss that jumps to squish the player"""
	
	def __init__(self, physics_manager, x, y, target_ball=None, size=150):
		"""Initialize the Cubodeez boss with improved mechanics"""
		super().__init__()
		
		# Reference to physics space and target
		self._physics = physics_manager
		self._target = target_ball
		
		# Store initial spawn position for reset
		self._spawn_x = x
		self._spawn_y = y
		
		# Boss stats
		self._name = "Cubodeez The Almighty Cube"
		self._size = size
		self._mass = 100.0  # Very heavy
		self._health = 100
		
		# Jump parameters (adjusted for space gravity)
		self._jump_force = 1200   # Base jump force
		self._max_jump_height = 800  # Maximum jump height
		self._max_jump_distance = 1000  # Maximum horizontal jump distance
		self._max_fall_speed = 1500  # Terminal velocity
		
		# Create physics body
		self._setup_physics()
		
		# Visual properties
		self._setup_visuals()
		
		# Target marker
		self._setup_target_marker()
						
		# AI state machine
		self._state = "idle"
		self._next_action_time = pygame.time.get_ticks() / 1000.0 + 1.0  # Seconds between actions
		self._target_x = 0
		self._target_y = 0
		self._jump_start_pos = (0, 0)  # Starting position of jump
		self._jumping = False
		self._grounded = True  # Start grounded by default (fixed)
		self._jump_time = 0  # Track time during jump
		self._jump_duration = 0  # Total duration of current jump
		self._descent_phase = False  # Whether boss is in descent phase of jump
		
		# Add landing settle timer for tracking landing stability
		self._landing_settle_timer = 0
		
		# Fall protection
		self._fall_threshold = 2000  # Max Y position before teleporting back
		self._fall_time = 0  # Time spent falling
		self._max_fall_time = 5.0  # Max time allowed to fall before reset
		self._falling_off_map = False
		
		# Trajectory prediction (only calculate once per jump for performance)
		self._predicted_landing_spot = None
		self._prediction_steps = 20  # Reduced for performance
		self._prediction_needs_update = True
		
		# Vulnerability state
		self._vulnerable = False
		self._flash_vulnerable = False
		self._vuln_timer = 0
		self._vuln_duration = 3.0  # Vulnerable for 3 seconds after landing
		self._damaged_this_cycle = False
		
		# Landing target area - defines where boss will accept collisions
		self._landing_target_x = 0
		self._landing_target_y = 0
		self._landing_target_radius = 300  # Increased from 200 to allow more flexibility
		
		# Sound effects
		self._load_sounds()
		
		# Animation properties
		self._shake_amount = 0
		self._shake_timer = 0
		self._shake_duration = 0.3
		self._eye_color = (255, 255, 0)  # Default yellow eyes
		
		# Track ground collision manually (reduced number of checks for performance)
		self._ground_check_distance = size * 3  # Increased distance to check for ground below
		self._ray_cast_points = []  # For debug visualization
		
		# Store last trajectory calculation time for performance
		self._last_prediction_time = 0
		self._prediction_interval = 0.5  # Only predict every half-second
		
		# Performance optimization
		self._update_counter = 0  # Used to stagger heavy operations
		
		# Debug flag for tracing state changes
		self._debug = True
		
		# Landing collisions
		self._landing_collision_only = False
		self._landing_collision_enabled = False
		
		# Jump timeout to prevent infinite jumps
		self._max_jump_time = 5.0  # Maximum 5 seconds per jump
		
		# Flag to track landing confirmation for improved cooldown timing
		self._landing_confirmation_needed = False
		
		print(f"Cubodeez initialized at ({x}, {y}) with size {size}")

	def _setup_physics(self):
		"""Set up the physics body and shape for the boss"""
		self._body = pymunk.Body(self._mass, float('inf'))  # Infinite moment to prevent rotation
		self._body.position = (self._spawn_x, self._spawn_y)
		
		# Create cube shape
		self._shape = pymunk.Poly.create_box(self._body, (self._size, self._size))
		self._shape.elasticity = 0.1  # Some bounce, but not too much
		self._shape.friction = 0.8  # Good friction for stability
		
		# Create custom collision type
		if "boss" not in self._physics.collision_types:
			self._physics.collision_types["boss"] = 5
		self._shape.collision_type = self._physics.collision_types["boss"]
		
		# Store reference to boss in the shape for collision callbacks
		self._shape.boss = self  # This allows us to access the boss from collision handlers
		
		# Enable collision with player and ground initially
		self._shape.filter = pymunk.ShapeFilter(
			categories=0x1,  # Boss category
			mask=0xFFFFFFFF  # Collide with everything initially
		)
		
		# Add to physics space
		self._physics.space.add(self._body, self._shape)
		
		# Set up collision handlers
		self.setup_collision_handlers()
	
	def _setup_visuals(self):
		"""Set up the visual appearance of the boss"""
		self._original_image = pygame.Surface((self._size, self._size), pygame.SRCALPHA)
		
		# Create cube appearance with gradient
		gradient_start = (120, 0, 0)  # Dark red
		gradient_end = (200, 0, 0)    # Bright red
		
		for y_offset in range(self._size):
			# Calculate gradient color based on position
			progress = y_offset / self._size
			current_color = [
				int(gradient_start[0] + (gradient_end[0] - gradient_start[0]) * progress),
				int(gradient_start[1] + (gradient_end[1] - gradient_start[1]) * progress),
				int(gradient_start[2] + (gradient_end[2] - gradient_start[2]) * progress)
			]
			# Draw a line of the gradient
			pygame.draw.line(self._original_image, current_color, (0, y_offset), (self._size, y_offset))
		
		# Add border
		pygame.draw.rect(self._original_image, (0, 0, 0), (0, 0, self._size, self._size), 3)
		
		# Add menacing eyes
		eye_size = self._size // 8
		eye_y = self._size // 3
		
		# Left eye
		pygame.draw.rect(self._original_image, (255, 255, 0), 
						(self._size // 4 - eye_size // 2, eye_y, eye_size, eye_size * 2))
		
		# Right eye
		pygame.draw.rect(self._original_image, (255, 255, 0), 
						(3 * self._size // 4 - eye_size // 2, eye_y, eye_size, eye_size * 2))
		
		# Draw angry eyebrows
		eyebrow_thickness = max(3, self._size // 30)
		pygame.draw.line(self._original_image, (0, 0, 0), 
						(self._size // 4 - eye_size, eye_y - 5), 
						(self._size // 4 + eye_size * 2, eye_y - 10), 
						eyebrow_thickness)
		pygame.draw.line(self._original_image, (0, 0, 0), 
						(3 * self._size // 4 - eye_size * 2, eye_y - 10), 
						(3 * self._size // 4 + eye_size, eye_y - 5), 
						eyebrow_thickness)
		
		# Final image preparation
		self._image = self._original_image.copy()
		self._rect = self._image.get_rect(center=(self._spawn_x, self._spawn_y))
	
	def _setup_target_marker(self):
		"""Set up the target marker visual"""
		self._target_marker = pygame.Surface((self._size, self._size//4), pygame.SRCALPHA)
		pygame.draw.rect(self._target_marker, (255, 0, 0, 128), (0, 0, self._size, self._size//4))
		pygame.draw.rect(self._target_marker, (255, 0, 0, 255), (0, 0, self._size, self._size//4), 2)
		
		# Draw "X" in the marker
		pygame.draw.line(self._target_marker, (255, 255, 255, 255), 
						(10, 10), (self._size-10, self._size//4-10), 3)
		pygame.draw.line(self._target_marker, (255, 255, 255, 255), 
						(10, self._size//4-10), (self._size-10, 10), 3)
						
		self._marker_rect = self._target_marker.get_rect()
		self._show_marker = False
		self._marker_locked = False
	
	def _load_sounds(self):
		"""Load the boss sound effects"""
		try:
			self._jump_sound = pygame.mixer.Sound(os.path.join("assets", "sounds", "boss_jump.mp3"))
			self._jump_sound.set_volume(0.7)
			self._land_sound = pygame.mixer.Sound(os.path.join("assets", "sounds", "boss_land.mp3"))
			self._land_sound.set_volume(0.8)
			self._hurt_sound = pygame.mixer.Sound(os.path.join("assets", "sounds", "boss_hurt.mp3"))
			if not self._hurt_sound:
				self._hurt_sound = self._land_sound  # Fallback
			self._squish_sound = pygame.mixer.Sound(os.path.join("assets", "sounds", "explosion.mp3"))
			self._squish_sound.set_volume(0.8)
		except:
			print("WARNING: Could not load boss sound effects")
			self._jump_sound = None
			self._land_sound = None
			self._hurt_sound = None
			self._squish_sound = None
	
	@property
	def body(self):
		return self._body
	
	@property
	def shape(self):
		return self._shape
	
	@property
	def size(self):
		return self._size
	
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
	def health(self):
		return self._health
	
	@health.setter
	def health(self, value):
		self._health = value
	
	@property
	def vulnerable(self):
		return self._vulnerable
	
	@property
	def physics(self):
		return self._physics
	
	@property
	def damaged_this_cycle(self):
		return self._damaged_this_cycle
	
	@damaged_this_cycle.setter
	def damaged_this_cycle(self, value):
		self._damaged_this_cycle = value
	
	def setup_collision_handlers(self):
		"""Set up collision handlers for boss-specific interactions"""
		# Boss vs Ball collision - for squishing the player
		boss_ball_handler = self._physics.space.add_collision_handler(
			self._physics.collision_types["boss"], 
			self._physics.collision_types.get("ball", 1)  # Default to 1 if not defined
		)
		boss_ball_handler.begin = self.on_hit_player
		
		# Add this print to verify the handler is registered
		print(f"Boss collision handler registered: boss type = {self._physics.collision_types['boss']}, ball type = {self._physics.collision_types.get('ball', 1)}")
		
		# Also add a pre-solve handler which might catch some collisions that begin doesn't
		boss_ball_handler.pre_solve = self.on_hit_player
		
		# Boss vs Ground collision - for landing detection
		if "ground" in self._physics.collision_types:
			boss_ground_handler = self._physics.space.add_collision_handler(
				self._physics.collision_types["boss"], 
				self._physics.collision_types["ground"]
			)
			boss_ground_handler.begin = self.on_hit_ground
		# Boss vs Launcher collision - destroy launchers on contact
		if "launcher" not in self._physics.collision_types:
			self._physics.collision_types["launcher"] = 6  # Assign a unique collision type for launchers
		boss_launcher_handler = self._physics.space.add_collision_handler(
			self._physics.collision_types["boss"],
			self._physics.collision_types["launcher"]
		)
		boss_launcher_handler.begin = self.on_hit_launcher

	def on_hit_player(self, arbiter, space, data):
		"""Kill the player any time they touch Cubodeez"""
		if not self._target:
			return True
			
		print("Boss-Player collision detected! Player will be squished.")
		
		# Kill the player immediately upon any contact
		if hasattr(self._target, 'death') and not (hasattr(self._target, 'is_dead') and self._target.is_dead):
			self._target.death()
			
			# Play squish sound
			if self._squish_sound:
				self._squish_sound.play()
			
			# Add visual/sound effects for impact
			self.shake_screen(0.5, 10)
		
		return True  # Always allow collision with player
	
	def on_hit_launcher(self, arbiter, space, data):
		"""Destroy launchers when the boss touches them"""
		for shape in arbiter.shapes:
			if hasattr(shape, "launcher") and shape.launcher:
				launcher = shape.launcher
				print(f"Boss destroyed launcher at position: {launcher.rect.center}")
				launcher.kill()  # Remove the launcher sprite
				self._physics.space.remove(launcher.body, launcher.shape)
		return True

	def on_hit_ground(self, arbiter, space, data):
		"""Handle collisions with ground - only when we're at the landing spot"""
		# Skip collisions when we're not in jumping state
		if not self._jumping:
			return True  # Allow normal ground collision when not jumping
		
		# Get shapes involved in the collision
		boss_shape = None
		ground_shape = None
		
		for shape in arbiter.shapes:
			if shape.collision_type == self._physics.collision_types["boss"]:
				boss_shape = shape
			elif shape.collision_type == self._physics.collision_types["ground"]:
				ground_shape = shape
		
		# Safety check - make sure we have both shapes
		if not boss_shape or not ground_shape:
			return True  # Default to allowing collision
		
		# Skip if we're not in landing phase yet
		if not self._landing_collision_enabled:
			print("Ignoring ground collision - not in landing phase yet")
			return False  # Ignore collision - phase through platform
		
		# Get the ground shape position (approximate from collision point)
		contact_point = arbiter.contact_point_set.points[0].point_b if arbiter.contact_point_set.points else None
		
		if not contact_point:
			# No contact point info, use boss position
			contact_x, contact_y = self._body.position
		else:
			contact_x, contact_y = contact_point
		
		# Calculate distance from contact point to target landing spot
		dx = contact_x - self._landing_target_x
		dy = contact_y - self._landing_target_y
		distance = math.sqrt(dx*dx + dy*dy)
		
		# Modified: Land if close to target OR we've been in descent phase for a while
		# This ensures the boss will eventually land even if not close to the target
		if distance <= self._landing_target_radius or (self._descent_phase and self._jump_time > 2.0):
			# If falling (positive y velocity), handle landing
			if self._body.velocity.y > 0:
				print(f"Landing at contact point: distance={distance:.1f}")
				self.handle_landing(contact_x, contact_y - self._size/2)
				return True  # Allow the collision
		else:
			print(f"Ignoring collision - too far from landing target ({distance:.1f} > {self._landing_target_radius})")
			return False  # Ignore collision - phase through this platform
		
		# Default to allowing collision
		return True
	
	def take_damage(self, amount=20):
		"""Take damage when vulnerable"""
		if self._vulnerable and not self._damaged_this_cycle:
			self._health -= amount
			self._health = max(0, self._health)
			self._damaged_this_cycle = True
			
			# Visual feedback
			self.shake_screen(0.5, 15)
			if self._hurt_sound:
				self._hurt_sound.play()
				
			print(f"Cubodeez took {amount} damage! Health: {self._health}")
			return True
		return False
	
	def reset_position(self):
		"""Reset Cubodeez to spawn position if he falls off the map"""
		print("Cubodeez fell off the map! Resetting position...")
		
		# Reset position to spawn point
		self._body.position = (self._spawn_x, self._spawn_y)
		self._body.velocity = (0, 0)
		
		# Reset state
		self._jumping = False
		self._grounded = True
		self._falling_off_map = False
		self._fall_time = 0
		self._state = "idle"
		self._next_action_time = pygame.time.get_ticks() / 1000.0 + 1.0  # Wait a bit before next action
		
		# Hide marker
		self._show_marker = False
		self._marker_locked = False
		
		# Update rect
		self._rect.center = self._body.position
		
		# Re-enable normal collisions
		self.enable_ground_collisions()
		self._landing_collision_enabled = False
		self._landing_collision_only = False
	
	def check_ground_below(self):
		"""Manually check for ground below using ray casts (improved for reliability)"""
		# Skip ground check if we're in a phase where we should ignore ground
		if self._jumping and not self._landing_collision_enabled:
			return self._grounded, None
			
		# Get current position
		x, y = self._body.position
		box_half_size = self._size / 2
		
		# Check multiple points along the bottom with better coverage
		check_points = [
			(x, y + box_half_size),                   # Center bottom
			(x - box_half_size * 0.7, y + box_half_size),  # Left bottom
			(x + box_half_size * 0.7, y + box_half_size)   # Right bottom
		]
		
		# Clear previous rays
		self._ray_cast_points = []
		
		# Check each point for ground
		for check_x, check_y in check_points:
			# If we're high above the ground, use deeper scanning
			if self._body.velocity.y > 0 or not self._grounded:  # If falling or not grounded
				# Cast a deeper ray when falling
				ray_distance = 500  # Longer ray for falling
				for dist in range(0, ray_distance, 10):  # Smaller steps for better precision
					test_y = check_y + dist
					
					# Store ray point for debug visualization
					self._ray_cast_points.append((check_x, test_y))
					
					if self.check_point_collision(check_x, test_y):
						# Found ground at this position
						if self._jumping and self._body.velocity.y > 0 and self._landing_collision_enabled:
							# Check if this ground is near our landing target
							dx = check_x - self._landing_target_x
							dy = test_y - self._landing_target_y
							distance = math.sqrt(dx*dx + dy*dy)
							
							# Only land if we're close to the targeted landing spot
							if distance <= self._landing_target_radius:
								print(f"Ground detected below boss at ({check_x}, {test_y})")
								self.handle_landing(x, test_y - box_half_size)
								return True, test_y - box_half_size
							else:
								# Ignore ground that's not near our landing target
								print(f"Ignoring ground - not near landing target ({distance:.1f} > {self._landing_target_radius})")
								continue
						elif not self._jumping:
							# Just make the boss grounded if we found ground below and we're not jumping
							self._grounded = True
							return True, test_y - box_half_size
			else:
				# When already grounded, just do a quick check
				if self.check_point_collision(check_x, check_y + 10):
					return True, None
		
		# No ground found - only reset grounded if we're not jumping
		if self._grounded and not self._jumping and self._body.velocity.y > 0:
			# Only unground if we're falling
			self._grounded = False
			print("Boss is no longer grounded - falling")
		
		return self._grounded, None  # Return current grounded state
	
	def check_point_collision(self, x, y):
		"""Check if a point collides with any ground shape (optimized)"""
		# Skip collision if we're in a jump phase and not ready to land
		if self._jumping and not self._landing_collision_enabled:
			return False
			
		# Use a query to check for ground collision
		query_info = self._physics.space.point_query_nearest(
			(x, y), 
			20,  # Increased radius for better detection
			pymunk.ShapeFilter(mask=self._physics.collision_types.get("ground", 1))
		)
		
		if query_info and query_info.distance <= 0:
			# If we're jumping, only accept ground that's near our landing target
			if self._jumping and self._landing_collision_enabled:
				# Calculate distance to landing target
				dx = x - self._landing_target_x
				dy = y - self._landing_target_y
				distance = math.sqrt(dx*dx + dy*dy)
				
				# Only accept ground near our landing target
				if distance <= self._landing_target_radius:
					return True
				else:
					return False
			else:
				# When not jumping, accept all ground
				return True
		
		# Fallback: Check if we're at the bottom of the level
		if hasattr(self._physics, 'level_height') and y >= self._physics.level_height - 50:
			return True
		
		return False
	
	def check_target_has_ground(self, x, y):
		"""Check if the target position has ground underneath it (optimized)"""
		# Use larger steps for better performance
		for dist in range(0, 500, 20):  # Increased depth check
			check_y = y + dist
			
			# For this check, we need to ignore the landing target check
			# Get any ground at all
			query_info = self._physics.space.point_query_nearest(
				(x, check_y), 
				20,  # Radius for detection
				pymunk.ShapeFilter(mask=self._physics.collision_types.get("ground", 1))
			)
			
			if query_info and query_info.distance <= 0:
				return True, check_y
		
		# Fallback: Check if we're at the bottom of the level
		if hasattr(self._physics, 'level_height') and y + 500 >= self._physics.level_height - 50:
			return True, self._physics.level_height - 50
		
		return False, None
	
	def handle_landing(self, x, y):
		"""Handle landing after a jump - ensure we complete the full jump animation"""
		if not self._jumping:
			return
			
		print(f"Boss landing at position: ({x}, {y})")
			
		# Transition to grounded state
		self._grounded = True
		self._jumping = False
		self._descent_phase = False
		
		# FIXED: Instead of teleporting, just stop horizontal movement
		# and slow vertical movement to simulate landing
		current_vx, current_vy = self._body.velocity
		self._body.velocity = (0, min(current_vy, 100))  # Maintain a small downward velocity
		
		# Enable full collisions with ground
		self.enable_ground_collisions()
		self._landing_collision_enabled = False
		self._landing_collision_only = False
		
		# Play landing sound
		if self._land_sound:
			self._land_sound.play()
		
		# Reset jump parameters
		self._jump_time = 0
		
		# Check if player is directly under the boss at landing
		if self._target:
			# Simple AABB collision check
			boss_rect = pygame.Rect(self._body.position.x - self._size/2, 
								self._body.position.y - self._size/2, 
								self._size, self._size)
			player_rect = self._target.rect
			
			if boss_rect.colliderect(player_rect):
				# Player is being squished during landing
				if hasattr(self._target, 'death') and not (hasattr(self._target, 'is_dead') and self._target.is_dead):
					print("Player squished during landing transition!")
					self._target.death()
					if self._squish_sound:
						self._squish_sound.play()
		
		# IMPROVED: Apply a stronger screen shake on landing
		self.shake_screen(0.6, 30)  # Longer duration, higher intensity for dramatic effect
		
		# Enter vulnerable state after landing
		self._vulnerable = True
		self._vuln_timer = 0
		self._flash_vulnerable = True
		self._damaged_this_cycle = False
		
		# FIXED: Reset the state but don't enter cooldown yet - we'll check when fully settled
		self._state = "landing"  # New intermediate state
		self._landing_settle_timer = 0  # Timer to track how long we've been settled
		
		# Hide marker
		self._show_marker = False
		self._marker_locked = False
		
		print("Cubodeez landed! Waiting to settle before cooldown...")

	def disable_all_collisions_except_player(self):
		"""
		Disable collisions with everything except the player - allows boss to phase through
		platforms during jump but still squish the player
		"""
		# Set collision filter to only collide with player/ball
		ball_category = self._physics.collision_types.get("ball", 1)
		
		# Make sure we're using the right mask
		self._shape.filter = pymunk.ShapeFilter(
			categories=0x1,  # Boss category
			mask=ball_category  # Only collide with ball
		)
		
		# Verify mask value with print
		print(f"Boss collision filter set to only collide with player: mask={self._shape.filter.mask}")
		
		# Track that we're in phase-through mode
		self._landing_collision_enabled = False
		self._landing_collision_only = False
		print("Boss is now phasing through all platforms (player collision only)")
	
	def enable_landing_spot_collision(self):
		"""
		Enable collision with ground at the landing spot but not with other platforms in between.
		This is used when we're close to the landing phase.
		"""
		# Set collision filter to allow collisions with ground and player
		ground_category = self._physics.collision_types.get("ground", 1)
		ball_category = self._physics.collision_types.get("ball", 1)
		self._shape.filter = pymunk.ShapeFilter(
			categories=0x1,  # Boss category
			mask=ground_category | ball_category  # Collide with both ground and ball
		)
		
		# The actual filtering will be done in the collision handlers based on distance to landing target
		
		# Track that we're now enabling landing collision
		self._landing_collision_enabled = True
		self._landing_collision_only = True
		print(f"Boss is now checking for landing collisions near target ({self._landing_target_x}, {self._landing_target_y})")
	
	def disable_ground_collisions(self):
		"""Disable collisions with ground but keep player collisions"""
		self.disable_all_collisions_except_player()
	
	def enable_ground_collisions(self):
		"""Enable collisions with both ground and player"""
		# Set collision filter to collide with ground and player
		ground_category = self._physics.collision_types.get("ground", 1)
		ball_category = self._physics.collision_types.get("ball", 1)
		self._shape.filter = pymunk.ShapeFilter(
			categories=0x1,  # Boss category
			mask=ground_category | ball_category  # Collide with both ground and ball
		)
		
		# Reset landing collision flags
		self._landing_collision_enabled = True
		self._landing_collision_only = False
		print("Boss collisions fully enabled")
	
	def enable_all_collisions(self):
		"""Enable all collisions"""
		self._shape.filter = pymunk.ShapeFilter(
			categories=0x1,  # Boss category
			mask=pymunk.ShapeFilter.ALL_MASKS  # Collide with everything
		)
		
		# Reset landing collision flags
		self._landing_collision_enabled = True
		self._landing_collision_only = False
	
	def shake_screen(self, duration, intensity):
		"""Set screen shake values - actual shaking applied in update"""
		self._shake_timer = duration
		self._shake_amount = intensity
	
	def check_player_squish(self):
		"""Simplified check - player dies on any contact with Cubodeez"""
		if not self._target or not hasattr(self._target, 'rect'):
			return False
		
		# Skip if player is already dead
		if hasattr(self._target, 'is_dead') and self._target.is_dead:
			return False
			
		# Get boss bounding box
		boss_left = self._body.position.x - self._size/2
		boss_right = self._body.position.x + self._size/2
		boss_top = self._body.position.y - self._size/2
		boss_bottom = self._body.position.y + self._size/2
		
		# Get player position
		player_x, player_y = self._target.rect.center
		player_radius = getattr(self._target, 'radius', 20)
		
		# Check if player circle intersects boss box
		closest_x = max(boss_left, min(player_x, boss_right))
		closest_y = max(boss_top, min(player_y, boss_bottom))
		
		dist_x = player_x - closest_x
		dist_y = player_y - closest_y
		distance = math.sqrt(dist_x**2 + dist_y**2)
		
		# Player dies if they're touching the boss at all
		if distance < player_radius:
			print("Player squished by direct collision! Distance:", distance)
			return True
		
		return False
	
	def check_if_falling_off_map(self):
		"""Check if Cubodeez is falling off the map and should be reset"""
		# Check if we're falling too far
		current_y = self._body.position.y
		
		# Check if we're below the maximum allowed height
		height_exceeded = False
		if hasattr(self._physics, 'level_height'):
			# If we know the level height, use it
			height_exceeded = current_y > self._physics.level_height + 500
		else:
			# Otherwise use a default threshold
			height_exceeded = current_y > self._fall_threshold
		
		# Check if we've been falling for too long
		if self._body.velocity.y > 100 and not self._grounded:
			self._fall_time += 1/60  # Increment fall time
			
			# If we've been falling too long, consider it falling off the map
			if self._fall_time > self._max_fall_time:
				return True
		else:
			# Reset fall time if not falling
			self._fall_time = 0
		
		return height_exceeded
	
	def find_alternate_target(self):
		"""Find an alternate target position that has ground underneath"""
		# Start at current target position
		start_x = self._target_x
		start_y = self._target_y
		
		# Try positions to the left and right
		for offset in [0, -200, 200, -400, 400, -600, 600]:
			test_x = start_x + offset
			
			# Check if there's ground at this position
			has_ground, ground_y = self.check_target_has_ground(test_x, start_y)
			
			if has_ground:
				# Found a valid position, update target
				self._target_x = test_x
				self._target_y = ground_y - self._size // 2
				self._landing_target_x = test_x
				self._landing_target_y = ground_y - self._size // 2
				print(f"Found alternate target at ({self._target_x}, {self._target_y})")
				return True
		
		# If we couldn't find a good target, use the boss spawn point
		print("Couldn't find valid target, falling back to spawn area")
		self._target_x = self._spawn_x
		self._target_y = self._spawn_y
		self._landing_target_x = self._spawn_x
		self._landing_target_y = self._spawn_y
		return False
	
	def calculate_jump_target(self):
		"""Calculate where to jump to hit the player"""
		if not self._target:
			return
			
		# Get current positions
		boss_pos = self._body.position
		player_pos = self._target.body.position
		
		# Target directly where the player is now (no prediction)
		self._target_x = player_pos.x
		self._target_y = player_pos.y
		
		# ADDED: Make sure landing target is explicitly set to the same position
		self._landing_target_x = self._target_x
		self._landing_target_y = self._target_y
		
		# Store jump start position
		self._jump_start_pos = (boss_pos.x, boss_pos.y)
	
	def jump_to_target(self):
		"""Execute a jump to the target position with more accurate trajectory calculation"""
		if not self._grounded or self._jumping:
			return False
				
		# Calculate jump parameters
		start_x, start_y = self._body.position
		dx = self._target_x - start_x
		dy = self._target_y - start_y
		
		# Calculate horizontal distance and cap it if needed
		distance = abs(dx)
		if distance > self._max_jump_distance:
			# Scale back the jump if too far
			direction = 1 if dx > 0 else -1
			dx = direction * self._max_jump_distance
			self._target_x = start_x + dx
			distance = self._max_jump_distance
		
		# Get space gravity (magnitude)
		gravity = abs(self._physics.space.gravity.y)
		
		# IMPROVED: Calculate time to target based on distance - ensure it's long enough for a visible arc
		time_to_target = max(1.8, math.sqrt(2 * distance / (gravity * 0.5)))
		time_to_target = min(3.0, max(1.8, time_to_target))  # Constrain between 1.8 and 3.0 seconds
		
		# Calculate velocity components
		velocity_x = dx / time_to_target
		
		# IMPROVED: Calculate vertical velocity for a more pronounced arc
		# We want a higher jump for visual appeal
		# Calculate minimum height to clear obstacles
		min_jump_height = max(300, abs(dy) + 200)  # At least 300px or higher than target + 200px
		
		# Calculate vertical velocity needed for the arc
		# Make sure the jump is high enough regardless of target position
		velocity_y = -math.sqrt(2 * gravity * min_jump_height)
		
		# Limit maximum upward velocity to prevent extreme jumps
		velocity_y = max(velocity_y, -1200)
		
		print(f"Jump velocity: ({velocity_x}, {velocity_y}), time_to_target: {time_to_target:.2f} seconds")
		print(f"Estimated jump height: {min_jump_height} pixels")
		
		# Apply the jump impulse
		self._body.velocity = (velocity_x, velocity_y)
		
		# Set jumping flags
		self._jumping = True
		self._grounded = False
		self._jump_time = 0
		self._jump_duration = time_to_target
		
		# Play jump sound
		if self._jump_sound:
			self._jump_sound.play()
		
		return True
	
	def update_visual_effects(self):
		"""Update visual effects like screen shake and animations"""
		# Update screen shake
		if self._shake_timer > 0:
			self._shake_timer -= 1/60  # Assume 60 FPS
			
			# Apply shake to visual position only (not physics)
			shake_offset_x = random.randint(-self._shake_amount, self._shake_amount)
			shake_offset_y = random.randint(-self._shake_amount, self._shake_amount)
			
			# Create new image with shake offset
			self._image = self._original_image.copy()
			self._rect = self._image.get_rect(center=(
				self._body.position.x + shake_offset_x,
				self._body.position.y + shake_offset_y
			))
		else:
			# Normal rendering without shake
			self._image = self._original_image.copy()
			self._rect = self._image.get_rect(center=self._body.position)
		
		# Update eyes based on current color
		eye_size = self._size // 8
		eye_y = self._size // 3
		
		# Handle vulnerability flashing
		if self._vulnerable and self._flash_vulnerable:
			# Flash white/yellow during vulnerability
			eye_color = (255, 255, 255)  # White flash
			
			# Also flash the entire body
			flash_overlay = pygame.Surface((self._size, self._size), pygame.SRCALPHA)
			flash_overlay.fill((255, 255, 255, 100))  # Semi-transparent white
			self._image.blit(flash_overlay, (0, 0))
		else:
			# Normal eye color
			eye_color = self._eye_color
		
		# Draw eyes with current color
		pygame.draw.rect(self._image, eye_color, 
						 (self._size // 4 - eye_size // 2, eye_y, eye_size, eye_size * 2))
		pygame.draw.rect(self._image, eye_color, 
						 (3 * self._size // 4 - eye_size // 2, eye_y, eye_size, eye_size * 2))
	
	def update(self):
		"""Update boss state and behavior"""
		# Skip if no target is set
		if not self._target:
			return
			
		# Check for falling off map and reset if needed
		if self.check_if_falling_off_map():
			self.reset_position()
			return
		
		# First check for player squishing
		if self.check_player_squish():
			# Kill the player if not already dead
			if hasattr(self._target, 'death') and not (hasattr(self._target, 'is_dead') and self._target.is_dead):
				print("Direct squish detection in update method!")
				self._target.death()
				if self._squish_sound:
					self._squish_sound.play()
			
		# Add direct collision check with player for better detection
		if self._jumping and self._body.velocity.y > 200 and self._target:
			# Simple AABB collision check
			boss_rect = self._rect
			player_rect = self._target.rect
			
			if boss_rect.colliderect(player_rect):
				# Direct collision detection
				print("Direct collision detected between boss and player!")
				
				# Kill the player if not already dead
				if hasattr(self._target, 'death') and not (hasattr(self._target, 'is_dead') and self._target.is_dead):
					print("Directly squishing player from update method")
					self._target.death()
					if self._squish_sound:
						self._squish_sound.play()
			
		# Update collision mode based on jump state
		if self._jumping:
			if self._body.velocity.y > 0 and not self._descent_phase:
				# Entering descent phase, enable landing spot collision
				self._descent_phase = True
				
				# Starting to fall down - enable landing spot collision immediately
				self.enable_landing_spot_collision()
				print("Entering descent phase - enabling landing collision detection")
		
		# Check for ground below (except when we're phasing through platforms)
		if not self._jumping or self._landing_collision_enabled:
			self.check_ground_below()
		
		# Update rect to match physics body
		self._rect.center = self._body.position
		
		# Update target marker
		if self._show_marker:
			if not self._marker_locked and self._target:
				# Track player until jump starts
				self._marker_rect.midbottom = (self._target.rect.centerx, self._target.rect.centery)
			# Otherwise marker stays where it was locked
			
		# Limit fall speed
		if self._body.velocity.y > self._max_fall_speed:
			self._body.velocity = (self._body.velocity.x, self._max_fall_speed)
		
		# State machine for boss behavior
		current_time = pygame.time.get_ticks() / 1000.0  # Current time in seconds
		
		# Update vulnerability state
		if self._vulnerable:
			self._vuln_timer += 1/60
			
			# Flash effect (alternate every few frames)
			self._flash_vulnerable = (int(self._vuln_timer * 15) % 2 == 0)
			
			# End vulnerability after duration
			if self._vuln_timer >= self._vuln_duration:
				self._vulnerable = False
				self._flash_vulnerable = False
		
		# Handle jumping state
		if self._jumping:
			self._jump_time += 1/60  # Assume 60 FPS
			
			# IMPROVED: Handle potential jump timeout more gracefully
			if self._jump_time > self._max_jump_time:
				print("Jump timeout - gracefully landing")
				# Don't force landing immediately - just make sure we're in descent phase
				# and moving downward with reasonable velocity
				if not self._descent_phase:
					self._descent_phase = True
					self.enable_landing_spot_collision()
				
				# If we're not moving down, give a gentle push
				if self._body.velocity.y < 100:
					current_vx = self._body.velocity.x
					self._body.velocity = (current_vx, 300)  # Gentle downward velocity
			
			# Update eyes to be red during jump
			self._eye_color = (255, 0, 0)
			
			# When reaching descent phase (falling down), enable ground collisions
			if self._body.velocity.y > 0 and not self._descent_phase:
				self._descent_phase = True
				print("Cubodeez entering descent phase")
				
				# Enable landing detection immediately when starting to fall
				self.enable_landing_spot_collision()
				print("Enabling landing collision detection on descent")
		else:
			# Normal yellow eyes when not jumping
			self._eye_color = (255, 255, 0)
		
		# Handle different AI states
		if self._state == "idle":
			self._handle_idle_state(current_time)
		elif self._state == "preparing":
			self._handle_preparing_state(current_time)
		elif self._state == "jumping":
			self._handle_jumping_state()
		elif self._state == "landing":
			self._handle_landing_state(current_time)
		elif self._state == "recovering":
			self._handle_recovering_state(current_time)
		
		# Update visual effects
		self.update_visual_effects()
		
		# Increment update counter
		self._update_counter += 1
		
		# Debug log every 60 frames
		if self._debug and self._update_counter % 60 == 0:
			print(f"Boss state: {self._state}, grounded: {self._grounded}, position: {self._body.position}, velocity: {self._body.velocity}")
	
	def _handle_idle_state(self, current_time):
		"""Handle boss behavior in idle state"""
		# In idle state, Cubodeez waits and prepares to jump
		
		# Start showing target marker
		self._show_marker = True
		self._marker_locked = False
		
		# Check if it's time for next action - FIXED: Added extra check to force state transition
		if (current_time > self._next_action_time and self._grounded) or (current_time > self._next_action_time + 3.0):
			# Prepare to jump at the player
			self._state = "preparing"
			self._next_action_time = current_time + 1.0  # Short preparation time
			
			print(f"Cubodeez preparing to jump at player")
	
	def _handle_preparing_state(self, current_time):
		"""Handle boss behavior in preparing state"""
		# In preparing state, Cubodeez glows briefly before jumping
		
		# Eyes start to glow red during preparation
		glow_progress = min(1.0, (current_time - (self._next_action_time - 1.0)) / 1.0)
		r = int(255)
		g = int((1.0 - glow_progress) * 255)
		b = int(0)
		self._eye_color = (r, g, b)
		
		# Check if preparation time is over
		if current_time > self._next_action_time:
			# Calculate target position (where the player is NOW)
			self.calculate_jump_target()
			
			# Check if the target has ground underneath it
			has_ground, ground_y = self.check_target_has_ground(self._target_x, self._target_y)
			if has_ground:
				# Update target y to be at ground level
				self._target_y = ground_y - self._size // 2
				self._landing_target_y = ground_y - self._size // 2
				self._landing_target_x = self._target_x
			else:
				# No ground at target, find another position
				self.find_alternate_target()
			
			# Lock the marker to the target position
			self._marker_locked = True
			self._marker_rect.midbottom = (self._target_x, self._target_y)
			
			# Disable ground collisions for jump - ensure we phase through platforms
			self.disable_all_collisions_except_player()
			
			# Execute the jump!
			success = self.jump_to_target()
			if success:
				self._state = "jumping"
				self._descent_phase = False
				print("Cubodeez jumping at player!")
			else:
				# If jump failed, go back to idle
				self._state = "idle"
				self._next_action_time = current_time + 0.5  # Short delay before trying again
				print("Cubodeez couldn't jump to target - recalculating...")
	
	def _handle_jumping_state(self):
		"""Handle boss behavior in jumping state"""
		# In jumping state, Cubodeez is airborne
		
		# If we're in descent phase, check how close we are to the landing spot
		if self._descent_phase and not self._landing_collision_enabled:
			# Distance to landing target
			dist_to_target = ((self._body.position.x - self._landing_target_x)**2 + 
							(self._body.position.y - self._landing_target_y)**2)**0.5
			
			# Enable landing collision when we're close to the target
			if dist_to_target < 300:
				self.enable_landing_spot_collision()
				print(f"Now close to landing target ({dist_to_target:.1f} units away) - enabling landing detection")
	
	def _handle_landing_state(self, current_time):
		"""Handle boss behavior in landing state"""
		# ADDED: Special landing state to wait until fully settled
		# Check if we're fully settled on the ground
		if self._grounded:
			# Check if y velocity is close to zero (settled)
			if abs(self._body.velocity.y) < 10:
				self._landing_settle_timer += 1/60  # Increment settle timer
				
				# Once we've been settled for a short time, transition to recovering
				if self._landing_settle_timer >= 0.2:  # 0.2 seconds of being settled
					print(f"Boss completely settled (y-velocity: {self._body.velocity.y}), entering cooldown phase")
					self._state = "recovering"
					self._next_action_time = current_time + self._vuln_duration
					
					# Add another screen shake for good measure
					self.shake_screen(0.3, 15)
			else:
				# If still moving, reset the settle timer
				self._landing_settle_timer = 0
				
			# Debug output to track settling
			if self._debug and self._update_counter % 10 == 0:
				print(f"Settling... y-velocity: {self._body.velocity.y}, timer: {self._landing_settle_timer:.2f}")
	
	def _handle_recovering_state(self, current_time):
		"""Handle boss behavior in recovering state"""
		# In recovering state, Cubodeez is vulnerable
		
		# Just wait until next_action_time
		if current_time > self._next_action_time:
			self._state = "idle"
			self._next_action_time = current_time + 1.0  # Time until next action
			print("Cubodeez returning to idle state")
	
	def draw(self, screen, camera):
		"""Draw boss with target marker"""
		# Draw target marker if active
		if self._show_marker:
			# Apply camera transform to marker position
			marker_rect = camera.apply_rect(self._marker_rect)
			screen.blit(self._target_marker, marker_rect)
			
		# Draw landing target visualization if in debug mode
		if self._jumping and self._debug:
			# Create a temporary rectangle at the landing target position
			landing_rect = pygame.Rect(0, 0, 10, 10)
			landing_rect.center = (self._landing_target_x, self._landing_target_y)
			
			# Apply camera transform to the rectangle
			transformed_rect = camera.apply_rect(landing_rect)
			landing_center = transformed_rect.center
			
			# Draw target circle - use a fixed size for simplicity
			pygame.draw.circle(screen, (0, 255, 0), landing_center, 20, 2)
			
			# Draw small rect at exact landing point
			pygame.draw.rect(screen, (0, 255, 0), transformed_rect)