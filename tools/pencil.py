from typing import TYPE_CHECKING

import pygame
from loguru import logger
from pygame.event import Event

from tools.tool import Tool

if TYPE_CHECKING:
    from window import window


MAX_SIZE = 50

SQUARE = 1


class Pencil(Tool):
    def __init__(self) -> None:
        self.size_inc = 0
        self.shape = SQUARE
        self.selecting_tile = False
        self.selectable_elements = [
            101,
            103,
            104,
            105,
            106,
            107,
            108,
            110,
            111,
            112,
            113,
            114,
            115,
            116,
            117,
            118,
            119,
            120,
        ]
        super().__init__()

    def render_selection(self, window: "window") -> None:
        self.selection_window_x = (window.window_width - self.selection_window.get_width()) // 2
        self.selection_window_y = (window.window_height - self.selection_window.get_height()) // 2
        window.screen.blit(self.selection_window, (self.selection_window_x, self.selection_window_y))
        # button_content =

    def render(self, window: "window") -> None:
        if not self.selecting_tile:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            x = (window.camera_x + mouse_x) // window.zoom_level - self.size_inc // 2
            y = (window.camera_y + mouse_y) // window.zoom_level - self.size_inc // 2
            hover_rect = pygame.Rect(
                (x * window.zoom_level - window.camera_x),
                (y * window.zoom_level - window.camera_y),
                window.zoom_level * (self.size_inc + 1),
                window.zoom_level * (self.size_inc + 1),
            )
            pygame.draw.rect(window.screen, (255, 0, 0), hover_rect)
        else:
            super().render(window)
            self.render_selection(window)

        tool_name = window.font.render(str(self), True, (255, 255, 255), (50, 50, 50, 50))
        window.screen.blit(tool_name, (10, window.window_height - tool_name.get_height() - 10))

    def handle_event(self, window, event: Event) -> tuple[bool, dict]:
        match event.type:
            case pygame.MOUSEBUTTONDOWN:
                return self.process_mouse_down(window, event)
            case pygame.MOUSEMOTION:
                return self.process_mouse_move(window, event)
            case pygame.KEYDOWN:
                return self.process_key_down(window, event)
            case _:
                return (False, {})

    def _toggle_selection(self) -> None:
        self.selecting_tile = not self.selecting_tile
        pygame.mouse.set_visible(self.selecting_tile)

    def process_key_down(self, window: "window", event: Event) -> tuple[bool, dict]:
        match event.key:
            case pygame.K_TAB:
                self._toggle_selection()
                return (False, {})
            case _:
                return (False, {})

    def process_mouse_move(self, window: "window", event: Event) -> tuple[bool, dict]:
        if event.buttons[0]:
            event.button = 1
            return self.process_mouse_down(window, event)
        return (False, {})

    def process_mouse_down(self, window: "window", event: Event) -> tuple[bool, dict]:
        if event.button == 4:
            if self.size_inc < MAX_SIZE:
                self.size_inc += 1
            return (False, {})
        if event.button == 5:
            if self.size_inc > 0:
                self.size_inc -= 1
            return (False, {})
        if not event.button == 1:
            return (False, {})
        if self.selecting_tile:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            mouse_x -= self.selection_window_x
            mouse_y -= self.selection_window_y
            if mouse_x <= self.selection_window_width and mouse_x <= self.selection_window_height:
                if mouse_y < self.selection_window_spacing:
                    id = self.selectable_elements[0]
                elif mouse_y > self.selection_window_height - self.selection_window_spacing:
                    id = self.selectable_elements[-1]
                else:
                    mouse_y -= self.selection_window_spacing // 2
                    id = self.selectable_elements[
                        mouse_y
                        // (
                            (self.selection_window_height - self.selection_window_spacing)
                            // (len(self.selectable_elements))
                        )
                    ]
                self.selected_tile = window.map.get_tile_info(id)
                self._toggle_selection()
            return (False, {})
        else:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            x = (window.camera_x + mouse_x) // window.zoom_level - self.size_inc // 2
            y = (window.camera_y + mouse_y) // window.zoom_level - self.size_inc // 2
            changed = False
            old = [[0] * (self.size_inc + 1)] * (self.size_inc + 1)
            x_pos = 0
            for c in range(max(0, x), min(window.cols - 1, x + (self.size_inc + 1))):
                y_pos = 0
                for r in range(max(0, y), min(window.rows - 1, y + (self.size_inc + 1))):
                    tile_info = window.map.get_tile_info_at(c, r)
                    if tile_info.is_empty():
                        old[x_pos][y_pos] = tile_info.id
                        window.map.set_tile(c, r, self.selected_tile.id)
                        changed = True
            if changed:
                logger.debug(
                    f"{max(0, x)} - {max(0, y)} - {min(window.cols, x + self.size_inc)} - {min(window.rows, y + self.size_inc)}"
                )
                window._update_tilemap_surface(max(0, x), max(0, y), self.size_inc + 1, self.size_inc + 1)
            return (changed, {"x": x, "y": y, "old": old, "new": 0, "size": self.size_inc})

    def activate(self, window: "window") -> None:
        if not hasattr(self, "selected_tile"):
            self.selected_tile = window.map.get_tile_info(101)
        if not hasattr(self, "selection_window"):
            selectable_elements = [window.map.get_tile_info(id) for id in self.selectable_elements]
            texts = [window.font.render(x.name, True, x.color) for x in selectable_elements]
            self.selection_window_spacing = 15
            self.selection_window_height = (
                sum([x.get_height() for x in texts])
                + self.selection_window_spacing * len(texts)
                + self.selection_window_spacing
            )
            self.selection_window_width = max([x.get_width() for x in texts]) + 2 * self.selection_window_spacing
            self.selection_window = pygame.Surface(
                (self.selection_window_width, self.selection_window_height), pygame.SRCALPHA
            )
            self.selection_window.fill((0, 0, 0, 0))
            pygame.draw.rect(
                self.selection_window,
                (68, 68, 68, 200),
                pygame.Rect(0, 0, self.selection_window_width, self.selection_window_height),
                0,
                5,
            )
            logger.debug(
                [
                    (
                        text,
                        (
                            self.selection_window_spacing,
                            sum([x.get_height() for x in texts[:i]])
                            + self.selection_window_spacing * i
                            + self.selection_window_spacing,
                        ),
                    )
                    for i, text in enumerate(texts)
                ]
            )
            self.selection_window.blits(
                [
                    (
                        text,
                        (
                            self.selection_window_spacing,
                            sum([x.get_height() for x in texts[:i]])
                            + self.selection_window_spacing * i
                            + self.selection_window_spacing,
                        ),
                    )
                    for i, text in enumerate(texts)
                ]
            )
        pygame.mouse.set_visible(self.selecting_tile)

    def deactivate(self, window: "window") -> None:
        pygame.mouse.set_visible(True)

    def __str__(self) -> str:
        return f"Pencil - {self.selected_tile.name}"
