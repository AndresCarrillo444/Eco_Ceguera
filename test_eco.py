import unittest
import math
import os
import json

# Import functions from eco-ceguera
import importlib.util
spec = importlib.util.spec_from_file_location("eco", "eco-ceguera.py")
eco = importlib.util.module_from_spec(spec)
# We mock pygame before loading the module to avoid requiring a display
import pygame
pygame.init()
pygame.display.set_mode((100, 100), pygame.HIDDEN)
try:
    spec.loader.exec_module(eco)
except Exception as e:
    pass # Catch exceptions during load, we just need the functions

from eco_features import lb_is_record
from eco_settings import custom_level_save, custom_level_load, CUSTOM_LEVELS_DIR
from eco_online_lb import _safe_key

class TestEcoCeguera(unittest.TestCase):

    def test_dist(self):
        """Test the distance function"""
        self.assertEqual(eco.dist((0, 0), (3, 4)), 5.0)
        self.assertEqual(eco.dist((10, 10), (10, 10)), 0.0)

    def test_normalize(self):
        """Test vector normalization"""
        self.assertEqual(eco.normalize(0, 0), (0, 0))
        nx, ny = eco.normalize(3, 4)
        self.assertAlmostEqual(nx, 0.6)
        self.assertAlmostEqual(ny, 0.8)

    def test_lerp_color(self):
        """Test color interpolation"""
        c1 = (0, 0, 0)
        c2 = (100, 100, 100)
        self.assertEqual(eco.lerp_color(c1, c2, 0.5), (50, 50, 50))
        self.assertEqual(eco.lerp_color(c1, c2, 1.0), (100, 100, 100))

    def test_astar_pathfinding(self):
        """Test the A* pathfinding algorithm"""
        # 0 is walkable, 1 is wall
        wall_grid = [
            [0, 0, 0],
            [0, 1, 0],
            [0, 0, 0]
        ]
        start = (0, 0)
        goal = (2, 2)
        path = eco.astar(wall_grid, start, goal)
        self.assertTrue(len(path) > 0)
        self.assertEqual(path[-1], goal)

        # Unreachable goal
        wall_grid_blocked = [
            [0, 1, 0],
            [1, 1, 1],
            [0, 1, 0]
        ]
        path_blocked = eco.astar(wall_grid_blocked, start, goal)
        self.assertEqual(path_blocked, [])

    def test_safe_key(self):
        """Test Firebase key sanitization"""
        self.assertEqual(_safe_key("Player 1"), "Player 1")
        self.assertEqual(_safe_key("Bad.Key#$[]/Name"), "Bad_Key_____Name")
        self.assertEqual(_safe_key(""), "anon")

    def test_custom_level_io(self):
        """Test saving and loading custom levels"""
        test_name = "test_level_999"
        grid = [["#", "."], [".", "E"]]
        
        # Save
        custom_level_save(test_name, grid)
        
        # Load
        loaded_grid = custom_level_load(test_name)
        self.assertEqual(loaded_grid, grid)
        
        # Cleanup
        file_path = os.path.join(CUSTOM_LEVELS_DIR, f"{test_name}.json")
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == '__main__':
    unittest.main()
