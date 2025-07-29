import pygame, os, pymunk, pygame_gui, random, math, time, threading, queue, json, base64
from constants import *
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

pygame.init()

pygame.joystick.init()

# Check if a joystick is connected
if pygame.joystick.get_count() > 0:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
else:
    joystick = None  # No controller connected

class Camera:
    """Camera class that follows a target entity and handles viewport calculations"""
    def __init__(self, width, height):
        self._viewport = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self._width = width
        self._height = height
        self._locked = False  # Add a lock state for the camera
        self._offset_x = 0
        self._offset_y = 0
    
    @property
    def viewport(self):
        """Get the camera viewport"""
        return self._viewport
        
    @property
    def width(self):
        """Get the camera width"""
        return self._width
        
    @width.setter
    def width(self, value):
        """Set the camera width"""
        self._width = value
        
    @property
    def height(self):
        """Get the camera height"""
        return self._height
        
    @height.setter
    def height(self, value):
        """Set the camera height"""
        self._height = value
        
    @property
    def locked(self):
        """Get the camera lock state"""
        return self._locked
        
    @locked.setter
    def locked(self, value):
        """Set the camera lock state"""
        self._locked = value
        
    @property
    def offset_x(self):
        """Get the camera x offset"""
        return self._offset_x
        
    @offset_x.setter
    def offset_x(self, value):
        """Set the camera x offset"""
        self._offset_x = value
        
    @property
    def offset_y(self):
        """Get the camera y offset"""
        return self._offset_y
        
    @offset_y.setter
    def offset_y(self, value):
        """Set the camera y offset"""
        self._offset_y = value
    
    def apply(self, obj):
        """Apply camera offset to an entity or rect."""
        if isinstance(obj, pygame.Rect):
            return obj.move(self._offset_x, self._offset_y)
        return obj.rect.move(self._offset_x, self._offset_y)

    def apply_rect(self, rect):
        """Apply camera offset to a rectangle"""
        return rect.move(self._offset_x, self._offset_y)
    
    def center_on_point(self, x, y):
        """Center the camera on a specific point"""
        self._offset_x = self._viewport.width // 2 - x
        self._offset_y = self._viewport.height // 2 - y
        
        # Clamp to map boundaries
        self._offset_x = min(0, max(-(self._width - self._viewport.width), self._offset_x))
        self._offset_y = min(0, max(-(self._height - self._viewport.height), self._offset_y))

    def update(self, target):
        """Move the camera to follow a target entity"""
        # If camera is locked (during death sequence), don't update position
        if self._locked:
            return
        
        # Calculate the offset to center the target on screen
        self._offset_x = SCREEN_WIDTH // 2 - target.rect.centerx
        self._offset_y = SCREEN_HEIGHT // 2 - target.rect.centery
        
        # Clamp camera to level boundaries
        self._offset_x = min(0, max(-(self._width - SCREEN_WIDTH), self._offset_x))
        self._offset_y = min(0, max(-(self._height - SCREEN_HEIGHT), self._offset_y))
        
        # Update viewport for other calculations
        self._viewport = pygame.Rect(-self._offset_x, -self._offset_y, self._width, self._height)

class CameraAwareGroup(pygame.sprite.Group):
    """A sprite group that automatically applies camera transformations."""
    def __init__(self, camera):
        super().__init__()
        self._camera = camera

    @property
    def camera(self):
        """Get the camera"""
        return self._camera

    def draw(self, surface):
        """Override draw to apply camera offsets."""
        for sprite in self.sprites():
            offset_rect = sprite.rect.move(self._camera.offset_x, self._camera.offset_y)
            surface.blit(sprite.image, offset_rect)

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
    """Physics manager with improved collision detection for switches and squares"""

    def __init__(self):
        # Create the Pymunk space
        self._space = pymunk.Space()
        self._space.gravity = (0, 980)  # Gravity

        # Expanded collision types
        self._collision_types = {
            "ball": 1,
            "ground": 2,
            "switch": 3,
            "square": 4
        }

        # Ground detection - we'll use a separate collision handler for this
        self._player_grounded = False
        
        # Level dimensions for boundaries
        self._level_width = None
        self._level_height = None

        # Set up collision handler for ground detection using new Pymunk 7.1 API
        self._space.on_collision(
            self._collision_types["ball"], 
            self._collision_types["ground"],
            begin=self._on_ground_begin,
            separate=self._on_ground_separate,
            pre_solve=self._on_ground_pre_solve
        )
        
        # Set up collision handler for switches using new Pymunk 7.1 API
        self._space.on_collision(
            self._collision_types["ball"], 
            self._collision_types["switch"],
            begin=self._on_switch_begin,
            separate=self._on_switch_separate
        )
        
        # Set up collision handler for squares using new Pymunk 7.1 API
        self._space.on_collision(
            self._collision_types["ball"], 
            self._collision_types["square"],
            begin=self._on_square_begin,
            separate=self._on_square_separate,
            pre_solve=self._on_square_pre_solve
        )

    @property
    def space(self):
        """Get the pymunk space"""
        return self._space
        
    @property
    def collision_types(self):
        """Get the collision types dictionary"""
        return self._collision_types
        
    @property
    def player_grounded(self):
        """Get whether the player is grounded"""
        return self._player_grounded
        
    @property
    def level_width(self):
        """Get the level width"""
        return self._level_width
        
    @level_width.setter
    def level_width(self, value):
        """Set the level width"""
        self._level_width = value
        
    @property
    def level_height(self):
        """Get the level height"""
        return self._level_height
        
    @level_height.setter
    def level_height(self, value):
        """Set the level height"""
        self._level_height = value

    def _on_ground_begin(self, arbiter, space, data):
        """Simple ground detection - just sets a flag"""
        # Check if contact is more vertical than horizontal
        n = arbiter.contact_point_set.normal
        if n.y < -0.7:  # If normal is pointing mostly upward
            self._player_grounded = True
        # In Pymunk 7.1, we don't return a bool to control processing
        # Instead we use arbiter.process_collision property if needed
        # For normal collision processing, we just don't set it to False

    def _on_ground_pre_solve(self, arbiter, space, data):
        """Keep updating grounded status during continuous contact"""
        n = arbiter.contact_point_set.normal
        if n.y < -0.7:  # If normal is pointing mostly upward
            self._player_grounded = True
        # No return value needed in Pymunk 7.1

    def _on_ground_separate(self, arbiter, space, data):
        """Simple ground detection - just clears a flag"""
        self._player_grounded = False
        # No return value needed in Pymunk 7.1
        
    def _on_switch_begin(self, arbiter, space, data):
        """Handle collision with switch - no physical collision effect"""
        # Prevent physical collision by setting process_collision to False
        arbiter.process_collision = False
        # No return value needed in Pymunk 7.1
        
    def _on_switch_separate(self, arbiter, space, data):
        """Handle separation from switch"""
        # No return value needed in Pymunk 7.1
        pass
        
    def _on_square_begin(self, arbiter, space, data):
        """Handle collision with square - normal physical collision"""
        # Allow normal collision processing (this is the default)
        # arbiter.process_collision = True  # This is the default, so we don't need to set it
        # No return value needed in Pymunk 7.1
        
    def _on_square_pre_solve(self, arbiter, space, data):
        """Handle pre-solve for square collision"""
        # This can be used for custom collision response if needed
        # No return value needed in Pymunk 7.1
        pass
        
    def _on_square_separate(self, arbiter, space, data):
        """Handle separation from square"""
        # No return value needed in Pymunk 7.1
        pass

    def is_grounded(self):
        """Return whether the player is on the ground"""
        return self._player_grounded
        
    def check_collision(self, shape1, shape2):
        """Check if two shapes are colliding"""
        # Create a contact set to test collision
        for s1 in self._space.shapes:
            if s1 == shape1:
                for s2 in self._space.shapes:
                    if s2 == shape2:
                        return self._space.shape_query(s1, pymunk.Transform.identity())
        return False

    def create_box(self, x, y, width, height, friction=0.9, is_static=True, collision_type=None):
        """Create a box with customizable properties"""
        body = pymunk.Body(body_type=pymunk.Body.STATIC if is_static else pymunk.Body.DYNAMIC)
        body.position = (x + width / 2, y + height / 2)

        shape = pymunk.Poly.create_box(body, (width, height))
        shape.elasticity = 0.0
        shape.friction = friction
        
        # Set collision type based on parameter
        if collision_type == "switch":
            shape.collision_type = self._collision_types["switch"]
        elif collision_type == "square":
            shape.collision_type = self._collision_types["square"]
        else:
            # Default to ground
            shape.collision_type = self._collision_types["ground"]

        self._space.add(body, shape)
        return body, shape

    def create_poly(self, vertices, friction=0.9, collision_type="ground"):
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
        
        # Set collision type based on parameter
        if collision_type in self._collision_types:
            shape.collision_type = self._collision_types[collision_type]
        else:
            shape.collision_type = self._collision_types["ground"]

        self._space.add(body, shape)
        return body, shape

    def create_segment(self, p1, p2, thickness=1, friction=0.9, collision_type="ground"):
        """Create a static line segment with high friction"""
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        shape = pymunk.Segment(body, p1, p2, thickness)
        shape.elasticity = 0.0
        shape.friction = friction
        
        # Set collision type based on parameter
        if collision_type in self._collision_types:
            shape.collision_type = self._collision_types[collision_type]
        else:
            shape.collision_type = self._collision_types["ground"]

        self._space.add(body, shape)
        return body, shape

    def step(self, dt=0):
        """Update physics simulation with substeps for better collision detection"""
        clock = pygame.time.Clock()
        if clock.get_fps() > 0:
            dt = 1.0 / clock.get_fps()
        else:
            dt = 1.0/60.0
        # Using multiple substeps to catch fast collisions
        substeps = 4  # Increase for better accuracy but worse performance
        sub_dt = dt / substeps
        
        for i in range(substeps):
            self._space.step(sub_dt)

    def clear(self):
        """Remove all physics objects"""
        # In Pymunk 7.1, we need to convert to list since space.bodies/shapes now return KeysView
        for body in list(self._space.bodies):
            self._space.remove(body)

        for shape in list(self._space.shapes):
            self._space.remove(shape)

