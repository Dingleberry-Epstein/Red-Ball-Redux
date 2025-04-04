import pygame
import pymunk
import pytmx
import os
import sys
import time
from constants import *
from utils import PhysicsManager, ParallaxBackground
from characters import PurePymunkBall
from utils import Camera
import math

class PymunkLevel:
    """Level that loads mask layers on demand, creating and destroying hitboxes completely when switching."""

    def __init__(self, tmx_map=None):
        self.physics = PhysicsManager()
        self.TILE_SIZE = 64
        self.ball = PurePymunkBall(self.physics, 178, 1800)
        self.camera = Camera(2000, 2000)
        
        # Set up parallax background
        self.parallax_bg = ParallaxBackground(SCREEN_WIDTH, SCREEN_HEIGHT)
        
        # Add background layers with different parallax factors
        bg_paths = [
            {"path": os.path.join("assets", "backgrounds", "DarkForest", "bg_shadows.png"), "factor": 0.1},
            {"path": os.path.join("assets", "backgrounds", "DarkForest", "bg_far.png"), "factor": 0.3},
            {"path": os.path.join("assets", "backgrounds", "DarkForest", "bg_mid.png"), "factor": 0.5},
            {"path": os.path.join("assets", "backgrounds", "DarkForest", "bg_near.png"), "factor": 0.7}
        ]
        
        # Try to load each layer
        bg_loaded = False
        for bg in bg_paths:
            if os.path.exists(bg["path"]):
                if self.parallax_bg.add_layer(bg["path"], bg["factor"]):
                    bg_loaded = True
        
        # If no backgrounds were loaded, try the original windmillisle.png or create a fallback
        if not bg_loaded:
            try:
                windmill_path = os.path.join("assets", "backgrounds", "windmillisle.png")
                self.parallax_bg.add_layer(windmill_path, 0.1)
            except:
                # Create a solid color background as last resort
                self.parallax_bg.add_color_layer((100, 100, 255))
        
        # Physics and visual objects
        self.static_bodies = []
        self.static_shapes = []
        self.visual_tiles = pygame.sprite.Group()
        self.mask_switch_triggers = []
        self.finish_tiles = []  # Store finish line tiles
        self.switch_used = False
        self.level_complete = False  # Track if level is complete
        
        # Layer tracking - only one is active at a time
        self.active_layer = "F"  # Start with F layer active
        
        # Load the level
        if tmx_map:
            self.tmx_map = tmx_map
            self.load_tmx(tmx_map)
        else:
            self.create_test_level()

    def create_test_level(self):
        """Create a simple test level with F and B sections."""
        # Set level dimensions
        self.width = 3000
        self.height = 1000
        
        # Update camera bounds
        self.camera = Camera(self.width, self.height)
        
        # Create shapes for currently active layer only
        if self.active_layer == "F":
            self.create_f_layer_test()
        else:
            self.create_b_layer_test()
        
        # Create a test switch that's always present
        body, shape = self.physics.create_box(350, 450, 64, 64, is_static=True, collision_type="switch")
        shape.collision_type = self.physics.collision_types["switch"]
        shape.used = False
        shape.switch_id = 0
        self.mask_switch_triggers.append(shape)
        self.static_bodies.append(body)
        self.static_shapes.append(shape)
        
        # Create visual representations for both layers
        self.create_test_visuals()

    def create_f_layer_test(self):
        """Create test level shapes for F layer."""
        # Ground platform
        body, shape = self.physics.create_box(-200, 500, 1000, 50)
        self.static_bodies.append(body)
        self.static_shapes.append(shape)

        # First slope
        slope_vertices = [(800, 500), (1000, 400), (1000, 500)]
        body, shape = self.physics.create_poly(slope_vertices)
        if body and shape:
            self.static_bodies.append(body)
            self.static_shapes.append(shape)

        # Middle platform
        body, shape = self.physics.create_box(1000, 400, 300, 50)
        self.static_bodies.append(body)
        self.static_shapes.append(shape)

        # Second slope
        slope2_vertices = [(1300, 400), (1500, 550), (1300, 550)]
        body, shape = self.physics.create_poly(slope2_vertices, friction=0.7)
        if body and shape:
            self.static_bodies.append(body)
            self.static_shapes.append(shape)

        # Bottom platform
        body, shape = self.physics.create_box(1500, 550, 400, 50)
        self.static_bodies.append(body)
        self.static_shapes.append(shape)

        # Loop
        self.create_loop(2100, 450, 100, 12)  # Reduced segments from 16 to 12 for performance

        # Platform before loop
        body, shape = self.physics.create_box(1900, 550, 100, 50)
        self.static_bodies.append(body)
        self.static_shapes.append(shape)

        # Platform after loop
        body, shape = self.physics.create_box(2300, 550, 200, 50)
        self.static_bodies.append(body)
        self.static_shapes.append(shape)

    def create_b_layer_test(self):
        """Create test level shapes for B layer."""
        # Alternative path - higher platforms
        body, shape = self.physics.create_box(400, 400, 600, 50)
        self.static_bodies.append(body)
        self.static_shapes.append(shape)

        # Second platform
        body, shape = self.physics.create_box(1200, 300, 400, 50)
        self.static_bodies.append(body)
        self.static_shapes.append(shape)
        
        # End platform
        body, shape = self.physics.create_box(1800, 350, 600, 50)
        self.static_bodies.append(body)
        self.static_shapes.append(shape)

    def create_test_visuals(self):
        """Create visual representations for test level."""
        # F Layer visuals
        f_ground = pygame.sprite.Sprite()
        f_ground.image = pygame.Surface((1000, 50))
        f_ground.image.fill((200, 0, 0))
        f_ground.rect = pygame.Rect(-200, 500, 1000, 50)
        f_ground.layer_name = "Masks F"
        f_ground.visible = (self.active_layer == "F")
        f_ground.has_collision = True
        f_ground.is_finish_line = False
        self.visual_tiles.add(f_ground)
        
        # Add slope visuals
        slope1_visual = pygame.Surface((200, 100), pygame.SRCALPHA)
        pygame.draw.polygon(slope1_visual, (200, 0, 0), [(0, 100), (200, 0), (200, 100)])
        slope1_sprite = pygame.sprite.Sprite()
        slope1_sprite.image = slope1_visual
        slope1_sprite.rect = pygame.Rect(800, 400, 200, 100)
        slope1_sprite.layer_name = "Masks F"
        slope1_sprite.visible = (self.active_layer == "F")
        slope1_sprite.has_collision = True
        slope1_sprite.is_finish_line = False
        self.visual_tiles.add(slope1_sprite)
        
        # B Layer visuals
        b_platform1 = pygame.sprite.Sprite()
        b_platform1.image = pygame.Surface((600, 50))
        b_platform1.image.fill((0, 0, 200))
        b_platform1.rect = pygame.Rect(400, 400, 600, 50)
        b_platform1.layer_name = "Masks B"
        b_platform1.visible = (self.active_layer == "B")
        b_platform1.has_collision = True
        b_platform1.is_finish_line = False
        self.visual_tiles.add(b_platform1)
        
        b_platform2 = pygame.sprite.Sprite()
        b_platform2.image = pygame.Surface((400, 50))
        b_platform2.image.fill((0, 0, 200))
        b_platform2.rect = pygame.Rect(1200, 300, 400, 50)
        b_platform2.layer_name = "Masks B"
        b_platform2.visible = (self.active_layer == "B")
        b_platform2.has_collision = True
        b_platform2.is_finish_line = False
        self.visual_tiles.add(b_platform2)
        
        # Add finish line visual for test level
        finish_sprite = pygame.sprite.Sprite()
        finish_sprite.image = pygame.Surface((64, 64))
        finish_sprite.image.fill((255, 255, 255))
        finish_sprite.rect = pygame.Rect(2500, 550, 64, 64)
        finish_sprite.layer_name = "Objects"
        finish_sprite.visible = True
        finish_sprite.has_collision = False
        finish_sprite.is_finish_line = True
        self.finish_tiles.append(finish_sprite)  # Add to finish tiles list
        self.visual_tiles.add(finish_sprite)

    def create_loop(self, center_x, center_y, radius, segments=12):
        """Create a circular loop with segments (reduced from 16 to 12 segments)."""
        angle_step = 2 * math.pi / segments
        points = []

        # Generate points around the circle
        for i in range(segments + 1):
            angle = i * angle_step
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            points.append((x, y))

        # Create segments between the points
        for i in range(segments):
            angle = i * angle_step
            position_factor = math.sin(angle)
            segment_friction = 0.5 + 0.4 * (position_factor + 1) / 2
            body, shape = self.physics.create_segment(points[i], points[i + 1], thickness=5, friction=segment_friction)
            if body and shape:
                self.static_bodies.append(body)
                self.static_shapes.append(shape)

    def load_tmx(self, tmx_map):
        """Load a level from a TMX file, loading only the active mask layer."""
        # Clear any existing physics objects
        self.clear_physics_objects()

        self.tmx_data = pytmx.load_pygame(tmx_map)
        self.width = self.tmx_data.width * self.TILE_SIZE
        self.height = self.tmx_data.height * self.TILE_SIZE
        self.camera = Camera(self.width, self.height)
        
        # Load all visual tiles first - both Surface F, Surface B, Masks F, Masks B, Objects
        self.load_visual_tiles()
        
        # Load only the active layer's collision shapes
        if self.active_layer == "F":
            self.load_collision_layer("Masks F")
        else:
            self.load_collision_layer("Masks B")
        
        # Process triggers (always present regardless of active layer)
        self.load_triggers()

    def clear_physics_objects(self):
        """Clear all physics objects from space and memory."""
        # Remove from physics space
        for shape in self.static_shapes:
            try:
                self.physics.space.remove(shape)
            except:
                pass
                
        for body in self.static_bodies:
            try:
                self.physics.space.remove(body)
            except:
                pass
        
        # Clear all lists
        self.static_bodies = []
        self.static_shapes = []
        self.mask_switch_triggers = []
        self.finish_tiles = []  # Clear finish tiles

    def load_visual_tiles(self):
        """Load visual tiles for all layers - Surface F, Surface B, Masks F, Masks B, Objects."""
        # Clear existing visual tiles
        self.visual_tiles.empty()
        self.finish_tiles = []  # Clear finish tiles
        
        # Cache for better performance
        visible_layers = []
        for layer in self.tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                visible_layers.append(layer)
        
        # Process all layers
        for layer in visible_layers:
            layer_name = layer.name if hasattr(layer, 'name') else "Unnamed"
            
            # Set visibility based on active layer for mask layers
            is_visible = True
            if layer_name == "Masks F":
                is_visible = (self.active_layer == "F")
            elif layer_name == "Masks B":
                is_visible = (self.active_layer == "B")
            
            # Process tiles in batches for better performance
            tiles_to_add = []
            
            for x, y, gid in layer.tiles():
                if gid:
                    world_x = x * self.TILE_SIZE
                    world_y = y * self.TILE_SIZE
                    
                    # Get tile image
                    tile_image = gid
                    if not tile_image:
                        tile_image = pygame.Surface((self.TILE_SIZE, self.TILE_SIZE))
                        tile_image.fill((255, 0, 0))
                    
                    # Create visual tile
                    visual_tile = pygame.sprite.Sprite()
                    visual_tile.image = pygame.transform.scale(tile_image, (self.TILE_SIZE, self.TILE_SIZE))
                    visual_tile.rect = pygame.Rect(world_x, world_y, self.TILE_SIZE, self.TILE_SIZE)
                    visual_tile.has_collision = (layer_name == "Masks F" or layer_name == "Masks B")
                    visual_tile.layer_name = layer_name
                    visual_tile.visible = is_visible
                    
                    # Check if this is a finish line tile in Objects layer
                    if layer_name == "Objects":
                        properties = self.tmx_data.get_tile_properties_by_gid(gid) or {}
                        if properties.get('Finish Line', True):  # Check for exact "Finish Line" property
                            visual_tile.is_finish_line = True
                            self.finish_tiles.append(visual_tile)  # Add to finish tiles list
                        else:
                            visual_tile.is_finish_line = False
                    else:
                        visual_tile.is_finish_line = False
                    
                    tiles_to_add.append(visual_tile)
            
            # Add tiles in a batch
            self.visual_tiles.add(tiles_to_add)

    def load_collision_layer(self, layer_name):
        """Load collision shapes for a specific layer using masks for precise shapes."""
        processed_tiles = set()
        
        # Cache layers for better performance
        collision_layers = []
        for layer in self.tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer) and layer.name == layer_name:
                collision_layers.append(layer)
        
        for layer in collision_layers:
            for x, y, gid in layer.tiles():
                if gid:
                    world_x = x * self.TILE_SIZE
                    world_y = y * self.TILE_SIZE
                    tile_key = (world_x, world_y)
                    
                    # Skip if already processed
                    if tile_key in processed_tiles:
                        continue
                    processed_tiles.add(tile_key)
                    
                    # Get tile properties
                    properties = self.tmx_data.get_tile_properties_by_gid(gid) or {}
                    shape_type = self.get_shape_type(properties)
                    angle = properties.get('angle', 0)
                    friction = self.get_friction_for_shape(shape_type, angle)
                    
                    # Create collision shape based on type
                    if shape_type == "slope":
                        vertices = self.get_slope_vertices(world_x, world_y, self.TILE_SIZE, self.TILE_SIZE, angle)
                        if len(vertices) >= 3:
                            body, shape = self.physics.create_poly(vertices, friction=friction)
                            if body and shape:
                                self.static_bodies.append(body)
                                self.static_shapes.append(shape)
                    else:
                        # Try to create from mask first - important for precise collision detection
                        tile_image = gid
                        success = False
                        if tile_image:
                            success = self.create_body_from_mask(tile_image, world_x, world_y, friction)
                        
                        # Fall back to box if needed
                        if not success:
                            body, shape = self.physics.create_box(world_x, world_y, self.TILE_SIZE, self.TILE_SIZE, friction=friction)
                            if body and shape:
                                self.static_bodies.append(body)
                                self.static_shapes.append(shape)

    def load_triggers(self):
        """Load trigger objects from the Invis Objects layer."""
        for layer in self.tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledObjectGroup) and layer.name == "Invis Objects":
                for i, obj in enumerate(layer):
                    if hasattr(obj, 'name') and obj.name == "Loop Switch":
                        # Create switch
                        body, shape = self.physics.create_box(
                            obj.x, obj.y, obj.width, obj.height, 
                            is_static=True, 
                            collision_type="switch"
                        )
                        
                        if body and shape:
                            shape.used = False
                            shape.switch_id = i
                            shape.collision_type = self.physics.collision_types["switch"]
                            
                            self.mask_switch_triggers.append(shape)
                            self.static_bodies.append(body)
                            self.static_shapes.append(shape)

    def update_visuals(self):
        """Update visibility of visual tiles based on active layer."""
        for tile in self.visual_tiles:
            if tile.layer_name == "Masks F":
                tile.visible = (self.active_layer == "F")
            elif tile.layer_name == "Masks B":
                tile.visible = (self.active_layer == "B")

    def handle_events(self, event):
        """Handle keyboard input for layer switching."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_l:
                self.switch_layer()
                return True  # Event handled
        return False

    def update(self, dt=1/60.0):
        """Update level state."""
        # Skip updates if level is complete
        if self.level_complete:
            return
            
        self.ball.update()
        self.physics.step(dt)
        self.camera.update(self.ball)
        
        # Update parallax background based on camera position
        camera_center_x = -self.camera.offset_x + SCREEN_WIDTH/2
        camera_center_y = -self.camera.offset_y + SCREEN_HEIGHT/2
        self.parallax_bg.update(camera_center_x, camera_center_y)
        
        # Check for finish line collisions
        self.check_finish_line()

    def check_finish_line(self):
        """Check if player has reached a finish line tile."""
        # Simple collision check between ball and finish tiles
        ball_rect = self.ball.rect
        
        for tile in self.finish_tiles:
            if tile.visible and ball_rect.colliderect(tile.rect):
                # Instead of freezing and quitting, just set the level_complete flag
                self.level_complete = True
                return True
        
        return False

    def draw(self, screen):
        """Draw level with visibility controls."""
        # Draw parallax background
        self.parallax_bg.draw(screen)
        
        # Get visible tiles within viewport
        viewport_rect = self.camera.viewport
        
        # Optimization: Only process visible tiles
        visible_tiles = []
        for tile in self.visual_tiles:
            if tile.visible and tile.rect.colliderect(viewport_rect):
                visible_tiles.append(tile)
        
        # Sort tiles by layer - optimization: pre-define layer order
        layer_order = {"Surface B": 0, "Masks B": 1, "Masks F": 2, "Surface F": 3, "Objects": 4}
        visible_tiles.sort(key=lambda t: layer_order.get(getattr(t, 'layer_name', ''), 0))
        
        # Draw visible tiles
        for tile in visible_tiles:
            screen.blit(tile.image, self.camera.apply(tile))
            
        for tile in self.finish_tiles:
            screen.blit(flag_image, self.camera.apply(tile))
        
        # Draw the player ball
        screen.blit(self.ball.image, self.camera.apply(self.ball))
        
    def create_body_from_mask(self, surface, x, y, friction=0.8, threshold=128):
        """Create a polygon shape from a surface mask - crucial for precise slopes."""
        try:
            if surface is None:
                return False
                
            scaled_surface = pygame.transform.scale(surface, (self.TILE_SIZE, self.TILE_SIZE))
            mask = pygame.mask.from_surface(scaled_surface)
            outline = mask.outline()
            if len(outline) < 3:
                return False
            simplified_outline = self.simplify_polygon(outline, tolerance=2)
            vertices = [(x + point[0], y + point[1]) for point in simplified_outline]
            if len(vertices) >= 3:
                body, shape = self.physics.create_poly(vertices, friction=friction)
                if body and shape:
                    self.static_bodies.append(body)
                    self.static_shapes.append(shape)
                    return True
        except Exception as e:
            pass
        return False

    def simplify_polygon(self, points, tolerance=2):
        """Simplify a polygon."""
        if len(points) <= 3:
            return points
        result = [points[0]]
        for i in range(1, len(points)):
            last = result[-1]
            current = points[i]
            # Use squared distance to avoid square root calculation
            squared_dist = (current[0] - last[0])**2 + (current[1] - last[1])**2
            if squared_dist >= tolerance**2:
                result.append(current)
        if len(result) < 3:
            return points
        return result

    def get_shape_type(self, properties):
        """Determine shape type."""
        if not properties:
            return "box"
        shape_props = ["shape_type", "shape", "type"]
        for prop in shape_props:
            if prop in properties:
                value = str(properties[prop]).lower()
                if value in ["slope", "triangle", "ramp"]:
                    return "slope"
                if value in ["loop", "circle"]:
                    return "loop"
        if "angle" in properties and properties["angle"] != 0:
            return "slope"
        return "mask"

    def get_friction_for_shape(self, shape_type, angle):
        """Determine friction based on shape and angle."""
        if shape_type == "slope":
            angle_abs = abs(angle) % 360
            if angle_abs > 180:
                angle_abs = 360 - angle_abs
            if angle_abs > 90:
                angle_abs = 180 - angle_abs
            return 0.8 - (angle_abs / 90.0) * 0.3
        elif shape_type == "loop":
            return 0.6
        else:
            return 0.8

    def get_slope_vertices(self, x, y, width, height, angle):
        """Get slope vertices."""
        if angle == 45:
            return [(x, y + height), (x + width, y + height), (x + width, y)]
        elif angle == -45 or angle == 315:
            return [(x, y), (x, y + height), (x + width, y + height)]
        elif angle == 30:
            return [(x, y + height), (x + width, y + height), (x + width, y + height // 2)]
        elif angle == -30 or angle == 330:
            return [(x, y + height // 2), (x, y + height), (x + width, y + height)]
        angle = angle % 360
        if 0 < angle < 90:
            h = height * (angle / 90)
            return [(x, y + height), (x + width, y + height), (x + width, y + height - h)]
        elif 270 < angle < 360:
            pos_angle = 360 - angle
            h = height * (pos_angle / 90)
            return [(x, y + height - h), (x, y + height), (x + width, y + height)]
        return [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]