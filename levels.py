import pygame, pytmx, os, math
from constants import *
from utils import PhysicsManager, ParallaxBackground
from characters import PurePymunkBall
from utils import Camera, SpatialGrid

pygame.mixer.init()

Level1 = os.path.join("assets", "world building", "Tiled Worlds", "Level1.tmx")
Level2 = os.path.join("assets", "world building", "Tiled Worlds", "Level2.tmx")
level3 = os.path.join("assets", "world building", "Tiled Worlds", "Level3.tmx")
level4 = os.path.join("assets", "world building", "Tiled Worlds", "Level4.tmx")
level5 = os.path.join("assets", "world building", "Tiled Worlds", "Level5.tmx")
levels = [Level1, Level2, level3, level4, level5]
spawn1 = (178, 1900)
spawn2 = (50, 1500)
spawn3 = (50, 900)
spawn4 = (50, 5228)
spawn5 = (50, 2500)
spawn_points = [spawn1, spawn2, spawn3, spawn4, spawn5]

class PymunkLevel:
    """Level that uses spatial partitioning for efficient rendering"""

    def __init__(self, spawn, tmx_map=None, play_music=True):
        x, y = spawn
        self.spawn_point = spawn
        self.physics = PhysicsManager()
        self.TILE_SIZE = 64
        self.ball = PurePymunkBall(self.physics, x, y)
        self.camera = Camera(2000, 2000)  # Default size, will be updated when map loads
        
        # Configure music
        pygame.mixer_music.fadeout(500)
        if play_music:
            try:
                pygame.mixer_music.load(os.path.join("assets", "music", "level 1.mp3"))
                pygame.mixer_music.play(-1)
            except:
                # Fallback to default music if level-specific music is not found
                print("Level music not found!")

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

        # If no backgrounds were loaded, try a fallback
        if not bg_loaded:
            try:
                windmill_path = os.path.join("assets", "backgrounds", "windmillisle.png")
                self.parallax_bg.add_layer(windmill_path, 0.1)
            except:
                # Create a solid color background as last resort
                self.parallax_bg.add_color_layer((100, 100, 255))

        # Create spatial grid for efficient tile rendering
        # Cell size is 2x the tile size to balance between too many and too few cells
        self.spatial_grid = SpatialGrid(cell_size=self.TILE_SIZE * 2)
        
        # Physics and visual objects
        self.static_bodies = []
        self.static_shapes = []
        self.visual_tiles = pygame.sprite.Group()  # Keep this for compatibility
        self.mask_switch_triggers = []
        self.finish_tiles = []  # Store finish line tiles
        self.switch_used = False
        self.level_complete = False  # Track if level is complete
        self.checkpoints = []  # List of checkpoints
        self.total_tiles = 0  # Track total tile count
        
        # Rendering statistics (for debugging/optimization)
        self.rendered_tiles_count = 0
        self.culled_tiles_count = 0

        # Layer tracking - only one is active at a time
        self.active_layer = "F"  # Start with F layer active

        # Buffer zone size (in pixels) to prevent pop-in at screen edges
        self.viewport_buffer = self.TILE_SIZE * 2

        # Load the level
        if tmx_map:
            self.tmx_map = tmx_map
            self.load_tmx(tmx_map)
        else:
            self.create_test_level()

    def load_tmx(self, tmx_map):
        """Load a level from a TMX file with spatial partitioning optimization"""
        # Clear any existing physics objects
        self.clear_physics_objects()

        self.tmx_data = pytmx.load_pygame(tmx_map)
        self.width = self.tmx_data.width * self.TILE_SIZE
        self.height = self.tmx_data.height * self.TILE_SIZE
        self.camera = Camera(self.width, self.height)

        # Load all visual tiles with spatial partitioning
        self.load_visual_tiles()

        # Load only the active layer's collision shapes
        if self.active_layer == "F":
            self.load_collision_layer("Masks F")
        else:
            self.load_collision_layer("Masks B")

        # Process triggers (always present regardless of active layer)
        self.load_triggers()

    def clear_physics_objects(self):
        """Clear all physics objects from space and memory"""
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
        self.finish_tiles = []
        
        # Clear spatial grid
        self.spatial_grid = SpatialGrid(cell_size=self.TILE_SIZE * 2)
        
        # Reset counters
        self.total_tiles = 0
        self.rendered_tiles_count = 0
        self.culled_tiles_count = 0

    def load_visual_tiles(self):
        """Load visual tiles into the spatial grid for efficient rendering"""
        # Clear existing visual tiles
        self.visual_tiles.empty()
        self.finish_tiles = []
        
        # Cache for better performance
        visible_layers = []
        for layer in self.tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                visible_layers.append(layer)

        print(f"Loading {len(visible_layers)} visible layers...")
        
        # Process all layers
        for layer in visible_layers:
            layer_name = layer.name if hasattr(layer, 'name') else "Unnamed"
            print(f"Processing layer: {layer_name}")

            # Set visibility based on layer type
            is_visible = True
            if layer_name == "Masks F" or layer_name == "Masks B":
                is_visible = False  # Always set mask layers to invisible

            # Process tiles in batches for better performance
            batch_count = 0
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
                        if properties.get('Finish Line', False):
                            visual_tile.is_finish_line = True
                            self.finish_tiles.append(visual_tile)
                        else:
                            visual_tile.is_finish_line = False
                    else:
                        visual_tile.is_finish_line = False

                    # Add to the spatial grid for efficient lookup
                    self.spatial_grid.insert(visual_tile)
                    
                    # Also add to the sprite group for compatibility
                    self.visual_tiles.add(visual_tile)
                    
                    # Increment batch counter
                    batch_count += 1
                    self.total_tiles += 1
            
            print(f"  - Added {batch_count} tiles from layer {layer_name}")
            
        print(f"Total tiles loaded: {self.total_tiles}")

    def update(self, dt=1/60.0):
        """Update level state"""
        # Skip updates if level is complete
        if self.level_complete:
            return

        self.ball.update()
        self.physics.step(dt)
        
        # Update camera
        self.camera.update(self.ball)

        # Update parallax background based on camera position
        camera_center_x = -self.camera.offset_x + SCREEN_WIDTH/2
        camera_center_y = -self.camera.offset_y + SCREEN_HEIGHT/2
        self.parallax_bg.update(camera_center_x, camera_center_y)

        # Check for finish line collisions
        self.check_finish_line()

        # Check if the ball has fallen off the bottom of the world
        if self.ball.body.position[1] > self.height - 20:
            self.ball.death()

        # Check for ball death and reset
        if self.ball.is_dead:
            self.reset_ball()

    def draw(self, screen):
        """Draw level with optimized tile rendering"""
        # Draw parallax background
        self.parallax_bg.draw(screen)

        # Get the current viewport rectangle with buffer zone
        viewport = pygame.Rect(
            -self.camera.offset_x, 
            -self.camera.offset_y, 
            SCREEN_WIDTH, 
            SCREEN_HEIGHT
        )
        
        # Expand viewport by buffer to prevent pop-in at edges
        buffered_viewport = viewport.inflate(self.viewport_buffer * 2, self.viewport_buffer * 2)
        
        # Query the spatial grid for visible tiles
        visible_tiles = self.spatial_grid.query_rect(buffered_viewport)
        
        # Update statistics
        self.rendered_tiles_count = 0
        self.culled_tiles_count = self.total_tiles - len(visible_tiles)
        
        # Sort tiles by layer - optimization: pre-define layer order
        layer_order = {"Surface B": 0, "Masks B": 1, "Masks F": 2, "Surface F": 3, "Objects": 4}
        
        # Group tiles by layer for batch rendering
        layer_groups = {}
        for tile in visible_tiles:
            if not tile.visible:
                continue
                
            layer_name = getattr(tile, 'layer_name', 'Unknown')
            if layer_name not in layer_groups:
                layer_groups[layer_name] = []
                
            layer_groups[layer_name].append(tile)
            self.rendered_tiles_count += 1
        
        # Draw the player ball
        screen.blit(self.ball.image, self.camera.apply(self.ball))
        
        # Draw visible tiles by layer order
        for layer_name in sorted(layer_groups.keys(), key=lambda name: layer_order.get(name, 999)):
            for tile in layer_groups[layer_name]:
                screen.blit(tile.image, self.camera.apply(tile))
        
        # Draw finish line tiles
        for tile in self.finish_tiles:
            if tile.visible and buffered_viewport.colliderect(tile.rect):
                screen.blit(flag_image, self.camera.apply(tile))
        
        # Optional: Draw debug statistics
        if True:  # Set to True to show debug info
            font = pygame.font.SysFont(None, 24)
            debug_text = f"Tiles: {self.rendered_tiles_count}/{self.total_tiles} ({int(100*self.rendered_tiles_count/max(1,self.total_tiles))}%)"
            debug_surface = font.render(debug_text, True, (255, 255, 255))
            screen.blit(debug_surface, (10, 40))

    # The remaining methods can stay the same as in the original PymunkLevel class
    def load_collision_layer(self, layer_name):
        """Load collision shapes for a specific layer using masks for precise shapes"""
        # This method doesn't need optimization as physics objects are always active
        # Use the original implementation from PymunkLevel
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
        """Load trigger objects from the Invis Objects layer"""
        # This method is also fine as is - triggers are relatively few
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
                    elif hasattr(obj, 'name') and obj.name == "Checkpoint":
                        self.checkpoints.append((obj.x, obj.y))

    def update_visuals(self):
        """Update visibility of visual tiles based on active layer"""
        # This needs to update all tiles, but we can optimize the iteration
        for tile in self.visual_tiles:
            if tile.layer_name == "Masks F":
                tile.visible = (self.active_layer == "F")
            elif tile.layer_name == "Masks B":
                tile.visible = (self.active_layer == "B")

    def handle_events(self, event):
        """Handle keyboard input for layer switching"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_l:
                self.switch_layer()
                return True  # Event handled
        return False

    def switch_layer(self):
        """Switch between F and B layers"""
        # Toggle active layer
        self.active_layer = "B" if self.active_layer == "F" else "F"
        
        # Clear physics objects
        self.clear_physics_objects()
        
        # Reload collision for the new active layer
        if self.active_layer == "F":
            self.load_collision_layer("Masks F")
        else:
            self.load_collision_layer("Masks B")
            
        # Update tile visibility
        self.update_visuals()
        
        return True

    def check_finish_line(self):
        """Check if player has reached a finish line tile"""
        # Simple collision check between ball and finish tiles
        ball_rect = self.ball.rect

        for tile in self.finish_tiles:
            if tile.visible and ball_rect.colliderect(tile.rect):
                self.level_complete = True
                return True

        return False

    def reset_ball(self):
        """Reset the ball to the last checkpoint or spawn point"""
        if not self.ball.is_dead:
            self.ball.death()
        
        if self.ball.is_dead:
            if self.checkpoints:
                # Reset to the last checkpoint
                last_checkpoint = self.checkpoints[-1]
                spawn_x, spawn_y = last_checkpoint
            else:
                # Reset to the original spawn point
                spawn_x, spawn_y = self.spawn_point

            self.ball.kill()

            # Create a new ball
            self.ball = PurePymunkBall(self.physics, spawn_x, spawn_y)

    def create_body_from_mask(self, surface, x, y, friction=0.8, threshold=128):
        """Create a polygon shape from a surface mask - for precise slopes"""
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
        """Simplify a polygon to reduce vertex count"""
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
        """Determine shape type from tile properties"""
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
        """Determine friction based on shape and angle"""
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
        """Get slope vertices based on angle"""
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
    
class CaveLevel(PymunkLevel):
    """Cave-themed level with fog particle effects, using optimized rendering"""
    def __init__(self, spawn, tmx_map=None):
        # Call the optimized parent class constructor
        super().__init__(spawn, tmx_map)
        
        try:
            pygame.mixer_music.load(os.path.join("assets", "music", "cave.mp3"))
            pygame.mixer_music.play(-1)
        except:
            # If cave music doesn't exist, keep the current music
            print("Cave music not found, keeping current track")
        
        # Override the parallax background with cave-themed images
        self.parallax_bg = ParallaxBackground(SCREEN_WIDTH, SCREEN_HEIGHT)
        
        # Define cave-themed background paths
        cave_bg_paths = [
            {"path": os.path.join("assets", "backgrounds", "Parallax Cave", "1.png"), "factor": 0.08},
            {"path": os.path.join("assets", "backgrounds", "Parallax Cave", "2.png"), "factor": 0.16},
            {"path": os.path.join("assets", "backgrounds", "Parallax Cave", "3.png"), "factor": 0.24},
            {"path": os.path.join("assets", "backgrounds", "Parallax Cave", "4.png"), "factor": 0.32},
            {"path": os.path.join("assets", "backgrounds", "Parallax Cave", "5.png"), "factor": 0.4},
            {"path": os.path.join("assets", "backgrounds", "Parallax Cave", "6.png"), "factor": 0.48},
            {"path": os.path.join("assets", "backgrounds", "Parallax Cave", "7.png"), "factor": 0.56},
            {"path": os.path.join("assets", "backgrounds", "Parallax Cave", "8.png"), "factor": 0.64},
            {"path": os.path.join("assets", "backgrounds", "Parallax Cave", "9.png"), "factor": 0.72}
        ]
        
        # Try to load each cave layer
        bg_loaded = False
        for bg in cave_bg_paths:
            if os.path.exists(bg["path"]):
                if self.parallax_bg.add_layer(bg["path"], bg["factor"]):
                    bg_loaded = True
        
        # If no cave backgrounds are found, use fallback
        if not bg_loaded:
            # Create dark-colored backgrounds to simulate a cave
            self.parallax_bg.add_color_layer((20, 20, 30))  # Very dark blue-grey
            self.parallax_bg.add_color_layer((30, 25, 40), 0.3)  # Dark purple-grey
            self.parallax_bg.add_color_layer((40, 30, 50), 0.5)  # Medium purple-grey
    
    # No need to override the update and draw methods as they're already optimized in the parent class
    
    def update(self, dt=1/60.0):
        """Update level state including fog particles"""
        # Call the parent update method
        super().update(dt)
    
    def draw(self, screen):
        """Draw level with fog effects"""
        # Draw the base level (including parallax background and tiles)
        super().draw(screen)

class SpaceLevel(PymunkLevel):
    """Space-themed level with low gravity and space backgrounds"""
    
    def __init__(self, spawn, tmx_map=None):
        # Call parent constructor
        super().__init__(spawn, tmx_map, play_music=False)

        # Change background music to something space-themed
        try:
            pygame.mixer_music.load(os.path.join("assets", "music", "space.mp3"))
            pygame.mixer_music.play(-1)
        except:
            print("Space music not found, using alternative music")
            try:
                pygame.mixer_music.load(os.path.join("assets", "music", "level 1.mp3"))
                pygame.mixer_music.set_volume(1.0)
                pygame.mixer_music.play(-1)
            except:
                print("Failed to load any music")
        
        # Override gravity with a much lower value
        self.physics.space.gravity = (0, 450)  # Adjusted for space-like conditions
        
        # Set up space-themed parallax background
        self.setup_space_background()
    
    def setup_space_background(self):
        """Set up space-themed parallax background"""
        # Create a new parallax background for space
        self.parallax_bg = ParallaxBackground(SCREEN_WIDTH, SCREEN_HEIGHT)
        
        # Define space-themed background paths
        # We'll look for space backgrounds in "Space" directory, but provide fallbacks
        space_bg_paths = [
            {"path": os.path.join("assets", "backgrounds", "moon", "1.png"), "factor": 0.1}
        ]
        
        # Try to load each space layer
        bg_loaded = False
        for bg in space_bg_paths:
            if os.path.exists(bg["path"]):
                if self.parallax_bg.add_layer(bg["path"], bg["factor"]):
                    bg_loaded = True
                    print(f"Loaded space background: {bg['path']}")
        
        # If no space backgrounds are found, create a starfield procedurally
        if not bg_loaded:
            print("No space backgrounds found. Creating procedural starfield.")
    
    def update(self, dt=1/60.0):
        """Update level state with space-specific behaviors"""
        # Call the parent update method first
        super().update(dt)
    
    def draw(self, screen):
        """Draw the space level with any special effects"""
        # Draw the basic level (parallax background, tiles, player)
        super().draw(screen)
        
        # Add any space-specific visual effects here
        # For example, we could add a subtle glow around the player in space
        
        # Optional: Add a subtle blue glow around the player to simulate spacesuit lights
        if hasattr(self.ball, 'rect'):
            # Create a glow surface slightly larger than the player
            glow_size = self.ball.radius * 3
            glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
            
            # Draw the glow with a radial gradient
            for radius in range(glow_size, 0, -10):
                alpha = int(50 * (radius / glow_size))  # Fade out from center
                pygame.draw.circle(
                    glow_surf, 
                    (100, 150, 255, alpha),  # Bluish glow
                    (glow_size, glow_size), 
                    radius
                )
            
            # Position the glow centered on the player and draw it
            glow_pos = self.camera.apply_rect(pygame.Rect(
                self.ball.rect.centerx - glow_size,
                self.ball.rect.centery - glow_size,
                glow_size * 2,
                glow_size * 2
            ))
            
            # Draw the glow with additive blending for better effect
            screen.blit(glow_surf, glow_pos, special_flags=pygame.BLEND_ADD)