class ParallaxBackground:
    """Class that manages multiple background layers with parallax effect"""
    
    def __init__(self, screen_width, screen_height):
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._layers = []  # Will store background layer information
    
    @property
    def screen_width(self):
        """Get the screen width"""
        return self._screen_width
    
    @property
    def screen_height(self):
        """Get the screen height"""
        return self._screen_height
    
    @property
    def layers(self):
        """Get the background layers"""
        return self._layers
        
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
                self._screen_width * 2 / image.get_width(),
                self._screen_height * 3 / image.get_height()
            )
            
            scaled_width = int(image.get_width() * scale_factor)
            scaled_height = int(image.get_height() * scale_factor)
            
            scaled_image = pygame.transform.scale(image, (scaled_width, scaled_height))
            
            # Add to layers list
            self._layers.append({
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
        surface = pygame.Surface((self._screen_width, self._screen_height))
        surface.fill(color)
        
        # Add to layers list
        self._layers.append({
            'image': surface,
            'factor': parallax_factor,
            'width': self._screen_width,
            'height': self._screen_height,
            'pos_x': 0,
            'pos_y': 0
        })
        
        return True
    
    def add_surface(self, surface, parallax_factor=0.05):
        """Add an existing surface as a background layer
        
        Args:
            surface: The pygame surface to use as a background
            parallax_factor: How much the layer should move relative to the camera
        """
        self._layers.append({
            'image': surface,
            'factor': parallax_factor,
            'width': surface.get_width(),
            'height': surface.get_height(),
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
        for layer in self._layers:
            # Calculate how much this layer should move based on its parallax factor
            # Invert the movement to create parallax effect (background moves opposite to camera)
            layer['pos_x'] = -camera_x * layer['factor']
            layer['pos_y'] = -camera_y * layer['factor']
            
            # If the layer is larger than the screen, we need to wrap it
            if layer['width'] > self._screen_width or layer['height'] > self._screen_height:
                # Keep the background position within the dimensions of the image
                # for proper wrapping (only needed for layers that need to tile)
                layer['pos_x'] = layer['pos_x'] % layer['width']
                layer['pos_y'] = layer['pos_y'] % layer['height']
            
    def draw(self, screen):
        """Draw all background layers to the screen
        
        Args:
            screen: Pygame surface to draw on
        """
        for layer in self._layers:
            # For a static full-screen color layer
            if layer['width'] == self._screen_width and layer['height'] == self._screen_height:
                screen.blit(layer['image'], (0, 0))
                continue
                
            # For layers that need to tile to cover the screen
            pos_x = int(layer['pos_x'])
            pos_y = int(layer['pos_y'])
            
            # Calculate how many tiles we need in each direction
            tiles_x = (self._screen_width // layer['width']) + 2
            tiles_y = (self._screen_height // layer['height']) + 2
            
            # Draw the tiles
            for i in range(-1, tiles_x):
                for j in range(-1, tiles_y):
                    x = pos_x + (i * layer['width'])
                    y = pos_y + (j * layer['height'])
                    screen.blit(layer['image'], (x, y))

def load_button_images(button_name, unpressed_folder, pressed_folder):
    """Loads unpressed and pressed images for a button."""
    unpressed_path = os.path.join(unpressed_folder, f"{button_name}.png")
    pressed_path = os.path.join(pressed_folder, f"P{button_name}.png") # add 'P' to pressed button name.

    try:
        unpressed_image = pygame.image.load(unpressed_path).convert_alpha()
        pressed_image = pygame.image.load(pressed_path).convert_alpha()
        return unpressed_image, pressed_image
    except FileNotFoundError:
        print(f"Error: Could not find images for {button_name}")
        return None, None

def create_sprite_button(rect, manager):
    """Creates a Pygame-GUI button with minimal arguments."""
    button = pygame_gui.elements.UIButton(
        relative_rect=rect,
        text='',  # No text, just sprites
        manager=manager
    )
    return button

class SpatialGrid:
    """
    Spatial partitioning grid for efficient tile querying.
    Organizes game objects into a grid for fast spatial lookups.
    """
    def __init__(self, cell_size=128):
        """
        Initialize the spatial grid.
        
        Args:
            cell_size: Size of each grid cell (should be larger than typical tile size)
        """
        self._cell_size = cell_size
        self._grid = {}  # Dictionary mapping (grid_x, grid_y) to list of objects
    
    @property
    def cell_size(self):
        """Get the cell size"""
        return self._cell_size
    
    @property
    def grid(self):
        """Get the grid dictionary"""
        return self._grid
        
    def _get_cell_coords(self, x, y):
        """Convert world coordinates to grid cell coordinates."""
        grid_x = x // self._cell_size
        grid_y = y // self._cell_size
        return int(grid_x), int(grid_y)
        
    def insert(self, obj):
        """
        Insert an object into the spatial grid.
        
        Args:
            obj: Object with rect attribute (pygame.Rect)
        """
        # Get the grid cell for the object's position
        grid_x, grid_y = self._get_cell_coords(obj.rect.x, obj.rect.y)
        
        # Create the cell if it doesn't exist
        cell_key = (grid_x, grid_y)
        if cell_key not in self._grid:
            self._grid[cell_key] = []
            
        # Add the object to the cell
        self._grid[cell_key].append(obj)
        
        # Store grid position on the object for quick removal
        obj.grid_pos = cell_key
        
    def remove(self, obj):
        """
        Remove an object from the spatial grid.
        
        Args:
            obj: Object to remove
        """
        if hasattr(obj, 'grid_pos'):
            cell_key = obj.grid_pos
            if cell_key in self._grid and obj in self._grid[cell_key]:
                self._grid[cell_key].remove(obj)
                
    def update(self, obj):
        """
        Update an object's position in the grid.
        
        Args:
            obj: Object with rect attribute (pygame.Rect)
        """
        old_cell_key = getattr(obj, 'grid_pos', None)
        new_cell_key = self._get_cell_coords(obj.rect.x, obj.rect.y)
        
        # If the object has moved to a new cell
        if old_cell_key != new_cell_key:
            # Remove from old cell
            if old_cell_key and old_cell_key in self._grid and obj in self._grid[old_cell_key]:
                self._grid[old_cell_key].remove(obj)
                
            # Add to new cell
            if new_cell_key not in self._grid:
                self._grid[new_cell_key] = []
                
            self._grid[new_cell_key].append(obj)
            obj.grid_pos = new_cell_key
            
    def query_rect(self, rect, buffer=0):
        """
        Get all objects that could be in the given rectangle plus a buffer.
        
        Args:
            rect: pygame.Rect to query
            buffer: Optional buffer distance around the rect
        
        Returns:
            List of objects in the area
        """
        # Expand the rectangle by the buffer
        expanded_rect = rect.inflate(buffer * 2, buffer * 2)
        
        # Calculate grid cells covered by the expanded rectangle
        min_x, min_y = self._get_cell_coords(expanded_rect.left, expanded_rect.top)
        max_x, max_y = self._get_cell_coords(expanded_rect.right, expanded_rect.bottom)
        
        # Collect all objects in those cells
        result = []
        for grid_x in range(min_x, max_x + 1):
            for grid_y in range(min_y, max_y + 1):
                cell_key = (grid_x, grid_y)
                if cell_key in self._grid:
                    result.extend(self._grid[cell_key])
                    
        return result
    
    def query_point(self, x, y):
        """
        Get all objects in the cell containing the point.
        
        Args:
            x, y: World coordinates
        
        Returns:
            List of objects in the cell
        """
        cell_key = self._get_cell_coords(x, y)
        return self._grid.get(cell_key, [])

class MapSystem:
    """Interactive map system that can be opened/closed with a key for any level."""
    
    def __init__(self, game):
        """Initialize the map system.
        
        Args:
            game: Reference to the main game object
        """
        self._game = game
        self._is_open = False
        self._fading_in = False
        self._fading_out = False
        self._fade_alpha = 0
        self._fade_speed = 8  # Alpha change per frame
        
        # Map availability
        self._map_available = False
        self._current_level_index = None
        self._current_map_path = None
        
        # Flash message variables
        self._show_message = False
        self._message_timer = 0
        self._message_duration = 2.0  # Show message for 2 seconds
        
        # Load scroll asset
        self._load_scroll_asset()
        
        # Map navigation variables
        self._setup_map_navigation()
        
        # Load fonts
        self._load_fonts()
            
        # "You are here" text
        self._location_text = self._font.render("YOU ARE HERE", True, (255, 0, 0))
        self._location_text_rect = self._location_text.get_rect()
        
        # "No map available" message
        self._no_map_text = self._message_font.render("No map available!", True, (255, 0, 0))
        self._no_map_text_rect = self._no_map_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        
        # Player position indicator
        self._player_indicator_radius = 5
        self._player_indicator_color = (255, 0, 0)  # Bright red
        
        # Map surface
        self._map_image = None
        self._map_surface = None
    
    def _load_scroll_asset(self):
        """Load the scroll background asset"""
        try:
            self._scroll_image = pygame.image.load(os.path.join("assets", "sprites", "map", "scroll.png")).convert_alpha()
            
            # Scale scroll to fill the entire screen while maintaining aspect ratio of 62:30
            aspect_ratio = 62 / 30
            
            # Calculate dimensions to fill screen
            if SCREEN_WIDTH / SCREEN_HEIGHT > aspect_ratio:
                # Screen is wider than scroll aspect ratio, fill height
                scroll_height = SCREEN_HEIGHT * 0.95  # 95% of screen height
                scroll_width = scroll_height * aspect_ratio
            else:
                # Screen is taller than scroll aspect ratio, fill width
                scroll_width = SCREEN_WIDTH * 0.95  # 95% of screen width
                scroll_height = scroll_width / aspect_ratio
                
            # Scale scroll to calculated dimensions
            self._scroll_image = pygame.transform.scale(self._scroll_image, (int(scroll_width), int(scroll_height)))
            
            # Position the scroll in the center of the screen
            self._scroll_rect = self._scroll_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            
        except Exception as e:
            print(f"Error loading scroll image: {e}")
            # Create a placeholder scroll if the image can't be loaded
            self._create_fallback_scroll()
        
        # Calculate map display area within scroll based on the proportion 38:17 within 62:30
        self._calculate_map_display_area()
    
    def _create_fallback_scroll(self):
        """Create a fallback scroll image if loading fails"""
        aspect_ratio = 62 / 30
        if SCREEN_WIDTH / SCREEN_HEIGHT > aspect_ratio:
            scroll_height = SCREEN_HEIGHT * 0.95
            scroll_width = scroll_height * aspect_ratio
        else:
            scroll_width = SCREEN_WIDTH * 0.95
            scroll_height = scroll_width / aspect_ratio
            
        self._scroll_image = pygame.Surface((int(scroll_width), int(scroll_height)), pygame.SRCALPHA)
        pygame.draw.rect(self._scroll_image, (200, 180, 140), (0, 0, int(scroll_width), int(scroll_height)), 0, 20)
        pygame.draw.rect(self._scroll_image, (160, 120, 80), (0, 0, int(scroll_width), int(scroll_height)), 4, 20)
        self._scroll_rect = self._scroll_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
    
    def _calculate_map_display_area(self):
        """Calculate the area within the scroll that will display the map"""
        usable_ratio_x = 38 / 62  # Proportion of width that is usable
        usable_ratio_y = 17 / 30  # Proportion of height that is usable
        
        usable_width = self._scroll_rect.width * usable_ratio_x
        usable_height = self._scroll_rect.height * usable_ratio_y
        
        # Calculate the position to center the usable area within the scroll
        margin_x = (self._scroll_rect.width - usable_width) // 2
        margin_y = (self._scroll_rect.height - usable_height) // 2
        
        # Define the map display rectangle with vertical offset
        self._map_display_rect = pygame.Rect(
            self._scroll_rect.left + margin_x,
            self._scroll_rect.top + margin_y + 44,
            usable_width,
            usable_height
        )
    
    def _setup_map_navigation(self):
        """Set up map navigation variables"""
        self._map_view_rect = pygame.Rect(0, 0, self._map_display_rect.width, self._map_display_rect.height)
        self._drag_start = None
        self._dragging = False
        self._map_speed = 600  # Pixels per second for keyboard navigation
        
        # Zoom variables
        self._max_zoom = 0.7  # Default zoom level (matches previous value)
        self._min_zoom = 0.1  # Minimum zoom level, will be calculated based on map size
        self._current_zoom = self._max_zoom  # Start at max zoom
        self._zoom_step = 0.05  # Amount to change zoom per action
        self._zoom_duration = 0.2  # Seconds for zoom animation
        self._zoom_timer = 0
        self._zoom_start = self._current_zoom
        self._zoom_target = self._current_zoom
        self._zoom_center_x = 0  # Center point X for zooming
        self._zoom_center_y = 0  # Center point Y for zooming
        self._zooming = False
        
        # Store player position for centering
        self._player_x = 0
        self._player_y = 0
        self._level_width = 1
        self._level_height = 1
        
        # Flag to force centering on open
        self._should_center_on_player = True
    
    def _load_fonts(self):
        """Load fonts for the map system"""
        try:
            self._font = pygame.font.Font(os.path.join("assets", "Daydream.ttf"), 10)
            self._message_font = pygame.font.Font(os.path.join("assets", "Daydream.ttf"), 24)
        except:
            self._font = pygame.font.SysFont(None, 16)
            self._message_font = pygame.font.SysFont(None, 30)
    
    @property
    def is_open(self):
        """Check if the map is currently open"""
        return self._is_open
    
    @property
    def fading_in(self):
        """Check if the map is fading in"""
        return self._fading_in
    
    @property
    def fading_out(self):
        """Check if the map is fading out"""
        return self._fading_out
    
    @property
    def show_message(self):
        """Check if a message is currently being shown"""
        return self._show_message
    
    @show_message.setter
    def show_message(self, value):
        """Set whether to show a message"""
        self._show_message = value
    
    @property
    def show_no_map_message(self):
        """Alias for show_message - use this to display the 'no map' message"""
        return self._show_message
    
    @show_no_map_message.setter
    def show_no_map_message(self, value):
        """Set to show the 'no map' message"""
        if value:
            self.show_no_map_message = True
    
    def load_map_for_level(self, level_index):
        """Load the map for the specified level with robust error handling.
        
        Args:
            level_index: Index of the level to load the map for
        
        Returns:
            bool: True if map was loaded successfully, False otherwise
        """
        if self._current_level_index == level_index and self._map_available:
            # Already loaded this map
            return True
            
        self._current_level_index = level_index
        
        # Try different possible map paths
        possible_paths = [
            os.path.join("assets", "sprites", f"map{level_index + 1}.png"),
            os.path.join("assets", "sprites", f"level{level_index + 1}_map.png"),
            os.path.join("assets", "sprites", "map", f"map{level_index + 1}.png"),
            os.path.join("assets", "sprites", "map.png") if level_index == 0 else None  # Default map for level 1
        ]
        
        # Filter out None values
        possible_paths = [path for path in possible_paths if path]
        
        # Reset map state
        self._map_available = False
        self._map_image = None
        self._map_surface = None
        self._current_map_path = None
        
        # Try to load the map from any of the possible paths
        for path in possible_paths:
            try:
                if os.path.exists(path):
                    print(f"Attempting to load map from: {path}")
                    self._map_image = pygame.image.load(path).convert_alpha()
                    self._current_map_path = path
                    
                    # Verify the image is valid
                    if self._map_image.get_width() < 10 or self._map_image.get_height() < 10:
                        print(f"Map image too small: {self._map_image.get_width()}x{self._map_image.get_height()}")
                        continue
                    
                    print(f"Map loaded successfully from: {path}")
                    print(f"Map dimensions: {self._map_image.get_width()}x{self._map_image.get_height()}")
                    self._map_available = True
                    
                    # Calculate min zoom level to ensure map fills the display area
                    self.calculate_min_zoom()
                    
                    # Reset zoom to max level (most zoomed in)
                    self._current_zoom = self._max_zoom
                    self._zoom_start = self._max_zoom
                    self._zoom_target = self._max_zoom
                    
                    # Update the map surface with the initial zoom level
                    self.update_map_surface()
                    
                    # Force centering when a new map is loaded
                    self._should_center_on_player = True
                    
                    return True
            except Exception as e:
                print(f"Error loading map from {path}: {e}")
        
        # If we get here, no map was found
        print(f"No map found for level {level_index + 1}")
        return False
    
    def calculate_min_zoom(self):
        """Calculate the minimum zoom level based on map and display dimensions."""
        if not self._map_image:
            return
            
        # Calculate the zoom level that would make the map just fit the display area
        width_ratio = self._map_display_rect.width / self._map_image.get_width()
        height_ratio = self._map_display_rect.height / self._map_image.get_height()
        
        # Use the smaller ratio so entire map is visible
        fit_zoom = min(width_ratio, height_ratio)
        
        # Set min zoom, but don't go below an absolute minimum for visibility
        self._min_zoom = max(0.1, fit_zoom)
        
        print(f"Calculated min zoom: {self._min_zoom}")
    
    def update_map_surface(self):
        """Update the scaled map surface for efficient rendering with error handling."""
        if not self._map_image:
            self._map_surface = None
            return
            
        try:
            # Calculate scaled dimensions
            scaled_width = max(1, int(self._map_image.get_width() * self._current_zoom))
            scaled_height = max(1, int(self._map_image.get_height() * self._current_zoom))
            
            # Create the scaled surface
            self._map_surface = pygame.transform.smoothscale(self._map_image, (scaled_width, scaled_height))
            
            print(f"Created scaled map surface: {scaled_width}x{scaled_height}")
        except Exception as e:
            print(f"Error creating map surface: {e}")
            self._map_surface = None
            self._map_available = False
    
    def toggle(self):
        """Toggle the map open/closed state."""
        if not self._map_available and not self._show_message:
            # If no map is available, show a message
            self._show_message = True
            self._message_timer = 0
            return
            
        if self._is_open and not self._fading_out:
            # Start closing
            self._fading_out = True
            self._fading_in = False
        elif not self._is_open and not self._fading_in and self._map_available:
            # Start opening only if map is available
            # Set centering flag WHEN OPENING, not when closing
            self._should_center_on_player = True
            
            # Immediately call center_on_player to ensure it happens
            self.center_on_player(self._player_x, self._player_y, self._level_width, self._level_height)
            
            self._fading_in = True
            self._fading_out = False
            
            print("Map opening - centering on player")
    
    def update(self, dt):
        """Update map state, handling fade effects and navigation.
        
        Args:
            dt: Delta time in seconds
        """
        # Update message flash if shown
        if self._show_message:
            self._message_timer += dt
            if self._message_timer >= self._message_duration:
                self._show_message = False
                self._message_timer = 0
            return
            
        # Handle fading
        if self._fading_in:
            self._fade_alpha += self._fade_speed
            if self._fade_alpha >= 255:
                self._fade_alpha = 255
                self._fading_in = False
                self._is_open = True
        
        elif self._fading_out:
            self._fade_alpha -= self._fade_speed
            if self._fade_alpha <= 0:
                self._fade_alpha = 0
                self._fading_out = False
                self._is_open = False
        
        # If we still need to center during fade-in, do it again
        # This ensures centering happens even if player position changed during fade
        if self._should_center_on_player and self._fading_in and self._fade_alpha > 100:
            self.center_on_player(self._player_x, self._player_y, self._level_width, self._level_height)
            self._should_center_on_player = False
            print("Centered map on player during fade-in")
        
        # Handle zoom animation
        self._update_zoom_animation(dt)
        
        # Handle map navigation when open
        self._handle_map_navigation(dt)
    
    def _update_zoom_animation(self, dt):
        """Handle zoom animation"""
        if self._zooming and self._map_surface:
            self._zoom_timer += dt
            progress = min(1.0, self._zoom_timer / self._zoom_duration)
            
            # Interpolate between start and target zoom
            old_zoom = self._current_zoom
            self._current_zoom = self._zoom_start + (self._zoom_target - self._zoom_start) * progress
            
            if progress >= 1.0:
                self._zooming = False
                self._zoom_timer = 0
            
            # If zoom has changed enough, update the map surface
            if abs(old_zoom - self._current_zoom) > 0.001:
                # Save the center point before zooming
                center_x = self._map_view_rect.x + self._map_view_rect.width / 2
                center_y = self._map_view_rect.y + self._map_view_rect.height / 2
                
                # Get the relative position of the zoom center
                rel_x = self._zoom_center_x / old_zoom
                rel_y = self._zoom_center_y / old_zoom
                
                # Update map surface with new zoom
                old_width = self._map_surface.get_width()
                old_height = self._map_surface.get_height()
                self.update_map_surface()
                
                # Calculate new view position to maintain the center point
                scale_factor = self._current_zoom / old_zoom
                new_width = self._map_surface.get_width()
                new_height = self._map_surface.get_height()
                
                # Set new map view position to maintain center
                self._map_view_rect.x = int(center_x * scale_factor - self._map_view_rect.width / 2)
                self._map_view_rect.y = int(center_y * scale_factor - self._map_view_rect.height / 2)
                
                # Ensure the view stays within map boundaries
                self.clamp_map_view()
    
    def _handle_map_navigation(self, dt):
        """Handle keyboard navigation of the map"""
        if self._is_open and self._map_surface:
            # Keyboard navigation
            keys = pygame.key.get_pressed()
            move_amount = int(self._map_speed * dt)
            
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                self._map_view_rect.y = max(0, self._map_view_rect.y - move_amount)
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                max_y = self._map_surface.get_height() - self._map_view_rect.height
                self._map_view_rect.y = min(max_y, self._map_view_rect.y + move_amount)
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                self._map_view_rect.x = max(0, self._map_view_rect.x - move_amount)
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                max_x = self._map_surface.get_width() - self._map_view_rect.width
                self._map_view_rect.x = min(max_x, self._map_view_rect.x + move_amount)
    
    def clamp_map_view(self):
        """Ensure the map view stays within the map boundaries."""
        if not self._map_surface:
            return
            
        # Ensure the view isn't larger than the map
        self._map_view_rect.width = min(self._map_display_rect.width, self._map_surface.get_width())
        self._map_view_rect.height = min(self._map_display_rect.height, self._map_surface.get_height())
        
        # Ensure the view stays within map boundaries
        max_x = max(0, self._map_surface.get_width() - self._map_view_rect.width)
        max_y = max(0, self._map_surface.get_height() - self._map_view_rect.height)
        
        self._map_view_rect.x = max(0, min(max_x, self._map_view_rect.x))
        self._map_view_rect.y = max(0, min(max_y, self._map_view_rect.y))
    
    def set_zoom(self, zoom_level, center_x=None, center_y=None):
        """Set the zoom level with animation.
        
        Args:
            zoom_level: Target zoom level
            center_x: X coordinate of zoom center (in view space)
            center_y: Y coordinate of zoom center (in view space)
        """
        if not self._map_surface or self._zooming:
            return
            
        # Clamp zoom level to valid range
        zoom_level = max(self._min_zoom, min(self._max_zoom, zoom_level))
        
        # If zoom level is very close to current, just set it directly
        if abs(zoom_level - self._current_zoom) < 0.01:
            self._current_zoom = zoom_level
            return
            
        # Set up zoom animation
        self._zoom_start = self._current_zoom
        self._zoom_target = zoom_level
        self._zoom_timer = 0
        self._zooming = True
        
        # Use center of view if not specified
        if center_x is None:
            center_x = self._map_view_rect.width / 2
        if center_y is None:
            center_y = self._map_view_rect.height / 2
            
        self._zoom_center_x = center_x
        self._zoom_center_y = center_y
        
        print(f"Setting zoom from {self._zoom_start} to {self._zoom_target}")
    
    def zoom_in(self, amount=None):
        """Zoom in by the zoom step amount."""
        if amount is None:
            amount = self._zoom_step
        self.set_zoom(self._current_zoom + amount)
    
    def zoom_out(self, amount=None):
        """Zoom out by the zoom step amount."""
        if amount is None:
            amount = self._zoom_step
        self.set_zoom(self._current_zoom - amount)
    
    def handle_event(self, event):
        """Handle mouse events for map dragging and zooming.
        
        Args:
            event: Pygame event to process
            
        Returns:
            bool: True if the event was handled
        """
        if not self._is_open or not self._map_available:
            return False
        
        # Handle mouse wheel for zooming
        if event.type == pygame.MOUSEWHEEL:
            # Only zoom if mouse is over map area
            mouse_pos = pygame.mouse.get_pos()
            if self._map_display_rect.collidepoint(mouse_pos):
                # Calculate relative position within map view
                rel_x = mouse_pos[0] - self._map_display_rect.x
                rel_y = mouse_pos[1] - self._map_display_rect.y
                
                # Determine zoom direction (scroll up = zoom in, scroll down = zoom out)
                zoom_amount = self._zoom_step * event.y
                
                # Zoom in or out
                if zoom_amount > 0:  # Zoom in
                    if self._current_zoom < self._max_zoom:
                        self.set_zoom(min(self._max_zoom, self._current_zoom + zoom_amount), rel_x, rel_y)
                else:  # Zoom out
                    if self._current_zoom > self._min_zoom:
                        self.set_zoom(max(self._min_zoom, self._current_zoom + zoom_amount), rel_x, rel_y)
                
                return True
                
        # Handle keyboard zoom (+ and -)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:  # "+" key
                if self._current_zoom < self._max_zoom:
                    self.zoom_in()
                return True
            elif event.key == pygame.K_MINUS:  # "-" key
                if self._current_zoom > self._min_zoom:
                    self.zoom_out()
                return True
            
        # Handle mouse dragging
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Start dragging if mouse is inside map area
            if self._map_display_rect.collidepoint(event.pos):
                self._drag_start = event.pos
                self._dragging = True
                return True
                
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            # Stop dragging
            self._dragging = False
            self._drag_start = None
            return True
            
        elif event.type == pygame.MOUSEMOTION and self._dragging:
            # Calculate drag distance
            if self._drag_start:
                dx = self._drag_start[0] - event.pos[0]
                dy = self._drag_start[1] - event.pos[1]
                
                # Move map view
                self._map_view_rect.x = max(0, min(
                    self._map_surface.get_width() - self._map_view_rect.width,
                    self._map_view_rect.x + dx
                ))
                self._map_view_rect.y = max(0, min(
                    self._map_surface.get_height() - self._map_view_rect.height,
                    self._map_view_rect.y + dy
                ))
                
                # Update drag start position
                self._drag_start = event.pos
                return True
                
        return False
    
    def center_on_player(self, player_x, player_y, level_width, level_height):
        """Center the map view on the player's position.
        
        Args:
            player_x: Player's x position in world coordinates
            player_y: Player's y position in world coordinates
            level_width: Width of the current level
            level_height: Height of the current level
        """
        # Store these values for when the map opens
        self._player_x = player_x
        self._player_y = player_y
        self._level_width = level_width
        self._level_height = level_height
        
        if not self._map_surface:
            return
            
        # Calculate the ratio between map and level
        map_width = self._map_surface.get_width()
        map_height = self._map_surface.get_height()
        
        # Calculate player position on the scaled map
        x_ratio = map_width / max(1, level_width)  # Prevent division by zero
        y_ratio = map_height / max(1, level_height)  # Prevent division by zero
        
        map_player_x = int(player_x * x_ratio)
        map_player_y = int(player_y * y_ratio)
        
        # Center the view on the player
        # Calculate where the player should be in the view
        view_width = self._map_view_rect.width
        view_height = self._map_view_rect.height
        
        # Target position - center of view
        target_x = map_player_x - (view_width // 2)
        target_y = map_player_y - (view_height // 2)
        
        # Make sure the view stays within map boundaries
        max_x = max(0, map_width - view_width)
        max_y = max(0, map_height - view_height)
        
        self._map_view_rect.x = max(0, min(max_x, target_x))
        self._map_view_rect.y = max(0, min(max_y, target_y))
        
        print(f"Map centered at player position: {map_player_x}, {map_player_y}")
    
    def draw(self, screen, player_x, player_y, level_width, level_height):
        """Draw the map if it's open or transitioning.
        
        Args:
            screen: Pygame surface to draw on
            player_x: Player's x position in world coordinates
            player_y: Player's y position in world coordinates
            level_width: Width of the current level in pixels
            level_height: Height of the current level in pixels
        """
        # Update stored player position
        self._player_x = player_x
        self._player_y = player_y
        self._level_width = level_width
        self._level_height = level_height
        
        # Handle flash message display
        if self._show_message:
            self._draw_no_map_message(screen)
            return
            
        # Handle normal map display
        if self._fade_alpha <= 0 or not self._map_available or not self._map_surface:
            return
            
        # Create overlay for dimming the game screen
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, min(180, self._fade_alpha)))
        screen.blit(overlay, (0, 0))
        
        # Apply fade to scroll
        scroll_with_alpha = self._scroll_image.copy()
        scroll_with_alpha.set_alpha(self._fade_alpha)
        screen.blit(scroll_with_alpha, self._scroll_rect)
        
        # Draw map within scroll, with clipping
        if self._fade_alpha > 100 and self._map_surface:  # Only start drawing map content at certain opacity
            self._draw_map_content(screen)
    
    def _draw_no_map_message(self, screen):
        """Draw the 'no map available' message"""
        # Create a semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        screen.blit(overlay, (0, 0))
        
        # Draw the "No map available" message
        # Add a black outline effect
        outline_offsets = [(-2, -2), (-2, 0), (-2, 2), (0, -2), (0, 2), (2, -2), (2, 0), (2, 2)]
        # Render the outline in black
        outline_color = (0, 0, 0)  # Black color (Red=0, Green=0, Blue=0)
        outline_text = self._message_font.render("No map available!", True, outline_color)

        # Draw the black outline
        for offset in outline_offsets:
            offset_pos = (self._no_map_text_rect.x + offset[0], self._no_map_text_rect.y + offset[1])
            screen.blit(outline_text, offset_pos)

        # Draw the white text on top of the outline
        screen.blit(self._no_map_text, self._no_map_text_rect)
    
    def _draw_map_content(self, screen):
        """Draw the actual map content and player position"""
        # Set up clipping rect to keep map inside scroll
        original_clip = screen.get_clip()
        screen.set_clip(self._map_display_rect)
        
        # Ensure map view stays within bounds
        self.clamp_map_view()
        
        try:
            # Create and draw the visible portion of the map
            visible_map = self._map_surface.subsurface(self._map_view_rect)
            screen.blit(visible_map, self._map_display_rect)
            
            # Draw player position
            self._draw_player_position(screen)
            
        except (ValueError, pygame.error) as e:
            print(f"Error rendering map: {e}")
            # If there's an error, try to center on player again
            self.center_on_player(self._player_x, self._player_y, self._level_width, self._level_height)
        
        finally:
            # Reset clipping rectangle
            screen.set_clip(original_clip)
        
        # Draw instructions and zoom level if map is fully visible
        if self._fade_alpha > 200:
            self._draw_map_instructions(screen)
    
    def _draw_player_position(self, screen):
        """Draw the player position indicator on the map"""
        # Calculate player position accurately
        # Convert from level coordinates to map coordinates
        map_width = self._map_surface.get_width()
        map_height = self._map_surface.get_height()
        
        # Calculate the exact ratio for player position
        x_ratio = map_width / max(1, self._level_width)  # Prevent division by zero
        y_ratio = map_height / max(1, self._level_height)  # Prevent division by zero
        
        # Get player position on the full map
        exact_map_player_x = self._player_x * x_ratio
        exact_map_player_y = self._player_y * y_ratio
        
        # Adjust for the current view
        map_player_x = exact_map_player_x - self._map_view_rect.x
        map_player_y = exact_map_player_y - self._map_view_rect.y
        
        # Convert to screen coordinates
        screen_player_x = self._map_display_rect.x + map_player_x
        screen_player_y = self._map_display_rect.y + map_player_y
        
        # Draw player position indicator (only if player is in view)
        if (0 <= map_player_x <= self._map_display_rect.width and 
            0 <= map_player_y <= self._map_display_rect.height):
            
            # Draw "YOU ARE HERE" text above player indicator
            self._location_text_rect.midbottom = (screen_player_x, screen_player_y - 5)
            screen.blit(self._location_text, self._location_text_rect)
            
            # Draw player indicator (red dot)
            pygame.draw.circle(
                screen, 
                self._player_indicator_color, 
                (screen_player_x, screen_player_y), 
                self._player_indicator_radius
            )
            # Add a white outline for better visibility
            pygame.draw.circle(
                screen, 
                (255, 255, 255), 
                (screen_player_x, screen_player_y), 
                self._player_indicator_radius + 1, 
                1
            )
    
    def _draw_map_instructions(self, screen):
        """Draw instructions and zoom level indicator"""
        instructions = self._font.render(
            "WASD/Arrows to navigate - Click and drag - Scroll to zoom - M to close", 
            True, 
            (255, 255, 255)
        )
        instructions_rect = instructions.get_rect(
            midbottom=(
                self._scroll_rect.centerx, 
                self._scroll_rect.bottom - 15
            )
        )
        screen.blit(instructions, instructions_rect)
        
        # Draw zoom level indicator
        zoom_percent = int(self._current_zoom * 100 / self._max_zoom)
        zoom_text = self._font.render(
            f"Zoom: {zoom_percent}%", 
            True, 
            (50, 30, 10)
        )
        zoom_rect = zoom_text.get_rect(
            topright=(
                self._map_display_rect.right - 10,
                self._map_display_rect.top + 5
            )
        )
        screen.blit(zoom_text, zoom_rect)

class DialogueSystem:
    # This class already has good OOP structure, so we'll leave it as is to avoid
    # breaking any functionality. The DialogueSystem class is very complex, and
    # modifying its implementation could potentially introduce bugs.
    # The existing implementation follows OOP principles well.
    """A dialogue system that displays text in an RPG-style dialogue box with portraits"""
    
    def __init__(self, screen_width, screen_height, ui_manager=None, theme_path=None):
        """Initialize the dialogue system"""
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Create or use UI manager
        if ui_manager:
            self.ui_manager = ui_manager
        else:
            self.ui_manager = pygame_gui.UIManager(
                (screen_width, screen_height),
                theme_path if theme_path else os.path.join("assets", "theme.json")
            )
        
        # Dialogue box dimensions - make it larger for better visibility
        self.box_width = int(screen_width * 0.8)
        self.box_height = int(screen_height * 0.3)  # Increased height
        self.box_x = (screen_width - self.box_width) // 2
        self.box_y = screen_height - self.box_height - 20  # 20px margin from bottom
        
        # Text parameters
        self.text_margin = 20
        self.portrait_size = 84
        self.portrait_margin = 10
        self.text_color = pygame.Color(255, 255, 255)
        self.name_color = pygame.Color(255, 255, 0)
        
        # Character-by-character display
        self.display_speed = 40  # Characters per second
        self.current_text = ""
        self.target_text = ""
        self.display_timer = 0
        self.chars_displayed = 0
        self.is_animating = False
        self.skipped_animation = False
        
        # Try to load a font for dialogue
        try:
            self.font = pygame.font.Font(os.path.join("assets", "Daydream.ttf"), 16)
            self.name_font = pygame.font.Font(os.path.join("assets", "Daydream.ttf"), 24)
        except pygame.error:
            self.font = pygame.font.SysFont(None, 20)
            self.name_font = pygame.font.SysFont(None, 26)
            print("Failed to load Daydream font, using fallback font")
        
        # Sound effect for text
        try:
            self.text_sound = pygame.mixer.Sound(os.path.join("assets", "sounds", "text_blip.mp3"))
            self.text_sound.set_volume(0.3)
        except:
            self.text_sound = None
            print("Failed to load text sound effect")
        
        # Create dialogue box panel
        self.dialogue_panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(self.box_x, self.box_y, self.box_width, self.box_height),
            manager=self.ui_manager,
            object_id="#dialogue_panel"
        )
        
        # Create portrait background
        portrait_panel_size = self.portrait_size + 20
        self.portrait_bg = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(10, 10, portrait_panel_size, portrait_panel_size),
            manager=self.ui_manager,
            container=self.dialogue_panel,
            object_id="#portrait_panel"
        )
        
        # Store portrait position for direct drawing
        self.portrait_rect = pygame.Rect(
            self.box_x + 20,  # dialogue_panel.x + portrait_bg.x + margin
            self.box_y + 20,  # dialogue_panel.y + portrait_bg.y + margin
            self.portrait_size,
            self.portrait_size
        )
        
        # Create name label
        self.name_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(self.portrait_size + 40, 5, 300, 30),
            text="",
            manager=self.ui_manager,
            container=self.dialogue_panel,
            object_id="#name_label"
        )
        
        # Instead of using UITextBox, we'll use our own system for drawing text
        self.text_rect = pygame.Rect(
            self.portrait_size + 40, 
            40, 
            self.box_width - (self.portrait_size + 80),  # Leave space for scrollbar
            self.box_height - 80
        )
        
        # Add a clickable scrollbar area
        self.scrollbar_rect = pygame.Rect(
            self.box_width - 30,
            40,
            20,
            self.box_height - 80
        )
        
        # Text rendering and scrolling variables
        self.text_lines = []  # Stores each line of text
        self.scroll_position = 0  # Current scroll position (in lines)
        self.visible_lines = 0  # Number of lines visible at once
        self.max_scroll = 0  # Maximum scroll position
        self.line_height = self.font.get_linesize()
        self.dragging_scrollbar = False
        self.drag_start_y = 0
        
        # Choice buttons area
        self.choice_button_rects = []  # Store button rects for direct drawing
        self.choice_text_surfaces = []  # Store text surfaces for direct drawing
        self.choice_full_texts = []     # Store full text for tooltips
        self.hover_choice_index = -1    # Track which choice is being hovered
        self.tooltip_active = False     # Whether to show tooltip
        self.tooltip_surface = None     # The tooltip surface
        
        # Create "continue" indicator
        try:
            self.continue_icon = pygame.image.load(os.path.join("assets", "sprites", "continue_arrow.png"))
            self.continue_icon = pygame.transform.scale(self.continue_icon, (32, 32))
        except:
            self.continue_icon = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.polygon(self.continue_icon, (255, 255, 255), [(16, 0), (32, 16), (16, 32), (0, 16)])
            print("Failed to load continue arrow, using fallback")
        
        self.continue_rect = self.continue_icon.get_rect(
            bottomright=(self.box_width - 20, self.box_height - 20)
        )
        self.continue_visible = False
        self.continue_timer = 0
        
        # Hide UI elements initially
        self.hide()
        
        # Dialogue state
        self.active = False
        self.has_choices = False
        self.showing_choices = False
        self.waiting_for_input = False
        self.current_speaker = None
        self.current_dialogue = None
        self.dialogue_choices = None
        self.sound_timer = 0
        self.sound_interval = 3
        self.player_choice_index = -1
        
        # Create portrait surfaces
        self.current_portrait = None
        self.default_portrait = pygame.Surface((self.portrait_size, self.portrait_size), pygame.SRCALPHA)
        pygame.draw.circle(self.default_portrait, (150, 150, 150), 
                          (self.portrait_size//2, self.portrait_size//2), 
                          self.portrait_size//2 - 2)
        
        # Debug flag
        self.debug = True
        print("DialogueSystem initialized with custom text rendering")

    def show(self, speaker_name=""):
        """Show the dialogue box with the given speaker name"""
        self.dialogue_panel.show()
        self.portrait_bg.show()
        
        if speaker_name:
            self.name_label.set_text(speaker_name)
            self.name_label.show()
        else:
            self.name_label.hide()
        
        self.active = True
        self.showing_choices = False
        self.waiting_for_input = False  # Reset waiting state
        self.scroll_position = 0      # Reset scroll position
        print(f"Dialogue system shown with speaker: {speaker_name}")
    
    def hide(self):
        """Hide the dialogue box and all related elements"""
        self.dialogue_panel.hide()
        self.portrait_bg.hide()
        self.name_label.hide()
        
        # Clear text
        self.text_lines = []
        self.scroll_position = 0
        
        # Clear choice data
        self.choice_button_rects = []
        self.choice_text_surfaces = []
        self.choice_full_texts = []
        self.hover_choice_index = -1
        self.tooltip_active = False
        
        self.active = False
        self.has_choices = False
        self.showing_choices = False
        self.waiting_for_input = False
        self.continue_visible = False
        self.dragging_scrollbar = False
        print("Dialogue system hidden")
    
    def start_dialogue(self, speaker, dialogue):
        """Start displaying a new dialogue"""
        if not dialogue:
            self.hide()
            return
            
        self.current_speaker = speaker
        self.current_dialogue = dialogue
        
        # Show dialogue box with speaker name
        self.show(speaker.name)
        
        # Add small delay to prevent flickering with first message
        pygame.time.delay(50)
        
        # Reset text animation
        self.target_text = dialogue["text"]
        self.current_text = ""
        self.chars_displayed = 0
        self.is_animating = True
        self.skipped_animation = False
        self.display_timer = 0
        self.continue_visible = False
        self.showing_choices = False
        self.waiting_for_input = False
        self.scroll_position = 0
        self.text_lines = []
        
        # Set portrait
        if hasattr(speaker, 'portrait') and speaker.portrait is not None:
            # Ensure portrait has the correct size
            if (speaker.portrait.get_width() != self.portrait_size or 
                speaker.portrait.get_height() != self.portrait_size):
                try:
                    scaled_portrait = pygame.transform.scale(
                        speaker.portrait, 
                        (self.portrait_size, self.portrait_size)
                    )
                    self.current_portrait = scaled_portrait
                except Exception as e:
                    print(f"Error scaling portrait: {e}")
                    self.current_portrait = self.default_portrait
            else:
                self.current_portrait = speaker.portrait
            
            # Update portrait position
            self.portrait_rect = pygame.Rect(
                self.dialogue_panel.rect.left + 29,
                self.dialogue_panel.rect.top + 29,
                self.portrait_size,
                self.portrait_size
            )
            
            print(f"Using portrait from {speaker.name} - Size: {self.current_portrait.get_width()}x{self.current_portrait.get_height()}")
        else:
            self.current_portrait = self.default_portrait
            print(f"Using default portrait for {speaker.name}")
        
        # Check for choices
        self.dialogue_choices = dialogue.get("choices")
        self.has_choices = bool(self.dialogue_choices)
        self.choice_button_rects = []
        self.choice_text_surfaces = []
        self.choice_full_texts = []
            
    def wrap_text(self, text, max_width):
        """Split text into lines that fit within max_width"""
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            # Try adding the word to the current line
            test_line = ' '.join(current_line + [word])
            width, _ = self.font.size(test_line)
            
            if width <= max_width:
                # Word fits, add it to the line
                current_line.append(word)
            else:
                # Word doesn't fit, start a new line
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # The word is too long for a single line, force it
                    lines.append(word)
                    current_line = []
        
        # Add the last line if there's anything left
        if current_line:
            lines.append(' '.join(current_line))
            
        return lines
    
    def update(self, dt):
        """Update dialogue animation and state"""
        if not self.active:
            return
            
        # Update continue indicator animation
        if self.continue_visible:
            self.continue_timer += dt
            if self.continue_timer > 0.5:
                self.continue_timer = 0
        
        # Update character-by-character animation
        if self.is_animating and not self.skipped_animation:
            self.display_timer += dt
            
            # Calculate characters to display
            target_chars = min(len(self.target_text), int(self.display_speed * self.display_timer))
            
            if target_chars > self.chars_displayed:
                # Play sound at intervals
                self.sound_timer += 1
                if self.sound_timer >= self.sound_interval:
                    self.sound_timer = 0
                    if self.text_sound:
                        self.text_sound.play()
                
                # Update displayed text
                self.chars_displayed = target_chars
                self.current_text = self.target_text[:self.chars_displayed]
                
                # Wrap text to fit in the dialogue box
                self.text_lines = self.wrap_text(self.current_text, self.text_rect.width - 10)
                
                # Calculate maximum scroll position
                self.calculate_max_scroll()
                
                # Auto-scroll to bottom as new text appears
                self.scroll_to_bottom()
            
            # Check if animation is complete
            if self.chars_displayed >= len(self.target_text):
                self.is_animating = False
                self.waiting_for_input = True
                self.continue_visible = True
        
        # Update tooltip for choice hover
        if self.showing_choices:
            mouse_pos = pygame.mouse.get_pos()
            self.tooltip_active = False
            
            # Check if mouse is hovering over a choice
            for i, rect in enumerate(self.choice_button_rects):
                if rect.collidepoint(mouse_pos):
                    self.hover_choice_index = i
                    self.tooltip_active = True
                    
                    # Create tooltip for the hovered choice
                    if self.hover_choice_index >= 0 and self.hover_choice_index < len(self.choice_full_texts):
                        # Render the full text as tooltip
                        tooltip_text = self.choice_full_texts[self.hover_choice_index]
                        
                        # Create the tooltip with proper wrapping
                        rendered_text = self.render_wrapped_text(tooltip_text, self.box_width - 80)
                        
                        # Store the tooltip surface
                        self.tooltip_surface = rendered_text
                    break
    def calculate_max_scroll(self):
        """Calculate maximum scroll position based on text height"""
        # Calculate how many lines can be visible at once
        self.visible_lines = int(self.text_rect.height // self.line_height)
        
        # Calculate max scroll position
        if len(self.text_lines) > self.visible_lines:
            self.max_scroll = len(self.text_lines) - self.visible_lines
        else:
            self.max_scroll = 0
    
    def scroll_to_bottom(self):
        """Scroll to the bottom of the text"""
        if self.max_scroll > 0:
            self.scroll_position = self.max_scroll
    
    def render_wrapped_text(self, text, max_width):
        """Render text with word wrapping"""
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            test_width, _ = self.font.size(test_line)
            
            if test_width <= max_width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Calculate dimensions needed for tooltip
        line_height = self.font.get_height() + 2
        total_height = line_height * len(lines) + 10  # Add padding
        
        # Create a surface for the tooltip
        tooltip = pygame.Surface((max_width + 20, total_height), pygame.SRCALPHA)
        pygame.draw.rect(tooltip, (40, 40, 40, 220), (0, 0, max_width + 20, total_height), 0, 5)
        pygame.draw.rect(tooltip, (200, 200, 200, 255), (0, 0, max_width + 20, total_height), 2, 5)
        
        # Render each line
        for i, line in enumerate(lines):
            text_surface = self.font.render(line, True, (255, 255, 255))
            tooltip.blit(text_surface, (10, 5 + i * line_height))
        
        return tooltip

    def handle_scroll(self, amount):
        """Handle scrolling by the given amount"""
        self.scroll_position = max(0, min(self.max_scroll, self.scroll_position + amount))
    
    def handle_event(self, event):
        """Handle input events"""
        if not self.active:
            return False
        
        # Handle mouse wheel for scrolling text
        if event.type == pygame.MOUSEWHEEL and not self.showing_choices:
            if self.dialogue_panel.rect.collidepoint(pygame.mouse.get_pos()):
                # Scroll up/down based on wheel direction
                self.handle_scroll(-event.y)
                return True
        
        # Handle scrollbar dragging
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check if click is on scrollbar
            scrollbar_screen_rect = pygame.Rect(
                self.dialogue_panel.rect.left + self.scrollbar_rect.left,
                self.dialogue_panel.rect.top + self.scrollbar_rect.top,
                self.scrollbar_rect.width,
                self.scrollbar_rect.height
            )
            
            if scrollbar_screen_rect.collidepoint(event.pos):
                self.dragging_scrollbar = True
                self.drag_start_y = event.pos[1]
                return True
                
            # Check for choices
            elif self.showing_choices:
                for i, rect in enumerate(self.choice_button_rects):
                    if rect.collidepoint(event.pos):
                        self.player_choice_index = i
                        return True
        
        # Handle scrollbar release
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_scrollbar = False
        
        # Handle scrollbar dragging motion
        elif event.type == pygame.MOUSEMOTION and self.dragging_scrollbar:
            # Calculate drag distance
            dy = event.pos[1] - self.drag_start_y
            self.drag_start_y = event.pos[1]
            
            # Convert drag distance to scroll amount
            if self.max_scroll > 0:
                scroll_factor = self.max_scroll / self.scrollbar_rect.height
                scroll_amount = dy * scroll_factor
                self.handle_scroll(scroll_amount)
            
            return True
        
        # Handle keypresses
        if event.type == pygame.KEYDOWN:
            # If still animating text, skip to the end
            if self.is_animating:
                self.chars_displayed = len(self.target_text)
                self.current_text = self.target_text
                
                # Wrap text to fit in the dialogue box
                self.text_lines = self.wrap_text(self.current_text, self.text_rect.width - 10)
                
                # Calculate maximum scroll position
                self.calculate_max_scroll()
                
                # Auto-scroll to bottom
                self.scroll_to_bottom()
                
                self.is_animating = False
                self.waiting_for_input = True
                self.continue_visible = True
                return True
            
            # If waiting for input to continue (not animating and continue arrow is showing)
            elif self.waiting_for_input and self.continue_visible:
                self.waiting_for_input = False
                self.continue_visible = False
                
                # If this dialogue has choices, show them now
                if self.has_choices:
                    self.showing_choices = True
                    self.show_choices_if_available()
                    print("Showing choices")
                
                return True
            
            # Number key selection for choices
            elif self.showing_choices:
                choice_index = -1
                if event.key == pygame.K_1:
                    choice_index = 0
                elif event.key == pygame.K_2:
                    choice_index = 1
                elif event.key == pygame.K_3:
                    choice_index = 2
                elif event.key == pygame.K_4:
                    choice_index = 3
                elif event.key == pygame.K_5:
                    choice_index = 4
                    
                if choice_index >= 0 and choice_index < len(self.dialogue_choices):
                    # Store choice and return True to indicate event was handled
                    self.player_choice_index = choice_index
                    return True
                
            # Arrow keys for scrolling
            elif not self.showing_choices:
                if event.key == pygame.K_UP:
                    self.handle_scroll(-1)
                    return True
                elif event.key == pygame.K_DOWN:
                    self.handle_scroll(1)
                    return True
                elif event.key == pygame.K_PAGEUP:
                    self.handle_scroll(-self.visible_lines)
                    return True
                elif event.key == pygame.K_PAGEDOWN:
                    self.handle_scroll(self.visible_lines)
                    return True
                
        return False
    
    def show_choices_if_available(self):
        """Show dialogue choices with direct drawing approach"""
        if not self.dialogue_choices:
            return
            
        # Clear previous choices
        self.choice_button_rects = []
        self.choice_text_surfaces = []
        self.choice_full_texts = []
        
        # Set flag
        self.showing_choices = True
        
        # Calculate area for choices
        choice_area_x = self.dialogue_panel.rect.left + self.portrait_size + 40
        choice_area_y = self.dialogue_panel.rect.top + 40
        choice_area_width = self.box_width - (self.portrait_size + 60)
        choice_area_height = self.box_height - 80
        
        # Button dimensions
        num_choices = len(self.dialogue_choices)
        button_height = min(40, (choice_area_height - 20) // num_choices)
        spacing = 10
        
        # Calculate total height
        total_height = (button_height + spacing) * num_choices - spacing
        
        # Center buttons vertically
        start_y = choice_area_y + (choice_area_height - total_height) // 2
        
        for i, choice in enumerate(self.dialogue_choices):
            # Button position
            y_pos = start_y + i * (button_height + spacing)
            
            # Create button rect
            button_rect = pygame.Rect(
                choice_area_x,
                y_pos,
                choice_area_width,
                button_height
            )
            
            # Store the full choice text for tooltips
            full_text = choice['text']
            self.choice_full_texts.append(full_text)
            
            # Calculate how much text can fit in the button
            max_text_width = button_rect.width - 40  # Leave margin
            button_prefix = f"{i+1}. "
            
            # Truncate text if necessary and add ellipsis
            choice_text = full_text
            truncated = False
            
            # Calculate the width of the prefix
            prefix_width, _ = self.font.size(button_prefix)
            available_width = max_text_width - prefix_width
            
            # Check if text needs truncation
            text_width, _ = self.font.size(choice_text)
            if text_width > available_width:
                # Truncate text
                truncated = True
                test_text = choice_text
                while text_width > available_width and len(test_text) > 0:
                    test_text = test_text[:-1]
                    text_width, _ = self.font.size(test_text)
                
                # Add ellipsis (always truncate if it's longer than 30 characters)
                if truncated or len(choice_text) > 30:
                    choice_text = test_text[:-3] + "..."
            
            # Create button text
            button_text = button_prefix + choice_text
            
            # Render text
            text_surface = self.font.render(button_text, True, (255, 255, 255))
            
            # Store for drawing
            self.choice_button_rects.append(button_rect)
            self.choice_text_surfaces.append(text_surface)
        
        print(f"Created {len(self.choice_button_rects)} clickable choice buttons")
    
    def draw(self, screen):
        """Draw the dialogue UI with direct pygame drawing"""
        if not self.active:
            return
        
        # Draw UI elements
        self.ui_manager.draw_ui(screen)
        
        # Draw portrait directly
        if self.current_portrait:
            # Draw portrait background
            pygame.draw.rect(screen, (30, 30, 40), self.portrait_rect)
            
            # Draw portrait
            screen.blit(self.current_portrait, self.portrait_rect)
            
            # Draw border
            border_rect = self.portrait_rect.inflate(4, 4)
            pygame.draw.rect(screen, (200, 200, 255), border_rect, 2)
        
        # Draw text area background
        text_area_rect = pygame.Rect(
            self.dialogue_panel.rect.left + self.text_rect.left,
            self.dialogue_panel.rect.top + self.text_rect.top,
            self.text_rect.width,
            self.text_rect.height
        )
        pygame.draw.rect(screen, (40, 40, 50), text_area_rect)
        pygame.draw.rect(screen, (100, 100, 120), text_area_rect, 1)
        
        # Draw text
        if not self.showing_choices and self.text_lines:  # Check if text_lines exists and isn't empty
            # Calculate visible range of lines
            visible_start = int(self.scroll_position)  # Convert to integer
            visible_end = min(len(self.text_lines), visible_start + int(self.visible_lines))  # Convert to integer
            
            # Draw visible lines
            for i in range(visible_start, visible_end):
                line_index = i - visible_start
                line_y = text_area_rect.top + line_index * self.line_height
                
                line_surface = self.font.render(self.text_lines[i], True, self.text_color)
                screen.blit(line_surface, (text_area_rect.left + 5, line_y + 5))
            
            # Draw scrollbar if needed
            if self.max_scroll > 0 and len(self.text_lines) > 0:  # Check len(self.text_lines) to prevent division by zero
                # Draw scrollbar background
                scrollbar_rect = pygame.Rect(
                    self.dialogue_panel.rect.left + self.scrollbar_rect.left,
                    self.dialogue_panel.rect.top + self.scrollbar_rect.top,
                    self.scrollbar_rect.width,
                    self.scrollbar_rect.height
                )
                pygame.draw.rect(screen, (80, 80, 80), scrollbar_rect, 0, 3)
                
                # Calculate thumb size and position (safely)
                if len(self.text_lines) > 0:  # Prevent division by zero
                    thumb_ratio = min(1.0, float(self.visible_lines) / len(self.text_lines))
                    thumb_height = max(20, int(scrollbar_rect.height * thumb_ratio))
                    
                    scroll_ratio = float(self.scroll_position) / max(1, self.max_scroll)
                    thumb_pos = scrollbar_rect.top + int((scrollbar_rect.height - thumb_height) * scroll_ratio)
                    
                    # Draw thumb
                    thumb_rect = pygame.Rect(
                        scrollbar_rect.left + 2,
                        thumb_pos,
                        scrollbar_rect.width - 4,
                        thumb_height
                    )
                    pygame.draw.rect(screen, (150, 150, 150), thumb_rect, 0, 2)
                    
                    # Draw thumb border
                    if self.dragging_scrollbar:
                        pygame.draw.rect(screen, (200, 200, 255), thumb_rect, 2, 2)
                    else:
                        pygame.draw.rect(screen, (120, 120, 120), thumb_rect, 1, 2)
        
        # Draw choices if showing
        if self.showing_choices:
            for i, (rect, text) in enumerate(zip(self.choice_button_rects, self.choice_text_surfaces)):
                # Highlight button if hovered
                bg_color = (40, 40, 60) if i == self.hover_choice_index else (30, 30, 50)
                border_color = (150, 150, 250) if i == self.hover_choice_index else (100, 100, 200)
                
                # Draw button background
                pygame.draw.rect(screen, bg_color, rect, 0, 5)
                pygame.draw.rect(screen, border_color, rect, 2, 5)
                
                # Center text in button horizontally, align vertically
                text_rect = text.get_rect()
                text_rect.midleft = (rect.left + 20, rect.centery)  # Left-aligned with margin
                screen.blit(text, text_rect)
            
            # Draw tooltip for hovered choice
            if self.tooltip_active and self.tooltip_surface:
                mouse_pos = pygame.mouse.get_pos()
                
                # Position tooltip above the mouse
                tooltip_x = mouse_pos[0] - self.tooltip_surface.get_width() // 2
                tooltip_y = mouse_pos[1] - self.tooltip_surface.get_height() - 10
                
                # Keep tooltip on screen
                tooltip_x = max(10, min(self.screen_width - self.tooltip_surface.get_width() - 10, tooltip_x))
                tooltip_y = max(10, tooltip_y)
                
                # Draw tooltip
                screen.blit(self.tooltip_surface, (tooltip_x, tooltip_y))
        
        # Draw "press any key to continue" help text
        if self.waiting_for_input and self.continue_visible:
            help_text = self.font.render("Press any key to continue", True, (200, 200, 200))
            help_rect = help_text.get_rect(midbottom=(
                self.dialogue_panel.rect.centerx,
                self.dialogue_panel.rect.bottom - 10
            ))
            screen.blit(help_text, help_rect)
            
        # Draw continue indicator
        if self.continue_visible and self.continue_timer < 0.25:
            indicator_x = self.dialogue_panel.rect.left + self.continue_rect.left
            indicator_y = self.dialogue_panel.rect.top + self.continue_rect.top
            screen.blit(self.continue_icon, (indicator_x, indicator_y))

class LevelTimer:
    """Timer system for tracking level completion time"""
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.paused_time = 0
        self.pause_start = None
        self.is_running = False
        self.is_paused = False
        
    def start(self):
        """Start the timer"""
        self.start_time = time.time()
        self.is_running = True
        self.is_paused = False
        self.paused_time = 0
        
    def stop(self):
        """Stop the timer and return final time"""
        if self.is_running and not self.is_paused:
            self.end_time = time.time()
            self.is_running = False
            return self.get_elapsed_time()
        return 0
        
    def pause(self):
        """Pause the timer (useful for dialogue or menus)"""
        if self.is_running and not self.is_paused:
            self.pause_start = time.time()
            self.is_paused = True
            
    def resume(self):
        """Resume the timer"""
        if self.is_paused and self.pause_start:
            self.paused_time += time.time() - self.pause_start
            self.pause_start = None
            self.is_paused = False
    
    def get_elapsed_time(self):
        """Get current elapsed time in seconds"""
        if not self.start_time:
            return 0
            
        if self.end_time:
            # Timer has stopped
            return (self.end_time - self.start_time) - self.paused_time
        elif self.is_paused:
            # Timer is paused
            return (self.pause_start - self.start_time) - self.paused_time
        elif self.is_running:
            # Timer is running
            return (time.time() - self.start_time) - self.paused_time
        else:
            return 0
    
    def format_time(self, time_seconds=None):
        """Format time as MM:SS.ss"""
        if time_seconds is None:
            time_seconds = self.get_elapsed_time()
            
        minutes = int(time_seconds // 60)
        seconds = time_seconds % 60
        return f"{minutes:02d}:{seconds:05.2f}"

class GameStats:
    """Track various game statistics for scoring"""
    def __init__(self):
        self.rings_collected = 0
        self.enemies_defeated = 0
        self.deaths = 0
        self.checkpoints_reached = 0
        self.secrets_found = 0
        self.completion_time = 0
        
    def reset(self):
        """Reset all stats"""
        self.__init__()
        
    def calculate_score(self):
        """Calculate total score based on stats"""
        base_score = 1000
        time_bonus = 300 - int(self.completion_time)  # Bonus for fast completion
        ring_bonus = self.rings_collected * 10
        enemy_bonus = self.enemies_defeated * 50
        secret_bonus = self.secrets_found * 200
        death_penalty = self.deaths * 100
        
        total_score = base_score + time_bonus + ring_bonus + enemy_bonus + secret_bonus - death_penalty
        return max(0, total_score)
        
    def get_rank(self, s=1355, a=1275, b=1150, c=950, d=750):
        """Calculate rank based on performance (S, A, B, C, D, E)"""
        score = self.calculate_score()
        
        if score >= s:
            return "S"
        elif score >= a:
            return "A"
        elif score >= b:
            return "B"
        elif score >= c:
            return "C"
        elif score >= d:
            return "D"
        else:
            return "E"

class ResultsScreen:
    """Enhanced results screen with New Best! effects for all improved stats"""
    def __init__(self, screen_width, screen_height, game_save):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.game_save = game_save
        
        # Enhanced font system with consistent sizing
        self.font_title = pygame.font.Font(daFont, 36)      # Title
        self.font_large = pygame.font.Font(daFont, 28)      # Rank
        self.font_medium = pygame.font.Font(daFont, 20)     # Stats labels/values
        self.font_small = pygame.font.Font(daFont, 16)      # "New Best!" text
        self.font_tiny = pygame.font.Font(daFont, 12)       # Small details
        
        self.animation_time = 0
        self.show_time = 0
        self.results_shown = False
        self.stats = None
        self.current_level_index = 0
        self.improvements = []  # Store improvements from save system
        
        self.rank_colors = {
            "S": (255, 215, 0),    # Gold
            "A": (255, 100, 100),  # Red
            "B": (100, 255, 100),  # Green  
            "C": (100, 100, 255),  # Blue
            "D": (255, 165, 0),    # Orange
            "E": (128, 128, 128)   # Gray
        }
        
        # Level-specific score thresholds
        self.level_thresholds = {
            0: {"s": 1350, "a": 1275, "b": 1150, "c": 950, "d": 750},
            1: {"s": 1365, "a": 1200, "b": 1050, "c": 850, "d": 650},
            2: {"s": 1720, "a": 1500, "b": 1300, "c": 1050, "d": 800},
            3: {"s": 1770, "a": 1565, "b": 1380, "c": 1150, "d": 850},
            4: {"s": 4000, "a": 3665, "b": 3220, "c": 2860, "d": 2380},
        }
        
        # Enhanced animation states
        self.title_alpha = 0
        self.title_scale = 0
        self.rank_scale = 0
        self.rank_glow_intensity = 0
        self.sparkle_particles = []
        self.rank_revealed = False
        
        # Rank-specific animation states
        self.rank_animation_progress = 0
        self.rank_fragments = []  # For E rank crumbling effect
        self.rank_wobble_offset = 0  # For D rank boring wobble
        self.rank_fade_alpha = 255  # For general rank fade effects
        self.e_rank_tilt = 0  # For E rank lopsided effect
        self.crack_lines = []  # For E rank crack lines
        
        # Sequential stat animation with "New Best!" support
        self.stat_display_delay = 0.5
        self.stat_interval = 1.2  # Slightly longer for "New Best!" animations
        self.stats_to_show = []
        self.current_stat_index = 0
        self.stat_start_time = None
        
        # Music control
        self.victory_music_started = False
        self.victory_music_finished = False
        self.rank_music_started = False
        self.victory_music_duration = 6.5
        
        # Cache colors and save data
        self._cached_colors = {}
        self._cached_save_data = {}
        
        # Threading
        self.thread_pool = []
        self.result_queue = queue.Queue()
        self.music_thread = None
        self.color_cache_thread = None
        self.color_caching_complete = False
        self.music_loading_complete = False
        
    def configure_timing(self, first_stat_delay=0.5, stat_interval=1.2):
        """Configure the timing for stat animations"""
        self.stat_display_delay = first_stat_delay
        self.stat_interval = stat_interval
        
    def show_results(self, stats, level_index=0):
        """Display the results screen with stats and save comparison"""
        self.stats = stats
        self.current_level_index = level_index
        self.results_shown = True
        self.animation_time = 0
        self.show_time = pygame.time.get_ticks()
        
        # Cache previous save data BEFORE calling save_level_result
        self._cache_save_data(level_index)
        
        # Now save the results (this may update the save file)
        self.improvements = self.game_save.save_level_result(level_index, stats, self)
        
        # Reset animation values
        self.title_alpha = 0
        self.title_scale = 0
        self.rank_scale = 0
        self.rank_glow_intensity = 0
        self.sparkle_particles = []
        self.current_stat_index = 0
        self.stat_start_time = None
        self.rank_revealed = False
        
        # Reset rank-specific animation states
        self.rank_animation_progress = 0
        self.rank_fragments = []
        self.rank_wobble_offset = 0
        self.rank_fade_alpha = 255
        self.e_rank_tilt = 0
        self.crack_lines = []
        
        # Reset thread flags
        self.color_caching_complete = False
        self.music_loading_complete = False
        
        # Reset music flags
        self.victory_music_started = False
        self.victory_music_finished = False
        self.rank_music_started = False
        
        # Initialize stats to show sequentially
        self.stats_to_show = []
        
        # Start background threads for heavy operations
        self.start_background_threads()
        
    def _cache_save_data(self, level_index):
        """Cache previous save data for comparison"""
        # Get the raw save data
        level_data = self.game_save.get_level_best(level_index)
        
        if level_data:
            self._cached_save_data = {
                'best_time': level_data.get('best_time', float('inf')),
                'best_score': level_data.get('best_score', 0),
                'best_rank': level_data.get('best_rank', 'E'),
                'best_rings': level_data.get('best_rings', 0),
                'best_enemies': level_data.get('best_enemies', 0),
                'best_secrets': level_data.get('best_secrets', 0),
                'best_deaths': level_data.get('best_deaths', float('inf'))
            }
        else:
            self._cached_save_data = {
                'best_time': float('inf'),
                'best_score': 0,
                'best_rank': 'E',
                'best_rings': 0,
                'best_enemies': 0,
                'best_secrets': 0,
                'best_deaths': float('inf')
            }
        
    def get_level_rank(self, level_index=None):
        """Get rank for specific level using appropriate thresholds"""
        if level_index is None:
            level_index = self.current_level_index
            
        thresholds = self.level_thresholds.get(level_index, self.level_thresholds[0])
        
        if not hasattr(self.stats, 'get_rank'):
            # Fallback rank calculation if stats doesn't have get_rank method
            score = self.stats.calculate_score() if hasattr(self.stats, 'calculate_score') else 0
            if score >= thresholds["s"]: return "S"
            elif score >= thresholds["a"]: return "A"
            elif score >= thresholds["b"]: return "B"
            elif score >= thresholds["c"]: return "C"
            elif score >= thresholds["d"]: return "D"
            else: return "E"
        
        return self.stats.get_rank(
            s=thresholds["s"],
            a=thresholds["a"], 
            b=thresholds["b"],
            c=thresholds["c"],
            d=thresholds["d"]
        )
        
    def start_background_threads(self):
        """Start background threads for heavy operations"""
        if self.color_cache_thread is None or not self.color_cache_thread.is_alive():
            self.color_cache_thread = threading.Thread(
                target=self._cache_stat_colors_threaded, 
                daemon=True
            )
            self.color_cache_thread.start()
        
        if self.music_thread is None or not self.music_thread.is_alive():
            self.music_thread = threading.Thread(
                target=self._load_music_threaded, 
                daemon=True
            )
            self.music_thread.start()
    
    def _cache_stat_colors_threaded(self):
        """Thread function to pre-calculate stat colors"""
        if self.stats:
            try:
                cached_colors = {
                    'rings': self.get_rings_color(self.stats.rings_collected),
                    'enemies': self.get_enemies_color(self.stats.enemies_defeated),
                    'deaths': self.get_deaths_color(self.stats.deaths)
                }
                
                self.result_queue.put(('colors_cached', cached_colors))
                
            except Exception as e:
                self.result_queue.put(('error', f"Color caching error: {e}"))
    
    def _load_music_threaded(self):
        """Thread function to load victory music"""
        try:
            self.result_queue.put(('music_ready', None))
        except Exception as e:
            self.result_queue.put(('error', f"Music loading error: {e}"))
    
    def _process_thread_results(self):
        """Process results from background threads"""
        try:
            while not self.result_queue.empty():
                result_type, data = self.result_queue.get_nowait()
                
                if result_type == 'colors_cached':
                    self._cached_colors = data
                    self.color_caching_complete = True
                elif result_type == 'music_ready':
                    self.music_loading_complete = True
                elif result_type == 'error':
                    print(f"Thread error: {data}")
                    
        except queue.Empty:
            pass
    
    def start_victory_music(self):
        """Start victory music with fadeout of current track"""
        if not self.victory_music_started and self.music_loading_complete:
            pygame.mixer.music.fadeout(300)
            
            try:
                pygame.mixer.music.load(os.path.join("assets", "music", "stage clear.mp3"))
                pygame.mixer.music.play()
                self.victory_music_started = True
            except pygame.error:
                self.victory_music_started = True
                self.victory_music_finished = True
    
    def start_rank_music(self, rank):
        """Start the appropriate music based on rank"""
        if self.rank_music_started:
            return
            
        pygame.mixer.music.fadeout(500)
        
        try:
            if rank == "S":
                pygame.mixer.music.load(os.path.join("assets", "music", "S rank.mp3"))
            elif rank in ["A", "B"]:
                pygame.mixer.music.load(os.path.join("assets", "music", "A B rank.mp3"))
            elif rank == "C":
                pygame.mixer.music.load(os.path.join("assets", "music", "C rank.mp3"))
            elif rank in ["D", "E"]:
                pygame.mixer.music.load(os.path.join("assets", "music", "boowhomp.mp3"))
            
            pygame.mixer.music.play()
        except pygame.error:
            pass
        
        self.rank_music_started = True
    
    def initialize_e_rank_cracks(self):
        """Initialize crack lines for E rank cracking effect"""
        import random
        self.crack_lines = []
        
        # Create several crack lines that will appear over the text
        crack_count = 5
        center_x = self.screen_width // 2
        center_y = 480
        
        for i in range(crack_count):
            # Create cracks that span across the rank text area
            start_x = center_x + random.randint(-80, 80)
            start_y = center_y + random.randint(-25, 25)
            
            # Cracks should be jagged lines
            points = [(start_x, start_y)]
            current_x, current_y = start_x, start_y
            
            # Create 3-5 segments for each crack
            segments = random.randint(3, 5)
            for segment in range(segments):
                current_x += random.randint(-20, 20)
                current_y += random.randint(-15, 15)
                points.append((current_x, current_y))
            
            crack = {
                'points': points,
                'alpha': 0,
                'width': random.randint(1, 3)
            }
            self.crack_lines.append(crack)
    
    def update(self, dt):
        """Update animations"""
        if not self.results_shown:
            return
        
        self._process_thread_results()
            
        self.animation_time += dt
        current_time = pygame.time.get_ticks()
        elapsed = (current_time - self.show_time) / 1000.0
        
        if not self.victory_music_started and self.music_loading_complete:
            self.start_victory_music()
        
        if not self.victory_music_finished and elapsed >= self.victory_music_duration:
            self.victory_music_finished = True
        
        # Enhanced title animation with scale and fade
        if elapsed < 1.5:
            progress = elapsed / 1.5
            self.title_alpha = int(255 * min(progress * 2, 1.0))
            # Bounce scale effect
            if progress < 0.8:
                self.title_scale = 0.5 + 0.5 * progress + 0.2 * math.sin(progress * math.pi * 4)
            else:
                self.title_scale = 1.0 + 0.1 * math.sin((progress - 0.8) * math.pi * 10)
        else:
            self.title_alpha = 255
            self.title_scale = 1.0
            
        self.update_sequential_stats(elapsed)
            
        # Enhanced rank animation with rank-specific behaviors
        if self.victory_music_finished:
            rank_start_time = self.victory_music_duration
            rank_elapsed = elapsed - rank_start_time
            
            if rank_elapsed >= 0:
                self.rank_revealed = True
                current_rank = self.get_level_rank()
                
                # Update rank-specific animations
                self.update_rank_animation(rank_elapsed, current_rank, dt)
                    
                if not self.rank_music_started:
                    self.start_rank_music(current_rank)
            
            # Enhanced sparkle system for S rank
            if (self.stats and self.get_level_rank() == "S" and 
                rank_elapsed > 1.0 and len(self.sparkle_particles) < 30):
                if rank_elapsed % 0.1 < dt:
                    self.add_sparkle()
                
        # Update sparkle particles
        for particle in self.sparkle_particles[:]:
            particle["life"] -= dt
            particle["y"] -= particle["speed"] * dt
            particle["x"] += math.sin(particle["y"] * 0.01) * 2
            particle["alpha"] = max(0, int(255 * (particle["life"] / particle["max_life"])))
            if particle["life"] <= 0:
                self.sparkle_particles.remove(particle)
                
        # Update E rank fragments
        for fragment in self.rank_fragments:
            fragment['x'] += fragment['vx'] * dt
            fragment['y'] += fragment['vy'] * dt
            fragment['vy'] += fragment['gravity'] * dt  # Apply gravity
            fragment['rotation'] += fragment['rotation_speed']
            fragment['alpha'] = max(0, fragment['alpha'] - fragment['fade_speed'])
    
    def update_rank_animation(self, rank_elapsed, rank, dt):
        """Update rank-specific animations"""
        self.rank_animation_progress = min(rank_elapsed / 2.0, 1.0)
        
        if rank in ["S", "A", "B"]:
            # Keep existing animations for S, A, B ranks
            if rank_elapsed < 2.0:
                progress = min(rank_elapsed / 2.0, 1.0)
                
                if progress < 0.3:
                    # Initial bounce
                    bounce_progress = progress / 0.3
                    self.rank_scale = bounce_progress * 1.5
                elif progress < 0.7:
                    # Settle with oscillation
                    settle_progress = (progress - 0.3) / 0.4
                    self.rank_scale = 1.5 - 0.5 * settle_progress + 0.2 * math.sin(settle_progress * math.pi * 6)
                else:
                    # Final glow pulse
                    glow_progress = (progress - 0.7) / 0.3
                    self.rank_scale = 1.0 + 0.1 * math.sin(glow_progress * math.pi * 8)
                    self.rank_glow_intensity = math.sin(glow_progress * math.pi * 4) * 0.5 + 0.5
                    
            else:
                self.rank_scale = 1.0
                self.rank_glow_intensity = 0.3 + 0.2 * math.sin(rank_elapsed * 3)
                
        elif rank == "C":
            # Standard "you passed" animation - simple fade-in with mild satisfaction
            if rank_elapsed < 1.5:
                progress = rank_elapsed / 1.5
                self.rank_scale = 0.8 + 0.2 * progress  # Modest growth
                self.rank_fade_alpha = int(255 * progress)
            else:
                self.rank_scale = 1.0
                self.rank_fade_alpha = 255
                # Very subtle pulse to show "okay, you did it"
                self.rank_glow_intensity = 0.1 + 0.1 * math.sin(rank_elapsed * 2)
                
        elif rank == "D":
            # Boring "could have done better" - underwhelming wobble
            if rank_elapsed < 2.0:
                progress = rank_elapsed / 2.0
                self.rank_scale = 0.9 + 0.1 * progress  # Smaller, less impressive growth
                self.rank_fade_alpha = int(255 * progress)
                
                # Disappointing wobble effect
                self.rank_wobble_offset = math.sin(rank_elapsed * 8) * 3 * (1 - progress)
            else:
                self.rank_scale = 1.0
                self.rank_fade_alpha = 200  # Slightly dimmed
                # Boring, slow wobble that suggests disappointment
                self.rank_wobble_offset = math.sin(rank_elapsed * 1.5) * 2
                
        elif rank == "E":
            # Cracked and lopsided failure animation
            if rank_elapsed < 1.0:
                # Initial normal appearance
                progress = rank_elapsed / 1.0
                self.rank_scale = progress
                self.rank_fade_alpha = int(255 * progress)
            elif rank_elapsed < 1.5:
                # Brief moment of stability
                self.rank_scale = 1.0
                self.rank_fade_alpha = 255
            elif rank_elapsed < 2.5:
                # Start cracking and tilting
                crack_progress = (rank_elapsed - 1.5) / 1.0
                
                # Initialize cracks if not done
                if not self.crack_lines:
                    self.initialize_e_rank_cracks()
                
                # Violent shaking gets more intense
                shake_intensity = 8 * crack_progress
                self.rank_wobble_offset = math.sin(rank_elapsed * 30) * shake_intensity
                
                # E starts to tilt/fall over
                self.e_rank_tilt = crack_progress * 15  # Gradually tilt 15 degrees
                
                # Cracks become more visible
                for crack in self.crack_lines:
                    crack['alpha'] = min(255, int(200 * crack_progress))
                
                # Slight dimming as it gets damaged
                self.rank_fade_alpha = int(255 * (1 - crack_progress * 0.3))
            else:
                # Settled in broken state - still visible but clearly damaged
                final_progress = min((rank_elapsed - 2.5) / 1.0, 1.0)
                
                # Less violent shaking, more like unstable settling
                self.rank_wobble_offset = math.sin(rank_elapsed * 4) * 3
                
                # E is noticeably lopsided
                self.e_rank_tilt = 15 + math.sin(rank_elapsed * 2) * 3  # Slight wobble in tilt
                
                # Cracks are fully visible
                for crack in self.crack_lines:
                    crack['alpha'] = 200
                
                # Dimmed but still readable
                self.rank_fade_alpha = 180
    
    def update_sequential_stats(self, elapsed):
        """Update sequential stat display with 'New Best!' indicators"""
        if (self.color_caching_complete and not self.stats_to_show and 
            elapsed > self.stat_display_delay):
            
            # Get current performance data
            current_score = self.stats.calculate_score() if hasattr(self.stats, 'calculate_score') else 0
            current_time = self.stats.completion_time
            current_rank = self.get_level_rank()
            current_rings = self.stats.rings_collected
            current_enemies = self.stats.enemies_defeated
            current_secrets = self.stats.secrets_found if hasattr(self.stats, 'secrets_found') else 0
            current_deaths = self.stats.deaths
            
            # Check for improvements using cached data
            is_time_best = current_time < self._cached_save_data['best_time']
            is_score_best = current_score > self._cached_save_data['best_score']
            is_rings_best = current_rings > self._cached_save_data['best_rings']
            is_enemies_best = current_enemies > self._cached_save_data['best_enemies']
            is_secrets_best = current_secrets > self._cached_save_data['best_secrets']
            is_deaths_best = current_deaths < self._cached_save_data['best_deaths']
            rank_values = {"S": 6, "A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
            is_rank_best = rank_values[current_rank] > rank_values[self._cached_save_data['best_rank']]
            
            self.stats_to_show = []
            
            # Time stat
            self.stats_to_show.append({
                "key": "time", 
                "label": "Time:", 
                "value": self.format_time(current_time),
                "color": (100, 255, 150) if is_time_best else (255, 255, 255),
                "alpha": 0, 
                "shown": False,
                "is_best": is_time_best,
                "shift_offset": 0,
                "best_alpha": 0
            })
            
            # Rings stat
            self.stats_to_show.append({
                "key": "rings", 
                "label": "Coins:", 
                "value": str(current_rings),
                "color": (100, 255, 150) if is_rings_best else self._cached_colors.get('rings', (255, 255, 255)),
                "alpha": 0, 
                "shown": False,
                "is_best": is_rings_best,
                "shift_offset": 0,
                "best_alpha": 0
            })
            
            # Enemies stat
            self.stats_to_show.append({
                "key": "enemies", 
                "label": "Enemies:", 
                "value": str(current_enemies),
                "color": (100, 255, 150) if is_enemies_best else self._cached_colors.get('enemies', (255, 255, 255)),
                "alpha": 0, 
                "shown": False,
                "is_best": is_enemies_best,
                "shift_offset": 0,
                "best_alpha": 0
            })
            
            # Secrets (if any)
            if current_secrets > 0:
                self.stats_to_show.append({
                    "key": "secrets", 
                    "label": "Secrets:", 
                    "value": str(current_secrets),
                    "color": (100, 255, 150) if is_secrets_best else (255, 255, 0),
                    "alpha": 0, 
                    "shown": False,
                    "is_best": is_secrets_best,
                    "shift_offset": 0,
                    "best_alpha": 0
                })
            
            # Deaths stat
            self.stats_to_show.append({
                "key": "deaths", 
                "label": "Deaths:", 
                "value": str(current_deaths),
                "color": (100, 255, 150) if is_deaths_best else self._cached_colors.get('deaths', (255, 255, 255)),
                "alpha": 0, 
                "shown": False,
                "is_best": is_deaths_best,
                "shift_offset": 0,
                "best_alpha": 0
            })
            
            # Score stat
            self.stats_to_show.append({
                "key": "score", 
                "label": "Score:", 
                "value": str(current_score),
                "color": (100, 255, 150) if is_score_best else (255, 255, 100),
                "alpha": 0, 
                "shown": False,
                "is_best": is_score_best,
                "shift_offset": 0,
                "best_alpha": 0
            })
            
            self.stat_start_time = elapsed
        
        # Animate stats sequentially
        if self.stats_to_show and self.stat_start_time is not None:
            time_since_start = elapsed - self.stat_start_time
            
            for i, stat in enumerate(self.stats_to_show):
                stat_should_start = i * self.stat_interval
                
                if time_since_start >= stat_should_start:
                    if not stat["shown"]:
                        stat["shown"] = True
                    
                    # Animate alpha for this stat
                    stat_progress = min((time_since_start - stat_should_start) / 0.8, 1.0)
                    stat["alpha"] = int(255 * stat_progress)
                    
                    # Animate "New Best!" effects for ANY stat that's a best
                    if stat["is_best"] and stat_progress > 0.5:
                        best_progress = min((stat_progress - 0.5) / 0.5, 1.0)
                        stat["shift_offset"] = int(-60 * best_progress)  # Shift left
                        stat["best_alpha"] = int(255 * best_progress)
    
    def get_rings_color(self, rings_count):
        """Get color for rings based on count"""
        max_rings = 20
        
        if rings_count >= max_rings:
            return (255, 255, 255)
        
        ratio = min(rings_count / max_rings, 1.0)
        red = 255
        green = int(255 * ratio)
        blue = int(255 * ratio)
        
        return (red, green, blue)
    
    def get_enemies_color(self, enemy_count):
        """Get color for enemy kills"""
        max_enemies = 50
        
        if enemy_count >= max_enemies:
            return (255, 255, 255)
        
        ratio = min(enemy_count / max_enemies, 1.0)
        red = 255
        green = int(255 * ratio)
        blue = int(255 * ratio)
        
        return (red, green, blue)
    
    def get_deaths_color(self, death_count):
        """Get color for deaths"""
        if death_count == 0:
            return (255, 255, 255)
        
        ratio = min(death_count / 5.0, 1.0)
        red = 255
        green = int(255 * (1 - ratio))
        blue = int(255 * (1 - ratio))
        
        return (red, green, blue)
    
    def add_sparkle(self):
        """Add enhanced sparkle particle effect"""
        import random
        sparkle = {
            "x": random.randint(50, self.screen_width - 50),
            "y": self.screen_height + 50,
            "speed": random.randint(80, 150),
            "life": random.uniform(2, 4),
            "max_life": random.uniform(2, 4),
            "size": random.randint(3, 8),
            "color": random.choice([(255, 255, 255), (255, 255, 0), (255, 215, 0)]),
            "alpha": 255
        }
        sparkle["max_life"] = sparkle["life"]
        self.sparkle_particles.append(sparkle)
    
    def draw(self, screen, level_index=0):
        """Draw the enhanced results screen"""
        if not self.results_shown or not self.stats:
            return
        
        if level_index != self.current_level_index:
            self.current_level_index = level_index
            
        # Enhanced background
        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.set_alpha(190)
        overlay.fill((5, 5, 15))  # Darker, more dramatic background
        screen.blit(overlay, (0, 0))
        
        self.draw_background_effect(screen)
        
        # Enhanced title with scaling
        if self.title_scale > 0:
            title_text = "LEVEL COMPLETE!"
            title_surf = self.font_title.render(title_text, True, (255, 255, 255))
            title_surf.set_alpha(self.title_alpha)
            
            # Apply scaling
            if self.title_scale != 1.0:
                original_size = title_surf.get_size()
                new_size = (int(original_size[0] * self.title_scale), int(original_size[1] * self.title_scale))
                title_surf = pygame.transform.scale(title_surf, new_size)
            
            title_rect = title_surf.get_rect(center=(self.screen_width // 2, 80))
            
            # Add subtle glow to title
            glow_surf = title_surf.copy()
            glow_surf.set_alpha(self.title_alpha // 3)
            for offset in [(2, 2), (-2, -2), (2, -2), (-2, 2)]:
                glow_rect = title_rect.copy()
                glow_rect.x += offset[0]
                glow_rect.y += offset[1]
                screen.blit(glow_surf, glow_rect)
            
            screen.blit(title_surf, title_rect)
        
        # Enhanced sequential stats
        self.draw_sequential_stats(screen)
            
        # Enhanced rank display with rank-specific animations
        if self.rank_revealed and self.rank_scale > 0:
            self.draw_enhanced_rank(screen)

        # Enhanced sparkles
        for particle in self.sparkle_particles:
            if particle["alpha"] > 0:
                # Create sparkle with varying transparency
                sparkle_surf = pygame.Surface((particle["size"] * 2, particle["size"] * 2), pygame.SRCALPHA)
                sparkle_color = (*particle["color"], particle["alpha"])
                pygame.draw.circle(sparkle_surf, sparkle_color[:3], 
                                 (particle["size"], particle["size"]), particle["size"])
                sparkle_surf.set_alpha(particle["alpha"])
                screen.blit(sparkle_surf, (int(particle["x"] - particle["size"]), 
                                         int(particle["y"] - particle["size"])))
    
    def draw_background_effect(self, screen):
        """Draw enhanced animated background effects"""
        current_time = pygame.time.get_ticks() / 1000.0
        
        # Multiple layers of animated rays
        for layer in range(2):
            for i in range(12):
                angle = (i * math.pi / 6) + (current_time * (0.3 + layer * 0.2))
                distance = 500 + layer * 100
                end_x = self.screen_width // 2 + math.cos(angle) * distance
                end_y = self.screen_height // 2 + math.sin(angle) * distance
                
                # Create multi-layered gradient effect
                for j in range(8):
                    alpha = max(0, 40 - (j * 5) - layer * 15)
                    if alpha > 0:
                        start_distance = j * 8
                        start_x = self.screen_width // 2 + math.cos(angle) * start_distance
                        start_y = self.screen_height // 2 + math.sin(angle) * start_distance
                        
                        color_intensity = 80 - layer * 30
                        ray_color = (color_intensity, color_intensity // 2, color_intensity + 50)
                        
                        ray_surf = pygame.Surface((2, 2), pygame.SRCALPHA)
                        ray_surf.fill((*ray_color, alpha))
                        
                        pygame.draw.line(screen, ray_color, 
                                       (start_x, start_y), (end_x, end_y), 1 + layer)
    
    def draw_sequential_stats(self, screen):
        """Draw statistics with 'New Best!' indicators"""
        if not self.stats_to_show:
            return
            
        stats_y = 180
        line_height = 45
        
        for i, stat_info in enumerate(self.stats_to_show):
            if stat_info["alpha"] > 0:
                y_pos = stats_y + (i * line_height)
                base_x = self.screen_width // 2
                
                # Apply horizontal shift for "New Best!" stats
                shift = stat_info["shift_offset"]
                
                # Draw stat label
                label_surf = self.font_medium.render(stat_info["label"], True, (220, 220, 220))
                label_surf.set_alpha(stat_info["alpha"])
                label_rect = label_surf.get_rect(center=(base_x - 120 + shift, y_pos))
                screen.blit(label_surf, label_rect)
                
                # Draw stat value with enhanced styling
                value_surf = self.font_medium.render(stat_info["value"], True, stat_info["color"])
                value_surf.set_alpha(stat_info["alpha"])
                value_rect = value_surf.get_rect(center=(base_x + 80 + shift, y_pos))
                
                # Add glow effect for improved stats
                if stat_info["is_best"]:
                    glow_surf = self.font_medium.render(stat_info["value"], True, (255, 255, 255))
                    glow_surf.set_alpha(min(stat_info["alpha"] // 3, 80))
                    for glow_offset in [(1, 1), (-1, -1), (1, -1), (-1, 1)]:
                        glow_rect = value_rect.copy()
                        glow_rect.x += glow_offset[0]
                        glow_rect.y += glow_offset[1]
                        screen.blit(glow_surf, glow_rect)
                
                screen.blit(value_surf, value_rect)
                
                # Draw "New Best!" indicator for ANY stat that's a best
                if stat_info["is_best"] and stat_info["best_alpha"] > 0:
                    best_text = "New Best!"
                    best_surf = self.font_small.render(best_text, True, (255, 215, 0))  # Gold color
                    best_surf.set_alpha(stat_info["best_alpha"])
                    best_rect = best_surf.get_rect(center=(base_x + 200, y_pos))
                    
                    # Add pulsing effect
                    pulse = 1.0 + 0.2 * math.sin(pygame.time.get_ticks() * 0.01)
                    if pulse != 1.0:
                        original_size = best_surf.get_size()
                        new_size = (int(original_size[0] * pulse), int(original_size[1] * pulse))
                        best_surf = pygame.transform.scale(best_surf, new_size)
                        best_rect = best_surf.get_rect(center=(base_x + 200, y_pos))
                    
                    # Background highlight for "New Best!"
                    highlight_rect = pygame.Rect(best_rect.x - 10, best_rect.y - 5, 
                                               best_rect.width + 20, best_rect.height + 10)
                    highlight_surf = pygame.Surface((highlight_rect.width, highlight_rect.height), pygame.SRCALPHA)
                    highlight_color = (255, 215, 0, min(stat_info["best_alpha"] // 4, 60))
                    highlight_surf.fill(highlight_color)
                    screen.blit(highlight_surf, highlight_rect)
                    
                    screen.blit(best_surf, best_rect)
    
    def draw_enhanced_rank(self, screen):
        """Draw rank with enhanced visual effects and rank-specific animations"""
        rank = self.get_level_rank()
        rank_color = self.rank_colors.get(rank, (255, 255, 255))
        
        # Enhanced scaling with size limits
        scaled_size = max(10, min(int(60 * self.rank_scale), 120))
        
        try:
            rank_font = pygame.font.Font(daFont, scaled_size)
            rank_text = f"RANK: {rank}"
            
            # Apply rank-specific modifications to color and alpha
            if rank == "D":
                # Slightly dimmed for disappointing performance
                rank_color = tuple(int(c * 0.8) for c in rank_color)
            elif rank == "E":
                # Use fade alpha for crumbling effect
                rank_color = tuple(int(c * (self.rank_fade_alpha / 255.0)) for c in rank_color)
            
            rank_surf = rank_font.render(rank_text, True, rank_color)
            rank_surf.set_alpha(self.rank_fade_alpha)
            
            # Calculate center position with wobble offset for D and E ranks
            center_x = self.screen_width // 2 + self.rank_wobble_offset
            center_y = 480
            center_pos = (center_x, center_y)
            
            # Rank-specific visual effects
            if rank in ["S", "A", "B"]:
                # Keep existing multi-layer glow effect for high ranks
                glow_layers = 3 if rank in ["S", "A"] else 1
                for layer in range(glow_layers):
                    glow_intensity = int((self.rank_glow_intensity * 150) / (layer + 1))
                    if glow_intensity > 0:
                        glow_surf = rank_font.render(rank_text, True, (255, 255, 255))
                        glow_surf.set_alpha(glow_intensity)
                        
                        offset = (layer + 1) * 2
                        for glow_offset in [(offset, offset), (-offset, -offset), 
                                          (offset, -offset), (-offset, offset)]:
                            glow_rect = rank_surf.get_rect(center=(center_pos[0] + glow_offset[0], 
                                                                 center_pos[1] + glow_offset[1]))
                            screen.blit(glow_surf, glow_rect)
            
            elif rank == "C":
                # Subtle, modest glow for C rank - "you passed"
                if self.rank_glow_intensity > 0:
                    glow_intensity = int(self.rank_glow_intensity * 80)  # Much more subtle
                    glow_surf = rank_font.render(rank_text, True, (150, 150, 200))  # Cooler tone
                    glow_surf.set_alpha(glow_intensity)
                    
                    for glow_offset in [(1, 1), (-1, -1), (1, -1), (-1, 1)]:
                        glow_rect = rank_surf.get_rect(center=(center_pos[0] + glow_offset[0], 
                                                             center_pos[1] + glow_offset[1]))
                        screen.blit(glow_surf, glow_rect)
            
            elif rank == "D":
                # No glow effect - boring and disappointing
                # The wobble and dimmed color are the only effects
                pass
            
            elif rank == "E":
                # Draw cracked and lopsided E rank
                # Split into "RANK: " and "E" parts for different effects
                
                # Draw "RANK: " part normally (just wobbles with shaking)
                rank_part_text = "RANK: "
                rank_part_surf = rank_font.render(rank_part_text, True, rank_color)
                rank_part_surf.set_alpha(self.rank_fade_alpha)
                
                # Calculate position for "RANK: " part
                rank_part_rect = rank_part_surf.get_rect()
                rank_part_x = center_x - 50  # Shift left a bit
                rank_part_pos = (rank_part_x, center_y)
                
                # Draw "E" part with tilt
                e_text = "E"
                e_surf = rank_font.render(e_text, True, rank_color)
                e_surf.set_alpha(self.rank_fade_alpha)
                
                # Apply rotation to the E
                if self.e_rank_tilt != 0:
                    e_surf = pygame.transform.rotate(e_surf, self.e_rank_tilt)
                
                # Position the E after "RANK: "
                e_rect = e_surf.get_rect()
                e_x = rank_part_x + (rank_part_rect.width//1.5)
                e_y = center_y + math.sin(pygame.time.get_ticks() * 0.01) * 2  # Slight independent wobble
                e_pos = (e_x, e_y)
                
                # Draw both parts
                screen.blit(rank_part_surf, rank_part_rect.move(rank_part_pos[0] - rank_part_rect.centerx, 
                                                               rank_part_pos[1] - rank_part_rect.centery))
                screen.blit(e_surf, e_rect.move(e_pos[0] - e_rect.centerx, 
                                               e_pos[1] - e_rect.centery))
                
                # Draw crack lines over everything
                if self.crack_lines:
                    for crack in self.crack_lines:
                        if crack['alpha'] > 0 and len(crack['points']) > 1:
                            # Draw the crack as connected line segments
                            for i in range(len(crack['points']) - 1):
                                start_point = crack['points'][i]
                                end_point = crack['points'][i + 1]
                                
                                # Create a surface for the crack line with alpha
                                crack_surf = pygame.Surface((abs(end_point[0] - start_point[0]) + 10, 
                                                           abs(end_point[1] - start_point[1]) + 10), pygame.SRCALPHA)
                                
                                # Calculate relative positions on the crack surface
                                rel_start = (5, 5) if start_point[0] <= end_point[0] else (crack_surf.get_width() - 5, 5)
                                rel_end = (crack_surf.get_width() - 5, crack_surf.get_height() - 5) if start_point[0] <= end_point[0] else (5, crack_surf.get_height() - 5)
                                
                                # Draw crack line
                                pygame.draw.line(crack_surf, (80, 80, 80, crack['alpha']), 
                                               rel_start, rel_end, crack['width'])
                                
                                # Blit the crack
                                crack_rect = crack_surf.get_rect()
                                crack_rect.center = ((start_point[0] + end_point[0]) // 2, 
                                                   (start_point[1] + end_point[1]) // 2)
                                screen.blit(crack_surf, crack_rect)
                
                return  # Skip the normal rank drawing for E rank which has custom rendering
            
            # Draw main rank text (unless it's E rank which has custom rendering)
            if rank != "E":
                rank_rect = rank_surf.get_rect(center=center_pos)
                screen.blit(rank_surf, rank_rect)
            
            # Additional rank-specific decorative effects
            if rank == "S":
                # Golden particle ring around S rank
                particle_count = 8
                ring_radius = 100
                current_time = pygame.time.get_ticks() / 1000.0
                
                for i in range(particle_count):
                    angle = (i * 2 * math.pi / particle_count) + (current_time * 2)
                    particle_x = center_pos[0] + math.cos(angle) * ring_radius
                    particle_y = center_pos[1] + math.sin(angle) * ring_radius
                    
                    particle_surf = pygame.Surface((8, 8), pygame.SRCALPHA)
                    particle_alpha = int(150 + 100 * math.sin(current_time * 4 + i))
                    pygame.draw.circle(particle_surf, (255, 215, 0, particle_alpha), (4, 4), 4)
                    screen.blit(particle_surf, (int(particle_x - 4), int(particle_y - 4)))
            
            elif rank in ["A", "B"]:
                # Pulsing border for A/B ranks
                border_alpha = int(100 + 50 * math.sin(pygame.time.get_ticks() * 0.005))
                border_color = (*rank_color, border_alpha)
                border_rect = pygame.Rect(rank_rect.x - 20, rank_rect.y - 10, 
                                        rank_rect.width + 40, rank_rect.height + 20)
                
                border_surf = pygame.Surface((border_rect.width, border_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(border_surf, border_color, border_surf.get_rect(), 3)
                screen.blit(border_surf, border_rect)
            
            elif rank == "C":
                # Simple, unexciting border that appears occasionally
                if self.rank_glow_intensity > 0.05:  # Only when there's some glow
                    border_alpha = int(60 + 20 * math.sin(pygame.time.get_ticks() * 0.003))
                    border_color = (100, 100, 150, border_alpha)
                    border_rect = pygame.Rect(rank_rect.x - 10, rank_rect.y - 5, 
                                            rank_rect.width + 20, rank_rect.height + 10)
                    
                    border_surf = pygame.Surface((border_rect.width, border_rect.height), pygame.SRCALPHA)
                    pygame.draw.rect(border_surf, border_color, border_surf.get_rect(), 1)
                    screen.blit(border_surf, border_rect)
            
            # D and E ranks get no special decorative effects
                
        except Exception as e:
            # Fallback rendering
            fallback_surf = self.font_large.render(f"RANK: {rank}", True, rank_color)
            fallback_rect = fallback_surf.get_rect(center=(self.screen_width // 2, 480))
            screen.blit(fallback_surf, fallback_rect)
    
    def format_time(self, time_seconds):
        """Format time as MM:SS.ss"""
        minutes = int(time_seconds // 60)
        seconds = time_seconds % 60
        return f"{minutes:02d}:{seconds:05.2f}"
    
    def is_complete(self):
        """Check if the results animation is complete"""
        if not self.results_shown:
            return True
        current_time = pygame.time.get_ticks()
        elapsed = (current_time - self.show_time) / 1000.0
        total_stat_time = len(self.stats_to_show) * self.stat_interval if self.stats_to_show else 6.0
        return elapsed > (self.victory_music_duration + 4.0 + total_stat_time)
    
    def hide(self):
        """Hide the results screen and clean up threads"""
        self.results_shown = False
        
        for thread in self.thread_pool:
            if thread.is_alive():
                thread.join(timeout=0.1)
        
        self.thread_pool.clear()
    
    def cleanup(self):
        """Clean up resources when done"""
        self.hide()
        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except queue.Empty:
                break

class GameSave:
    """Secure save system for game progress with encryption"""
    def __init__(self, save_file="game_save.dat", password=None):
        self.save_file = save_file
        self.password = password or self._get_default_password()
        self.salt = self._get_or_create_salt()
        self.fernet = self._create_fernet()
        self.data = self.load_save()
    
    def _get_default_password(self):
        """Generate a default password based on machine characteristics.
        In production, you might want to use more sophisticated methods."""
        import platform
        import getpass
        
        # Create a password from system info - this makes saves machine-specific
        system_info = f"{platform.node()}-{platform.system()}-{getpass.getuser()}"
        return system_info.encode()
    
    def _get_or_create_salt(self):
        """Get existing salt or create new one. Salt file is stored separately."""
        salt_file = self.save_file + ".salt"
        
        if os.path.exists(salt_file):
            try:
                with open(salt_file, 'rb') as f:
                    return f.read()
            except IOError:
                pass
        
        # Create new salt
        salt = os.urandom(16)  # 16 bytes = 128 bits
        try:
            with open(salt_file, 'wb') as f:
                f.write(salt)
        except IOError as e:
            print(f"Warning: Could not save salt file: {e}")
        
        return salt
    
    def _create_fernet(self):
        """Create Fernet cipher from password and salt"""
        # Derive key from password using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 32 bytes = 256 bits for Fernet
            salt=self.salt,
            iterations=100000,  # Recommended minimum
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.password))
        return Fernet(key)
    
    def load_save(self):
        """Load and decrypt save data from file, create new if doesn't exist"""
        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, 'rb') as f:
                    encrypted_data = f.read()
                
                # Decrypt the data
                decrypted_data = self.fernet.decrypt(encrypted_data)
                return json.loads(decrypted_data.decode('utf-8'))
                
            except Exception as e:
                print(f"Save file corrupted or invalid: {e}")
                # Backup the corrupted file
                backup_file = self.save_file + ".backup"
                try:
                    os.rename(self.save_file, backup_file)
                    print(f"Corrupted save moved to {backup_file}")
                except:
                    pass
                return self.create_new_save()
        else:
            return self.create_new_save()
    
    def create_new_save(self):
        """Create new save data structure"""
        return {
            "levels": {},  # Will store data for each level
            "total_playtime": 0.0,
            "version": "1.0",
            "checksum": self._calculate_checksum({})  # Add integrity check
        }
    
    def _calculate_checksum(self, level_data):
        """Calculate a simple checksum for additional integrity verification"""
        import hashlib
        
        # Create a string representation of critical data
        checksum_data = json.dumps(level_data, sort_keys=True)
        return hashlib.md5(checksum_data.encode()).hexdigest()
    
    def _verify_integrity(self):
        """Verify save file integrity using checksum"""
        if "checksum" not in self.data:
            return True  # Old save format, skip verification
        
        stored_checksum = self.data["checksum"]
        current_checksum = self._calculate_checksum(self.data["levels"])
        
        if stored_checksum != current_checksum:
            print("Warning: Save file integrity check failed - possible tampering detected")
            return False
        
        return True
    
    def save_level_result(self, level_index, stats, results_screen):
        """Save the results for a specific level - only saves if there's an improvement"""
        # Verify integrity before making changes
        if not self._verify_integrity():
            print("Save integrity compromised - creating new save")
            self.data = self.create_new_save()
        
        # Get the rank using the results screen's level-specific thresholds
        rank = results_screen.get_level_rank(level_index)
        score = stats.calculate_score()
        time = stats.completion_time
        rings_collected = stats.rings_collected
        deaths = stats.deaths
        
        level_key = str(level_index)
        
        # Initialize level data if it doesn't exist
        if level_key not in self.data["levels"]:
            self.data["levels"][level_key] = {
                "best_rank": "E",
                "best_time": float('inf'),
                "best_score": 0,
                "best_rings": 0,
                "fewest_deaths": float('inf'),
                "attempts": 0,
                "completed": False
            }
        
        level_data = self.data["levels"][level_key]
        level_data["attempts"] += 1
        level_data["completed"] = True
        
        # Check for improvements
        rank_values = {"S": 6, "A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
        improvements = []
        save_needed = False
        
        # Check rank improvement
        if rank_values[rank] > rank_values[level_data["best_rank"]]:
            level_data["best_rank"] = rank
            improvements.append(f"New best rank: {rank}")
            save_needed = True
        
        # Check time improvement
        if time < level_data["best_time"]:
            level_data["best_time"] = time
            improvements.append(f"New best time: {self.format_time(time)}")
            save_needed = True
        
        # Check score improvement
        if score > level_data["best_score"]:
            level_data["best_score"] = score
            improvements.append(f"New best score: {score}")
            save_needed = True
        
        # Check rings improvement (more rings is better)
        if rings_collected > level_data["best_rings"]:
            level_data["best_rings"] = rings_collected
            improvements.append(f"New best rings: {rings_collected}")
            save_needed = True
        
        # Check deaths improvement (fewer deaths is better)
        if deaths < level_data["fewest_deaths"]:
            level_data["fewest_deaths"] = deaths
            improvements.append(f"New fewest deaths: {deaths}")
            save_needed = True
        
        # Always update total playtime
        self.data["total_playtime"] += time
        
        # Update checksum before saving
        self.data["checksum"] = self._calculate_checksum(self.data["levels"])
        
        # Only save to file if there were improvements or first completion
        if save_needed or level_data["attempts"] == 1:
            self.save_to_file()
            if improvements:
                print(f"Level {level_index} - Improvements: {', '.join(improvements)}")
            else:
                print(f"Level {level_index} completed (first time)")
        else:
            print(f"Level {level_index} completed - no new records")
        
        return improvements  # Return list of improvements for UI feedback
    
    def get_level_best(self, level_index):
        """Get best results for a specific level"""
        level_key = str(level_index)
        if level_key in self.data["levels"]:
            # Handle legacy saves that might not have rings/deaths data
            level_data = self.data["levels"][level_key]
            if "best_rings" not in level_data:
                level_data["best_rings"] = 0
            if "fewest_deaths" not in level_data:
                level_data["fewest_deaths"] = float('inf')
            return level_data
        return None
    
    def display_best_time(self, level_index):
        """Display the best time for a level in MM:SS.ss format"""
        level_data = self.get_level_best(level_index)
        if level_data and level_data["best_time"] < float('inf'):
            return self.format_time(level_data["best_time"])
        return "--:--:--"
    
    def display_best_rank(self, level_index):
        """Display the best rank for a level"""
        level_data = self.get_level_best(level_index)
        if level_data:
            return level_data["best_rank"]
        return "N/A"
    
    def display_best_score(self, level_index):
        """Display the best score for a level"""
        level_data = self.get_level_best(level_index)
        if level_data:
            return level_data["best_score"]
        return 0
    
    def display_best_rings(self, level_index):
        """Display the best rings collected for a level"""
        level_data = self.get_level_best(level_index)
        if level_data:
            return level_data["best_rings"]
        return 0
    
    def display_fewest_deaths(self, level_index):
        """Display the fewest deaths for a level"""
        level_data = self.get_level_best(level_index)
        if level_data and level_data["fewest_deaths"] < float('inf'):
            return level_data["fewest_deaths"]
        return "N/A"
    
    def is_level_completed(self, level_index):
        """Check if a level has been completed"""
        level_data = self.get_level_best(level_index)
        return level_data["completed"] if level_data else False
    
    def get_total_playtime(self):
        """Get total time spent playing"""
        return self.data["total_playtime"]
    
    def save_to_file(self):
        """Encrypt and save current data to file"""
        try:
            # Convert data to JSON string
            json_data = json.dumps(self.data, indent=2)
            
            # Encrypt the JSON data
            encrypted_data = self.fernet.encrypt(json_data.encode('utf-8'))
            
            # Write encrypted data to file
            with open(self.save_file, 'wb') as f:
                f.write(encrypted_data)
                
        except Exception as e:
            print(f"Failed to save game: {e}")
    
    def format_time(self, time_seconds):
        """Format time as MM:SS.ss (same as your existing format)"""
        if time_seconds == float('inf'):
            return "--:--:--"
        minutes = int(time_seconds // 60)
        seconds = time_seconds % 60
        return f"{minutes:02d}:{seconds:05.2f}"
    
    def export_save(self, export_file):
        """Export save data to a readable JSON file (for debugging/backup)"""
        try:
            with open(export_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            print(f"Save exported to {export_file}")
        except Exception as e:
            print(f"Failed to export save: {e}")