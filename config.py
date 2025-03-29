import json
import atexit
import os
from loguru import logger

class Config:
    CONFIG_FILE = "config.json"

    def __init__(self):
        self.zoom_level = 1
        self.scroll_speed = 10
        self.window_x = 800
        self.window_y = 600
        self.log_level = "INFO"
        self.tiles = {"0":{"id":0,"name":"Air","hex_code":"#111111"},"2":{"id":2,"name":"Soil","hex_code":"#ba7f2e"},"3":{"id":3,"name":"Sporemound","hex_code":"#779325"},"4":{"id":4,"name":"Fog","hex_code":"#000000"},"5":{"id":5,"name":"Artifact Number Block","hex_code":"#ff0000"},"6":{"id":6,"name":"Undiscovered Water","hex_code":"#70a8ec"},"7":{"id":7,"name":"Frostbed","hex_code":"#eef6f6"},"8":{"id":8,"name":"Sealing Block","hex_code":"#ff8000"},"9":{"id":9,"name":"Grass","hex_code":"#73b143"},"10":{"id":10,"name":"Moss","hex_code":"#5bce22"},"13":{"id":13,"name":"Undiscovered Lava","hex_code":"#ff6600"},"14":{"id":14,"name":"Fluxite","hex_code":"#af00e0"},"15":{"id":15,"name":"Block","hex_code":"#d99d0e"},"16":{"id":16,"name":"SlidingBlock","hex_code":"#d99d0e"},"17":{"id":17,"name":"SlidingBlockLeft","hex_code":"#d99d0e"},"18":{"id":18,"name":"SlidingBlockRight","hex_code":"#d99d0e"},"19":{"id":19,"name":"ConveyorLeft","hex_code":"#d99d0e"},"20":{"id":20,"name":"ConveyorRight","hex_code":"#d99d0e"},"21":{"id":21,"name":"ShakerLeft","hex_code":"#d99d0e"},"22":{"id":22,"name":"ShakerRight","hex_code":"#d99d0e"},"23":{"id":23,"name":"Bedrock","hex_code":"#aaaaaa"},"24":{"id":24,"name":"Kinetic Slag Press","hex_code":"#d99d0e"},"25":{"id":25,"name":"Ice","hex_code":"#66ccff"},"28":{"id":28,"name":"Redsoil","hex_code":"#a30000"},"29":{"id":29,"name":"Scoria","hex_code":"#671b00"},"30":{"id":30,"name":"Crackstone","hex_code":"#e0d3b8"},"101":{"id":101,"name":"Sand","hex_code":"#daab69"},"103":{"id":103,"name":"Water","hex_code":"#70a8ec"},"104":{"id":104,"name":"Wet Sand","hex_code":"#d29a4c"},"105":{"id":105,"name":"Redsand","hex_code":"#a30000"},"106":{"id":106,"name":"Slag","hex_code":"#ababab"},"107":{"id":107,"name":"Gold","hex_code":"#fafa02"},"108":{"id":108,"name":"Voidbloom","hex_code":"#60246c"},"110":{"id":110,"name":"Steam","hex_code":"#acc4e5"},"111":{"id":111,"name":"Fire","hex_code":"#ffae0b"},"112":{"id":112,"name":"Snow","hex_code":"#eef6f6"},"113":{"id":113,"name":"Flame","hex_code":"#ffae0b"},"114":{"id":114,"name":"Burnt Slag","hex_code":"#636363"},"115":{"id":115,"name":"Spore","hex_code":"#beda69"},"116":{"id":116,"name":"Wet Spore","hex_code":"#96ba2e"},"117":{"id":117,"name":"Seed","hex_code":"#46991a"},"118":{"id":118,"name":"Amethelis","hex_code":"#8b69da"},"119":{"id":119,"name":"Lava","hex_code":"#ffae0b"},"120":{"id":120,"name":"Cinder","hex_code":"#750a00"}}
        self.load_config()
        atexit.register(self.save_config)

    def load_config(self):
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.__dict__.update(data)
        except Exception as e:
            logger.error(f"Error loading config: {e}")

    def save_config(self):
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.__dict__, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving config: {e}")

config = Config()