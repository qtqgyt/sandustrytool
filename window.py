import math
import sys
from config import config
from loguru import logger

from os import environ
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
import threading
import queue

from map import Map

MAX_ZOOM = config.max_zoom

class window:
    def __init__(self, title: str, map: Map) -> None:
        self.map = map
        self.zoom_level = config.zoom_level
        self.window_width, self.window_height = config.window_x, config.window_y

        pygame.init()

        ICON_SIZE = 32
        pygame.display.set_icon(self._create_magnifying_glass(ICON_SIZE, filled=True))

        CURSOR_SIZE = 24
        cursor_surface = self._create_magnifying_glass(CURSOR_SIZE)
        cursor = pygame.cursors.Cursor((CURSOR_SIZE // 2, CURSOR_SIZE // 2), cursor_surface)
        pygame.mouse.set_cursor(cursor)

        pygame.display.set_caption(title)
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)

        self.rows = len(self.map.world)
        self.cols = max(len(row) for row in self.map.world)
        self.tilemap_width = self.cols * self.zoom_level
        self.tilemap_height = self.rows * self.zoom_level

        self.font = pygame.font.SysFont(None, 24)

        self.scroll_speed = config.scroll_speed
        self.camera_x = (self.tilemap_width - self.window_width) // 2
        self.camera_y = (self.tilemap_height - self.window_height) // 2
        self._calculate_camera_borders()

        self._generation_thread = None
        self._generation_queue = None
        self._generating = False
        self._generation_error = None
        self._progress = 0.0

        self._tile_color_cache = {}
        self._overlay_bg = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(self._overlay_bg, (0, 0, 0, 160), self._overlay_bg.get_rect())

        self._tile_surface_cache = {}
        self._resources_surface = None
        self._last_resources_tuple = (None, None, None)

    def _create_magnifying_glass(self, size: int, filled: bool = False) -> pygame.Surface:
        magnifying_glass = pygame.Surface((size, size), pygame.SRCALPHA)
        magnifying_glass.fill((0, 0, 0, 0))

        circle_radius = size // 3
        circle_center = (size // 2, size // 2)

        handle_offset = math.floor((circle_radius) / math.sqrt(2))
        handle_start = (circle_center[0] + handle_offset, circle_center[1] + handle_offset)
        handle_end = (size - 2, size - 2)

        pygame.draw.line(magnifying_glass, (64, 64, 64), handle_start, handle_end, 4)
        pygame.draw.circle(magnifying_glass, (128, 128, 128), circle_center, circle_radius, 2)
        if filled:
            pygame.draw.circle(magnifying_glass, (173, 216, 230, 128), circle_center, circle_radius - 1, 0)
        return magnifying_glass

    def draw_loading_overlay(self):
        loading_text = self.font.render("LOADING...", True, (255, 255, 255))
        text_rect = loading_text.get_rect(center=(self.screen.get_width() // 2, self.screen.get_height() // 2))

        background = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(background, (0, 0, 0, 128), background.get_rect())
        self.screen.blit(background, (0, 0))
        self.screen.blit(loading_text, text_rect)
        pygame.display.flip()

    def draw_progress_bar(self, progress: float, text: str = "") -> None:
        progress = max(0.0, min(1.0, float(progress)))
        screen_width, screen_height = self.screen.get_size()

        if self._overlay_bg.get_size() != (screen_width, screen_height):
            self._overlay_bg = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            pygame.draw.rect(self._overlay_bg, (0, 0, 0, 160), self._overlay_bg.get_rect())

        self.screen.blit(self._overlay_bg, (0, 0))

        bar_width = screen_width // 2
        bar_height = 28
        bar_x = (screen_width - bar_width) // 2
        bar_y = (screen_height - bar_height) // 2

        pygame.draw.rect(self.screen, (200, 200, 200), (bar_x - 2, bar_y - 2, bar_width + 4, bar_height + 4), border_radius=6)
        pygame.draw.rect(self.screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height), border_radius=6)
        pygame.draw.rect(self.screen, (0, 200, 0), (bar_x, bar_y, int(bar_width * progress), bar_height), border_radius=6)

        if text:
            text_surface = self.font.render(text, True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=(screen_width // 2, bar_y - 18))
            self.screen.blit(text_surface, text_rect)

        percent_text = f"{int(progress * 100)}%"
        percent_surface = self.font.render(percent_text, True, (255, 255, 255))
        percent_rect = percent_surface.get_rect(center=(bar_x + bar_width // 2, bar_y + bar_height // 2))
        self.screen.blit(percent_surface, percent_rect)

        pygame.display.flip()

    def _get_tile_surface(self, color, zoom):
        key = (color, zoom)
        surf = self._tile_surface_cache.get(key)
        if surf is None:
            surf = pygame.Surface((zoom, zoom))
            surf.fill(color)
            self._tile_surface_cache[key] = surf
        return surf

    def draw_resources(self) -> pygame.Surface:
        gold_text = self.font.render(f"Gold: {self.map.gold}", True, (255, 215, 0))
        fluxite_text = self.font.render(f"Fluxite: {self.map.fluxite}", True, (175, 0, 224))
        artifacts_text = self.font.render(f"Artifacts: {self.map.artifacts}/2", True, (45, 197, 214))

        background_width = max(gold_text.get_width(), fluxite_text.get_width(), artifacts_text.get_width()) + 10
        resources_hud = pygame.Surface((background_width + 10, 100), pygame.SRCALPHA)
        resources_hud.fill((0, 0, 0, 0))

        pygame.draw.rect(resources_hud, (128, 128, 128, 128), pygame.Rect(5, 5, background_width, 90), 0, 5)
        resources_hud.blits(
            [
                (gold_text, (10, 10)),
                (fluxite_text, (10, 40)),
                (artifacts_text, (10, 70)),
            ]
        )
        return resources_hud

    def _generate_tilemap_worker(self, q: queue.Queue, zoom_level: int) -> None:
        try:
            _cache = self._tile_color_cache
            _lock = getattr(self, "_cache_lock", None)
            _get_tile_color = getattr(self.map, "get_tile_color", None)
            world = self.map.world

            for y, row in enumerate(world):
                row_colors = []
                for tile in row:
                    tile_id = tile[0] if isinstance(tile, list) else tile
                    c = _cache.get(tile_id)
                    if c is None:
                        if _get_tile_color is not None:
                            c = _get_tile_color(tile_id)
                        else:
                            c = self.map.get_tile_info(tile_id).color
                        if _lock:
                            with _lock:
                                if tile_id not in _cache:
                                    _cache[tile_id] = c
                        else:
                            _cache[tile_id] = c
                    row_colors.append(c)
                q.put(("row", y, row_colors))
            q.put(("done", None, None))
        except Exception as e:
            q.put(("error", str(e), None))

    def draw_new_tilemap(self) -> None:
        self.draw_loading_overlay()
        self.tilemap_width = self.cols * self.zoom_level
        self.tilemap_height = self.rows * self.zoom_level
        logger.debug(f"New dimensions - width: {self.tilemap_width}, height: {self.tilemap_height}")

        self.tilemap_surface = pygame.Surface((self.tilemap_width, self.tilemap_height))
        q: queue.Queue = queue.Queue()
        self._generation_queue = q
        self._generation_error = None
        self._progress = 0.0
        self._generating = True

        worker = threading.Thread(target=self._generate_tilemap_worker, args=(q, self.zoom_level), daemon=True)
        self._generation_thread = worker
        worker.start()

        clock = pygame.time.Clock()
        rows_drawn = 0
        try:
            while True:
                pygame.event.pump()
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        self._generation_error = "quit"
                        self._generating = False
                        return
                    elif ev.type == pygame.VIDEORESIZE:
                        self.window_width, self.window_height = ev.size
                        if self._overlay_bg.get_size() != ev.size:
                            self._overlay_bg = pygame.Surface(ev.size, pygame.SRCALPHA)
                            pygame.draw.rect(self._overlay_bg, (0, 0, 0, 160), self._overlay_bg.get_rect())
                        self._calculate_camera_borders()

                handled = False
                while True:
                    try:
                        item = q.get_nowait()
                    except queue.Empty:
                        break
                    handled = True
                    tag, a, b = item
                    if tag == "row":
                        y = a
                        row_colors = b
                        zoom = self.zoom_level
                        xi = 0
                        n = len(row_colors)
                        fill = self.tilemap_surface.fill
                        blit = self.tilemap_surface.blit
                        while xi < n:
                            color = row_colors[xi]
                            start = xi
                            xi += 1
                            while xi < n and row_colors[xi] == color:
                                xi += 1
                            length = xi - start
                            if length == 1:
                                tile_surf = self._get_tile_surface(color, zoom)
                                blit(tile_surf, (start * zoom, y * zoom))
                            else:
                                rect = pygame.Rect(start * zoom, y * zoom, length * zoom, zoom)
                                fill(color, rect)
                        rows_drawn += 1
                        self._progress = rows_drawn / max(1, self.rows)
                        try:
                            self.draw_progress_bar(self._progress, "Loading tilemap...")
                        except Exception:
                            pass
                    elif tag == "done":
                        self._progress = 1.0
                        self._generating = False
                        break
                    elif tag == "error":
                        self._generation_error = a
                        self._generating = False
                        break

                if not self._generating:
                    while True:
                        try:
                            item = q.get_nowait()
                        except queue.Empty:
                            break
                        tag, a, b = item
                        if tag == "row":
                            y = a
                            row_colors = b
                            zoom = self.zoom_level
                            xi = 0
                            n = len(row_colors)
                            while xi < n:
                                color = row_colors[xi]
                                start = xi
                                xi += 1
                                while xi < n and row_colors[xi] == color:
                                    xi += 1
                                length = xi - start
                                rect = pygame.Rect(start * zoom, y * zoom, length * zoom, zoom)
                                pygame.draw.rect(self.tilemap_surface, color, rect)
                    break

                if not handled:
                    clock.tick(60)
        except Exception as e:
            logger.exception("Error while generating tilemap")
            self._generation_error = str(e)
            self._generating = False

        if self._generation_error:
            logger.warning(f"Generation thread failed ({self._generation_error}), falling back to blocking generation")
            cache = self._tile_color_cache
            for y, row in enumerate(self.map.world):
                row_colors = []
                for tile in row:
                    tile_id = tile[0] if isinstance(tile, list) else tile
                    c = cache.get(tile_id)
                    if c is None:
                        tile_info = self.map.get_tile_info(tile_id)
                        c = tile_info.color
                        cache[tile_id] = c
                    row_colors.append(c)
                zoom = self.zoom_level
                xi = 0
                n = len(row_colors)
                while xi < n:
                    color = row_colors[xi]
                    start = xi
                    xi += 1
                    while xi < n and row_colors[xi] == color:
                        xi += 1
                    length = xi - start
                    rect = pygame.Rect(start * zoom, y * zoom, length * zoom, zoom)
                    pygame.draw.rect(self.tilemap_surface, color, rect)

        pygame.draw.circle(
            self.tilemap_surface,
            (0, 255, 0),
            (self.map.player_x * self.zoom_level, self.map.player_y * self.zoom_level),
            max(self.zoom_level // 2, 5),
        )

    def _calculate_camera_borders(self) -> None:
        if 0 < self.tilemap_width - self.window_width:
            self.min_camera_x = 0
            self.max_camera_x = self.tilemap_width - self.window_width
        else:
            self.min_camera_x = self.tilemap_width - self.window_width
            self.max_camera_x = 0
        if 0 < self.tilemap_height - self.window_height:
            self.min_camera_y = self.tilemap_height - self.window_height
            self.max_camera_y = 0
        else:
            self.min_camera_y = 0
            self.max_camera_y = self.tilemap_height - self.window_height

    def update_map_dimensions(self, change: int) -> None:
        old_zoom = self.zoom_level
        self.zoom_level = max(1, min(4, self.zoom_level + change))
        if old_zoom == self.zoom_level:
            return
        logger.debug(f"Updating dimensions - Current zoom: {self.zoom_level}")

        self.draw_new_tilemap()

        mouse_x, mouse_y = pygame.mouse.get_pos()
        world_x = self.camera_x + mouse_x
        world_y = self.camera_y + mouse_y
        rel_x = world_x / self.tilemap_width if self.tilemap_width > 0 else 0.5
        rel_y = world_y / self.tilemap_height if self.tilemap_height > 0 else 0.5
        new_world_x = rel_x * self.tilemap_width
        new_world_y = rel_y * self.tilemap_height
        self.camera_x = int(new_world_x - mouse_x)
        self.camera_y = int(new_world_y - mouse_y)
        self._calculate_camera_borders()

    def _ensure_resources_surface(self):
        cur = (self.map.gold, self.map.fluxite, self.map.artifacts)
        if cur == self._last_resources_tuple and self._resources_surface is not None:
            return
        self._last_resources_tuple = cur
        gold_text = self.font.render(f"Gold: {self.map.gold}", True, (255, 215, 0))
        fluxite_text = self.font.render(f"Fluxite: {self.map.fluxite}", True, (175, 0, 224))
        artifacts_text = self.font.render(f"Artifacts: {self.map.artifacts}/2", True, (45, 197, 214))
        background_width = max(gold_text.get_width(), fluxite_text.get_width(), artifacts_text.get_width()) + 10
        resources_hud = pygame.Surface((background_width + 10, 100), pygame.SRCALPHA)
        pygame.draw.rect(resources_hud, (128, 128, 128, 128), pygame.Rect(5, 5, background_width, 90), 0, 5)
        resources_hud.blits(
            [
                (gold_text, (10, 10)),
                (fluxite_text, (10, 40)),
                (artifacts_text, (10, 70)),
            ]
        )
        self._resources_surface = resources_hud

    def render(self):
        running = True
        clock = pygame.time.Clock()

        self.draw_new_tilemap()

        while running:
            pygame.event.pump()

            keys = pygame.key.get_pressed()
            if keys[pygame.K_ESCAPE] or keys[pygame.K_q]:
                running = False
                continue

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.window_width, self.window_height = event.size
                    self._calculate_camera_borders()
                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS]:
                        logger.debug(f"Attempting to zoom in from {self.zoom_level}")
                        self.update_map_dimensions(1)
                        logger.debug(f"New zoom level: {self.zoom_level}")
                    elif event.key in [pygame.K_MINUS, pygame.K_KP_MINUS]:
                        logger.debug(f"Attempting to zoom out from {self.zoom_level}")
                        self.update_map_dimensions(-1)
                        logger.debug(f"New zoom level: {self.zoom_level}")

            scroll_x = scroll_y = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                scroll_x -= self.scroll_speed
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                scroll_x += self.scroll_speed
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                scroll_y += self.scroll_speed
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                scroll_y -= self.scroll_speed
            self.camera_x = max(min(self.camera_x + scroll_x, self.max_camera_x), self.min_camera_x)
            self.camera_y = min(max(self.camera_y - scroll_y, self.max_camera_y), self.min_camera_y)

            self.screen.fill((0, 0, 0))
            self.screen.blit(
                self.tilemap_surface,
                (0, 0),
                area=pygame.Rect(self.camera_x, self.camera_y, self.window_width, self.window_height),
            )
            mouse_x, mouse_y = pygame.mouse.get_pos()
            world_x = self.camera_x + mouse_x
            world_y = self.camera_y + mouse_y
            tile_x = world_x // self.zoom_level
            tile_y = world_y // self.zoom_level
            if 0 <= tile_y < self.rows and 0 <= tile_x < self.cols:
                tile = self.map.world[tile_y][tile_x]
                if isinstance(tile, list):
                    tile = tile[0]
                hover_rect = pygame.Rect(
                    tile_x * self.zoom_level - self.camera_x,
                    tile_y * self.zoom_level - self.camera_y,
                    self.zoom_level,
                    self.zoom_level,
                )
                pygame.draw.rect(self.screen, (255, 0, 0), hover_rect, 2)
                tile_info = self.map.get_tile_info(tile)
                text_surface = self.font.render(str(tile_info), True, (255, 255, 255))
                self.screen.blit(text_surface, (mouse_x + 10, mouse_y - text_surface.get_height() + 10))
            self._ensure_resources_surface()
            self.screen.blit(self._resources_surface, (0, 0))

            pygame.display.flip()
            clock.tick(60)

        pygame.quit()
        sys.exit()
        if cur == self._last_resources_tuple and self._resources_surface is not None:
            return
        self._last_resources_tuple = cur
        # build cached HUD
        gold_text = self.font.render(f"Gold: {self.map.gold}", True, (255, 215, 0))
        fluxite_text = self.font.render(f"Fluxite: {self.map.fluxite}", True, (175, 0, 224))
        artifacts_text = self.font.render(f"Artifacts: {self.map.artifacts}/2", True, (45, 197, 214))
        background_width = max(gold_text.get_width(), fluxite_text.get_width(), artifacts_text.get_width()) + 10
        resources_hud = pygame.Surface((background_width + 10, 100), pygame.SRCALPHA)
        pygame.draw.rect(resources_hud, (128, 128, 128, 128), pygame.Rect(5, 5, background_width, 90), 0, 5)
        resources_hud.blits(
            [
                (gold_text, (10, 10)),
                (fluxite_text, (10, 40)),
                (artifacts_text, (10, 70)),
            ]
        )
        self._resources_surface = resources_hud

    def render(self):
        running = True
        clock = pygame.time.Clock()

        self.draw_new_tilemap()

        while running:
            pygame.event.pump()

            keys = pygame.key.get_pressed()
            if keys[pygame.K_ESCAPE] or keys[pygame.K_q]:
                running = False
                continue

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.window_width, self.window_height = event.size
                    self._calculate_camera_borders()
                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS]:
                        logger.debug(f"Attempting to zoom in from {self.zoom_level}")
                        self.update_map_dimensions(1)
                        logger.debug(f"New zoom level: {self.zoom_level}")
                    elif event.key in [pygame.K_MINUS, pygame.K_KP_MINUS]:
                        logger.debug(f"Attempting to zoom out from {self.zoom_level}")
                        self.update_map_dimensions(-1)
                        logger.debug(f"New zoom level: {self.zoom_level}")

            scroll_x = scroll_y = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                scroll_x -= self.scroll_speed
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                scroll_x += self.scroll_speed
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                scroll_y += self.scroll_speed
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                scroll_y -= self.scroll_speed
            self.camera_x = max(min(self.camera_x + scroll_x, self.max_camera_x), self.min_camera_x)
            self.camera_y = min(max(self.camera_y - scroll_y, self.max_camera_y), self.min_camera_y)

            self.screen.fill((0, 0, 0))
            self.screen.blit(
                self.tilemap_surface,
                (0, 0),
                area=pygame.Rect(self.camera_x, self.camera_y, self.window_width, self.window_height),
            )
            mouse_x, mouse_y = pygame.mouse.get_pos()
            world_x = self.camera_x + mouse_x
            world_y = self.camera_y + mouse_y
            tile_x = world_x // self.zoom_level
            tile_y = world_y // self.zoom_level
            if 0 <= tile_y < self.rows and 0 <= tile_x < self.cols:
                tile = self.map.world[tile_y][tile_x]

                ###############################################
                # If tile is an array, use its first element. #
                ###############################################
                if isinstance(tile, list):
                    tile = tile[0]
                hover_rect = pygame.Rect(
                    tile_x * self.zoom_level - self.camera_x,
                    tile_y * self.zoom_level - self.camera_y,
                    self.zoom_level,
                    self.zoom_level,
                )
                pygame.draw.rect(self.screen, (255, 0, 0), hover_rect, 2)
                tile_info = self.map.get_tile_info(tile)
                text_surface = self.font.render(str(tile_info), True, (255, 255, 255))
                self.screen.blit(text_surface, (mouse_x + 10, mouse_y - text_surface.get_height() + 10))
            # before blitting HUD, ensure cached surface is up-to-date
            self._ensure_resources_surface()
            self.screen.blit(self._resources_surface, (0, 0))

            pygame.display.flip()
            clock.tick(60)

        pygame.quit()
        sys.exit()
