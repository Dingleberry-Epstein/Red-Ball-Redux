import pygame, pytmx, os, random, math, time, threading
from constants import *
from utils import PhysicsManager, ParallaxBackground, DialogueSystem, LevelTimer, GameStats, ResultsScreen, GameSave
from characters import PurePymunkBall, NPCCharacter, BlueBall, SignNPC, Cubodeez_The_Almighty_Cube as cb
from utils import Camera, SpatialGrid
from objects import RocketLauncher, Rocket, Credits, Explosion, Coin
pygame.mixer.init()

Level1 = os.path.join("assets", "world building", "Tiled Worlds", "Level1.tmx")
Level2 = os.path.join("assets", "world building", "Tiled Worlds", "Level2.tmx")
level3 = os.path.join("assets", "world building", "Tiled Worlds", "Level3.tmx")
level4 = os.path.join("assets", "world building", "Tiled Worlds", "Level4.tmx")
level5 = os.path.join("assets", "world building", "Tiled Worlds", "Level5.tmx")
level6 = os.path.join("assets", "world building", "Tiled Worlds", "Boss.tmx")
levels = [Level1, Level2, level3, level4, level5, level6]
spawn1 = (178, 1900)
spawn2 = (50, 1500)
spawn3 = (50, 900)
spawn4 = (50, 5228)
spawn5 = (50, 2500)
spawn6 = (250, 450)
spawn_points = [spawn1, spawn2, spawn3, spawn4, spawn5, spawn6]

