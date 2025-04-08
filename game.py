import pygame, pygame_gui, os, random
from constants import *
from levels import SpaceLevel, CaveLevel, PymunkLevel, levels, spawn_points
from utils import PhysicsManager, SceneManager

class Game:
    """Main game using impulse-based ball movement"""
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        pygame.mixer_music.load(os.path.join("assets", "music", "theme.mp3"))
        pygame.mixer_music.set_volume(0.75)  # Set volume to 75%

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = "intro"  # Start with intro state

        # Set up physics and level
        self.physics = None
        self.level = None
        self.current_level_index = 0  # To track the current level

        # Load theme file for pygame_gui
        self.theme_path = os.path.join("assets", "theme.json")

        # Set up pygame_gui with theme
        self.ui_manager = pygame_gui.UIManager(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            self.theme_path
        )

        # Add audio control state variables
        self.music_muted = False
        self.sound_muted = False
        self.previous_music_volume = 0.75  # Default value (75%)
        self.previous_sound_volume = 1.0   # Default value (100%)

        # Load menu background
        self.setup_reactive_background()

        # Set up menu buttons
        self.setup_menu()

        # Add variables for flashing text
        self.flash_timer = 0
        self.flash_rate = 0.5  # Flash every 0.5 seconds
        self.show_flash_text = True

        # Add transition variables
        self.is_transitioning = False
        self.transition_phase = 0  # 0=not transitioning, 1=flashing, 2=moving
        self.transition_timer = 0
        self.flash_duration = 1.5  # 1.5 seconds for rapid flashing
        self.move_duration = 0.3  # 0.3 seconds for quick movement
        self.title_y_pos = 0
        self.title_target_y = 0
        self.button_alpha = 0

        # Variables for level complete handling
        self.show_level_complete = False
        self.level_complete_timer = 0
        self.level_complete_delay = 1.0  # 1 second delay to show completion message

        # Try to load a pixelated font
        try:
            self.pixel_font = pygame.font.Font(os.path.join("assets", "Daydream.ttf"), 32)
        except pygame.error as e:
            print(f"Error loading font: {e}")
            # Fallback to default font
            self.pixel_font = pygame.font.SysFont(None, 36)

        self.fade_duration = 1.0  # 1 second for fades

        # load logo
        self.logo_image = pygame.image.load(os.path.join("assets", "migglesoft.png")).convert_alpha()

        # Load title once to reuse
        self.title_text = pygame.image.load(os.path.join("assets", "title.png")).convert_alpha()

        pygame.display.set_caption("Red Ball: REDUX!")

        # Resolution settings
        self.resolutions = [(640, 480), (800, 600), (1280, 720), (1920, 1080)]
        self.current_resolution = (SCREEN_WIDTH, SCREEN_HEIGHT)
        self.fullscreen_mode = pygame.SHOWN

        # Level select variables
        self.level_select_open = False
        self.level_music_faded = False # Added this line
        
        # Store level buttons for reference
        self.level_buttons = []

    def toggle_music(self):
        """Toggle music on/off"""
        if self.music_muted:
            # Unmute - restore previous volume
            pygame.mixer_music.set_volume(self.previous_music_volume)
            print(f"Music unmuted - volume set to {self.previous_music_volume * 100}%")
        else:
            # Mute - store current volume and set to 0
            self.previous_music_volume = pygame.mixer_music.get_volume()
            pygame.mixer_music.set_volume(0)
            print("Music muted")
        
        # Toggle the state
        self.music_muted = not self.music_muted

    def toggle_sound_effects(self):
        """Toggle sound effects on/off"""
        # Note: This is a placeholder for your actual sound effect system
        # Implement based on how you handle sound effects in your game
        
        if self.sound_muted:
            # Unmute sound effects
            print("Sound effects unmuted")
            # Example implementation if you have sound channels:
            # for channel in range(1, pygame.mixer.get_num_channels()):
            #     pygame.mixer.Channel(channel).set_volume(self.previous_sound_volume)
        else:
            # Mute sound effects
            print("Sound effects muted")
            # Example implementation if you have sound channels:
            # self.previous_sound_volume = pygame.mixer.Channel(1).get_volume()
            # for channel in range(1, pygame.mixer.get_num_channels()):
            #     pygame.mixer.Channel(channel).set_volume(0)
        
        # Toggle the state
        self.sound_muted = not self.sound_muted

    def setup_reactive_background(self):
        """Load three background layers for a parallax effect based on mouse movement"""
        # Define paths for the three background layers
        bg_paths = [
            os.path.join("assets", "backgrounds", "cloud", "1.png"),  # Far background
            os.path.join("assets", "backgrounds", "cloud", "3.png"),  # Middle ground
            os.path.join("assets", "backgrounds", "cloud", "2.png"),  # Foreground
        ]

        # Define speed factors for each layer (higher value = more movement)
        speed_factors = [0.9, 1.5, 2]  # Background moves slower, foreground faster

        # Initialize list to store layer information
        self.bg_layers = []

        # Try to load each layer
        for i, path in enumerate(bg_paths):
            try:
                # Load the image
                print(f"Loading background layer: {path}")
                image = pygame.image.load(path).convert_alpha()

                # Scale slightly larger to allow movement without showing edges
                scaled_width = int(SCREEN_WIDTH * 1.1)
                scaled_height = int(SCREEN_HEIGHT * 1.1)
                scaled_image = pygame.transform.scale(image, (scaled_width, scaled_height))

                # Store layer information: image, center position, and speed factor
                center_x = (scaled_width - SCREEN_WIDTH) / 2
                center_y = (scaled_height - SCREEN_HEIGHT) / 2

                self.bg_layers.append({
                    'image': scaled_image,
                    'center_x': center_x,
                    'center_y': center_y,
                    'pos_x': 0,
                    'pos_y': 0,
                    'factor': speed_factors[i]
                })

            except Exception as e:
                print(f"Error loading background layer {path}: {e}")
                # Create a simple colored background as fallback
                color = (20, 30, 50)  # Dark blue
                if i == 1:
                    color = (30, 40, 60)  # Slightly lighter blue for middle
                elif i == 2:
                    color = (40, 50, 70)  # Even lighter for foreground

                surface = pygame.Surface((int(SCREEN_WIDTH * 1.1), int(SCREEN_HEIGHT * 1.1)))
                surface.fill(color)

                # Add some simple stars for the farthest background
                if i == 0:
                    for _ in range(200):
                        x = random.randint(0, surface.get_width() - 1)
                        y = random.randint(0, surface.get_height() - 1)
                        size = random.randint(1, 3)
                        pygame.draw.circle(surface, (255, 255, 255), (x, y), size)

                center_x = (surface.get_width() - SCREEN_WIDTH) / 2
                center_y = (surface.get_height() - SCREEN_HEIGHT) / 2

                self.bg_layers.append({
                    'image': surface,
                    'center_x': center_x,
                    'center_y': center_y,
                    'pos_x': 0,
                    'pos_y': 0,
                    'factor': speed_factors[i]
                })

        # Maximum amount the backgrounds can move in each direction
        self.bg_move_amount = 20

    def setup_menu(self):
        """Set up menu buttons using theme-defined images"""
        # Standard button size - make sure your images match this
        button_size = (64, 64)
        
        # Create a dictionary to store button definitions
        # Each definition contains: name, size, position and (optional) visible state
        button_definitions = [
            {
                "name": "play", 
                "size": button_size, 
                "position": (SCREEN_WIDTH // 2 - button_size[0] // 2, SCREEN_HEIGHT // 2),
                "visible_in_main_menu": True
            },
            {
                "name": "settings", 
                "size": button_size, 
                "position": ((SCREEN_WIDTH // 2) - 120, SCREEN_HEIGHT // 2),
                "visible_in_main_menu": True
            },
            {
                "name": "exit", 
                "size": button_size, 
                "position": ((SCREEN_WIDTH // 2) + 80, SCREEN_HEIGHT // 2),
                "visible_in_main_menu": True
            },
            
            # Settings menu buttons - positioned in a row at bottom of screen
            {
                "name": "audio", 
                "size": button_size, 
                "position": (SCREEN_WIDTH // 2 - button_size[0] * 1.5, SCREEN_HEIGHT - button_size[1] - 20),
                "visible_in_main_menu": False
            },
            {
                "name": "music", 
                "size": button_size, 
                "position": (SCREEN_WIDTH // 2, SCREEN_HEIGHT - button_size[1] - 20),
                "visible_in_main_menu": False
            },
            {
                "name": "mute_audio", 
                "size": button_size, 
                "position": (SCREEN_WIDTH // 2 + button_size[0] * 1.5, SCREEN_HEIGHT - button_size[1] - 20),
                "visible_in_main_menu": False
            },
            
            # Game control buttons
            {
                "name": "respawn", 
                "size": button_size, 
                "position": (20, 20),
                "visible_in_main_menu": False
            },
            {
                "name": "pause", 
                "size": button_size, 
                "position": (SCREEN_WIDTH - button_size[0] - 20, 20),
                "visible_in_main_menu": False
            },
            
            # Navigation buttons
            {
                "name": "return", 
                "size": button_size, 
                "position": (20, SCREEN_HEIGHT - button_size[1] - 20),
                "visible_in_main_menu": False
            },
            {
                "name": "accept", 
                "size": button_size, 
                "position": (SCREEN_WIDTH // 2 - button_size[0] - 10, SCREEN_HEIGHT - button_size[1] - 20),
                "visible_in_main_menu": False
            },
            {
                "name": "cancel", 
                "size": button_size, 
                "position": (SCREEN_WIDTH // 2 + 10, SCREEN_HEIGHT - button_size[1] - 20),
                "visible_in_main_menu": False
            }
        ]
        
        # Create a dictionary to store button references
        self.buttons = {}
        
        # Check for assets directory
        if not os.path.exists("assets/sprites/buttons/unpressed"):
            print("WARNING: Button images directory not found!")
            print(f"Expected path: {os.path.abspath('assets/sprites/buttons/unpressed')}")
        
        # Create each button with its appropriate object_id
        for button_def in button_definitions:
            name = button_def["name"]
            size = button_def["size"]
            position = button_def["position"]
            
            # Check if the button images exist (for debugging)
            unpressed_path = os.path.join("assets", "sprites", "buttons", "unpressed", f"{name}.png")
            pressed_path = os.path.join("assets", "sprites", "buttons", "pressed", f"P{name}.png")
            
            exists_unpressed = os.path.exists(unpressed_path)
            exists_pressed = os.path.exists(pressed_path)
            
            print(f"Button '{name}':")
            print(f"  - Unpressed: {unpressed_path} (exists: {exists_unpressed})")
            print(f"  - Pressed: {pressed_path} (exists: {exists_pressed})")
            
            if not exists_unpressed or not exists_pressed:
                print(f"  ⚠️ WARNING: Image(s) missing for button '{name}'!")
            
            # Create the button with object_id that matches our theme.json
            self.buttons[name] = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(position, size),
                text="",  # No text, using images instead
                manager=self.ui_manager,
                object_id=f"#{name}_button"  # This is the key - must match theme.json
            )
            
            # Initially hide all buttons
            self.buttons[name].hide()
        
        # Show only the main menu buttons initially
        for button_def in button_definitions:
            if button_def.get("visible_in_main_menu", False):
                self.buttons[button_def["name"]].show()

    def handle_intro_sequence(self, events):
        """Handle the intro logo sequence"""
        if self.state == 'intro':
            def render_logo():
                self.screen.fill((0, 0, 0)) # Fill with black first

            if SceneManager.fade_in(self.screen, render_logo, self.logo_image, self.fade_duration, (0, 0, 0)):
                pygame.time.delay(1000)  # show the logo for one second.
                if SceneManager.fade_out(self.screen, render_logo, self.logo_image, self.fade_duration, (0, 0, 0)):
                    self.state = 'start_screen'  # Go to start screen instead of main menu

                    # Initialize title position for start screen (center)
                    self.title_y_pos = SCREEN_HEIGHT // 2 - self.title_text.get_height() // 2
                    # Set target position for when we transition (top quarter)
                    self.title_target_y = SCREEN_HEIGHT // 4 - self.title_text.get_height() // 2

                    # Start playing the music in a loop
                    pygame.mixer_music.play(-1)  # -1 means loop indefinitely

                    def render_start_screen():
                        self.update_background()
                        self.render_start_screen()
                    SceneManager.fade_from_black(self.screen, render_start_screen, self.fade_duration)

    def handle_start_screen(self, events, dt):
        """Handle the start screen with flashing text"""
        if not self.is_transitioning:
            # Normal flashing for "press anything to start"
            self.flash_timer += dt
            if self.flash_timer >= self.flash_rate:
                self.flash_timer = 0
                self.show_flash_text = not self.show_flash_text

            # Check for any input to start transition
            for event in events:
                if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    self.is_transitioning = True
                    self.transition_phase = 1  # Start with flashing phase
                    self.transition_timer = 0
                    self.flash_rate = 0.08  # Faster flashing during transition
                    self.button_alpha = 0
        else:
            # Transition handling
            self.transition_timer += dt

            # Flash text rapidly during transition phase 1
            self.flash_timer += dt
            if self.flash_timer >= self.flash_rate:
                self.flash_timer = 0
                self.show_flash_text = not self.show_flash_text

            # Phase 1: Just flash the text rapidly
            if self.transition_phase == 1:
                if self.transition_timer >= self.flash_duration:
                    # Move to phase 2 once flashing is complete
                    self.transition_phase = 2
                    self.transition_timer = 0
                    self.show_flash_text = False  # Hide the text during movement

            # Phase 2: Move the title up quickly and fade in buttons
            elif self.transition_phase == 2:
                if self.transition_timer <= self.move_duration:
                    # Calculate progress (0 to 1)
                    progress = min(self.transition_timer / self.move_duration, 1.0)

                    # Move title up quickly
                    start_y = SCREEN_HEIGHT // 2 - self.title_text.get_height() // 2
                    end_y = SCREEN_HEIGHT // 4 - self.title_text.get_height() // 2
                    self.title_y_pos = start_y + (end_y - start_y) * progress

                    # Fade in buttons
                    self.button_alpha = int(progress * 255)  # 0 to 255
                else:
                    # Transition complete
                    self.is_transitioning = False
                    self.transition_phase = 0
                    self.state = "main_menu"
                    self.title_y_pos = SCREEN_HEIGHT // 4 - self.title_text.get_height() // 2

                    # Show buttons for main menu
                    self.buttons['play'].show()
                    self.buttons['settings'].show()
                    self.buttons['exit'].show()

    def render_outlined_text(self, text, color, outline_color, position):
        """Render text with an outline effect"""
        # Render the outline by drawing the text multiple times with offsets
        outline_offsets = [(-2, -2), (-2, 0), (-2, 2), (0, -2), (0, 2), (2, -2), (2, 0), (2, 2)]

        # First render outline
        for offset in outline_offsets:
            offset_position = (position[0] + offset[0], position[1] + offset[1])
            outline_surface = self.pixel_font.render(text, True, outline_color)
            self.screen.blit(outline_surface, offset_position)

        # Then render the text on top
        text_surface = self.pixel_font.render(text, True, color)
        self.screen.blit(text_surface, position)

        return text_surface.get_rect(topleft=position)

    def run(self):
        """Main game loop"""
        while self.running:
            # Calculate delta time for smooth physics
            global dt
            dt = self.clock.tick(60) / 1000.0  # Convert to seconds

            # Get events
            events = pygame.event.get()
            for event in events:
                # Handle quit
                if event.type == pygame.QUIT:
                    self.running = False

                # If in main menu, handle UI events
                if self.state == "main_menu":
                    # Handle UI events
                    self.ui_manager.process_events(event)
                    self.handle_menu_events(event)

                # Handle keyboard input
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state == "game":
                            def render_game():
                                self.update(dt)
                                self.render()
                            def render_main_menu():
                                self.update_background()
                                self.render_main_menu_content()

                            SceneManager.fade_to_black(self.screen, render_game, self.fade_duration)
                            pygame.mixer_music.fadeout(500)
                            self.state = "main_menu"
                            pygame.mixer_music.load(os.path.join("assets", "music", "theme.mp3"))
                            pygame.mixer_music.play(-1)  # Restart music
                            SceneManager.fade_from_black(self.screen, render_main_menu, self.fade_duration)
                            self.level_music_faded = False #reset fade flag.
                        else:
                            self.update_background()
                            self.render_main_menu_content()
                            pygame.mixer_music.fadeout(900)
                            SceneManager.fade_to_black(self.screen, render_main_menu, self.fade_duration)
                            self.running = False
                    elif event.key == pygame.K_r and self.state == "game":
                        self.level.reset_ball()

                # Pass events to level if in game state - just handle events, don't check for completion here
                if self.level and self.state == "game" and not self.show_level_complete:
                    self.level.handle_events(event)

            # Update and render based on state
            if self.state == "intro":
                self.handle_intro_sequence(events)
            elif self.state == "start_screen":
                self.update_background()  # Keep parallax working
                self.handle_start_screen(events, dt)
                self.render_start_screen()
            elif self.state == "main_menu":
                # Update UI manager
                self.ui_manager.update(dt)
                self.update_background()
                self.render_main_menu()
            elif self.state == "game":
                self.update(dt)
                self.render()

            pygame.display.flip()

    def update_background(self):
        """Update background position of all layers based on mouse movement"""
        # Get mouse position
        mouse_x, mouse_y = pygame.mouse.get_pos()

        # Calculate relative position from -1 to 1
        # When mouse is in center, these values are 0
        # When mouse is at edge, these values approach -1 or 1
        relative_x = (mouse_x / SCREEN_WIDTH) * 2 - 1
        relative_y = (mouse_y / SCREEN_HEIGHT) * 2 - 1

        # Update each layer with its own movement speed
        for layer in self.bg_layers:
            # Calculate new background position
            # Move opposite to mouse position for parallax effect
            # Multiple by move amount and layer factor to control sensitivity
            layer['pos_x'] = layer['center_x'] - (relative_x * self.bg_move_amount * layer['factor'])
            layer['pos_y'] = layer['center_y'] - (relative_y * self.bg_move_amount * layer['factor'])

    def setup_game(self, level_index=0):
        """Set up physics and level with impulse-based ball"""
        # Create minimal physics manager
        self.physics = PhysicsManager()

        # Check if the level index is 3 or 4
        if level_index in [2, 3]:
            # Use CaveLevel if it is level 3 or 4
            self.level = CaveLevel(tmx_map=levels[level_index], spawn=spawn_points[level_index])
        elif level_index == 4:
            # Use SpaceLevel for level 5
            self.level = SpaceLevel(tmx_map=levels[level_index], spawn=spawn_points[level_index])
        else:
            # Use PymunkLevel for all other levels
            self.level = PymunkLevel(tmx_map=levels[level_index], spawn=spawn_points[level_index])

        self.current_level_index = level_index  # Store current index.

        # Reset level completion flags
        self.show_level_complete = False
        self.level_complete_timer = 0

    def update(self, dt):
        """Update physics simulation and handle level completion"""
        if not self.level:
            return

        # If level is complete, handle the transition
        if self.show_level_complete:
            self.level_complete_timer += dt
            if self.level_complete_timer >= self.level_complete_delay:
                # Transition back to main menu after the delay
                def render_game():
                    self.render()
                def render_main_menu():
                    self.update_background()
                    self.render_main_menu_content()

                pygame.mixer_music.fadeout(500)
                SceneManager.fade_to_black(self.screen, render_game, self.fade_duration)
                self.state = "main_menu"
                pygame.mixer_music.load(os.path.join("assets", "music", "theme.mp3"))
                pygame.mixer_music.play(-1)  # Restart music
                SceneManager.fade_from_black(self.screen, render_main_menu, self.fade_duration)

                # Reset completion flags
                self.show_level_complete = False
                self.level_complete_timer = 0
                self.level.level_complete = False
                self.level_music_faded = False # Reset fade flag.
        else:
            # Normal level update
            self.level.update(dt)

            # Check for level completion after updating
            if self.level.level_complete:
                self.show_level_complete = True
                self.level_complete_timer = 0

    def render(self):
        """Render simulation to screen"""
        self.screen.fill("BLACK")

        if self.level:
            self.level.draw(self.screen)

            # Draw "Level Complete" message if needed
            if self.show_level_complete:
                # Create a semi-transparent overlay
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 128))  # Semi-transparent black
                self.screen.blit(overlay, (0, 0))

                # Draw completion message
                completion_text = "Level Complete!"
                text_surface = self.pixel_font.render(completion_text, True, (255, 255, 255))
                text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                self.screen.blit(text_surface, text_rect)

        # FPS Display
        fps_counter = self.clock.get_fps()
        fps_display = pygame.font.SysFont(None, 24).render(f"FPS: {int(fps_counter)}", True, (255, 255, 255))
        self.screen.blit(fps_display, (SCREEN_WIDTH - 100, 10))

    def render_start_screen(self):
        """Render the start screen with centered title and flashing text"""
        # Draw background layers with parallax effect (from back to front)
        self.screen.fill((0, 0, 0))  # Fill with black first

        for layer in self.bg_layers:
            self.screen.blit(layer['image'], (-layer['pos_x'], -layer['pos_y']))

        # Draw title text at current position (will be animated during transition)
        title_x = SCREEN_WIDTH // 2 - self.title_text.get_width() // 2
        self.screen.blit(self.title_text, (title_x, self.title_y_pos))

        # Draw flashing "Press anything to start" text with outline
        if self.show_flash_text and (not self.is_transitioning or self.transition_phase == 1):
            text = "Press anything to start!"
            # Calculate position to center the text
            text_width = self.pixel_font.size(text)[0]
            text_x = SCREEN_WIDTH // 2 - text_width // 2
            text_y = self.title_y_pos + self.title_text.get_height() + 30

            # Render with outline
            self.render_outlined_text(text, (255, 255, 255), (0, 0, 0), (text_x, text_y))

        # If in movement phase, draw buttons with fade-in effect
        if self.is_transitioning and self.transition_phase == 2 and self.button_alpha > 0:
            # Need to temporarily make buttons visible to draw them
            self.buttons['play'].show()
            self.buttons['settings'].show()
            self.buttons['exit'].show()

            # Create a surface with alpha for fading effect
            ui_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            self.ui_manager.draw_ui(ui_surface)

            # Apply alpha to the entire surface
            ui_surface.set_alpha(self.button_alpha)

            # Draw alpha-adjusted surface
            self.screen.blit(ui_surface, (0, 0))

            # Hide buttons again until transition is complete
            self.buttons['play'].hide()
            self.buttons['settings'].hide()
            self.buttons['exit'].hide()
            

    def render_main_menu(self):
        """Render main menu screen"""
        # Draw background layers with parallax effect (from back to front)
        self.screen.fill((0, 0, 0))  # Fill with black first

        for layer in self.bg_layers:
            self.screen.blit(layer['image'], (-layer['pos_x'], -layer['pos_y']))

        # Draw title text
        title_x = SCREEN_WIDTH // 2 - self.title_text.get_width() // 2
        self.screen.blit(self.title_text, (title_x, SCREEN_HEIGHT // 4 - self.title_text.get_height() // 2))

        # Draw UI elements
        self.ui_manager.draw_ui(self.screen)

    def render_main_menu_content(self):
        """Renders the main menu content, used for fade operations"""
        self.update_background()
        self.render_main_menu()

    def handle_menu_events(self, event):
        """Handles menu events with improved button handling"""
        if event.type == pygame.USEREVENT:
            if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                # Main menu buttons
                if event.ui_element == self.buttons['play']:
                    self.open_level_select()
                elif event.ui_element == self.buttons['settings']:
                    self.open_settings_menu()
                elif event.ui_element == self.buttons['exit']:
                    def render_main_menu():
                        self.update_background()
                        self.render_main_menu_content()
                    pygame.mixer_music.fadeout(900)
                    SceneManager.fade_to_black(self.screen, render_main_menu, self.fade_duration)
                    self.running = False
                
                # Return button (used in submenus)
                elif event.ui_element == self.buttons['return']:
                    if self.level_select_open:
                        self.close_level_select()
                    else:
                        # Return to main menu from settings or other screens
                        # Hide all buttons first
                        for name in self.buttons:
                            self.buttons[name].hide()
                        
                        # Show only main menu buttons
                        self.buttons['play'].show()
                        self.buttons['settings'].show()
                        self.buttons['exit'].show()
                
                # Audio control buttons
                elif event.ui_element == self.buttons['music']:
                    # Toggle music volume
                    self.toggle_music()
                    print("Music button pressed - toggled music")
                
                elif event.ui_element == self.buttons['audio'] or event.ui_element == self.buttons['mute_audio']:
                    # Toggle sound effects volume
                    self.toggle_sound_effects()
                    print("Audio/mute button pressed - toggled sound effects")
                
                # Handle level select events
                elif self.level_select_open:
                    # Check if the button is one of our level buttons
                    for i, button in enumerate(self.level_buttons):
                        if event.ui_element == button:
                            self.start_level(i)
                            break

    def open_level_select(self):
        """Opens the level select menu with properly styled buttons"""
        # Hide main menu buttons
        self.buttons['play'].hide()
        self.buttons['settings'].hide()
        self.buttons['exit'].hide()
        
        # Show return button
        self.buttons['return'].show()
        
        # Create level selection buttons
        button_width = 200
        button_height = 70
        
        # Clear any existing level buttons
        for button in self.level_buttons:
            if button.alive():
                button.kill()
        self.level_buttons = []
        
        for i in range(len(levels)):  # Use the number of levels you have
            level_button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    (SCREEN_WIDTH // 2 - button_width // 2, 
                    SCREEN_HEIGHT // 2 - 150 + (i * (button_height + 20))),
                    (button_width, button_height)
                ),
                text=f'Level {i + 1}',
                manager=self.ui_manager
            )
            self.level_buttons.append(level_button)
        
        self.level_select_open = True

    def close_level_select(self):
        """Closes the level select menu and returns to main menu"""
        # Remove level buttons
        for button in self.level_buttons:
            if button.alive():
                button.kill()
        self.level_buttons = []
        
        # Hide return button
        self.buttons['return'].hide()
        
        # Show main menu buttons
        self.buttons['play'].show()
        self.buttons['settings'].show()
        self.buttons['exit'].show()
        
        self.level_select_open = False

    def start_level(self, level_index):
        """Start the specified level with proper transitions"""
        def render_game():
            self.update(dt)
            self.render()
        def render_main_menu():
            self.update_background()
            self.render_main_menu_content()

        if not self.level_music_faded:
            pygame.mixer_music.fadeout(500)
            self.level_music_faded = True

        SceneManager.fade_to_black(self.screen, render_main_menu, self.fade_duration)
        self.setup_game(level_index)
        self.state = "game"
        SceneManager.fade_from_black(self.screen, render_game, self.fade_duration)
        self.close_level_select()

    def open_settings_menu(self):
        """Opens the settings menu"""
        # Hide main menu buttons
        self.buttons['play'].hide()
        self.buttons['settings'].hide()
        self.buttons['exit'].hide()
        
        # Show settings-related buttons
        self.buttons['audio'].show()
        self.buttons['music'].show()
        if 'mute_audio' in self.buttons:
            self.buttons['mute_audio'].show()
        self.buttons['return'].show()
        
        # Add custom implementation for settings menu
        # This could include resolution options, fullscreen toggle, etc.
        print("Settings menu opened")

if __name__ == "__main__":
    Game().run()