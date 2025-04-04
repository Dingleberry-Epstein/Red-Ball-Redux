import pygame, pygame_gui, os, random
from constants import *
from levels import PymunkLevel
from utils import PhysicsManager, SceneManager
from objects import levels

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

        # Load theme file for pygame_gui
        self.theme_path = os.path.join("assets", "theme.json")

        # Set up pygame_gui with theme
        self.ui_manager = pygame_gui.UIManager(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            self.theme_path
        )

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

        # Help menu variables
        self.help_menu_open = False
        self.help_menu_panel = None
        self.video_menu_panel = None

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
        """Set up menu buttons"""
        button_width = 200
        button_height = 70  # Made buttons a bit taller for pixelated style

        self.play_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((SCREEN_WIDTH // 2 - button_width // 2,
                                        SCREEN_HEIGHT // 2 - (button_height // 2) + 40),
                                        (button_width, button_height)),
            text='PLAY',
            manager=self.ui_manager
        )

        # Help and Settings Button
        self.help_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((SCREEN_WIDTH // 2 - button_width // 2,
                                        SCREEN_HEIGHT // 2 + 20 + 35),
                                        (button_width, button_height)),
            text='HELP & SETTINGS',
            manager=self.ui_manager
        )

        self.quit_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((SCREEN_WIDTH // 2 - button_width // 2,
                                        SCREEN_HEIGHT // 2 + button_height + 20 + 70),  # Added more space between buttons
                                        (button_width, button_height)),
            text='QUIT',
            manager=self.ui_manager
        )

        # Initially hide buttons for start screen
        self.play_button.hide()
        self.quit_button.hide()

    def handle_intro_sequence(self, events):
        """Handle the intro logo sequence"""
        if self.state == 'intro':
            def render_logo():
                self.screen.fill((255, 255, 255))  # White background
                logo_rect = self.logo_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))

            if SceneManager.fade_in(self.screen, render_logo, self.logo_image, self.fade_duration, (255, 255, 255)):
                pygame.time.delay(1000)  # show the logo for one second.
                if SceneManager.fade_out(self.screen, render_logo, self.logo_image, self.fade_duration, (255, 255, 255)):
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
                    self.play_button.show()
                    self.quit_button.show()
                    self.help_button.show()

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
                            self.state = "main_menu"
                            SceneManager.fade_from_black(self.screen, render_main_menu, self.fade_duration)
                        else:
                            self.running = False
                    elif event.key == pygame.K_RETURN and self.state == "main_menu":
                        def render_game():
                            self.update(dt)
                            self.render()
                        def render_main_menu():
                            self.update_background()
                            self.render_main_menu_content()
                        SceneManager.fade_to_black(self.screen, render_main_menu, self.fade_duration)
                        self.setup_game()
                        self.state = "game"
                        SceneManager.fade_from_black(self.screen, render_game, self.fade_duration)
                    elif event.key == pygame.K_r and self.state == "game":
                        self.setup_game()

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

    def setup_game(self):
        """Set up physics and level with impulse-based ball"""
        # Create minimal physics manager
        self.physics = PhysicsManager()

        # Create level with impulse-based ball
        self.level = PymunkLevel(tmx_map=levels[0])

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

                SceneManager.fade_to_black(self.screen, render_game, self.fade_duration)
                self.state = "main_menu"
                SceneManager.fade_from_black(self.screen, render_main_menu, self.fade_duration)

                # Reset completion flags
                self.show_level_complete = False
                self.level_complete_timer = 0
                self.level.level_complete = False
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
            self.play_button.show()
            self.quit_button.show()
            self.help_button.show()

            # Create a surface with alpha for fading effect
            ui_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            self.ui_manager.draw_ui(ui_surface)

            # Apply alpha to the entire surface
            ui_surface.set_alpha(self.button_alpha)

            # Draw alpha-adjusted surface
            self.screen.blit(ui_surface, (0, 0))

            # Hide buttons again until transition is complete
            self.play_button.hide()
            self.quit_button.hide()
            self.help_button.hide()

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
        """Handles menu events"""
        if event.type == pygame.USEREVENT:
            if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.play_button:
                    # ... (your play button logic)
                    def render_game():
                        self.update(dt)
                        self.render()
                    def render_main_menu():
                        self.update_background()
                        self.render_main_menu_content()

                    SceneManager.fade_to_black(self.screen, render_main_menu, self.fade_duration)
                    self.setup_game()
                    self.state = "game"
                    SceneManager.fade_from_black(self.screen, render_game, self.fade_duration)
                elif event.ui_element == self.quit_button:
                    self.running = False
                elif event.ui_element == self.help_button:
                    self.open_help_menu()
                elif self.help_menu_open:
                    self.handle_help_menu_events(event)
            elif event.user_type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
                if event.ui_element == self.resolution_dropdown:
                    self.change_resolution(event.text)

    def open_help_menu(self):
        """Opens the help menu panel"""
        self.help_menu_panel = pygame_gui.elements.UIWindow(
            rect=pygame.Rect((SCREEN_WIDTH // 4, SCREEN_HEIGHT // 4), (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)),
            manager=self.ui_manager,
            window_display_title="Help and Settings"
        )
        button_width = 150
        button_height = 50

        self.how_to_play_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((10, 50), (button_width, button_height)),
            text='How to Play',
            manager=self.ui_manager,
            container=self.help_menu_panel
        )
        self.video_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((10, 110), (button_width, button_height)),
            text='Video',
            manager=self.ui_manager,
            container=self.help_menu_panel
        )
        self.controls_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((10, 170), (button_width, button_height)),
            text='Controls',
            manager=self.ui_manager,
            container=self.help_menu_panel
        )
        self.credits_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((10, 230), (button_width, button_height)),
            text='Credits',
            manager=self.ui_manager,
            container=self.help_menu_panel
        )
        self.help_menu_open = True

    def handle_help_menu_events(self, event):
        """Handles events within the help menu"""
        if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.video_button:
                self.open_video_menu()

    def open_video_menu(self):
        """Opens the video settings panel"""
        self.video_menu_panel = pygame_gui.elements.UIWindow(
            rect=pygame.Rect((SCREEN_WIDTH // 4, SCREEN_HEIGHT // 4), (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)),
            manager=self.ui_manager,
            window_display_title="Video Settings"
        )
        resolution_options = [f"{w}x{h}" for w, h in self.resolutions]
        self.resolution_dropdown = pygame_gui.elements.UIDropDownMenu(
            options_list=resolution_options,
            starting_option=f"{self.current_resolution[0]}x{self.current_resolution[1]}",
            relative_rect=pygame.Rect((10, 50), (200, 40)),
            manager=self.ui_manager,
            container=self.video_menu_panel
        )

        self.fullscreen_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((10, 100), (200, 40)),
            text='Fullscreen',
            manager=self.ui_manager,
            container=self.video_menu_panel
        )
        self.borderless_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((10, 150), (200, 40)),
            text='Borderless',
            manager=self.ui_manager,
            container=self.video_menu_panel
        )
        self.windowed_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((10, 200), (200, 40)),
            text='Windowed',
            manager=self.ui_manager,
            container=self.video_menu_panel
        )

    def change_resolution(self, resolution_str):
        """Changes the game resolution"""
        width, height = map(int, resolution_str.split('x'))
        self.current_resolution = (width, height)
        pygame.display.set_mode((width, height), self.fullscreen_mode)
        self.ui_manager.set_window_resolution((width, height))
        global SCREEN_WIDTH, SCREEN_HEIGHT
        SCREEN_WIDTH, SCREEN_HEIGHT = width, height
        self.setup_reactive_background()
        self.setup_menu()

if __name__ == "__main__":
    Game().run()