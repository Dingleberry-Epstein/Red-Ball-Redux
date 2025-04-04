import pygame, os, pymunk
from constants import *

pygame.init()


pygame.joystick.init()

# Check if a joystick is connected
if pygame.joystick.get_count() > 0:
	joystick = pygame.joystick.Joystick(0)
	joystick.init()
else:
	joystick = None  # No controller connected

class Camera:
	# Camera class that follows a target entity and handles viewport calculations"""
	def __init__(self, width, height):

		self.viewport = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
		self.width = width
		self.height = height
		self.locked = False  # Add a lock state for the camera
		self.offset_x = 0
		self.offset_y = 0
	
	def apply(self, obj):
		# Apply camera offset to an entity or rect.

		if isinstance(obj, pygame.Rect):
			return obj.move(self.offset_x, self.offset_y)
		return obj.rect.move(self.offset_x, self.offset_y)

	def apply_rect(self, rect):
	   # Apply camera offset to a rectangle

		return rect.move(self.offset_x, self.offset_y)
	
	def update(self, target):
		# Move the camera to follow a target entity

		# If camera is locked (during death sequence), don't update position
		if self.locked:
			return
		
		# Calculate the offset to center the target on screen
		self.offset_x = SCREEN_WIDTH // 2 - target.rect.centerx
		self.offset_y = SCREEN_HEIGHT // 2 - target.rect.centery
		
		# Clamp camera to level boundaries
		self.offset_x = min(0, max(-(self.width - SCREEN_WIDTH), self.offset_x))
		self.offset_y = min(0, max(-(self.height - SCREEN_HEIGHT), self.offset_y))
		
		# Update viewport for other calculations
		self.viewport = pygame.Rect(-self.offset_x, -self.offset_y, self.width, self.height)

class CameraAwareGroup(pygame.sprite.Group):
	"""A sprite group that automatically applies camera transformations."""
	def __init__(self, camera):
		super().__init__()
		self.camera = camera

	def draw(self, surface):
		"""Override draw to apply camera offsets."""
		for sprite in self.sprites():
			offset_rect = sprite.rect.move(self.camera.offset_x, self.camera.offset_y)
			surface.blit(sprite.image, offset_rect)

class Button:
	# Interactive button class for UI elements
	def __init__(self, x, y, width, height, text):
		# Initialize a button with position and text
		"""
		Args:
			x (int): X position
			y (int): Y position
			width (int): Button width
			height (int): Button height
			text (str): Button text
		"""
		self.rect = pygame.Rect(x, y, width, height)
		self.default_color = GRAY
		self.hover_color = LIGHT_GRAY
		self.clicked = False
		self.hovered = False
		self.text = text
		self.hover_sound = pygame.mixer.Sound(os.path.join("assets", "sounds", "HoverSound.mp3"))
		self.select_sound = pygame.mixer.Sound(os.path.join("assets", "sounds", "SelectSound.mp3"))
		self.hover_sound_played = False
		self.click_sound_played = False

	def draw(self, surface, font, text_color=(0, 0, 0)):
		# Draw the button on a surface
		"""
		Args:
			surface (pygame.Surface): Surface to draw on
			font (pygame.font.Font): Font for text rendering
			text_color (tuple): RGB color for text
		"""
		# Use hover color if hovered, otherwise default color
		color = self.hover_color if self.hovered else self.default_color
		
		# Draw button rectangle
		pygame.draw.rect(surface, color, self.rect)
		
		# Render and center text
		text_surface = font.render(self.text, True, text_color)
		text_rect = text_surface.get_rect(center=self.rect.center)
		surface.blit(text_surface, text_rect)

	def handle_event(self, event):
		# Handle mouse events for the button
		"""
		Args:
			event (pygame.event.Event): Pygame event to process
			
		Returns:
			bool: True if button was clicked, False otherwise
		"""
		if event.type == pygame.MOUSEMOTION:
			# Check for hover state
			pos = pygame.mouse.get_pos()
			self.hovered = self.rect.collidepoint(pos)
			
			# Play hover sound once when first hovering
			if self.hovered and not self.hover_sound_played:
				self.hover_sound.play()
				self.hover_sound_played = True
			elif not self.hovered:
				self.hover_sound_played = False
				
		elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
			# Check for click state
			pos = pygame.mouse.get_pos()
			is_clicked = self.rect.collidepoint(pos)
			
			# Play select sound once when clicked
			if is_clicked and not self.click_sound_played:
				self.select_sound.play()
				self.click_sound_played = True
				self.clicked = True
			elif not is_clicked:
				self.click_sound_played = False
				
		elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
			was_clicked = self.clicked
			self.clicked = False
			return was_clicked and self.rect.collidepoint(pygame.mouse.get_pos())
			
		return False

