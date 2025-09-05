import json
from config import config
from loguru import logger


class TileInfo:
    def __init__(self, id: int, name: str, hex_code: str):
        self.id = id
        self.color = tuple(int((hex_code.lstrip('#'))[i:i+2], 16) for i in (0, 2, 4))
        self.name = name
        self.hex_code = hex_code

    def __str__(self) -> str:
        return f"Tile: {self.id} - {self.name}"




tiles_data = config.tiles
tile_colors = {int(k): TileInfo(**v) for k, v in tiles_data.items()}
DEFAULT_TILE = TileInfo(-1, "Unknown", "#FFC0CB")

class Map:
    def __init__(self, path) -> None:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as file:
                contents = file.read()
            objects = [json.loads(s.strip()) for s in contents.splitlines()]
            resources = objects[0].get("resources", {}) if objects else {}
            self.gold = resources.get("gold", 0)
            self.fluxite = resources.get("fluxite", 0)
            self.artifacts = resources.get("artifacts", 0)

            found = False
            for obj in objects:
                if "world" in obj and "matrix" in obj["world"]:
                    found = True
                    self.world = obj["world"]["matrix"]
                    break
            if not found:
                raise RuntimeError("Could not find world.matrix in save file.")
            if not (isinstance(self.world, list) and all(isinstance(row, list) for row in self.world)):
                raise RuntimeError("world.matrix is not a valid tilemap.")
            player_data = objects[1].get("player", {}) if len(objects) > 1 else {}
            self.player_x = player_data.get("x", 0) / 4
            self.player_y = player_data.get("y", 0) / 4
            self.active_slot = player_data.get("activeslotindex", 0)
        except Exception as e:
            raise e

    def get_tile_info(self, tile) -> TileInfo:
        _tile_colors = tile_colors
        if isinstance(tile, int):
            return _tile_colors.get(tile, DEFAULT_TILE)
        if isinstance(tile, dict):
            elem = tile.get("element")
            if isinstance(elem, dict) and "type" in elem:
                return _tile_colors.get(elem["type"] + 100, DEFAULT_TILE)
        return DEFAULT_TILE

    def get_tile_color(self, tile):
        _tile_colors = tile_colors
        if isinstance(tile, int):
            ti = _tile_colors.get(tile)
            return ti.color if ti is not None else DEFAULT_TILE.color
        if isinstance(tile, dict):
            elem = tile.get("element")
            if isinstance(elem, dict) and "type" in elem:
                ti = _tile_colors.get(elem["type"] + 100)
                return ti.color if ti is not None else DEFAULT_TILE.color
        return DEFAULT_TILE.color
