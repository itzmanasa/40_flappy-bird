from pathlib import Path
import pygame


class SoundManager:
    """Loads and plays the game's optional sound effects."""

    def __init__(self):
        self.enabled = False
        self.flap_sound = None
        self.score_sound = None
        self.death_sound = None

        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()

            sound_dir = (
                Path(__file__).resolve().parent.parent
                / "assets"
                / "sounds"
            )

            self.flap_sound = self._load(sound_dir / "flap.wav")
            self.score_sound = self._load(sound_dir / "score.wav")
            self.death_sound = self._load(sound_dir / "death.wav")

            self.enabled = any(
                sound is not None
                for sound in (
                    self.flap_sound,
                    self.score_sound,
                    self.death_sound,
                )
            )
        except pygame.error as exc:
            print(f"Warning: sound disabled: {exc}")

    @staticmethod
    def _load(path):
        try:
            return pygame.mixer.Sound(str(path))
        except (pygame.error, FileNotFoundError) as exc:
            print(f"Warning: could not load sound '{path}': {exc}")
            return None

    @staticmethod
    def _play(sound):
        if sound is not None:
            try:
                sound.play()
            except pygame.error:
                pass

    def play_flap(self):
        self._play(self.flap_sound)

    def play_score(self):
        self._play(self.score_sound)

    def play_death(self):
        self._play(self.death_sound)