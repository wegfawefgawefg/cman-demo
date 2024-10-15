import pygame
import glm
import os
import math
from pygame.locals import *

# Initialize Pygame
pygame.init()

# Constants
RENDER_RESOLUTION = glm.vec2(240, 160) * 2
WINDOW_SCALE = 2
WINDOW_SIZE = RENDER_RESOLUTION * WINDOW_SCALE
FPS = 60
STEP_INTERVAL = 0.3  # Seconds between steps
TILT_MAX_ANGLE = 5  # Degrees
TILT_SPEED = 60  # Degrees per second

# Directions in order: right, down right, down, down left, left, up left, up, up right
DIRECTIONS = [
    glm.vec2(1, 0),  # Right
    glm.vec2(1, 1),  # Down Right
    glm.vec2(0, 1),  # Down
    glm.vec2(-1, 1),  # Down Left
    glm.vec2(-1, 0),  # Left
    glm.vec2(-1, -1),  # Up Left
    glm.vec2(0, -1),  # Up
    glm.vec2(1, -1),  # Up Right
]

# Normalize direction vectors
DIRECTIONS = [
    glm.normalize(dir) if glm.length(dir) != 0 else glm.vec2(0, 0) for dir in DIRECTIONS
]

# Direction names for reference
DIRECTION_NAMES = [
    "Right",
    "Down Right",
    "Down",
    "Down Left",
    "Left",
    "Up Left",
    "Up",
    "Up Right",
]

# Initialize display
window = pygame.display.set_mode(WINDOW_SIZE.to_tuple())
pygame.display.set_caption("Animated Character Movement")

# Load step sound
step_sound_path = os.path.join("step.wav")
if not os.path.isfile(step_sound_path):
    print(f"Step sound file '{step_sound_path}' not found.")
    pygame.quit()
    exit()
step_sound = pygame.mixer.Sound(step_sound_path)

# Load sprite sheet
sprite_sheet_path = os.path.join("cman.png")
if not os.path.isfile(sprite_sheet_path):
    print(f"Sprite sheet '{sprite_sheet_path}' not found.")
    pygame.quit()
    exit()
sprite_sheet = pygame.image.load(sprite_sheet_path).convert_alpha()

# Sprite sheet details
FRAME_WIDTH, FRAME_HEIGHT = 256, 256
ROWS = 3  # Lowered arms, half-raised arms, raised arms
COLUMNS = 8  # Directions

# Scaling factor for sprite frames
SCALE = 0.5  # Adjust as needed


# Function to extract frames from the sprite sheet
def extract_frames(sheet, rows, columns, scale=1.0):
    frames = []
    for row in range(rows):
        arm_state_frames = []
        for col in range(columns):
            rect = pygame.Rect(
                col * FRAME_WIDTH, row * FRAME_HEIGHT, FRAME_WIDTH, FRAME_HEIGHT
            )
            frame = sheet.subsurface(rect).copy()
            if scale != 1.0:
                frame = pygame.transform.scale(
                    frame, (int(FRAME_WIDTH * scale), int(FRAME_HEIGHT * scale))
                )
            arm_state_frames.append(frame)
        frames.append(arm_state_frames)
    return frames


# Extract and scale frames
frames = extract_frames(sprite_sheet, ROWS, COLUMNS, SCALE)

ARM_LOWER_SPEED = 0.05
CHAR_SCALE = 0.4