class SceneManager:
    """Handles scene transitions and effects with improved fade functionality."""

    @staticmethod
    def fade_in(screen, render_func, image=None, duration=1.0, background_color=(0, 0, 0)):
        """Fade in a scene on the screen, optionally with an image."""
        clock = pygame.time.Clock()
        alpha = 0

        # Prepare image if provided
        scaled_image = None  # Initialize to None
        image_rect = None  # Initialize to None

        if image is not None and hasattr(image, 'get_width') and hasattr(image, 'get_height'):
            # Scale down if too large
            if image.get_width() > 800 or image.get_height() > 600:
                scale_factor = 3
                scaled_image = pygame.transform.smoothscale(image, (image.get_width() // scale_factor, image.get_height() // scale_factor))
            else:
                scaled_image = image

            image_rect = scaled_image.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))

        # Calculate alpha increment per frame (60 FPS)
        alpha_increment = 255 / (duration * 60)

        # Fade in loop
        skip_fade = False
        while alpha < 255 and not skip_fade:
            alpha += alpha_increment
            if alpha > 255:
                alpha = 255

            # Render the scene
            screen.fill(background_color)
            render_func()

            # Apply fade
            fade_surface = pygame.Surface((screen.get_width(), screen.get_height()))
            fade_surface.fill(background_color)
            fade_surface.set_alpha(int(255 - alpha))  # Reverse alpha for fade-in
            screen.blit(fade_surface, (0, 0))

            # Draw image if provided
            if scaled_image is not None and image_rect is not None:
                temp_image = scaled_image.copy()
                temp_image.set_alpha(int(alpha))
                screen.blit(temp_image, image_rect)

            pygame.display.flip()
            clock.tick(60)

            # Check for key press to skip
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    skip_fade = True

        # Ensure final frame is drawn
        screen.fill(background_color)
        render_func()
        if scaled_image is not None and image_rect is not None:
            screen.blit(scaled_image, image_rect)
        pygame.display.flip()
        return True

    @staticmethod
    def fade_out(screen, render_func, image=None, duration=1.0, background_color=(0, 0, 0)):
        """Fade out a scene from the screen, optionally with an image."""
        clock = pygame.time.Clock()
        alpha = 255

        # Prepare image if provided
        scaled_image = None  # Initialize to None
        image_rect = None  # Initialize to None

        if image is not None and hasattr(image, 'get_width') and hasattr(image, 'get_height'):
            # Scale down if too large
            if image.get_width() > 800 or image.get_height() > 600:
                scale_factor = 3
                scaled_image = pygame.transform.smoothscale(image, (image.get_width() // scale_factor, image.get_height() // scale_factor))
            else:
                scaled_image = image

            image_rect = scaled_image.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))

        # Calculate alpha decrement per frame (60 FPS)
        alpha_decrement = 255 / (duration * 60)

        # Fade out loop
        skip_fade = False
        while alpha > 0 and not skip_fade:
            alpha -= alpha_decrement
            if alpha < 0:
                alpha = 0

            # Render the scene
            screen.fill(background_color)
            render_func()

            # Apply fade
            fade_surface = pygame.Surface((screen.get_width(), screen.get_height()))
            fade_surface.fill(background_color)
            fade_surface.set_alpha(int(255 - alpha))
            screen.blit(fade_surface, (0, 0))

            # Draw image if provided
            if scaled_image is not None and image_rect is not None:
                temp_image = scaled_image.copy()
                temp_image.set_alpha(int(alpha))
                screen.blit(temp_image, image_rect)

            pygame.display.flip()
            clock.tick(60)

            # Check for key press to skip
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    skip_fade = True

        # Ensure final frame is drawn
        screen.fill(background_color)
        render_func()
        pygame.display.flip()
        return True

    @staticmethod
    def fade_to_black(screen, render_func, duration=1.0):
        """Generic fade to black transition that works without a specific image."""
        fade_surface = pygame.Surface((screen.get_width(), screen.get_height()))
        fade_surface.fill((0, 0, 0))
        clock = pygame.time.Clock()

        skip_fade = False
        for alpha in range(0, 256, 4):  # Use step of 4 for smooth fade
            if skip_fade:
                break

            # Render the content that should be visible
            render_func()

            # Apply fading overlay
            fade_surface.set_alpha(alpha)
            screen.blit(fade_surface, (0, 0))
            pygame.display.flip()
            clock.tick(60)

            # Check for key press to skip
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    skip_fade = True

        # Ensure we end with a black screen
        screen.fill((0, 0, 0))
        pygame.display.flip()
        return True

    @staticmethod
    def fade_from_black(screen, render_func, duration=1.0):
        """Generic fade from black that accepts a rendering function."""
        fade_surface = pygame.Surface((screen.get_width(), screen.get_height()))
        fade_surface.fill((0, 0, 0))
        clock = pygame.time.Clock()

        skip_fade = False
        for alpha in range(255, -1, -4):  # Use step of 4 for smooth fade
            if skip_fade:
                break

            # Render the content that should be visible
            render_func()

            # Apply fading overlay
            fade_surface.set_alpha(alpha)
            screen.blit(fade_surface, (0, 0))
            pygame.display.flip()
            clock.tick(60)

            # Check for key press to skip
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    skip_fade = True

        # Ensure we render one final frame without the fade
        render_func()
        pygame.display.flip()
        return True