class PymunkLevel:
    """Level that uses spatial partitioning for efficient rendering"""
    def __init__(self, spawn, tmx_map=None, play_music=True, level_index=0, gamesave=None):
        self._level_index = level_index  # Store the level index for music and stats
        x, y = spawn
        self._spawn_point = spawn
        self._physics = PhysicsManager()
        self._TILE_SIZE = 64
        self._ball = PurePymunkBall(self._physics, x, y)
        self._camera = Camera(2000, 2000)  # Default size, will be updated when map loads
        self._game_ref = None  # Reference to the game object, if needed
        self._gamesave = gamesave
        # Initialize dialogue system
        self._setup_dialogue_system()
        
        # Play level music
        if play_music:
            self._setup_music()
        
        self._music_switched = False  # Track if music has been switched
        self._music_switching = False  # New flag to prevent multiple switches
        self._pending_track = None     # Track to load after fadeout

        # Set up parallax background
        self._setup_parallax_background()

        # Create spatial grid for efficient tile rendering
        # Cell size is 2x the tile size to balance between too many and too few cells
        self._spatial_grid = SpatialGrid(cell_size=self._TILE_SIZE * 2)
        
        # Physics and visual objects
        self._static_bodies = []
        self._static_shapes = []
        self._visual_tiles = pygame.sprite.Group()  # Keep this for compatibility
        self._mask_switch_triggers = []
        self._finish_tiles = []  # Store finish line tiles
        self._coin_tiles = []
        self._music_switch_tiles = []
        self._switch_used = False
        self._level_complete = False  # Track if level is complete
        self._checkpoints = []  # List of checkpoints
        self._total_tiles = 0  # Track total tile count
        
        # Rendering statistics (for debugging/optimization)
        self._rendered_tiles_count = 0
        self._culled_tiles_count = 0

        # Layer tracking - only one is active at a time
        self._active_layer = "F"  # Start with F layer active

        # Buffer zone size (in pixels) to prevent pop-in at screen edges
        self._viewport_buffer = self._TILE_SIZE * 2

            # Add timer and stats systems
        self._timer = LevelTimer()
        self._stats = GameStats()
        self._results_screen = ResultsScreen(SCREEN_WIDTH, SCREEN_HEIGHT, self._gamesave)
        self._showing_results = False

        # Load the level
        if tmx_map:
            self._tmx_map = tmx_map
            self.load_tmx(tmx_map)
        else:
            self.create_test_level()

        self._timer.start()  # Start the timer when the level is created
        self._secret_found = False  # Track if a secret has been found

    def _setup_dialogue_system(self):
        """Initialize the dialogue system"""
        self._dialogue_system = DialogueSystem(SCREEN_WIDTH, SCREEN_HEIGHT, ui_manager=None)
        self._in_dialogue = False
        self._showing_player_choice = False
        self._waiting_for_player_continue = False  # Flag to wait for player to continue
        self._player_choice_text = ""
        self._player_choice_index = -1
        self._waiting_for_player_dialogue = False
        self._current_npc = None
        self._dialogue_just_started = False
        
        # Load portrait placeholder
        self._load_player_portrait()

    def _load_player_portrait(self):
        """Load the player portrait for dialogues"""
        try:
            self._player_portrait = pygame.image.load(os.path.join("assets", "sprites", "red ball portrait.png")).convert_alpha()
            self._player_portrait = pygame.transform.scale(self._player_portrait, (84, 84))
        except:
            # Create a fallback portrait if image not found
            self._player_portrait = pygame.Surface((84, 84), pygame.SRCALPHA)
            pygame.draw.circle(self._player_portrait, (255, 0, 0), (42, 42), 38)
            pygame.draw.circle(self._player_portrait, (0, 0, 0), (42, 42), 38, 2)

    def _setup_music(self):
        """Set up the level music"""
        global CURRENT_TRACK
        # Configure music
        if not CURRENT_TRACK == 'boss':
            pygame.mixer_music.fadeout(500)
        try:
            pygame.mixer_music.load(os.path.join("assets", "music", "level 1.mp3"))
            CURRENT_TRACK = 'level 1'
            pygame.mixer_music.play(-1)
        except:
            # Fallback to default music if level-specific music is not found
            print("Level music not found!")

    def _setup_parallax_background(self):
        """Set up the parallax background for the level"""
        self._parallax_bg = ParallaxBackground(SCREEN_WIDTH, SCREEN_HEIGHT)

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
                if self._parallax_bg.add_layer(bg["path"], bg["factor"]):
                    bg_loaded = True

        # If no backgrounds were loaded, try a fallback
        if not bg_loaded:
            try:
                windmill_path = os.path.join("assets", "backgrounds", "windmillisle.png")
                self._parallax_bg.add_layer(windmill_path, 0.1)
            except:
                # Create a solid color background as last resort
                self._parallax_bg.add_color_layer((100, 100, 255))

    @property
    def physics(self):
        return self._physics
    
    @property
    def width(self):
        return self._width if hasattr(self, '_width') else 2000
    
    @width.setter
    def width(self, value):
        self._width = value
    
    @property
    def height(self):
        return self._height if hasattr(self, '_height') else 2000
    
    @height.setter
    def height(self, value):
        self._height = value
    
    @property
    def ball(self):
        return self._ball
    
    @property
    def camera(self):
        return self._camera
    
    @property
    def game_ref(self):
        return self._game_ref
    
    @game_ref.setter
    def game_ref(self, value):
        self._game_ref = value
    
    @property
    def spatial_grid(self):
        return self._spatial_grid
    
    @property
    def visual_tiles(self):
        return self._visual_tiles
    
    @property
    def static_shapes(self):
        return self._static_shapes
    
    @property
    def level_complete(self):
        return self._level_complete
    
    @level_complete.setter
    def level_complete(self, value):
        self._level_complete = value
    
    @property
    def current_npc(self):
        return self._current_npc
    
    @property
    def in_dialogue(self):
        return self._in_dialogue
    
    def collect_ring(self):
        """Call this when player collects a ring"""
        self._stats.rings_collected += 1

    def defeat_enemy(self):
        """Call this when player defeats an enemy"""
        self._stats.enemies_defeated += 1

    def find_secret(self):
        """Call this when player finds a secret area/item"""
        self._stats.secrets_found += 1

    def player_died(self):
        """Call this when player dies"""
        self._stats.deaths += 1

    def reach_checkpoint(self):
        """Call this when player reaches a checkpoint"""
        self._stats.checkpoints_reached += 1

    def load_tmx(self, tmx_map):
        """Load a level from a TMX file with spatial partitioning optimization"""
        # Clear any existing physics objects
        self.clear_physics_objects()

        self._tmx_data = pytmx.load_pygame(tmx_map)
        self.width = self._tmx_data.width * self._TILE_SIZE
        self.height = self._tmx_data.height * self._TILE_SIZE
        self._camera = Camera(self.width, self.height)

        # Load all visual tiles with spatial partitioning
        self.load_visual_tiles()

        # Load only the active layer's collision shapes
        if self._active_layer == "F":
            self.load_collision_layer("Masks F")
        else:
            self.load_collision_layer("Masks B")

        # Process triggers (always present regardless of active layer)
        self.load_triggers()
        self.initialize_npcs()
        self.initialize_coins()

    def clear_physics_objects(self):
        """Clear all physics objects from space and memory"""
        # Remove from physics space
        for shape in self._static_shapes:
            try:
                self._physics.space.remove(shape)
            except:
                pass

        for body in self._static_bodies:
            try:
                self._physics.space.remove(body)
            except:
                pass

        # Clear all lists
        self._static_bodies = []
        self._static_shapes = []
        self._mask_switch_triggers = []
        self._finish_tiles = []
        self._music_switch_tiles = []
        self.NPCs = pygame.sprite.Group()
        
        # Clear spatial grid
        self._spatial_grid = SpatialGrid(cell_size=self._TILE_SIZE * 2)
        
        # Reset counters
        self._total_tiles = 0
        self._rendered_tiles_count = 0
        self._culled_tiles_count = 0

    def load_visual_tiles(self):
        """Load visual tiles into the spatial grid with improved NPC and sign handling"""
        # Clear existing visual tiles
        self._visual_tiles.empty()
        self._finish_tiles = []
        self.npc_tiles = []  # Store NPC tiles for initialization later
        self.sign_objects = []  # New list to store sign objects
        self._coin_tiles = []  # Store coin tiles for initialization later
        self.NPCs = pygame.sprite.Group()  # Initialize NPCs group

        # Cache for better performance
        visible_layers = []
        for layer in self._tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                visible_layers.append(layer)

        print(f"Loading {len(visible_layers)} visible layers...")

        # Process all tile layers first
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
                    world_x = x * self._TILE_SIZE
                    world_y = y * self._TILE_SIZE

                    # Get the tile image
                    if isinstance(gid, pygame.Surface):
                        tile_image = gid  # Use it directly
                    else:
                        try:
                            tile_image = self._tmx_data.get_tile_image_by_gid(gid)
                        except (TypeError, ValueError) as e:
                            print(f"Error getting image for GID {gid}: {e}")
                            tile_image = None

                    # Fallback if we couldn't get a proper image
                    if not tile_image:
                        tile_image = pygame.Surface((self._TILE_SIZE, self._TILE_SIZE))
                        tile_image.fill((255, 0, 0))

                    # Create visual tile
                    visual_tile = pygame.sprite.Sprite()
                    visual_tile.image = pygame.transform.scale(tile_image, (self._TILE_SIZE, self._TILE_SIZE))
                    visual_tile.rect = pygame.Rect(world_x, world_y, self._TILE_SIZE, self._TILE_SIZE)
                    visual_tile.has_collision = (layer_name == "Masks F" or layer_name == "Masks B")
                    visual_tile.layer_name = layer_name
                    visual_tile.visible = is_visible
                    visual_tile.is_finish_line = False  # Default value

                    # Properties handling for Objects layer
                    if layer_name == "Objects":
                        self._process_object_layer_tile(visual_tile, gid, layer, x, y, world_x, world_y, layer_index=self._tmx_data.layers.index(layer))

                    # Add to the spatial grid for efficient lookup
                    self._spatial_grid.insert(visual_tile)

                    # Also add to the sprite group for compatibility
                    self._visual_tiles.add(visual_tile)

                    # Increment batch counter
                    batch_count += 1
                    self._total_tiles += 1
                    
            print(f"  - Added {batch_count} tiles from layer {layer_name}")
        
        # Now process object layers for direct object placement (especially signs)
        self._process_object_layers()
        
        print(f"Total tiles loaded: {self._total_tiles}")
        print(f"Found {len(self._finish_tiles)} finish line tiles")
        print(f"Found {len(self.npc_tiles)} NPC tiles for initialization")
        print(f"Found {len(self.sign_objects)} direct sign objects")

    def _process_object_layer_tile(self, visual_tile, gid, layer, x, y, world_x, world_y, layer_index):
        """Process a tile from the Objects layer"""
        # Get properties from the tile
        try:
            if isinstance(gid, pygame.Surface):
                # Try to get properties through the layer directly
                properties = self._tmx_data.get_tile_properties(x, y, layer_index) or {}
            else:
                # Standard way to get properties
                properties = self._tmx_data.get_tile_properties_by_gid(gid) or {}
        except Exception as e:
            print(f"Error getting properties: {e}")
            properties = {}

        # Handle finish line property
        if properties and properties.get('Finish Line', False):
            visual_tile.is_finish_line = True
            self._finish_tiles.append(visual_tile)
            print(f"Finish line tile created at ({world_x}, {world_y})")
        
        # Handle NPC property
        if properties and properties.get('NPC', False):
            # Store NPC info in the tile for later use
            visual_tile.is_npc = True
            visual_tile.npc_type = properties.get('NPCType', '').lower()
            visual_tile.npc_name = properties.get('NPCName', 'NPC')
            
            # For signs, store the message
            if visual_tile.npc_type == 'sign':
                visual_tile.sign_message = properties.get('SignMessage', 'Read this sign for information.')
                print(f"Found sign: '{visual_tile.npc_name}' at ({world_x}, {world_y}) with message: {visual_tile.sign_message[:30]}...")
            
            # Add to npc_tiles list for initialization later
            self.npc_tiles.append(visual_tile)
            print(f"Found NPC tile: {visual_tile.npc_type} at ({world_x}, {world_y})")
        
        if properties and properties.get('music switch', False):
            # Store music switch tile
            self._music_switch_tiles.append(visual_tile)
            print(f"Music switch tile created at ({world_x}, {world_y})")

        if properties and properties.get('coin', False):  # Check for 'coin' property
            # Store coin info in the tile for later use
            visual_tile.is_coin = True
            visual_tile.coin_type = properties.get('coin_type', 'gold').lower()
            visual_tile.coin_value = int(properties.get('coin_value', 10))
            
            # Add to coin_tiles list for initialization later
            if not hasattr(self, 'coin_tiles'):
                self.coin_tiles = []
            self.coin_tiles.append(visual_tile)
            
            print(f"Found coin tile: {visual_tile.coin_type} (value: {visual_tile.coin_value}) at ({world_x}, {world_y})")
  
    def _process_object_layers(self):
        """Process the TiledObjectGroup layers for direct object placement"""
        for layer in self._tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledObjectGroup):
                layer_name = layer.name if hasattr(layer, 'name') else "Unnamed"
                print(f"Processing object layer: {layer_name}")
                
                # Process all objects in the layer
                for obj in layer:
                    # Check if this is a sign object
                    properties = obj.properties if hasattr(obj, 'properties') else {}
                    
                    if properties.get('sign', False) or properties.get('Sign', False):
                        # Get sign properties
                        sign_name = properties.get('name', properties.get('Name', 'Sign'))
                        sign_message = properties.get('message', properties.get('Message', 'Read this sign for information.'))
                        
                        # Store sign info for later creation
                        sign_info = {
                            'x': obj.x + (obj.width / 2 if hasattr(obj, 'width') else 0),
                            'y': obj.y + (obj.height / 2 if hasattr(obj, 'height') else 0),
                            'name': sign_name,
                            'message': sign_message
                        }
                        
                        self.sign_objects.append(sign_info)
                        print(f"Found sign object: '{sign_name}' at ({sign_info['x']}, {sign_info['y']})")
                    
                    # Check for NPCs as objects (alternative method)
                    elif properties.get('NPC', False) or properties.get('npc', False):
                        # Get NPC properties
                        npc_type = properties.get('NPCType', properties.get('npcType', '')).lower()
                        npc_name = properties.get('NPCName', properties.get('npcName', 'NPC'))
                        
                        # For signs, get the message
                        sign_message = None
                        if npc_type == 'sign':
                            sign_message = properties.get('SignMessage', properties.get('signMessage', 'Read this sign for information.'))
                        
                        # Create a temporary object with the necessary attributes
                        npc_obj = pygame.sprite.Sprite()
                        npc_obj.rect = pygame.Rect(obj.x, obj.y, 48, 48)
                        npc_obj.npc_type = npc_type
                        npc_obj.npc_name = npc_name
                        
                        if sign_message:
                            npc_obj.sign_message = sign_message
                        
                        # Add to npc_tiles list
                        self.npc_tiles.append(npc_obj)
                        print(f"Found NPC object: {npc_type} '{npc_name}' at ({obj.x}, {obj.y})")

    def load_collision_layer(self, layer_name):
        """Load collision shapes for a specific layer using masks for precise shapes"""
        processed_tiles = set()

        # Cache layers for better performance
        collision_layers = []
        for layer in self._tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer) and layer.name == layer_name:
                collision_layers.append(layer)

        for layer in collision_layers:
            layer_index = self._tmx_data.layers.index(layer)
            
            for x, y, gid in layer.tiles():
                if gid:
                    world_x = x * self._TILE_SIZE
                    world_y = y * self._TILE_SIZE
                    tile_key = (world_x, world_y)

                    # Skip if already processed
                    if tile_key in processed_tiles:
                        continue
                    processed_tiles.add(tile_key)

                    # Handle both cases - gid as image or gid as number
                    properties, tile_image = self._get_tile_properties(gid, x, y, layer_index)

                    # Get shape parameters
                    shape_type = self.get_shape_type(properties)
                    angle = properties.get('angle', 0)
                    friction = self.get_friction_for_shape(shape_type, angle)

                    # Create collision shape based on type
                    if shape_type == "slope":
                        vertices = self.get_slope_vertices(world_x, world_y, self._TILE_SIZE, self._TILE_SIZE, angle)
                        if len(vertices) >= 3:
                            body, shape = self._physics.create_poly(vertices, friction=friction)
                            if body and shape:
                                self._static_bodies.append(body)
                                self._static_shapes.append(shape)
                    else:
                        # Try to create from mask first - important for precise collision detection
                        success = False
                        if tile_image:
                            success = self.create_body_from_mask(tile_image, world_x, world_y, friction)

                        # Fall back to box if needed
                        if not success:
                            body, shape = self._physics.create_box(world_x, world_y, self._TILE_SIZE, self._TILE_SIZE, friction=friction)
                            if body and shape:
                                self._static_bodies.append(body)
                                self._static_shapes.append(shape)

    def _get_tile_properties(self, gid, x, y, layer_index):
        """Get tile properties and image from GID"""
        if isinstance(gid, pygame.Surface):
            # Use layer index to get properties
            try:
                properties = self._tmx_data.get_tile_properties(x, y, layer_index) or {}
            except Exception as e:
                print(f"Error getting properties at ({x}, {y}): {e}")
                properties = {}
                
            # Store gid as image for later use
            tile_image = gid
        else:
            # Standard case - gid is a number
            try:
                properties = self._tmx_data.get_tile_properties_by_gid(gid) or {}
                tile_image = self._tmx_data.get_tile_image_by_gid(gid)
            except Exception as e:
                print(f"Error with GID {gid}: {e}")
                properties = {}
                tile_image = None
                
        return properties, tile_image

    def load_triggers(self):
        """Load trigger objects from the Invis Objects layer"""
        # This method is also fine as is - triggers are relatively few
        for layer in self._tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledObjectGroup) and layer.name == "Invis Objects":
                for i, obj in enumerate(layer):
                    if hasattr(obj, 'name') and obj.name == "Loop Switch":
                        # Create switch
                        body, shape = self._physics.create_box(
                            obj.x, obj.y, obj.width, obj.height,
                            is_static=True,
                            collision_type="switch"
                        )

                        if body and shape:
                            shape.used = False
                            shape.switch_id = i
                            shape.collision_type = self._physics.collision_types["switch"]

                            self._mask_switch_triggers.append(shape)
                            self._static_bodies.append(body)
                            self._static_shapes.append(shape)
                    elif hasattr(obj, 'name') and obj.name == "Checkpoint":
                        self._checkpoints.append((obj.x, obj.y))

    def initialize_coins(self):
        """Create coins at their designated positions"""
        
        # Keep existing coins group if it exists, otherwise create new
        if not hasattr(self, 'coins') or self.coins is None:
            self.coins = pygame.sprite.Group()
            print("created new coins group")
        
        # Process coin tiles from the Objects layer
        if hasattr(self, 'coin_tiles') and self.coin_tiles:
            print(f"Initializing {len(self.coin_tiles)} coins from tiles...")
            
            for coin_tile in self.coin_tiles:
                x, y = coin_tile.rect.center
                coin_type = getattr(coin_tile, 'coin_type', 'gold').lower()
                coin_value = getattr(coin_tile, 'coin_value', 10)
                
                print(f"Creating {coin_type} coin worth {coin_value} at ({x}, {y})")
                
                # Create coin based on type
                coin = Coin(self._physics, x, y, coin_type=coin_type, value=coin_value)
                
                # Add to sprite group
                self.coins.add(coin)
                
                # Verify coin added properly
                if coin in self.coins:
                    print(f"Successfully added {coin_type} coin to group")
                else:
                    print(f"WARNING: Failed to add {coin_type} coin to group")
                
                # Align coin to ground
                if hasattr(coin, 'align_to_ground'):
                    coin.align_to_ground(self)
        
        # Add coin collection state if not already present
        if not hasattr(self, '_total_coins_collected'):
            self._total_coins_collected = 0
        if not hasattr(self, '_coin_score'):
            self._coin_score = 0
        
        # Log completion
        coin_count = len(self.coins) if hasattr(self, 'coins') else 0
        print(f"Coin initialization complete. {coin_count} coins created.")

    def update_coins(self, dt):
        """Update all coins (add this method to your level class)"""
        if hasattr(self, 'coins'):
            # Update all coins
            self.coins.update(dt)
            
            # Remove collected coins
            for coin in list(self.coins):
                if coin.collected:
                    self.coins.remove(coin)

    def check_coin_collection(self, player):
        """Check if player collects any coins (add this method to your level class)"""
        if not hasattr(self, 'coins'):
            return 0
        
        coins_collected = 0
        
        for coin in list(self.coins):
            if not coin.is_being_collected and not coin.collected:
                # Check collision with player
                if player.rect.colliderect(coin.rect):
                    value = coin.collect()
                    if value > 0:
                        coins_collected += 1
                        self._coin_score += value
                        self._total_coins_collected += 1
                        
                        # Call the existing collect_ring method to integrate with your stats system
                        if hasattr(player, 'collect_ring'):
                            player.collect_ring()
                        elif hasattr(self, 'collect_ring'):
                            self.collect_ring()
                        
                        # You can add sound effects here
                        # self.play_sound('coin_collect')
                        
                        print(f"Collected {coin.coin_type} coin worth {value}! Total score: {self._coin_score}")
        
        return coins_collected

    def initialize_npcs(self):
        """Create NPC characters and signs at their designated positions"""
        
        # Keep existing NPCs group if it exists, otherwise create new
        if not hasattr(self, 'NPCs') or self.NPCs is None:
            self.NPCs = pygame.sprite.Group()
        
        # Process NPC tiles
        if hasattr(self, 'npc_tiles') and self.npc_tiles:
            print(f"Initializing {len(self.npc_tiles)} NPCs from tiles...")
            
            for npc_tile in self.npc_tiles:
                x, y = npc_tile.rect.center
                npc_type = getattr(npc_tile, 'npc_type', '').lower()
                npc_name = getattr(npc_tile, 'npc_name', 'NPC')
                
                print(f"Creating NPC {npc_name} of type {npc_type} at ({x}, {y})")
                
                if npc_type == 'blueball':
                    npc = BlueBall(self._physics, x, y)
                elif npc_type == 'sign':
                    # Get the sign message
                    sign_message = getattr(npc_tile, 'sign_message', 'Read this sign for information.')
                    npc = SignNPC(self._physics, x, y, name=npc_name, message=sign_message)
                    print(f"Created sign '{npc_name}' with message: {sign_message[:30]}...")
                else:
                    # Generic NPC with custom name
                    npc = NPCCharacter(self._physics, x, y, name=npc_name)
                
                # Add to sprite group
                self.NPCs.add(npc)
                
                # Verify NPC added properly
                if npc in self.NPCs:
                    print(f"Successfully added {npc_type} NPC to group")
                else:
                    print(f"WARNING: Failed to add {npc_type} NPC to group")
                
                # Align NPC to ground
                if hasattr(npc, 'align_to_ground'):
                    npc.align_to_ground(self)
        
        # Process direct sign objects
        if hasattr(self, 'sign_objects') and self.sign_objects:
            print(f"Initializing {len(self.sign_objects)} signs from objects...")
            
            for sign_info in self.sign_objects:
                x, y = sign_info['x'], sign_info['y']
                name = sign_info['name']
                message = sign_info['message']
                
                # Create the sign
                sign = SignNPC(self._physics, x, y, name=name, message=message)
                
                # Add to sprite group
                self.NPCs.add(sign)
                
                # Verify sign added properly
                if sign in self.NPCs:
                    print(f"Successfully added sign '{name}' to group")
                else:
                    print(f"WARNING: Failed to add sign '{name}' to group")
                
                # Align sign to ground if the method exists
                if hasattr(sign, 'align_to_ground'):
                    sign.align_to_ground(self)
        
        # Add dialogue state if not already present
        if not hasattr(self, '_current_npc'):
            self._current_npc = None
        if not hasattr(self, '_in_dialogue'):
            self._in_dialogue = False
        if not hasattr(self, '_dialogue_just_started'):
            self._dialogue_just_started = False
        
        # Log completion
        npc_count = len(self.NPCs) if hasattr(self, 'NPCs') else 0
        print(f"NPC and sign initialization complete. {npc_count} NPCs and signs created.")

    def update(self, dt=0, level_index=0):
        """Update level state with NPCs and dialogue handling"""
        clock = pygame.time.Clock()
        if clock.get_fps() > 0:
            dt = 1.0 / clock.get_fps()
        else:
            dt = 1.0/60.0
        
        # Handle timer pausing for dialogue
        if self._in_dialogue and not self._timer.is_paused:
            self._timer.pause()
            if not self._secret_found:
                for i in self.NPCs:
                    if isinstance(i, BlueBall) and i._is_talking:
                        self.find_secret()
                        self._secret_found = True
                        break
        elif not self._in_dialogue and self._timer.is_paused:
            self._timer.resume()
            
        # Update results screen if showing
        if self._showing_results:
            self._results_screen.update(dt)
            # Don't update anything else while showing results
            return
            
        # Skip updates if level is complete but not showing results yet
        if self._level_complete:
            return
        
        # Update dialogue system if active
        if self._in_dialogue:
            self._dialogue_system.ui_manager.update(dt)
            self._dialogue_system.update(dt)
        
        # Don't update physics if in dialogue
        if not self._in_dialogue:
            self._ball.update()
            self._physics.step(dt)
            
            # Update NPCs - only if they're near the player for performance
            if hasattr(self, 'NPCs'):
                for npc in self.NPCs:
                    npc.update(self._ball)
            
            # Update camera
            self._camera.update(self._ball)

            # Update coins
            if hasattr(self, 'update_coins'):
                self.update_coins(dt)
            
            # Check coin collection (probably in your player update section)
            if hasattr(self, 'check_coin_collection') and hasattr(self, '_ball'):
                self.check_coin_collection(self._ball)

            # Update parallax background based on camera position
            camera_center_x = -self._camera.offset_x + SCREEN_WIDTH/2
            camera_center_y = -self._camera.offset_y + SCREEN_HEIGHT/2
            self._parallax_bg.update(camera_center_x, camera_center_y)

            # Check for finish line collisions
            self.check_finish_line()

            # Check if the ball has fallen off the bottom of the world
            if self._ball.body.position[1] > self.height - 20:
                self._ball.death()

            # Check for ball death and reset
            if self._ball.is_dead:
                self.reset_ball()
        
        # Handle dialogue if active
        if getattr(self, '_in_dialogue', False) and getattr(self, '_dialogue_just_started', False):
            self._dialogue_just_started = False
            # Print the current dialogue
            if self._current_npc:
                self._current_npc.print_dialogue()

    def draw(self, screen, level_index=0):
        """Draw level with optimized tile rendering including NPCs"""
        level_index=self._level_index
        # Draw parallax background
        self._parallax_bg.draw(screen)
        
        # Get the current viewport rectangle with buffer zone
        viewport = pygame.Rect(
            -self._camera.offset_x, 
            -self._camera.offset_y, 
            SCREEN_WIDTH, 
            SCREEN_HEIGHT
        )
        
        # Expand viewport by buffer to prevent pop-in at edges
        buffered_viewport = viewport.inflate(self._viewport_buffer * 2, self._viewport_buffer * 2)
        
        # Query the spatial grid for visible tiles
        visible_tiles = self._spatial_grid.query_rect(buffered_viewport)
        
        # Update statistics
        self._rendered_tiles_count = 0
        self._culled_tiles_count = self._total_tiles - len(visible_tiles)
        
        # Define explicit layer order with background first, then other layers
        layer_order = {"background": 0, "Surface B": 1, "Masks B": 2, "Masks F": 3, "Surface F": 4, "Objects": 5}
        
        # Group tiles by layer for batch rendering
        layer_groups = {}
        for tile in visible_tiles:
            if not tile.visible:
                continue
                
            layer_name = getattr(tile, 'layer_name', 'Unknown')
            if layer_name not in layer_groups:
                layer_groups[layer_name] = []
                
            layer_groups[layer_name].append(tile)
            self._rendered_tiles_count += 1
        
        # Draw visible tiles by layer order
        for layer_name in sorted(layer_groups.keys(), key=lambda name: layer_order.get(name, 999)):
            for tile in layer_groups[layer_name]:
                screen.blit(tile.image, self._camera.apply(tile))
        
        # Draw NPCs - All NPCs first, then hide based on distance
        if hasattr(self, 'NPCs') and self.NPCs:
            # First update activity state of all NPCs
            for npc in self.NPCs:
                if hasattr(npc, 'update'):
                    # Only pass the ball if it exists and has the right properties
                    if hasattr(self, '_ball') and hasattr(self._ball, 'body') and hasattr(self._ball.body, 'position'):
                        npc.update(self._ball)
                    else:
                        npc.update()
            
            # Now draw only active NPCs
            npc_count = 0
            for npc in self.NPCs:
                # Always draw all NPCs for debugging, or use is_active check for optimization
                #if True or (hasattr(npc, 'is_active') and npc.is_active):
                if hasattr(npc, 'is_active') and npc.is_active:
                    # Draw NPC
                    screen.blit(npc.image, self._camera.apply(npc))
                    npc_count += 1
                    
                    # Draw interaction indicator if player is close enough
                    if hasattr(npc, 'draw_indicator') and hasattr(npc, 'show_indicator') and npc.show_indicator:
                        npc.draw_indicator(screen, self._camera)
        
        # Draw finish line tiles
        for tile in self._finish_tiles:
            if buffered_viewport.colliderect(tile.rect):
                # Get flag_image from constants
                try:
                    from constants import flag_image
                    screen.blit(flag_image, self._camera.apply(tile))
                except ImportError:
                    # Fallback if flag_image not available
                    pygame.draw.rect(screen, (255, 0, 0), self._camera.apply_rect(tile.rect), 3)
        
        # Draw the player ball LAST so it's on top of everything
        if hasattr(self, '_ball'):
            screen.blit(self._ball.image, self._camera.apply(self._ball))

        if self.coins:
            for coin in self.coins:
                screen.blit(coin.image, self._camera.apply(coin))

        # Draw dialogue system if active
        if self._in_dialogue:
            self._dialogue_system.draw(screen)
        
        # Draw timer in top-left corner (only if not in dialogue or showing results)
        if not self._in_dialogue and not self._showing_results and self._timer.is_running:
            self.draw_timer(screen)
        
        # Draw stats HUD in top-right corner
        if not self._showing_results:
            self.draw_stats_hud(screen)
        
        # Draw results screen if active
        if self._showing_results:
            self._results_screen.draw(screen, level_index=level_index)

    def draw_timer(self, screen):
        """Draw the timer display"""
        font = pygame.font.Font(daFont, 18)
        time_text = f"TIME: {self._timer.format_time()}"
        
        # Create text with black outline for visibility
        outline_color = (0, 0, 0)
        text_color = (255, 255, 255)
        
        # Draw outline
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx != 0 or dy != 0:
                    outline_surf = font.render(time_text, True, outline_color)
                    screen.blit(outline_surf, (20 + dx, 20 + dy))
        
        # Draw main text
        text_surf = font.render(time_text, True, text_color)
        screen.blit(text_surf, (20, 20))

    def draw_stats_hud(self, screen):
        """Draw current stats in HUD"""
        font = pygame.font.Font(daFont, 14)
        stats_info = [
            f"Coins: {self._stats.rings_collected}",
            f"Enemies: {self._stats.enemies_defeated}",
            f"Deaths: {self._stats.deaths}"
        ]
        
        for i, stat_text in enumerate(stats_info):
            y_pos = 20 + (i * 30)
            
            # Draw outline for visibility
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx != 0 or dy != 0:
                        outline_surf = font.render(stat_text, True, (0, 0, 0))
                        screen.blit(outline_surf, (SCREEN_WIDTH - 150 + dx, y_pos + dy))
            
            # Draw main text
            text_surf = font.render(stat_text, True, (255, 255, 255))
            screen.blit(text_surf, (SCREEN_WIDTH - 150, y_pos))

    def update_visuals(self):
        """Update visibility of visual tiles based on active layer"""
        # This needs to update all tiles, but we can optimize the iteration
        for tile in self._visual_tiles:
            if tile.layer_name == "Masks F":
                tile.visible = (self._active_layer == "F")
            elif tile.layer_name == "Masks B":
                tile.visible = (self._active_layer == "B")

    def handle_player_choice(self, choice_index):
        """Handle when the player selects a dialogue choice"""
        if not self._current_npc or not self._in_dialogue:
            return False
            
        current_dialogue = self._current_npc.get_current_dialogue()
        if current_dialogue and current_dialogue.get("choices"):
            choices = current_dialogue["choices"]
            if 0 <= choice_index < len(choices):
                # Store the player's choice text and index
                self._player_choice_text = choices[choice_index]["text"]
                self._player_choice_index = choice_index
                
                # Create a dialogue object for player's response
                player_dialogue = {
                    "text": self._player_choice_text,
                    "choices": None
                }
                
                # Create temporary player "NPC" with portrait
                player_npc = NPCCharacter(self._physics, 0, 0, name="You")
                player_npc.portrait = self._player_portrait
                
                # Show player dialogue first
                self._dialogue_system.start_dialogue(player_npc, player_dialogue)
                self._showing_player_choice = True
                
                # We no longer use a timer - player must press a key to continue
                self._waiting_for_player_continue = True
                
                print(f"Player chose: {self._player_choice_text}")
                return True
        return False

    def handle_events(self, event):
        """Handle events including results screen"""
        # If showing results, handle results-specific events
        if self._showing_results:
            if event.type == pygame.KEYDOWN and event.key in [pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE]:
                if self._results_screen.is_complete():
                    self._results_screen.hide()
                    self._showing_results = False
                    self._level_complete = True
                    return True
            return True  # Consume all events while showing results
        
        # If dialogue system is active, pass events to it first
        if self._in_dialogue and self._dialogue_system.active:
            # Handle player response continuation
            if self._waiting_for_player_continue and event.type == pygame.KEYDOWN:
                self._waiting_for_player_continue = False
                self._showing_player_choice = False
                
                # Get the chosen option's next dialogue from the NPC
                choice = self._current_npc.handle_choice(self._player_choice_index)
                
                # Check if this is the map-giving dialogue
                if (self._game_ref and 
                    self._current_npc.name == "Blue Ball" and 
                    self._current_npc.current_dialogue_index == 6 and
                    self._current_npc.get_current_dialogue() and
                    self._current_npc.get_current_dialogue()["text"].startswith("What you need is a map!")):
                    
                    # Player just got the map!
                    self._game_ref.player_has_map = True
                    print("Player received map from Blue Ball!")
                
                # If there's another dialogue, start it
                if choice:
                    self._dialogue_system.start_dialogue(self._current_npc, choice)
                else:
                    # End the dialogue
                    self._dialogue_system.hide()
                    self._in_dialogue = False
                    self._current_npc = None
                    
                return True
                
            # If dialogue system has choices showing and an event was handled
            if self._dialogue_system.showing_choices and self._dialogue_system.handle_event(event):
                # Get the choice index from dialogue system
                choice_index = getattr(self._dialogue_system, 'player_choice_index', -1)
                
                if choice_index >= 0 and self._current_npc:
                    # Handle player's choice
                    self.handle_player_choice(choice_index)
                    return True
            
            # If dialogue system is just showing text (no choices) 
            elif self._dialogue_system.handle_event(event):
                # Check if we need to end the dialogue
                if (not self._dialogue_system.waiting_for_input and 
                    not self._dialogue_system.continue_visible and 
                    not self._dialogue_system.showing_choices and
                    isinstance(self._current_npc, SignNPC)):
                    
                    # For signs, end the dialogue when the key is pressed
                    print(f"Ending sign dialogue with {self._current_npc.name}")
                    self._dialogue_system.hide()
                    self._in_dialogue = False
                    self._current_npc = None
                    
                return True
            
            # If dialogue system has choices showing and an event was handled
            if self._dialogue_system.showing_choices and self._dialogue_system.handle_event(event):
                # Get the choice index from dialogue system
                choice_index = getattr(self._dialogue_system, 'player_choice_index', -1)
                
                if choice_index >= 0 and self._current_npc:
                    # Handle player's choice
                    self.handle_player_choice(choice_index)
                    return True
            
            # If dialogue system is just showing text (no choices)
            elif self._dialogue_system.handle_event(event):
                return True
        
        # Handle interaction start if not in dialogue
        if not self._in_dialogue and event.type == pygame.KEYDOWN and event.key == pygame.K_e:
            # Find closest NPC that can be interacted with
            closest_npc = None
            min_distance = float('inf')
            
            if hasattr(self, 'NPCs'):
                for npc in self.NPCs:
                    if hasattr(npc, 'can_interact') and npc.can_interact(self._ball):
                        # Calculate distance
                        dx = self._ball.body.position.x - npc.body.position.x
                        dy = self._ball.body.position.y - npc.body.position.y
                        distance = (dx**2 + dy**2)**0.5
                        
                        if distance < min_distance:
                            min_distance = distance
                            closest_npc = npc
            
            if closest_npc:
                # Start dialogue with this NPC
                self._current_npc = closest_npc
                self._in_dialogue = True
                self._dialogue_just_started = True
                self._waiting_for_player_continue = False
                
                # Ensure portraits are properly loaded
                self.prepare_npc_portrait(closest_npc)
                self.prepare_player_portrait()
                
                # Start dialogue
                initial_dialogue = closest_npc.start_dialogue()
                if initial_dialogue:
                    print(f"Starting dialogue with {closest_npc.name}")
                    self._dialogue_system.start_dialogue(closest_npc, initial_dialogue)
                else:
                    print(f"No dialogue available for {closest_npc.name}")
                    self._in_dialogue = False
                
                return True
        
        # Handle layer switching if not in dialogue
        if not self._in_dialogue and event.type == pygame.KEYDOWN and event.key == pygame.K_l:
            if hasattr(self, 'switch_layer'):
                return self.switch_layer()
            
        return False
    
    def prepare_npc_portrait(self, npc):
        """Ensure the NPC has a properly sized portrait"""
        if not hasattr(npc, 'portrait') or npc.portrait is None:
            try:
                # Try to load a portrait based on NPC name
                portrait_path = os.path.join("assets", "sprites", f"{npc.name.lower()} portrait.png")
                if os.path.exists(portrait_path):
                    npc.portrait = pygame.image.load(portrait_path).convert_alpha()
                    npc.portrait = pygame.transform.scale(npc.portrait, (84, 84))  # Match DialogueSystem portrait size
                    print(f"Loaded portrait for {npc.name}")
                elif hasattr(npc, 'portrait'):
                    # If there's already a portrait attribute but it's None, create a colored portrait
                    npc.portrait = pygame.Surface((84, 84), pygame.SRCALPHA)
                    # Make a bright colored circle for visibility
                    if npc.name == "Blue Ball":
                        color = (20, 20, 255)  # Bright blue for Blue Ball
                    else:
                        color = (0, 128, 255)  # Default bright blue for other NPCs
                        
                    pygame.draw.circle(npc.portrait, color, (42, 42), 38)
                    pygame.draw.circle(npc.portrait, (255, 255, 255), (42, 42), 38, 2)  # White outline
                    print(f"Created bright fallback portrait for {npc.name}")
            except Exception as e:
                # Create a fallback portrait if there's an error
                npc.portrait = pygame.Surface((84, 84), pygame.SRCALPHA)
                pygame.draw.circle(npc.portrait, (100, 100, 255), (42, 42), 38)
                pygame.draw.circle(npc.portrait, (255, 255, 255), (42, 42), 38, 2)
                print(f"Error creating portrait for {npc.name}: {e}")
        else:
            # Ensure the portrait is properly sized if it already exists
            if npc.portrait.get_width() != 84 or npc.portrait.get_height() != 84:
                try:
                    npc.portrait = pygame.transform.scale(npc.portrait, (84, 84))
                    print(f"Resized existing portrait for {npc.name} to 84x84")
                except Exception as e:
                    print(f"Error resizing portrait for {npc.name}: {e}")
                    # Create a fallback portrait
                    npc.portrait = pygame.Surface((84, 84), pygame.SRCALPHA)
                    pygame.draw.circle(npc.portrait, (100, 100, 255), (42, 42), 38)
                    pygame.draw.circle(npc.portrait, (255, 255, 255), (42, 42), 38, 2)
                    
    def prepare_player_portrait(self):
        """Ensure the player portrait is available and properly sized"""
        if not hasattr(self, '_player_portrait') or self._player_portrait is None:
            try:
                portrait_path = os.path.join("assets", "sprites", "Red Ball portrait.png")
                if os.path.exists(portrait_path):
                    self._player_portrait = pygame.image.load(portrait_path).convert_alpha()
                    self._player_portrait = pygame.transform.scale(self._player_portrait, (84, 84))
                    print("Loaded player portrait")
                else:
                    # Create a bright red fallback portrait for visibility
                    self._player_portrait = pygame.Surface((84, 84), pygame.SRCALPHA)
                    pygame.draw.circle(self._player_portrait, (255, 0, 0), (42, 42), 38)
                    pygame.draw.circle(self._player_portrait, (255, 255, 255), (42, 42), 38, 2)  # White outline
                    print("Created bright fallback player portrait")
            except Exception as e:
                # Create a fallback portrait if there's an error
                self._player_portrait = pygame.Surface((84, 84), pygame.SRCALPHA)
                pygame.draw.circle(self._player_portrait, (255, 0, 0), (42, 42), 38)
                pygame.draw.circle(self._player_portrait, (255, 255, 255), (42, 42), 38, 2)
                print(f"Error creating player portrait: {e}")
        else:
            # Ensure the portrait is properly sized if it already exists
            if self._player_portrait.get_width() != 84 or self._player_portrait.get_height() != 84:
                try:
                    self._player_portrait = pygame.transform.scale(self._player_portrait, (84, 84))
                    print("Resized player portrait to 84x84")
                except Exception as e:
                    print(f"Error resizing player portrait: {e}")
                    # Create a fallback portrait
                    self._player_portrait = pygame.Surface((84, 84), pygame.SRCALPHA)
                    pygame.draw.circle(self._player_portrait, (255, 0, 0), (42, 42), 38)
                    pygame.draw.circle(self._player_portrait, (255, 255, 255), (42, 42), 38, 2)
                
    def switch_layer(self):
        """Switch between F and B layers"""
        # Toggle active layer
        self._active_layer = "B" if self._active_layer == "F" else "F"
        
        # Clear physics objects
        self.clear_physics_objects()
        
        # Reload collision for the new active layer
        if self._active_layer == "F":
            self.load_collision_layer("Masks F")
        else:
            self.load_collision_layer("Masks B")
            
        # Update tile visibility
        self.update_visuals()
        
        return True
    
    def check_finish_line(self):
        """Check if player has reached a finish line tile"""
        # If we're already showing results, don't check again
        if self._showing_results:
            return False
            
        ball_rect = self._ball.rect

        if not self._finish_tiles:
            return False

        for tile in self._finish_tiles:
            if ball_rect.colliderect(tile.rect):
                # Level finished! (but not complete yet)
                print(f"Finish line reached at {tile.rect.x}, {tile.rect.y}")
                
                # Stop timer and calculate final stats
                final_time = self._timer.stop()
                self._stats.completion_time = final_time
                
                # Show results screen
                self._results_screen.show_results(self._stats, self._level_index)
                self._showing_results = True
                
                # NEW: Save level progress and check for improvements
                if hasattr(self, '_gamesave') and self._gamesave:
                    improvements = self._gamesave.save_level_result(
                        self._level_index, 
                        self._stats, 
                        self._results_screen
                    )
                    
                    # Optional: Store improvements to show in UI later
                    self._recent_improvements = improvements
                    
                    # Optional: Print improvements for debugging
                    if improvements:
                        print("🎉 NEW RECORDS:")
                        for improvement in improvements:
                            print(f"  - {improvement}")
                    else:
                        print("Level completed - no new records this time")
                else:
                    print("Warning: GameSave not available - progress not saved")
                
                # Pause the game physics/movement while showing results
                if hasattr(self, '_space'):
                    # If using pymunk physics, you might want to pause the space
                    pass
                
                return True

        return False

    def check_music_switch(self, track):
        """Check if player has reached a music switch tile"""
        if not self._music_switch_tiles or self._music_switched or self._music_switching:
            return False
        
        ball_rect = self._ball.rect
        
        # Check collision with any music switch tile
        for tile in self._music_switch_tiles:
            if ball_rect.colliderect(tile.rect):
                print(f"Music switch activated at {tile.rect.x}, {tile.rect.y}")
                self._start_music_transition(track)
                return True
        
        return False

    def _start_music_transition(self, new_track):
        """Start the music transition process"""
        if self._music_switching:
            return
        
        self._music_switching = True
        self._pending_track = new_track
        
        # Start fadeout and schedule the music switch
        pygame.mixer.music.fadeout(500)  # Fade out over 1 second
        
        # Start a thread to handle the music switching after fadeout
        switch_thread = threading.Thread(target=self._handle_music_switch)
        switch_thread.daemon = True  # Dies when main thread dies
        switch_thread.start()

    def _handle_music_switch(self):
        """Handle the actual music switching after fadeout (runs in separate thread)"""
        
        # Check if music is still playing (fadeout might not be complete)
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        
        try:
            # Load and play new music
            pygame.mixer.music.load(self._pending_track)
            pygame.mixer.music.play(-1)  # Loop the new track
            print(f"Successfully switched to: {self._pending_track}")
            
            # Mark as switched
            self._music_switched = True
            
        except pygame.error as e:
            print(f"Error switching music: {e}")
        
        finally:
            self._music_switching = False
            self._pending_track = None

    def reset_ball(self):
        """Reset the ball to the last checkpoint or spawn point"""
        if not self._ball.is_dead:
            self._ball.death()

        if self._ball.is_dead:
            if self._checkpoints:
                # Reset to the last checkpoint
                last_checkpoint = self._checkpoints[-1]
                spawn_x, spawn_y = last_checkpoint
            else:
                # Reset to the original spawn point
                spawn_x, spawn_y = self._spawn_point

            self._ball.kill()

            # Create a new ball
            self._ball = PurePymunkBall(self._physics, spawn_x, spawn_y)
            self.player_died()

    def create_body_from_mask(self, surface, x, y, friction=0.8, threshold=128):
        """Create a polygon shape from a surface mask - for precise slopes"""
        try:
            if surface is None:
                return False

            scaled_surface = pygame.transform.scale(surface, (self._TILE_SIZE, self._TILE_SIZE))
            mask = pygame.mask.from_surface(scaled_surface)
            outline = mask.outline()
            if len(outline) < 3:
                return False
            simplified_outline = self.simplify_polygon(outline, tolerance=2)
            vertices = [(x + point[0], y + point[1]) for point in simplified_outline]
            if len(vertices) >= 3:
                body, shape = self._physics.create_poly(vertices, friction=friction)
                if body and shape:
                    self._static_bodies.append(body)
                    self._static_shapes.append(shape)
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
    def __init__(self, spawn, tmx_map=None, level_index=2, gamesave=None):
        # Call the optimized parent class constructor but disable default music
        super().__init__(spawn, tmx_map, play_music=False, level_index=2, gamesave=gamesave)
        self._level_index = level_index  # Store the level index for music and stats
        # Set cave-specific music
        self._setup_cave_music()
        self._gamesave = gamesave
        # Override the parallax background with cave-themed images
        self._setup_cave_background()
    
    def _setup_cave_music(self):
        """Set up cave-specific music"""
        pygame.mixer_music.load(os.path.join("assets", "music", "level 1.mp3"))
        pygame.mixer_music.play(-1)
    
    def _setup_cave_background(self):
        """Set up cave-themed parallax background"""
        self._parallax_bg = ParallaxBackground(SCREEN_WIDTH, SCREEN_HEIGHT)
        
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
                if self._parallax_bg.add_layer(bg["path"], bg["factor"]):
                    bg_loaded = True
        
        # If no cave backgrounds are found, use fallback
        if not bg_loaded:
            # Create dark-colored backgrounds to simulate a cave
            self._parallax_bg.add_color_layer((20, 20, 30))  # Very dark blue-grey
            self._parallax_bg.add_color_layer((30, 25, 40), 0.3)  # Dark purple-grey
            self._parallax_bg.add_color_layer((40, 30, 50), 0.5)  # Medium purple-grey
    
    def update(self, dt=0, level_index=2):
        """Update level state including fog particles"""
        # Call the parent update method
        super().update(dt, level_index=self._level_index)
    
    def draw(self, screen, level_index=2):
        """Draw level with fog effects"""
        level_index = self._level_index
        # Draw parallax background
        self._parallax_bg.draw(screen)
        
        # Get the current viewport rectangle with buffer zone
        viewport = pygame.Rect(
            -self._camera.offset_x, 
            -self._camera.offset_y, 
            SCREEN_WIDTH, 
            SCREEN_HEIGHT
        )

        self.check_music_switch(os.path.join("assets", "music", "cave.mp3"))

        # Expand viewport by buffer to prevent pop-in at edges
        buffered_viewport = viewport.inflate(self._viewport_buffer * 2, self._viewport_buffer * 2)
        
        # Query the spatial grid for visible tiles
        visible_tiles = self._spatial_grid.query_rect(buffered_viewport)
        
        # Update statistics
        self._rendered_tiles_count = 0
        self._culled_tiles_count = self._total_tiles - len(visible_tiles)
        
        # Define explicit layer order with background first, then other layers
        layer_order = {"background": 0, "Surface B": 1, "Masks B": 2, "Masks F": 3, "Surface F": 4, "Objects": 5}
        
        # Group tiles by layer for batch rendering
        layer_groups = {}
        for tile in visible_tiles:
            if not tile.visible:
                continue
                
            layer_name = getattr(tile, 'layer_name', 'Unknown')
            if layer_name not in layer_groups:
                layer_groups[layer_name] = []
                
            layer_groups[layer_name].append(tile)
            self._rendered_tiles_count += 1
        
        # First draw only background layer if it exists
        if "background" in layer_groups:
            for tile in layer_groups["background"]:
                screen.blit(tile.image, self._camera.apply(tile))
        
        # Now draw the ball AFTER background but BEFORE other tiles
        if hasattr(self, '_ball'):
            screen.blit(self._ball.image, self._camera.apply(self._ball))
        
        # Draw remaining layers (excluding background which was already drawn)
        for layer_name in sorted(layer_groups.keys(), key=lambda name: layer_order.get(name, 999)):
            if layer_name != "background":  # Skip background as it's already drawn
                for tile in layer_groups[layer_name]:
                    screen.blit(tile.image, self._camera.apply(tile))
        
        # Draw NPCs - All NPCs first, then hide based on distance
        if hasattr(self, 'NPCs') and self.NPCs:
            # First update activity state of all NPCs
            for npc in self.NPCs:
                if hasattr(npc, 'update'):
                    # Only pass the ball if it exists and has the right properties
                    if hasattr(self, '_ball') and hasattr(self._ball, 'body') and hasattr(self._ball.body, 'position'):
                        npc.update(self._ball)
                    else:
                        npc.update()
            
            # Now draw only active NPCs
            npc_count = 0
            for npc in self.NPCs:
                if hasattr(npc, 'is_active') and npc.is_active:
                    # Draw NPC
                    screen.blit(npc.image, self._camera.apply(npc))
                    npc_count += 1
                    
                    # Draw interaction indicator if player is close enough
                    if hasattr(npc, 'draw_indicator') and hasattr(npc, 'show_indicator') and npc.show_indicator:
                        npc.draw_indicator(screen, self._camera)
        
        # Draw finish line tiles
        for tile in self._finish_tiles:
            if buffered_viewport.colliderect(tile.rect):
                # Get flag_image from constants
                try:
                    from constants import flag_image
                    screen.blit(flag_image, self._camera.apply(tile))
                except ImportError:
                    # Fallback if flag_image not available
                    pygame.draw.rect(screen, (255, 0, 0), self._camera.apply_rect(tile.rect), 3)

        if self.coins:
            for coin in self.coins:
                screen.blit(coin.image, self._camera.apply(coin))

        # Draw dialogue system if active
        if self._in_dialogue:
            self._dialogue_system.draw(screen)
        
                # Draw timer in top-left corner (only if not in dialogue or showing results)
        if not self._in_dialogue and not self._showing_results and self._timer.is_running:
            self.draw_timer(screen)
        
        # Draw stats HUD in top-right corner
        if not self._showing_results:
            self.draw_stats_hud(screen)
        
        # Draw results screen if active
        if self._showing_results:
            self._results_screen.draw(screen, level_index=level_index)

