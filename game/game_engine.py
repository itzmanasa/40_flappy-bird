import pygame
from .bird import Bird
from .pipe import Pipe
from .sound_manager import SoundManager


WHITE = (255, 255, 255)
GREEN = (0, 150, 0)


class GameEngine:
    DIFFICULTIES = {
        "Easy": {"speed": 3, "gap": 180},
        "Medium": {"speed": 4, "gap": 150},
        "Hard": {"speed": 6, "gap": 120},
    }

    DIFFICULTY_NAMES = ["Easy", "Medium", "Hard"]

    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.difficulty = "Medium"
        self.pipe_speed = self.DIFFICULTIES[self.difficulty]["speed"]
        self.pipe_gap = self.DIFFICULTIES[self.difficulty]["gap"]

        self.pipe_interval = 90
        self.score = 0
        self._spawn_timer = 0

        self.bird = Bird(width // 4, height // 2)

        self.pipes = [
            Pipe(
                width + 100,
                height,
                gap=self.pipe_gap,
                speed=self.pipe_speed,
            )
        ]

        self.font = pygame.font.SysFont("Arial", 30)
        self.game_over_font = pygame.font.SysFont(
            "Arial",
            64,
            bold=True,
        )
        self.final_score_font = pygame.font.SysFont(
            "Arial",
            36,
            bold=True,
        )
        self.menu_font = pygame.font.SysFont(
            "Arial",
            30,
            bold=True,
        )
        self.small_font = pygame.font.SysFont(
            "Arial",
            20,
        )

        self.game_over = False
        self.exit_requested = False
        self.selected_difficulty = 1

        # Load sounds once for the entire game session.
        self.sounds = SoundManager()

    def handle_event(self, event):
        # After Game Over, only replay-menu controls are accepted.
        if self.game_over:
            self._handle_game_over_event(event)
            return

        # Normal gameplay controls.
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self.bird.flap()
            self.sounds.play_flap()

        if event.type == pygame.MOUSEBUTTONDOWN:
            self.bird.flap()
            self.sounds.play_flap()

    def _handle_game_over_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        # Exit.
        if event.key == pygame.K_ESCAPE:
            self.exit_requested = True
            return

        # Move through difficulty options.
        if event.key == pygame.K_UP:
            self.selected_difficulty = (
                self.selected_difficulty - 1
            ) % len(self.DIFFICULTY_NAMES)
            return

        if event.key == pygame.K_DOWN:
            self.selected_difficulty = (
                self.selected_difficulty + 1
            ) % len(self.DIFFICULTY_NAMES)
            return

        # Start selected difficulty.
        if event.key == pygame.K_RETURN:
            self.reset_game(
                self.DIFFICULTY_NAMES[self.selected_difficulty]
            )
            return

        # Direct shortcuts.
        if event.key == pygame.K_1:
            self.reset_game("Easy")
        elif event.key == pygame.K_2:
            self.reset_game("Medium")
        elif event.key == pygame.K_3:
            self.reset_game("Hard")

    def handle_input(self):
        # Kept for compatibility with the existing project architecture.
        pass

    def reset_game(self, difficulty):
        """
        Completely reset gameplay and apply the selected difficulty.
        """
        if difficulty not in self.DIFFICULTIES:
            raise ValueError(f"Unknown difficulty: {difficulty}")

        settings = self.DIFFICULTIES[difficulty]

        self.difficulty = difficulty
        self.pipe_speed = settings["speed"]
        self.pipe_gap = settings["gap"]

        # Reset score and spawning.
        self.score = 0
        self._spawn_timer = 0

        # Reset bird position and velocity.
        self.bird = Bird(
            self.width // 4,
            self.height // 2,
        )

        # Remove all previous pipes and create a fresh one.
        self.pipes = [
            Pipe(
                self.width + 100,
                self.height,
                gap=self.pipe_gap,
                speed=self.pipe_speed,
            )
        ]

        # Return to normal gameplay.
        self.game_over = False
        self.exit_requested = False

        self.selected_difficulty = self.DIFFICULTY_NAMES.index(
            difficulty
        )

    def _set_game_over(self):
        """
        Enter Game Over exactly once and play the death sound exactly once.
        """
        if not self.game_over:
            self.game_over = True
            self.sounds.play_death()

    # ------------------------------------------------------------------
    # Task 1: Improved collision detection
    # ------------------------------------------------------------------

    @staticmethod
    def _circle_rect_collision(center, radius, rect):
        """
        Check whether the bird's circular body overlaps a pipe rectangle.
        """
        closest_x = max(
            rect.left,
            min(center[0], rect.right),
        )

        closest_y = max(
            rect.top,
            min(center[1], rect.bottom),
        )

        dx = center[0] - closest_x
        dy = center[1] - closest_y

        return dx * dx + dy * dy <= radius * radius

    @staticmethod
    def _segment_intersects_rect(start, end, rect):
        """
        Check whether a line segment intersects an axis-aligned rectangle.

        Used for continuous collision detection between frames.
        """
        x1, y1 = start
        x2, y2 = end

        dx = x2 - x1
        dy = y2 - y1

        t_min = 0.0
        t_max = 1.0

        for start_value, delta, lower, upper in (
            (x1, dx, rect.left, rect.right),
            (y1, dy, rect.top, rect.bottom),
        ):
            if delta == 0:
                if start_value < lower or start_value > upper:
                    return False
                continue

            t1 = (lower - start_value) / delta
            t2 = (upper - start_value) / delta

            if t1 > t2:
                t1, t2 = t2, t1

            t_min = max(t_min, t1)
            t_max = min(t_max, t2)

            if t_min > t_max:
                return False

        return True

    @staticmethod
    def _swept_circle_rect_collision(
        previous_bird_center,
        current_bird_center,
        previous_pipe_rect,
        current_pipe_rect,
        radius,
    ):
        """
        Detect collision occurring between two frames.
        """
        previous_relative = (
            previous_bird_center[0] - previous_pipe_rect.x,
            previous_bird_center[1],
        )

        current_relative = (
            current_bird_center[0] - current_pipe_rect.x,
            current_bird_center[1],
        )

        swept_rect = pygame.Rect(
            -radius,
            previous_pipe_rect.top - radius,
            previous_pipe_rect.width + 2 * radius,
            previous_pipe_rect.height + 2 * radius,
        )

        return GameEngine._segment_intersects_rect(
            previous_relative,
            current_relative,
            swept_rect,
        )

    def _pipe_collision(
        self,
        previous_bird_center,
        current_bird_center,
        previous_pipe_x,
        pipe,
    ):
        """
        Check collision against both top and bottom pipe sections.
        """
        for pipe_rect in (
            pipe.top_rect(),
            pipe.bottom_rect(),
        ):
            # Current-frame circle/rectangle collision.
            if self._circle_rect_collision(
                current_bird_center,
                self.bird.radius,
                pipe_rect,
            ):
                return True

            # Between-frame collision.
            previous_rect = pygame.Rect(
                previous_pipe_x,
                pipe_rect.top,
                pipe_rect.width,
                pipe_rect.height,
            )

            if self._swept_circle_rect_collision(
                previous_bird_center,
                current_bird_center,
                previous_rect,
                pipe_rect,
                self.bird.radius,
            ):
                return True

        return False

    # ------------------------------------------------------------------
    # Main game update
    # ------------------------------------------------------------------

    def update(self):
        # Task 2: freeze gameplay after Game Over.
        if self.game_over:
            return

        previous_bird_center = self.bird.center()

        # Gravity/flapping update.
        self.bird.update()

        current_bird_center = self.bird.center()

        # Ceiling and ground collision.
        if (
            self.bird.y - self.bird.radius <= 0
            or self.bird.y + self.bird.radius >= self.height
        ):
            self._set_game_over()
            return

        # Pipe spawning.
        self._spawn_timer += 1

        if self._spawn_timer >= self.pipe_interval:
            self._spawn_timer = 0

            self.pipes.append(
                Pipe(
                    self.width,
                    self.height,
                    gap=self.pipe_gap,
                    speed=self.pipe_speed,
                )
            )

        # Move pipes and check collisions/scoring.
        for pipe in self.pipes:
            previous_pipe_x = pipe.x

            pipe.move()

            # Task 1 collision detection.
            if self._pipe_collision(
                previous_bird_center,
                current_bird_center,
                previous_pipe_x,
                pipe,
            ):
                self._set_game_over()
                return

            # Scoring.
            if (
                not pipe.scored
                and pipe.x + pipe.width < self.bird.x
            ):
                pipe.scored = True
                self.score += 1

                # Task 4: scoring sound.
                self.sounds.play_score()

        # Remove pipes that have completely left the screen.
        self.pipes = [
            p
            for p in self.pipes
            if not p.off_screen()
        ]

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self, screen):
        # Pipes.
        for pipe in self.pipes:
            pygame.draw.rect(
                screen,
                GREEN,
                pipe.top_rect(),
            )

            pygame.draw.rect(
                screen,
                GREEN,
                pipe.bottom_rect(),
            )

        # Bird.
        pygame.draw.circle(
            screen,
            WHITE,
            (int(self.bird.x), int(self.bird.y)),
            self.bird.radius,
        )

        # Current score.
        score_text = self.font.render(
            f"Score: {self.score}",
            True,
            WHITE,
        )

        screen.blit(
            score_text,
            (10, 10),
        )

        # Task 2 + Task 3 game-over/replay screen.
        if self.game_over:
            self._render_game_over(screen)

    def _render_game_over(self, screen):
        overlay = pygame.Surface(
            (self.width, self.height),
            pygame.SRCALPHA,
        )

        overlay.fill(
            (0, 0, 0, 150)
        )

        screen.blit(
            overlay,
            (0, 0),
        )

        # GAME OVER.
        game_over_text = self.game_over_font.render(
            "GAME OVER",
            True,
            WHITE,
        )

        screen.blit(
            game_over_text,
            game_over_text.get_rect(
                center=(
                    self.width // 2,
                    110,
                )
            ),
        )

        # Final score.
        final_score_text = self.final_score_font.render(
            f"Final Score: {self.score}",
            True,
            WHITE,
        )

        screen.blit(
            final_score_text,
            final_score_text.get_rect(
                center=(
                    self.width // 2,
                    175,
                )
            ),
        )

        # Difficulty menu.
        menu_title = self.menu_font.render(
            "Choose Difficulty",
            True,
            WHITE,
        )

        screen.blit(
            menu_title,
            menu_title.get_rect(
                center=(
                    self.width // 2,
                    250,
                )
            ),
        )

        for index, difficulty in enumerate(
            self.DIFFICULTY_NAMES
        ):
            if index == self.selected_difficulty:
                option_text = self.menu_font.render(
                    f"> {difficulty} <",
                    True,
                    WHITE,
                )
            else:
                option_text = self.menu_font.render(
                    difficulty,
                    True,
                    WHITE,
                )

            screen.blit(
                option_text,
                option_text.get_rect(
                    center=(
                        self.width // 2,
                        310 + index * 50,
                    )
                ),
            )

        controls_text = self.small_font.render(
            "UP/DOWN: Select   ENTER: Play",
            True,
            WHITE,
        )

        shortcuts_text = self.small_font.render(
            "1: Easy   2: Medium   3: Hard   ESC: Exit",
            True,
            WHITE,
        )

        screen.blit(
            controls_text,
            controls_text.get_rect(
                center=(
                    self.width // 2,
                    490,
                )
            ),
        )

        screen.blit(
            shortcuts_text,
            shortcuts_text.get_rect(
                center=(
                    self.width // 2,
                    520,
                )
            )
        )