class PhysicsManager:
    """Physics manager with improved collision detection for switches"""

    def __init__(self):
        # Create the Pymunk space
        self.space = pymunk.Space()
        self.space.gravity = (0, 980)  # Gravity

        # Expanded collision types
        self.collision_types = {
            "ball": 1,
            "ground": 2,
            "switch": 3
        }

        # Ground detection - we'll use a separate collision handler for this
        self.player_grounded = False

        # Set up collision handler for ground detection
        ground_handler = self.space.add_collision_handler(
            self.collision_types["ball"], self.collision_types["ground"]
        )
        ground_handler.begin = self._on_ground_begin
        ground_handler.separate = self._on_ground_separate
        ground_handler.pre_solve = self._on_ground_pre_solve
        
        # Set up collision handler for switches
        switch_handler = self.space.add_collision_handler(
            self.collision_types["ball"], self.collision_types["switch"]
        )
        switch_handler.begin = self._on_switch_begin
        switch_handler.separate = self._on_switch_separate

    def _on_ground_begin(self, arbiter, space, data):
        """Simple ground detection - just sets a flag"""
        # Check if contact is more vertical than horizontal
        n = arbiter.contact_point_set.normal
        if n.y < -0.7:  # If normal is pointing mostly upward
            self.player_grounded = True
        return True  # Always let normal physics handle the collision

    def _on_ground_pre_solve(self, arbiter, space, data):
        """Keep updating grounded status during continuous contact"""
        n = arbiter.contact_point_set.normal
        if n.y < -0.7:  # If normal is pointing mostly upward
            self.player_grounded = True
        return True

    def _on_ground_separate(self, arbiter, space, data):
        """Simple ground detection - just clears a flag"""
        self.player_grounded = False
        return True  # Always let normal physics handle the collision
        
    def _on_switch_begin(self, arbiter, space, data):
        """Handle collision with switch - no physical collision effect"""
        return True  # Let physics handle the collision normally
        
    def _on_switch_separate(self, arbiter, space, data):
        """Handle separation from switch"""
        return True  # Let physics handle the separation normally

    def is_grounded(self):
        """Return whether the player is on the ground"""
        return self.player_grounded
        
    def check_collision(self, shape1, shape2):
        """Check if two shapes are colliding"""
        # Create a contact set to test collision
        for s1 in self.space.shapes:
            if s1 == shape1:
                for s2 in self.space.shapes:
                    if s2 == shape2:
                        return self.space.shape_query(s1, pymunk.Transform.identity)
        return False

    def create_box(self, x, y, width, height, friction=0.9, is_static=True, collision_type=None):
        """Create a box with customizable properties"""
        body = pymunk.Body(body_type=pymunk.Body.STATIC if is_static else pymunk.Body.DYNAMIC)
        body.position = (x + width / 2, y + height / 2)

        shape = pymunk.Poly.create_box(body, (width, height))
        shape.elasticity = 0.0
        shape.friction = friction
        
        # Set collision type - use ground by default or specified type
        if collision_type == "switch":
            shape.collision_type = self.collision_types["switch"]
        else:
            shape.collision_type = self.collision_types["ground"]

        self.space.add(body, shape)
        return body, shape

    def create_poly(self, vertices, friction=0.9):
        """Create a static polygon with high friction"""
        if len(vertices) < 3:
            print(f"Error: Cannot create polygon with less than 3 vertices")
            return None, None

        body = pymunk.Body(body_type=pymunk.Body.STATIC)

        # Calculate center for body position
        avg_x = sum(v[0] for v in vertices) / len(vertices)
        avg_y = sum(v[1] for v in vertices) / len(vertices)
        body.position = (avg_x, avg_y)

        # Convert to local coordinates
        local_verts = [(v[0] - avg_x, v[1] - avg_y) for v in vertices]

        shape = pymunk.Poly(body, local_verts)
        shape.elasticity = 0.0
        shape.friction = friction
        shape.collision_type = self.collision_types["ground"]

        self.space.add(body, shape)
        return body, shape

    def create_segment(self, p1, p2, thickness=1, friction=0.9):
        """Create a static line segment with high friction"""
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        shape = pymunk.Segment(body, p1, p2, thickness)
        shape.elasticity = 0.0
        shape.friction = friction
        shape.collision_type = self.collision_types["ground"]

        self.space.add(body, shape)
        return body, shape

    def step(self, dt=1 / 60.0):
        """Update physics simulation"""
        self.space.step(dt)

    def clear(self):
        """Remove all physics objects"""
        for body in list(self.space.bodies):
            self.space.remove(body)

        for shape in list(self.space.shapes):
            self.space.remove(shape)