class SpaceLevel(PymunkLevel):
    """Space-themed level with low gravity and space backgrounds"""
    
    def __init__(self, spawn, tmx_map=None, level_index=4, gamesave=None):
        # Call parent constructor with disabled music
        super().__init__(spawn, tmx_map, play_music=False, level_index=4, gamesave=gamesave)
        self._level_index = level_index  # Store the level index for music and stats
        # Set space-specific music
        self._setup_space_music()
        self._gamesave = gamesave
        # Override gravity with a much lower value
        self._physics.space.gravity = (0, 450)  # Adjusted for space-like conditions
        
        # Set up space-themed parallax background
        self._setup_space_background()
    
    def _setup_space_music(self):
        """Set up space-themed music"""
        global CURRENT_TRACK
        try:
            pygame.mixer_music.load(os.path.join("assets", "music", "space.mp3"))
            CURRENT_TRACK = 'space'
            pygame.mixer_music.play(-1)
        except:
            print("Space music not found, using alternative music")
            try:
                pygame.mixer_music.load(os.path.join("assets", "music", "level 1.mp3"))
                pygame.mixer_music.set_volume(1.0)
                pygame.mixer_music.play(-1)
            except:
                print("Failed to load any music")
    
    def _setup_space_background(self):
        """Set up space-themed parallax background"""
        # Create a new parallax background for space
        self._parallax_bg = ParallaxBackground(SCREEN_WIDTH, SCREEN_HEIGHT)
        
        # Define space-themed background paths
        # We'll look for space backgrounds in "Space" directory, but provide fallbacks
        space_bg_paths = [
            {"path": os.path.join("assets", "backgrounds", "moon", "1.png"), "factor": 0.1}
        ]
        
        # Try to load each space layer
        bg_loaded = False
        for bg in space_bg_paths:
            if os.path.exists(bg["path"]):
                if self._parallax_bg.add_layer(bg["path"], bg["factor"]):
                    bg_loaded = True
                    print(f"Loaded space background: {bg['path']}")
        
        # If no space backgrounds are found, create a starfield procedurally
        if not bg_loaded:
            print("No space backgrounds found. Creating procedural starfield.")
            self._create_procedural_starfield()
    
    def _create_procedural_starfield(self):
        """Create a procedural starfield background"""
        # Create a black background
        bg_surface = pygame.Surface((SCREEN_WIDTH * 2, SCREEN_HEIGHT * 2))
        bg_surface.fill((0, 0, 20))  # Very dark blue
        
        # Add stars of different sizes and brightness
        for _ in range(300):
            x = random.randint(0, bg_surface.get_width() - 1)
            y = random.randint(0, bg_surface.get_height() - 1)
            size = random.randint(1, 3)
            brightness = random.randint(100, 255)
            color = (brightness, brightness, brightness)
            pygame.draw.circle(bg_surface, color, (x, y), size)
        
        # Add the starfield as a layer with minimal parallax
        self._parallax_bg.add_surface(bg_surface, 0.05)
    
    def update(self, dt=0, level_index=4):
        """Update level state with space-specific behaviors"""
        # Call the parent update method first
        super().update(dt, level_index=self._level_index)
    
    def draw(self, screen, level_index=0):
        """Draw the space level with the ball rendered behind everything else"""
        level_index = self._level_index
        # Draw parallax background
        self._parallax_bg.draw(screen)
        
        # Get the current viewport rectangle with buffer zone
        viewport = pygame.Rect(
            -self._camera.offset_x, 
            -self._camera.offset_y, 
            SCREEN_WIDTH, 
            SCREEN_HEIGHT
        )
        
        # Expand viewport by buffer to prevent pop-in at edges
        buffered_viewport = viewport.inflate(self._viewport_buffer * 2, self._viewport_buffer * 2)
        
        # Query the spatial grid for visible tiles
        visible_tiles = self._spatial_grid.query_rect(buffered_viewport)
        
        # Update statistics
        self._rendered_tiles_count = 0
        self._culled_tiles_count = self._total_tiles - len(visible_tiles)
        
        # Define explicit layer order with background first, then other layers
        layer_order = {"background": 0, "Surface B": 1, "Masks B": 2, "Masks F": 3, "Surface F": 4, "Objects": 5}
        
        # Group tiles by layer for batch rendering
        layer_groups = {}
        for tile in visible_tiles:
            if not tile.visible:
                continue
                
            layer_name = getattr(tile, 'layer_name', 'Unknown')
            if layer_name not in layer_groups:
                layer_groups[layer_name] = []
                
            layer_groups[layer_name].append(tile)
            self._rendered_tiles_count += 1
        
        # First draw only background layer if it exists
        if "background" in layer_groups:
            for tile in layer_groups["background"]:
                screen.blit(tile.image, self._camera.apply(tile))
        
        # Now draw the ball AFTER background but BEFORE other tiles
        if hasattr(self, '_ball'):
            screen.blit(self._ball.image, self._camera.apply(self._ball))
        
        # Draw remaining layers (excluding background which was already drawn)
        for layer_name in sorted(layer_groups.keys(), key=lambda name: layer_order.get(name, 999)):
            if layer_name != "background":  # Skip background as it's already drawn
                for tile in layer_groups[layer_name]:
                    screen.blit(tile.image, self._camera.apply(tile))
        
        # Draw NPCs - All NPCs first, then hide based on distance
        if hasattr(self, 'NPCs') and self.NPCs:
            # First update activity state of all NPCs
            for npc in self.NPCs:
                if hasattr(npc, 'update'):
                    # Only pass the ball if it exists and has the right properties
                    if hasattr(self, '_ball') and hasattr(self._ball, 'body') and hasattr(self._ball.body, 'position'):
                        npc.update(self._ball)
                    else:
                        npc.update()
            
            # Now draw only active NPCs
            npc_count = 0
            for npc in self.NPCs:
                if hasattr(npc, 'is_active') and npc.is_active:
                    # Draw NPC
                    screen.blit(npc.image, self._camera.apply(npc))
                    npc_count += 1
                    
                    # Draw interaction indicator if player is close enough
                    if hasattr(npc, 'draw_indicator') and hasattr(npc, 'show_indicator') and npc.show_indicator:
                        npc.draw_indicator(screen, self._camera)
        
        # Draw finish line tiles
        for tile in self._finish_tiles:
            if buffered_viewport.colliderect(tile.rect):
                # Get flag_image from constants
                try:
                    from constants import flag_image
                    screen.blit(flag_image, self._camera.apply(tile))
                except ImportError:
                    # Fallback if flag_image not available
                    pygame.draw.rect(screen, (255, 0, 0), self._camera.apply_rect(tile.rect), 3)

        if self.coins:
            for coin in self.coins:
                screen.blit(coin.image, self._camera.apply(coin))
                
        # Draw dialogue system if active
        if self._in_dialogue:
            self._dialogue_system.draw(screen)
        
                # Draw timer in top-left corner (only if not in dialogue or showing results)
        if not self._in_dialogue and not self._showing_results and self._timer.is_running:
            self.draw_timer(screen)
        
        # Draw stats HUD in top-right corner
        if not self._showing_results:
            self.draw_stats_hud(screen)
        
        # Draw results screen if active
        if self._showing_results:
            self._results_screen.draw(screen, level_index=level_index)

