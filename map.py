import json

from config import config


class TileInfo:
    def __init__(self, id: int, name: str, hex_code: str):
        self.id = id
        self.color = tuple(int((hex_code.lstrip("#"))[i : i + 2], 16) for i in (0, 2, 4))
        self.name = name
        self.hex_code = hex_code

    def is_particle(self):
        return self.id > 100

    def is_empty(self):
        return self.id == 0

    def __str__(self) -> str:
        return f"Tile: {self.id} - {self.name}"


default_tile = TileInfo(-1, "Unknown", "#FFC0CB")

tiles_data = config.tiles
tile_colors = {int(k): TileInfo(**v) for k, v in tiles_data.items()}


class Map:
    def __init__(self, path) -> None:
        self.path = path
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as file:
                contents = file.read()
            self.data = [json.loads(s.strip()) for s in contents.splitlines()]
            # Extract gold, fluxite, and artifacts from the first JSON segment at path resources.gold, fluxite, artifacts
            resources = self.data[0].get("resources", {}) if self.data else {}
            self.gold = resources.get("gold", 0)
            self.fluxite = resources.get("fluxite", 0)
            self.artifacts = resources.get("artifacts", 0)

            found = False
            for obj in self.data:
                if "world" in obj and "matrix" in obj["world"]:
                    found = True
                    self.world = obj["world"]["matrix"]
                    break
            if not found:
                raise RuntimeError("Could not find world.matrix in save file.")
            if not (isinstance(self.world, list) and all(isinstance(row, list) for row in self.world)):
                raise RuntimeError("world.matrix is not a valid tilemap.")
            player_data = self.data[1].get("player", {}) if len(self.data) > 1 else {}
            self.player_x = player_data.get("x", 0) / 4
            self.player_y = player_data.get("y", 0) / 4
            self.active_slot = player_data.get("activeslotindex", 0)
        except Exception as e:
            raise e

    def get_tile(self, x: int, y: int):
        return self.world[y][x]

    def set_tile(self, x: int, y: int, tile) -> None:
        self.world[y][x] = tile

    def get_tile_info_at(self, x: int, y: int) -> TileInfo:
        return self.get_tile_info(self.world[y][x])

    def get_tile_info(self, tile) -> TileInfo:
        tileInfo = default_tile
        if isinstance(tile, int):
            tileInfo = tile_colors.get(tile, default_tile)
        if isinstance(tile, dict) and "element" in tile and "type" in tile["element"]:
            tileInfo = tile_colors.get(tile["element"]["type"] + 100, default_tile)
        return tileInfo

    def save(self):
        with open(self.path, "w", encoding="utf-8", errors="replace") as file:
            for obj in self.data:
                file.write(json.dumps(obj) + "\n")