class ParallaxBackground:
    """Class that manages multiple background layers with parallax effect"""
    
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.layers = []  # Will store background layer information
        
    def add_layer(self, image_path, parallax_factor):
        """Add a background layer with a specific parallax factor
        
        Args:
            image_path: Path to the background image
            parallax_factor: Float between 0 and 1, where:
                             0 = stationary
                             1 = moves at the same speed as the camera
                             Values in between create the parallax effect
        """
        try:
            # Load and prepare the image
            image = pygame.image.load(image_path).convert_alpha()
            
            # Scale the image to be slightly larger than the screen to allow movement
            scale_factor = max(
                self.screen_width * 2 / image.get_width(),
                self.screen_height * 3 / image.get_height()
            )
            
            scaled_width = int(image.get_width() * scale_factor)
            scaled_height = int(image.get_height() * scale_factor)
            
            scaled_image = pygame.transform.scale(image, (scaled_width, scaled_height))
            
            # Add to layers list
            self.layers.append({
                'image': scaled_image,
                'factor': parallax_factor,
                'width': scaled_width,
                'height': scaled_height,
                'pos_x': 0,
                'pos_y': 0
            })
            
            return True
        except Exception as e:
            print(f"Error loading background layer: {e}")
            return False
    
    def add_color_layer(self, color, parallax_factor=0.0):
        """Add a solid color background layer
        
        Args:
            color: RGB tuple for the background color
            parallax_factor: Usually 0 for static background
        """
        # Create a solid color surface
        surface = pygame.Surface((self.screen_width, self.screen_height))
        surface.fill(color)
        
        # Add to layers list
        self.layers.append({
            'image': surface,
            'factor': parallax_factor,
            'width': self.screen_width,
            'height': self.screen_height,
            'pos_x': 0,
            'pos_y': 0
        })
        
        return True
            
    def update(self, camera_x, camera_y):
        """Update the position of all background layers based on camera position
        
        Args:
            camera_x: The x-coordinate of the camera in world space
            camera_y: The y-coordinate of the camera in world space
        """
        for layer in self.layers:
            # Calculate how much this layer should move based on its parallax factor
            # Invert the movement to create parallax effect (background moves opposite to camera)
            layer['pos_x'] = -camera_x * layer['factor']
            layer['pos_y'] = -camera_y * layer['factor']
            
            # If the layer is larger than the screen, we need to wrap it
            if layer['width'] > self.screen_width or layer['height'] > self.screen_height:
                # Keep the background position within the dimensions of the image
                # for proper wrapping (only needed for layers that need to tile)
                layer['pos_x'] = layer['pos_x'] % layer['width']
                layer['pos_y'] = layer['pos_y'] % layer['height']
            
    def draw(self, screen):
        """Draw all background layers to the screen
        
        Args:
            screen: Pygame surface to draw on
        """
        for layer in self.layers:
            # For a static full-screen color layer
            if layer['width'] == self.screen_width and layer['height'] == self.screen_height:
                screen.blit(layer['image'], (0, 0))
                continue
                
            # For layers that need to tile to cover the screen
            pos_x = int(layer['pos_x'])
            pos_y = int(layer['pos_y'])
            
            # Calculate how many tiles we need in each direction
            tiles_x = (self.screen_width // layer['width']) + 2
            tiles_y = (self.screen_height // layer['height']) + 2
            
            # Draw the tiles
            for i in range(-1, tiles_x):
                for j in range(-1, tiles_y):
                    x = pos_x + (i * layer['width'])
                    y = pos_y + (j * layer['height'])
                    screen.blit(layer['image'], (x, y))