class Character:
    def __init__(self, frames):
        self.frames = frames  # frames[arm_state][direction]
        self.position = glm.vec2(RENDER_RESOLUTION.x / 2, RENDER_RESOLUTION.y / 2)
        self.speed = 100  # Pixels per second
        self.arm_state = 0  # 0: lowered, 1: half-raised, 2: raised
        self.arm_upness = 0.0
        self.direction_index = 0  # Current facing direction (0-7)
        self.is_moving = False
        self.tilt_angle = 0.0
        self.tilt_direction = 1  # 1 for increasing angle, -1 for decreasing
        self.time_since_last_step = 0.0
        self.tilt_target_angle = TILT_MAX_ANGLE
        self.tilt_change_direction = 1  # 1 or -1

    def handle_input(self, keys):
        movement = glm.vec2(0, 0)
        if keys[pygame.K_w]:
            movement += glm.vec2(0, -1)
        if keys[pygame.K_s]:
            movement += glm.vec2(0, 1)
        if keys[pygame.K_a]:
            movement += glm.vec2(-1, 0)
        if keys[pygame.K_d]:
            movement += glm.vec2(1, 0)

        if glm.length(movement) != 0:
            self.is_moving = True
            movement = glm.normalize(movement)
            self.current_velocity = movement * self.speed
            # Determine direction index based on movement vector
            self.direction_index = self.get_direction_index(movement)
        else:
            self.is_moving = False
            self.current_velocity = glm.vec2(0, 0)

        # Handle arm state
        if keys[pygame.K_SPACE]:
            self.arm_upness += ARM_LOWER_SPEED * 2
            if self.arm_upness > 1.0:
                self.arm_upness = 1.0

    def get_direction_index(self, movement):
        # Find the closest direction index based on movement vector
        angles = [math.degrees(math.atan2(-dir.y, dir.x)) % 360 for dir in DIRECTIONS]
        movement_angle = math.degrees(math.atan2(-movement.y, movement.x)) % 360
        # Find the direction with the smallest angle difference
        smallest_diff = 360
        index = 0
        for i, angle in enumerate(angles):
            diff = min(abs(angle - movement_angle), 360 - abs(angle - movement_angle))
            if diff < smallest_diff:
                smallest_diff = diff
                index = i
        return index

    def update(self, delta_time):
        # Update position
        if self.is_moving:
            self.position += self.current_velocity * delta_time
            # Clamp position to render resolution
            self.position.x = max(0, min(RENDER_RESOLUTION.x, self.position.x))
            self.position.y = max(0, min(RENDER_RESOLUTION.y, self.position.y))

            # Update tilt
            tilt_increment = TILT_SPEED * delta_time * self.tilt_change_direction
            self.tilt_angle += tilt_increment
            if self.tilt_angle > TILT_MAX_ANGLE:
                self.tilt_angle = TILT_MAX_ANGLE
                self.tilt_change_direction *= -1
                step_sound.play()
            elif self.tilt_angle < -TILT_MAX_ANGLE:
                self.tilt_angle = -TILT_MAX_ANGLE
                self.tilt_change_direction *= -1
                step_sound.play()
        else:
            # Reset tilt when not moving
            self.tilt_angle = 0.0

        self.arm_upness -= ARM_LOWER_SPEED
        if self.arm_upness < 0.0:
            self.arm_upness = 0.0

        # set arm state based on arm upness
        if self.arm_upness < 0.33:
            self.arm_state = 0
        elif self.arm_upness < 0.66:
            self.arm_state = 1
        else:
            self.arm_state = 2

    def draw(self, surface):
        # Get current frame based on arm state and direction
        frame = self.frames[self.arm_state][self.direction_index]

        # scale the frame save as frame
        frame = pygame.transform.scale(
            frame,
            (int(frame.get_width() * CHAR_SCALE), int(frame.get_height() * CHAR_SCALE)),
        )

        # Rotate frame based on tilt angle
        rotated_frame = pygame.transform.rotate(frame, self.tilt_angle)
        rotated_rect = rotated_frame.get_rect(center=(self.position.x, self.position.y))
        # Blit to surface
        surface.blit(rotated_frame, rotated_rect.topleft)


# Initialize character
character = Character(frames)

# Clock for frame rate and timing
clock = pygame.time.Clock()

# Render surface
render_surface = pygame.Surface(RENDER_RESOLUTION.to_tuple())


def main():
    running = True
    while running:
        delta_time = clock.tick(FPS) / 1000.0  # Delta time in seconds

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key in [K_ESCAPE, K_q]:
                    running = False

        # Handle input
        keys = pygame.key.get_pressed()
        character.handle_input(keys)

        # Update character
        character.update(delta_time)

        # Fill render surface
        render_surface.fill((0, 0, 0))  # Black background

        # Draw character
        character.draw(render_surface)

        # Scale and blit to window
        stretched_surface = pygame.transform.scale(
            render_surface, WINDOW_SIZE.to_tuple()
        )
        window.blit(stretched_surface, (0, 0))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
