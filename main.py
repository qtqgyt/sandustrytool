#!python
from loguru import logger
from config import config
import sys
import tkinter as tk
from tkinter import filedialog
import argparse

from map import Map
from window import window

parser = argparse.ArgumentParser()
parser.add_argument('path', type=str, help='Path to the save file')
parser.add_argument('--resetconfig', action='store_true', help='Reset the config file to defaults')
args = parser.parse_args()

if args.resetconfig == True:
    config.reset_config()
    logger.info("Config file reset to defaults.")

@logger.catch
def main():
    if args.path:
        json_path = args.path
    else:
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        json_path = filedialog.askopenfilename(title="Select save file", filetypes=[("Save Files", "*.save")])
        root.destroy()
    if not json_path:
        logger.info("No file selected.")
        return
    window("Sandustry Save Visualizer", Map(json_path)).render()


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level=config.log_level)
    main()