class BossArena(SpaceLevel):
    """The final Level is a bossfight against Cubodeez The Almighty Cube"""
    
    def __init__(self, spawn, tmx_map=None):
        # Call parent constructor but disable default music
        super().__init__(spawn, tmx_map)
        
        # Set proper space gravity (use SpaceLevel's gravity)
        self._physics.space.gravity = (0, 450)  # Same as SpaceLevel

        # Initialize explosion group
        self._explosion_group = pygame.sprite.Group()
        
        # Boss arena properties
        self._initialize_boss_state()
        
        # Make physics space available to boss for collision filtering
        self._setup_physics_properties()
        
        # Set boss-specific music
        self._setup_boss_music()
        
        # Load sound effects
        self._load_sound_effects()
        
        # Set up arrow indicator
        self._setup_arrow_indicator()
        
        # Camera properties for boss fight
        self._camera_shake_amount = 0
        self._camera_shake_duration = 0
        
        # Performance optimizations
        self._update_frame_counter = 0
        self._help_text_alpha = 255  # For fading help text
        self._help_text_surf = None  # Cache help text surface
        self._boss_name_surf = None  # Cache boss name text
        self._cached_health_width = -1  # For health bar optimization
        self._player_defeat_sound = None
        # Player death handling for game over screen
        self._setup_player_death_handling()
        
        # Game over UI
        self._setup_game_over_ui()
        
        # Victory sequence after victory
        self._setup_victory_sequence()
        
        # Set up the original ball with custom death behavior
        self._setup_ball_with_custom_death()

        # Initialize rocket launchers group
        self._rocket_launchers = pygame.sprite.Group()
        self._explosions = pygame.sprite.Group()
        
        print("Boss arena initialized with space gravity and defeat mechanisms")
    
    def _initialize_boss_state(self):
        """Initialize the boss state variables"""
        self._boss_active = False
        self._boss_intro_played = False
        self._boss_defeated = False
        self._intro_timer = 3.0  # Time for intro sequence
        self._intro_sequence_active = True  # Flag to ensure intro completes
        self._intro_fade_in = 0.0  # Intro fade in progress
        self._intro_text_scale = 1.0  # Initial scale for intro text
        self._boss = None
        self._show_boss_arrow = False
    
    def _setup_physics_properties(self):
        """Set up physics properties for the level"""
        if hasattr(self, 'width'):
            self._physics.level_width = self.width
        if hasattr(self, 'height'):
            self._physics.level_height = self.height
    
    def _setup_boss_music(self):
        """Set up boss-specific music"""
        global CURRENT_TRACK
        # Load boss-specific music
        if CURRENT_TRACK != 'boss':
            try:
                pygame.mixer_music.load(os.path.join("assets", "music", "boss.mp3"))
                CURRENT_TRACK = 'boss'
                pygame.mixer_music.set_volume(0.5)  # Slightly louder for intensity
                pygame.mixer_music.play(-1)
            except:
                print("Boss music not found, using alternative music")
                try:
                    pygame.mixer_music.load(os.path.join("assets", "music", "space.mp3"))
                    pygame.mixer_music.play(-1)
                except:
                    print("Failed to load any boss music")
        self._player_defeat_sound = os.path.join("assets", "music", "game over.mp3")
    
    def _load_sound_effects(self):
        """Load boss-related sound effects"""
        try:
            self._boss_intro_sound = pygame.mixer.Sound(os.path.join("assets", "sounds", "boss_intro.mp3"))
            self._boss_defeat_sound = pygame.mixer.Sound(os.path.join("assets", "sounds", "boss_defeat.mp3"))
        except:
            print("Could not load boss sound effects")
            self._boss_intro_sound = None
            self._boss_defeat_sound = None
    
    def _setup_arrow_indicator(self):
        """Set up the arrow indicator for the boss"""
        self._arrow_size = 69  # Size of the arrow
        self._arrow_distance = 40  # Distance from edge of screen
        self._arrow_color = (255, 0, 0)  # Bright red arrow
        self._arrow_outline_color = (255, 255, 255)  # White outline
        self._arrow_thickness = 3
        self._arrow_outline_thickness = 5
        self._arrow_fade_speed = 0.1  # For arrow pulsing effect
        self._arrow_alpha = 255
        self._arrow_fade_dir = -1  # Direction of fade (in or out)
        self._arrow_rotation = 0  # Current rotation angle
        self._arrow_position = (0, 0)  # Current position of the arrow

        # Create an arrow surface (or load one if you have an image)
        try:
            self._arrow_image = pygame.image.load(os.path.join("assets", "sprites", "arrow.png"))
            self._arrow_image = pygame.transform.scale(self._arrow_image, (self._arrow_size, self._arrow_size))
        except:
            # Create a triangular arrow if image loading fails
            self._arrow_image = None
            print("Using fallback arrow - couldn't load arrow image")
    
    def _setup_player_death_handling(self):
        """Set up player death handling variables"""
        self._player_death_timer = 0
        self._player_death_delay = 1.0  # Shorter delay before showing game over
        self._player_is_dead = False
        self._show_game_over = False
        self._prevent_auto_respawn = True  # Prevent auto-respawn
        
        # Update the auto-return delay to make it shorter
        self._game_over_delay = 2.0  # 2 seconds before returning to menu
        self._game_over_timer = 0.0  # Timer to track the delay
    
    def _setup_game_over_ui(self):
        """Set up the game over UI elements"""
        self._game_over_buttons = []
        self._retry_button_rect = None
        self._menu_button_rect = None
        self._button_hover = {
            "retry": False,
            "menu": False
        }
        
        # Fade effect for game over screen
        self._game_over_fade_alpha = 0  # Start at 0 (transparent)
        self._game_over_fade_speed = 255  # Alpha units per second
        self._game_over_buttons_ready = False
        
        # NEW: Auto-return to menu after game over
        self._game_over_delay = 2.0  # 2 seconds delay before returning to menu
        self._game_over_timer = 0.0  # Timer to track the delay
        
        # Font for game over screen - adjusted size
        try:
            self._game_over_font = pygame.font.Font(os.path.join("assets", "Daydream.ttf"), 28)  # Smaller size
            self._button_font = pygame.font.Font(os.path.join("assets", "Daydream.ttf"), 24)
        except:
            self._game_over_font = pygame.font.SysFont(None, 36)  # Smaller fallback
            self._button_font = pygame.font.SysFont(None, 28)
    
    def _setup_victory_sequence(self):
        """Set up the victory sequence variables"""
        self._credits = None
        self._victory_delay = 3.0  # Time to show victory message before credits
        self._victory_timer = 0.0  # Timer to track delay
        self._show_credits = False
        
        # Boss explosion and fade to black effect variables
        self._boss_explosion = None
        self._fade_alpha = 0
        self._fading_to_black = False
        self._credits_duration = 65  # 1 minute and 5 seconds in seconds
    
    def _setup_ball_with_custom_death(self):
        """Set up custom death handling for the player ball"""
        # Store the original death method to call it later
        if hasattr(self._ball, 'death'):
            self._ball._original_death = self._ball.death
            
            # Create a reference to self that can be used in the method
            boss_arena = self
            
            # Override the death method with our custom version
            def custom_death_method():
                # Call the original method
                boss_arena._ball._original_death()
                
                # Now set our flags to show game over instead of respawning
                boss_arena._prevent_auto_respawn = True
                boss_arena._player_is_dead = True
                boss_arena._game_over_fade_alpha = 0  # Start with transparent overlay
                boss_arena._game_over_timer = 0.0  # Reset the auto-return timer
                
                # Play death sound if available
                pygame.mixer_music.fadeout(200)
                time.sleep(0.2)  # Wait for fadeout to complete
                pygame.mixer_music.load(os.path.join("assets", "music", "game over.mp3"))
                pygame.mixer_music.play()  

                print("Player killed by Cubodeez - showing game over screen")
                
            # Replace the death method
            self._ball.death = custom_death_method
        
        # Add a reference to this level in the ball
        self._ball.level = self
    
    @property
    def boss(self):
        return self._boss

    @property
    def explosions(self):
        return self._explosions
    
    @property
    def rocket_launchers(self):
        return self._rocket_launchers
    
    @property
    def boss_defeated(self):
        return self._boss_defeated
    
    def initialize_boss(self):
        """Initialize the boss after intro sequence is complete"""
        boss_x, boss_y = self._get_boss_spawn_point()
        # Import Cubodeez at runtime to avoid circular imports
        self._boss = cb(self._physics, boss_x, boss_y, target_ball=self._ball, size=150)
        print(f"Boss initialized at ({boss_x}, {boss_y})")
        
        # Verify boss collision type
        if hasattr(self._boss, 'shape') and hasattr(self._boss.shape, 'collision_type'):
            print(f"Boss collision type: {self._boss.shape.collision_type}")

        # Load rocket launchers now that boss is available
        self._load_rocket_launchers()

    def _load_rocket_launchers(self):
        """Find and place rocket launchers at marked rocket tiles or objects"""
        rocket_count = 0
        
        # Process tile layers for rocket properties
        for layer in self._tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer) and layer.name == "Objects":
                print(f"Searching for rocket tiles in Objects layer")
                
                # Get the layer index for direct property access
                layer_index = self._tmx_data.layers.index(layer)
                
                for x, y, gid in layer.tiles():
                    try:
                        # Try two different methods to get properties
                        if isinstance(gid, pygame.Surface):
                            # For direct image tiles, try using coordinates and layer index
                            properties = self._tmx_data.get_tile_properties(x, y, layer_index) or {}
                            print(f"Image tile at ({x}, {y}) properties: {properties}")
                        else:
                            # For tileset-based tiles, use GID
                            properties = self._tmx_data.get_tile_properties_by_gid(gid) or {}
                            print(f"Tileset tile at ({x}, {y}) properties: {properties}")
                        
                        # Check if this tile is marked as a rocket launcher
                        if properties.get('Rocket', False):
                            # Create rocket launcher logic
                            world_x = x * self._TILE_SIZE
                            world_y = y * self._TILE_SIZE
                            
                            launcher = RocketLauncher(
                                world_x + self._TILE_SIZE // 2,
                                world_y + self._TILE_SIZE // 2,
                                self._boss,
                                explosion_group=self._explosions
                            )
                            self._rocket_launchers.add(launcher)
                            rocket_count += 1
                            print(f"Placed tile-based rocket launcher at ({world_x}, {world_y})")
                            
                    except Exception as e:
                        print(f"Error processing rocket tile at ({x}, {y}): {e}")
        
        print(f"Found and placed {rocket_count} rocket launchers")
    
    def _get_boss_spawn_point(self):
        """Find a suitable spawn point for the boss based on level design"""
        # Check if there's a designated spawn point in the level data
        for layer in self._tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledObjectGroup):
                for obj in layer:
                    if hasattr(obj, 'name') and obj.name == "BossSpawn":
                        return obj.x, obj.y
        
        # Fallback: Place boss on the other side of the level from the player
        spawn_x = 500
        spawn_y = 900  # A reasonable height above ground
        return spawn_x, spawn_y
    
    def is_boss_on_screen(self):
        """Check if the boss is currently visible on screen"""
        if not self._boss or not self._boss_active:
            return True  # No boss to show arrow for
            
        # Get screen boundaries in world coordinates
        screen_left = -self._camera.offset_x
        screen_right = -self._camera.offset_x + SCREEN_WIDTH
        screen_top = -self._camera.offset_y
        screen_bottom = -self._camera.offset_y + SCREEN_HEIGHT
        
        # Get boss position and size
        boss_x, boss_y = self._boss.body.position
        half_size = self._boss.size / 2
        
        # Check if boss is visible on screen
        boss_rect = pygame.Rect(
            boss_x - half_size,
            boss_y - half_size,
            self._boss.size,
            self._boss.size
        )
        
        screen_rect = pygame.Rect(
            screen_left,
            screen_top,
            SCREEN_WIDTH,
            SCREEN_HEIGHT
        )
        
        # Consider boss visible if at least 25% of it is on screen
        # This adds some buffer so the arrow doesn't flicker when boss is partially visible
        visible_threshold = 0.25
        
        # Calculate intersection area
        intersection = boss_rect.clip(screen_rect)
        if intersection.width * intersection.height <= 0:
            return False  # No intersection at all
        
        # Calculate percentage of boss visible
        boss_area = boss_rect.width * boss_rect.height
        visible_area = intersection.width * intersection.height
        percent_visible = visible_area / boss_area
        
        return percent_visible >= visible_threshold

    def calculate_arrow_position_and_rotation(self):
        """Calculate where to position the arrow and what direction it should point"""
        if not self._boss or not self._boss_active:
            return
            
        # Get screen center in world coordinates
        screen_center_x = -self._camera.offset_x + SCREEN_WIDTH / 2
        screen_center_y = -self._camera.offset_y + SCREEN_HEIGHT / 2
        
        # Get boss position
        boss_x, boss_y = self._boss.body.position
        
        # Calculate direction vector from screen center to boss
        dir_x = boss_x - screen_center_x
        dir_y = boss_y - screen_center_y
        
        # Calculate angle in radians, then convert to degrees
        angle = math.atan2(dir_y, dir_x)
        angle_degrees = math.degrees(angle)
        
        # Store rotation angle for the arrow (point towards the boss)
        self._arrow_rotation = angle_degrees
        
        # Calculate position at the edge of the screen
        # Start with the screen edges minus arrow_distance (buffer)
        edge_buffer = self._arrow_distance
        
        # Screen boundaries for arrow placement
        min_x = edge_buffer
        max_x = SCREEN_WIDTH - edge_buffer
        min_y = edge_buffer
        max_y = SCREEN_HEIGHT - edge_buffer
        
        # Calculate intersection with screen edge
        # Normalized direction vector
        length = math.sqrt(dir_x * dir_x + dir_y * dir_y)
        if length == 0:  # Avoid division by zero
            norm_x, norm_y = 0, 0
        else:
            norm_x = dir_x / length
            norm_y = dir_y / length
        
        # Calculate intersection with screen edge
        # Determine which edge we're going to hit first
        t_values = []
        
        # Left edge
        if norm_x < 0:
            t_values.append((min_x - SCREEN_WIDTH/2) / norm_x)
        # Right edge
        elif norm_x > 0:
            t_values.append((max_x - SCREEN_WIDTH/2) / norm_x)
        
        # Top edge
        if norm_y < 0:
            t_values.append((min_y - SCREEN_HEIGHT/2) / norm_y)
        # Bottom edge
        elif norm_y > 0:
            t_values.append((max_y - SCREEN_HEIGHT/2) / norm_y)
        
        # Find the smallest positive t value
        t = min([t for t in t_values if t > 0], default=0)
        
        # Calculate the intersection point at the edge of the screen
        arrow_x = SCREEN_WIDTH/2 + norm_x * t
        arrow_y = SCREEN_HEIGHT/2 + norm_y * t
        
        # Clamp to screen edges (just in case)
        arrow_x = max(min_x, min(max_x, arrow_x))
        arrow_y = max(min_y, min(max_y, arrow_y))
        
        self._arrow_position = (arrow_x, arrow_y)

    def draw_boss_arrow(self, screen):
        """Draw an arrow pointing to the boss when off-screen"""
        # Check if we need to show the arrow
        self._show_boss_arrow = self._boss_active and not self.is_boss_on_screen()
        
        if not self._show_boss_arrow:
            return
        
        # Calculate arrow position and rotation
        self.calculate_arrow_position_and_rotation()
        
        # Update pulse effect
        self._arrow_alpha += self._arrow_fade_dir * self._arrow_fade_speed * 255
        if self._arrow_alpha <= 150:
            self._arrow_alpha = 150
            self._arrow_fade_dir = 1
        elif self._arrow_alpha >= 255:
            self._arrow_alpha = 255
            self._arrow_fade_dir = -1
        
        # Draw the arrow
        if self._arrow_image:
            # Rotate the image
            rotated_arrow = pygame.transform.rotate(self._arrow_image, -self._arrow_rotation - 90)
            
            # Set transparency
            rotated_arrow.set_alpha(int(self._arrow_alpha))
            
            # Position it
            arrow_rect = rotated_arrow.get_rect(center=self._arrow_position)
            screen.blit(rotated_arrow, arrow_rect)
        else:
            # Draw a triangular arrow if no image
            # Calculate vertices of the triangle
            angle_rad = math.radians(self._arrow_rotation)
            
            # Triangle points (arrow shape)
            x, y = self._arrow_position
            pt1_x = x + math.cos(angle_rad) * self._arrow_size
            pt1_y = y + math.sin(angle_rad) * self._arrow_size
            
            pt2_x = x + math.cos(angle_rad + 2.5) * (self._arrow_size * 0.6)
            pt2_y = y + math.sin(angle_rad + 2.5) * (self._arrow_size * 0.6)
            
            pt3_x = x + math.cos(angle_rad - 2.5) * (self._arrow_size * 0.6)
            pt3_y = y + math.sin(angle_rad - 2.5) * (self._arrow_size * 0.6)
            
            points = [(pt1_x, pt1_y), (pt2_x, pt2_y), (pt3_x, pt3_y)]
            
            # Draw white outline first (for better visibility)
            pygame.draw.polygon(screen, self._arrow_outline_color, points, 0)
            
            # Then draw the inner color with adjusted alpha
            inner_color = (self._arrow_color[0], self._arrow_color[1], self._arrow_color[2], int(self._arrow_alpha))
            arrow_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(arrow_surf, inner_color, points, 0)
            screen.blit(arrow_surf, (0, 0))
    
    def create_game_over_buttons(self):
        """Create buttons for the game over screen"""
        # Calculate button sizes and positions
        button_width = 200
        button_height = 60
        button_y_offset = 80
        
        # Center positions
        screen_center_x = SCREEN_WIDTH // 2
        screen_center_y = SCREEN_HEIGHT // 2
        
        # Create retry button
        retry_x = screen_center_x - button_width - 20
        retry_y = screen_center_y + button_y_offset
        self._retry_button_rect = pygame.Rect(retry_x, retry_y, button_width, button_height)
        
        # Create menu button
        menu_x = screen_center_x + 20
        menu_y = screen_center_y + button_y_offset
        self._menu_button_rect = pygame.Rect(menu_x, menu_y, button_width, button_height)
        
        # Mark buttons as ready
        self._game_over_buttons_ready = True
    
    def reset_level(self):
        """Completely reload the entire level as if quitting and relogging, but keep the music playing."""
        print("Resetting the entire level...")

        # Clear all physics objects
        self.clear_physics_objects()
        # Reset all attributes to their initial state
        self.__init__(self._spawn_point, self._tmx_map)

        # Reload the TMX map
        if self._tmx_map:
            self.load_tmx(self._tmx_map)

        # Reinitialize the boss
        self._boss = None
        self.initialize_boss()

        # Reset game state flags
        self._boss_active = False
        self._boss_intro_played = False
        self._boss_defeated = False
        self._intro_timer = 3.0
        self._intro_sequence_active = True
        self._intro_fade_in = 0.0
        self._intro_text_scale = 1.0
        self._player_is_dead = False
        self._show_game_over = False
        self._prevent_auto_respawn = False
        self._game_over_fade_alpha = 0
        self._game_over_buttons_ready = False
        self._show_credits = False

        print("Level reset complete.")
    
    def start_boss_fight(self):
        """Start the boss fight with an introduction sequence"""
        self._boss_intro_played = True
        self._boss_active = True
        
        # Play intro sound if available
        if self._boss_intro_sound:
            self._boss_intro_sound.play()
        
        # Add a camera shake for dramatic effect
        self._shake_camera(0.5, 10)
        
        print("Boss fight started!")
    
    def _shake_camera(self, duration, amount):
        """Apply a camera shake effect"""
        self._camera_shake_duration = duration
        self._camera_shake_amount = amount
    
    def handle_boss_defeat(self):
        """Handle boss defeat sequence with explosion and transition to credits"""
        if self._boss_defeated:
            return  # Prevent multiple calls
            
        self._boss_defeated = True
        
        # Get boss position for the explosion
        boss_x, boss_y = self._boss.body.position
        
        # Create a large explosion at the boss's position
        self._boss_explosion = Explosion(boss_x, boss_y)
        
        # Scale up the explosion to be bigger than the boss
        explosion_scale = self._boss.size / 50  # Adjust based on boss size and explosion sprite size
        for i in range(len(self._boss_explosion.explosion_frames)):
            frame = self._boss_explosion.explosion_frames[i]
            scaled_width = int(frame.get_width() * explosion_scale)
            scaled_height = int(frame.get_height() * explosion_scale)
            self._boss_explosion.explosion_frames[i] = pygame.transform.scale(frame, (scaled_width, scaled_height))
        
        # Set the initial frame
        self._boss_explosion.image = self._boss_explosion.explosion_frames[0]
        self._boss_explosion.rect = self._boss_explosion.image.get_rect(center=(boss_x, boss_y))
        
        # Play defeat sound if available
        if self._boss_defeat_sound:
            self._boss_defeat_sound.play()
        else:
            # Fallback to explosion sound if defeat sound isn't available
            if hasattr(self._boss_explosion, 'explosion_sound') and self._boss_explosion.explosion_sound:
                self._boss_explosion.explosion_sound.set_volume(1.0)  # Make it louder
        
        # Apply camera shake for impact
        self._shake_camera(1.0, 20)
        
        # Reset victory timer for transition timing
        self._victory_timer = 0.0
        
        # Remove the boss from physics space to avoid further collisions
        if self._boss.body in self._physics.space.bodies:
            try:
                self._physics.space.remove(self._boss.body, self._boss.shape)
            except:
                pass
        
        print("Boss defeated! Beginning end sequence.")
    
    def damage_boss(self, damage=10):
        """Apply damage to the boss"""
        if self._boss and self._boss.vulnerable and not self._boss.damaged_this_cycle:
            self._boss.health -= damage
            self._boss.health = max(0, self._boss.health)  # Ensure health doesn't go negative
            self._boss.damaged_this_cycle = True
            
            # Apply camera shake for effect
            self._shake_camera(0.2, 5)
            
            return True
        return False
    
    def reset_ball(self):
        """Reset the ball to the last checkpoint or spawn point"""
        # Skip if auto-respawn is prevented
        if self._prevent_auto_respawn and self._player_is_dead:
            print("Auto-respawn prevented - showing game over screen instead")
            # Start the timer for the game over screen
            self._player_death_timer = 0
            return False  # Indicate that we didn't reset
        
        # Otherwise, proceed with normal reset
        return super().reset_ball()
    
    def update(self, dt=0):
        """Update boss arena state with improved ending sequence"""
        # If showing credits, update credits and check for timeout
        if self._show_credits and self._credits:
            self._credits.update()
            
            # Calculate elapsed time in credits
            credits_elapsed_time = (pygame.time.get_ticks() - self._credits.start_time) / 1000
            
            # Return to main menu after credits duration
            if credits_elapsed_time >= self._credits_duration:
                print(f"Credits complete after {credits_elapsed_time:.1f} seconds - returning to main menu")
                
                if hasattr(self, '_game_ref') and self._game_ref:
                    # Fade out music
                    pygame.mixer_music.fadeout(500)
                    # Set state to main menu
                    self._game_ref.state = "main_menu"
                    # Play menu music
                    try:
                        pygame.mixer_music.load(os.path.join("assets", "music", "theme.mp3"))
                        global CURRENT_TRACK
                        CURRENT_TRACK = 'menu'
                        pygame.mixer_music.play(-1)
                    except:
                        pass
            
            return

        # Update the boss explosion animation if it exists
        if self._boss_defeated and self._boss_explosion:
            if hasattr(self._boss_explosion, 'update'):
                self._boss_explosion.update(dt)
                
                # If the explosion animation reaches its end, start fading to black
                if self._boss_explosion.frame_index >= len(self._boss_explosion.explosion_frames) - 1:
                    self._fading_to_black = True

        # Handle fade to black transition
        if self._fading_to_black:
            self._fade_alpha += 300 * dt  # Fade speed (0-255 in about 0.85 seconds)
            if self._fade_alpha >= 255:
                self._fade_alpha = 255
                
                # If fade is complete, start showing credits
                if not self._show_credits:
                    self._show_credits = True
                    
                    # Initialize credits if not already done
                    if not self._credits:
                        print("Initializing credits sequence")
                        screen = pygame.display.get_surface()
                        screen.fill("BLACK")
                        self._credits = Credits(screen, SCREEN_WIDTH, SCREEN_HEIGHT)
                    
                    # Stop any boss-related sounds that might still be playing
                    if self._boss_defeat_sound:
                        self._boss_defeat_sound.stop()
                    if self._boss_explosion and hasattr(self._boss_explosion, 'explosion_sound'):
                        self._boss_explosion.explosion_sound.stop()

        # Intro sequence handling
        if self._intro_sequence_active:
            self._handle_intro_sequence(dt)
            return
        
        # Game over screen handling
        if self._player_is_dead:
            self._handle_player_death(dt)
            return
        
        # Victory sequence handling
        if self._boss_defeated and not self._show_credits and not self._fading_to_black:
            self._victory_timer += dt
            
            # Show victory text for a moment before starting the fade
            if self._victory_timer >= self._victory_delay:
                print("Victory delay complete - starting fade to black")
                self._fading_to_black = True
            
            # Don't update gameplay during victory screen
            return
        
        # Don't update gameplay if showing game over screen
        if self._show_game_over:
            return
        
        # Handle camera shake
        if self._camera_shake_duration > 0:
            self._camera_shake_duration -= dt
            if self._camera_shake_duration <= 0:
                # Reset camera position when shake ends
                self._camera.offset_x = self._camera.offset_x
                self._camera.offset_y = self._camera.offset_y
            else:
                # Apply random shake offset to camera
                shake_x = random.randint(-self._camera_shake_amount, self._camera_shake_amount)
                shake_y = random.randint(-self._camera_shake_amount, self._camera_shake_amount)
                self._camera.offset_x += shake_x
                self._camera.offset_y += shake_y
        
        # Core gameplay update
        self._update_gameplay(dt)
    
    def _handle_intro_sequence(self, dt):
        """Handle the boss intro sequence"""
        # Update intro timer
        self._intro_timer -= dt
        
        # Update intro fade in effect
        if self._intro_fade_in < 1.0:
            self._intro_fade_in += dt * 0.5  # Fade in over 2 seconds
            if self._intro_fade_in > 1.0:
                self._intro_fade_in = 1.0
        
        # Calculate text effect based on timer
        self._intro_text_scale = max(1.0, 2.0 - self._intro_timer / 1.5)
        
        # When timer runs out, initialize boss and start fight
        if self._intro_timer <= 0 and not self._boss_intro_played:
            self._intro_sequence_active = False
            if not self._boss:
                self.initialize_boss()
            self.start_boss_fight()
        
        # Call parent update for basic physics
        super().update(dt)
    
    def _handle_player_death(self, dt):
        """Handle player death and game over screen"""
        # Update death timer
        self._player_death_timer += dt
        
        # Start showing game over screen after delay
        if self._player_death_timer >= self._player_death_delay:
            self._show_game_over = True
            
            # Create buttons if not already created
            if not self._game_over_buttons_ready:
                self.create_game_over_buttons()
            
            # Fade in effect
            if self._game_over_fade_alpha < 255:
                self._game_over_fade_alpha += int(self._game_over_fade_speed * dt)
                self._game_over_fade_alpha = min(255, self._game_over_fade_alpha)
                
            # Update the auto-return timer
            self._game_over_timer += dt
    
    def _update_gameplay(self, dt):
        """Update core gameplay elements"""
        # Update rocket launchers with player, keys, and dt
        keys = pygame.key.get_pressed()
        if keys[pygame.K_F11]:
            self.boss.health = 0  # For testing purposes, set boss health to 0
        for launcher in self._rocket_launchers:
            launcher.update(dt, self._ball, keys)
        
        # Update explosions
        self._explosions.update(dt)
        
        # Call parent update for normal gameplay (skip if transitioning)
        if not self._fading_to_black and not self._boss_defeated:
            super().update(dt)
        
        # Skip boss updates if not active
        if not self._boss_active or not self._boss:
            return
            
        # Update boss state (unless defeated)
        if not self._boss_defeated:
            self._boss.update()
            
            # Check for direct player squishing by boss
            self._check_boss_player_collision()
            
            # Check for victory condition
            if self._boss and self._boss.health <= 0 and not self._boss_defeated:
                self.handle_boss_defeat()
    
    def _check_boss_player_collision(self):
        """Check for direct collision between boss and player"""
        if not self._boss or not self._boss_active or not self._ball:
            return
        
        # First check for player squishing
        if self._boss.check_player_squish():
            # Kill the player if not already dead
            if hasattr(self._ball, 'death') and not self._ball.is_dead:
                print("Direct squish detection in update method!")
                self._ball.death()
        
        # Add direct collision check with player for better detection
        if self._boss._jumping and self._boss.body.velocity.y > 200:
            # Simple AABB collision check
            boss_rect = self._boss.rect
            player_rect = self._ball.rect
            
            if boss_rect.colliderect(player_rect):
                # Direct collision detection
                print("Direct collision detected between boss and player!")
                
                # Kill the player if not already dead
                if hasattr(self._ball, 'death') and not self._ball.is_dead:
                    print("Directly squishing player from collision check")
                    self._ball.death()
                    if self._boss._squish_sound:
                        self._boss._squish_sound.play()
    
    def draw(self, screen):
        """Draw the boss arena with all elements"""
        # If showing credits, only draw them
        if self._show_credits and self._credits:
            # Let the credits class handle the drawing completely
            self._credits.draw()
            return
            
        # Draw the level (from parent class)
        super().draw(screen)

        # Draw rocket launchers
        for launcher in self._rocket_launchers:
            launcher.draw(screen, self._camera)
        
        # Draw active rockets
        for launcher in self._rocket_launchers:
            for rocket in launcher.rockets:
                screen.blit(rocket.image, self._camera.apply(rocket))
        
        # Draw explosions
        for explosion in self._explosions:
            screen.blit(explosion.image, self._camera.apply(explosion))
        
        # If the boss is defeated, draw the big explosion instead of the boss
        if self._boss_defeated and self._boss_explosion:
            if hasattr(self._boss_explosion, 'rect') and hasattr(self._boss_explosion, 'image'):
                screen.blit(self._boss_explosion.image, self._camera.apply(self._boss_explosion))
        # Otherwise draw the boss if it's active and exists
        elif self._boss_active and self._boss:
            # Draw Cubodeez's target marker first
            self._boss.draw(screen, self._camera)
            
            # Draw the boss sprite itself
            screen.blit(self._boss.image, self._camera.apply(self._boss))
        
        # Draw boss health bar if active
        if self._boss_active and self._boss and not self._boss_defeated:
            self._draw_boss_health_bar(screen)
            
        # Draw intro/outro text
        if self._intro_sequence_active and not self._boss_intro_played:
            self._draw_intro_text(screen)
        elif self._boss_defeated and not self._show_credits:
            self._draw_victory_text(screen)
        
        # Draw help text for player
        if self._boss_active and self._boss and self._boss.vulnerable and not self._boss_defeated:
            self._draw_help_text(screen)
        
        # Draw boss arrow (if boss is off-screen)
        self.draw_boss_arrow(screen)

        # Draw game over screen if needed
        if self._show_game_over:
            self._draw_game_over_screen(screen)
            
        # Draw fade to black overlay for transition to credits
        if self._fading_to_black:
            fade_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            fade_surface.fill((0, 0, 0, self._fade_alpha))
            screen.blit(fade_surface, (0, 0))
    
    def _draw_boss_health_bar(self, screen):
        """Draw the boss health bar at the top of the screen"""
        if not self._boss:
            return
            
        # Health bar dimensions and position
        bar_width = 500
        bar_height = 30
        x = (SCREEN_WIDTH - bar_width) // 2
        y = 20
        
        # Health percentage
        health_percent = self._boss.health / 100
        current_width = int(bar_width * health_percent)
        
        # Draw background (empty health)
        pygame.draw.rect(screen, (80, 0, 0), (x, y, bar_width, bar_height))
        
        # Draw filled health
        pygame.draw.rect(screen, (200, 0, 0), (x, y, current_width, bar_height))
        
        # Draw border
        pygame.draw.rect(screen, (0, 0, 0), (x, y, bar_width, bar_height), 2)
        
        # Draw boss name
        try:
            font = pygame.font.Font(os.path.join("assets", "Daydream.ttf"), 14)
        except:
            font = pygame.font.SysFont(None, 24)
            
        # Cache boss name surface for better performance
        if not self._boss_name_surf:
            self._boss_name_surf = font.render("CUBODEEZ THE ALMIGHTY CUBE", True, (255, 255, 255))
        
        text_rect = self._boss_name_surf.get_rect(center=(SCREEN_WIDTH // 2, y + bar_height // 2))
        screen.blit(self._boss_name_surf, text_rect)
    
    def _draw_help_text(self, screen):
        """Draw help text when boss is vulnerable"""
        # Cache help text for better performance
        if not self._help_text_surf:
            try:
                font = pygame.font.Font(os.path.join("assets", "Daydream.ttf"), 16)
            except:
                font = pygame.font.SysFont(None, 24)
                
            help_text = "CUBODEEZ IS VULNERABLE! USE THE ROCKET LAUNCHERS!"
            self._help_text_surf = font.render(help_text, True, (255, 255, 0))
            self._help_text_shadow = font.render(help_text, True, (0, 0, 0))
            
        text_rect = self._help_text_surf.get_rect(center=(screen.get_width()//2, 80))
        
        # Draw with shadow for better visibility
        shadow_rect = self._help_text_shadow.get_rect(center=(text_rect.centerx+2, text_rect.centery+2))
        
        screen.blit(self._help_text_shadow, shadow_rect)
        screen.blit(self._help_text_surf, text_rect)
    
    def _draw_intro_text(self, screen):
        """Draw boss introduction text"""
        try:
            font = pygame.font.Font(os.path.join("assets", "Daydream.ttf"), 24)
        except:
            font = pygame.font.SysFont(None, 36)
            
        # Create a semi-transparent overlay with fade-in effect
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(128 * self._intro_fade_in)))  # Fade in the overlay
        screen.blit(overlay, (0, 0))
        
        # Only show text if started fading in
        if self._intro_fade_in > 0.2:
            # Apply alpha to text based on fade-in progress
            text_alpha = int(255 * min(1.0, self._intro_fade_in * 1.5))
            
            # Draw boss name with dramatic effect
            # Introduce the boss with a scaling effect based on timer
            boss_text = font.render("CUBODEEZ THE ALMIGHTY CUBE", True, (255, 50, 50))
            
            # Scale text for dramatic effect
            scaled_width = int(boss_text.get_width() * self._intro_text_scale)
            scaled_height = int(boss_text.get_height() * self._intro_text_scale)
            
            # Make sure text is not too big
            max_width = SCREEN_WIDTH - 60
            if scaled_width > max_width:
                scale_factor = max_width / scaled_width
                scaled_width = max_width
                scaled_height = int(scaled_height * scale_factor)
            
            boss_text = pygame.transform.scale(
                boss_text, 
                (scaled_width, scaled_height)
            )
            
            # Apply alpha
            boss_text.set_alpha(text_alpha)
            
            # Position in center
            text_rect = boss_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            screen.blit(boss_text, text_rect)
            
            # Draw subtitle with fade-in
            subtitle = font.render("PREPARE TO BE SQUISHED", True, (255, 200, 200))
            subtitle.set_alpha(text_alpha)
            subtitle_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, text_rect.bottom + 40))
            screen.blit(subtitle, subtitle_rect)
    
    def _draw_victory_text(self, screen):
        """Draw victory text after defeating the boss"""
        try:
            font = pygame.font.Font(os.path.join("assets", "Daydream.ttf"), 36)
        except:
            font = pygame.font.SysFont(None, 48)
            
        # Create a semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        screen.blit(overlay, (0, 0))
        
        # Draw victory text
        victory_text = font.render("ENEMY FELLED", True, (200, 255, 200))
        text_rect = victory_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        screen.blit(victory_text, text_rect)
        
        # Draw subtitle
        subtitle = font.render("You have defeated Cubodeez", True, (255, 255, 255))
        subtitle_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, text_rect.bottom + 40))
        screen.blit(subtitle, subtitle_rect)
    
    def _draw_game_over_screen(self, screen):
        """Draw game over screen when the player is defeated by Cubodeez"""
        # Create a semi-transparent red overlay with fade effect
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((200, 0, 0, self._game_over_fade_alpha))  # Red with fading opacity
        screen.blit(overlay, (0, 0))
        
        # Only show text and buttons when sufficiently faded in
        if self._game_over_fade_alpha > 100:
            # Calculate alpha for text (starts appearing earlier than buttons)
            text_alpha = min(255, int(self._game_over_fade_alpha * 1.5))
            
            # Draw game over text - main text centered
            game_over_text = "You have been terminated"
            text_surf = self._game_over_font.render(game_over_text, True, (255, 255, 255))
            
            # Ensure text isn't too wide for screen
            if text_surf.get_width() > SCREEN_WIDTH - 40:
                # Recreate with smaller font
                try:
                    smaller_font = pygame.font.Font(os.path.join("assets", "Daydream.ttf"), 22)
                    text_surf = smaller_font.render(game_over_text, True, (255, 255, 255))
                except:
                    text_surf = pygame.font.SysFont(None, 28).render(game_over_text, True, (255, 255, 255))
            
            # Position in center
            text_rect = text_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))
            
            # Draw text shadow for better visibility
            shadow_surf = self._game_over_font.render(game_over_text, True, (0, 0, 0))
            shadow_rect = shadow_surf.get_rect(center=(text_rect.centerx + 3, text_rect.centery + 3))
            
            # Apply alpha to text surfaces
            text_surf.set_alpha(text_alpha)
            shadow_surf.set_alpha(text_alpha)
            
            screen.blit(shadow_surf, shadow_rect)
            screen.blit(text_surf, text_rect)
            
            # Only show buttons when fully faded in
            # Note: We don't need the buttons for auto-return, but leaving this code
            # in case we want to use buttons in the future
            if self._game_over_fade_alpha > 200 and self._game_over_buttons_ready:
                # Draw retry button with hover effect
                retry_color = (220, 220, 0) if self._button_hover["retry"] else (200, 200, 200)
                pygame.draw.rect(screen, (50, 0, 0), self._retry_button_rect)
                pygame.draw.rect(screen, (100, 0, 0), self._retry_button_rect, 3)
                
                retry_text = "RETRY"
                retry_surf = self._button_font.render(retry_text, True, retry_color)
                retry_text_rect = retry_surf.get_rect(center=self._retry_button_rect.center)
                screen.blit(retry_surf, retry_text_rect)
                
                # Draw menu button with hover effect
                menu_color = (220, 220, 0) if self._button_hover["menu"] else (200, 200, 200)
                pygame.draw.rect(screen, (50, 0, 0), self._menu_button_rect)
                pygame.draw.rect(screen, (100, 0, 0), self._menu_button_rect, 3)
                
                menu_text = "MENU"
                menu_surf = self._button_font.render(menu_text, True, menu_color)
                menu_text_rect = menu_surf.get_rect(center=self._menu_button_rect.center)
                screen.blit(menu_surf, menu_text_rect)
    
    def handle_events(self, event):
        """Handle boss arena-specific events"""
        # Handle F9 key press for instant boss kill
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F9:
            if self._boss and not self._boss_defeated:
                print("F9 pressed - instantly defeating boss")
                self._boss.health = 0  # Set health to 0
                self.handle_boss_defeat()  # Trigger defeat sequence
                return True
        
        # Skip event handling if showing credits
        if self._show_credits:
            # Only handle specific keys for skipping credits
            if event.type == pygame.KEYDOWN and (event.key == pygame.K_SPACE or event.key == pygame.K_ESCAPE):
                # Return to main menu
                if hasattr(self, '_game_ref') and self._game_ref:
                    # Fade out music
                    pygame.mixer_music.fadeout(500)
                    # Set state to main menu
                    self._game_ref.state = "main_menu"
                    # Play menu music
                    try:
                        pygame.mixer_music.load(os.path.join("assets", "music", "theme.mp3"))
                        global CURRENT_TRACK
                        CURRENT_TRACK = 'menu'
                        pygame.mixer_music.play(-1)
                    except:
                        pass
                return True
            return True  # Consume all other events during credits
            
        # Skip event handling during intro sequence
        if self._intro_sequence_active and not self._boss_intro_played:
            return True  # Consume all events during intro
        
        # Handle game over screen events
        if self._show_game_over:
            return self._handle_game_over_events(event)
        
        # If not in game over, let parent handle events
        handled = super().handle_events(event)
        return handled
    
    def _check_boss_player_collision(self):
        """Check for direct collision between boss and player"""
        if not self._boss or not self._boss_active or not self._ball:
            return
        
        # First check for player squishing
        if self._boss.check_player_squish():
            # Kill the player if not already dead
            if hasattr(self._ball, 'death') and not self._ball.is_dead:
                print("Direct squish detection in update method!")
                self._ball.death()
                if self._boss._squish_sound:
                    self._boss._squish_sound.play()
        
        # Add direct collision check with player for better detection
        if self._boss._jumping and self._boss.body.velocity.y > 200:
            # Simple AABB collision check
            boss_rect = self._boss.rect
            player_rect = self._ball.rect
            
            if boss_rect.colliderect(player_rect):
                # Direct collision detection
                print("Direct collision detected between boss and player!")
                
                # Kill the player if not already dead
                if hasattr(self._ball, 'death') and not self._ball.is_dead:
                    print("Directly squishing player from collision check")
                    self._ball.death()
                    if self._boss._squish_sound:
                        self._boss._squish_sound.play()

    def _handle_game_over_events(self, event):
        """Handle events for the game over screen"""
        # Only process clicks when fully faded in
        if self._game_over_fade_alpha >= 200:
            if event.type == pygame.MOUSEMOTION:
                # Update button hover states
                mouse_pos = event.pos
                self._button_hover["retry"] = self._retry_button_rect.collidepoint(mouse_pos)
                self._button_hover["menu"] = self._menu_button_rect.collidepoint(mouse_pos)
            
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left click
                mouse_pos = event.pos
                
                # Check if retry button was clicked
                if self._retry_button_rect.collidepoint(mouse_pos):
                    print("Retry button clicked - resetting level")
                    self.reset_level()
                    return True
                
                # Check if menu button was clicked
                elif self._menu_button_rect.collidepoint(mouse_pos):
                    print("Menu button clicked - returning to main menu")
                    # Signal to the game to return to main menu
                    # Fade out music
                    pygame.mixer_music.fadeout(500)
                    # Set state to main menu
                    self._game_ref.state = "main_menu"
                    # Play menu music
                    try:
                        pygame.mixer_music.load(os.path.join("assets", "music", "theme.mp3"))
                        global CURRENT_TRACK
                        CURRENT_TRACK = 'menu'
                        pygame.mixer_music.play(-1)
                    except:
                        pass
                    return True
        
        # All events are consumed by game over screen when active
        return True

    # Add the additional property getters if they're not already in your code
    @property
    def boss(self):
        return self._boss

    @property
    def explosions(self):
        return self._explosions
    
    @property
    def rocket_launchers(self):
        return self._rocket_launchers
    
    @property
    def boss_defeated(self):
        return self._boss_defeated