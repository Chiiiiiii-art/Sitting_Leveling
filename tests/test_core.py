"""Unit tests for Sitting Leveling core game logic and geometry calculations."""

import math
from types import SimpleNamespace
import unittest

from rpg_system import CALORIES_PER_KG_FAT, RPGSystem
from vision_engine import MissionType, VisionEvent, VisionResult, calculate_angle


class TestRPGSystem(unittest.TestCase):
    """Test suite for RPG progression rules and health mechanics."""

    def test_initialization(self) -> None:
        rpg = RPGSystem(target_weight_loss_kg=2.0, base_muscle_mass_kg=10.0)
        self.assertEqual(rpg.max_hp, int(2.0 * CALORIES_PER_KG_FAT))
        self.assertEqual(rpg.current_hp, rpg.max_hp)
        self.assertEqual(rpg.armor, 0)
        self.assertEqual(rpg.coins, 0)
        self.assertAlmostEqual(rpg.damage_multiplier, 1.2)

    def test_invalid_initialization(self) -> None:
        with self.assertRaises(ValueError):
            RPGSystem(target_weight_loss_kg=0)
        with self.assertRaises(ValueError):
            RPGSystem(target_weight_loss_kg=1.0, base_muscle_mass_kg=-1.0)

    def test_add_armor(self) -> None:
        rpg = RPGSystem(target_weight_loss_kg=1.0)
        rpg.add_armor_from_food(300)
        self.assertEqual(rpg.armor, 300)
        with self.assertRaises(ValueError):
            rpg.add_armor_from_food(-50)

    def test_damage_absorption(self) -> None:
        rpg = RPGSystem(target_weight_loss_kg=1.0)
        initial_hp = rpg.current_hp

        # Add 100 armor and deal 60 damage -> armor becomes 40, HP untouched
        rpg.add_armor_from_food(100)
        damage = rpg.process_action_success(base_calories_burned=60, coin_reward=10)
        self.assertEqual(damage, 60)
        self.assertEqual(rpg.armor, 40)
        self.assertEqual(rpg.current_hp, initial_hp)
        self.assertEqual(rpg.coins, 10)

        # Deal another 60 damage -> breaks 40 armor, 20 damage penetrates to HP
        rpg.process_action_success(base_calories_burned=60, coin_reward=5)
        self.assertEqual(rpg.armor, 0)
        self.assertEqual(rpg.current_hp, initial_hp - 20)
        self.assertEqual(rpg.coins, 15)


class TestGeometry(unittest.TestCase):
    """Test suite for coordinate math and angle computation."""

    def test_right_angle(self) -> None:
        a = SimpleNamespace(x=0.0, y=1.0)
        b = SimpleNamespace(x=0.0, y=0.0)
        c = SimpleNamespace(x=1.0, y=0.0)
        angle = calculate_angle(a, b, c)
        self.assertIsNotNone(angle)
        self.assertAlmostEqual(angle, 90.0, places=3)

    def test_straight_line(self) -> None:
        a = SimpleNamespace(x=-1.0, y=0.0)
        b = SimpleNamespace(x=0.0, y=0.0)
        c = SimpleNamespace(x=1.0, y=0.0)
        angle = calculate_angle(a, b, c)
        self.assertIsNotNone(angle)
        self.assertAlmostEqual(angle, 180.0, places=3)

    def test_coincident_points(self) -> None:
        a = SimpleNamespace(x=0.0, y=0.0)
        b = SimpleNamespace(x=0.0, y=0.0)
        c = SimpleNamespace(x=1.0, y=0.0)
        self.assertIsNone(calculate_angle(a, b, c))


class TestVisionResult(unittest.TestCase):
    """Test suite for VisionResult structure and backward-compatible indexing."""

    def test_result_indexing(self) -> None:
        res = VisionResult(
            mission=MissionType.HEAD,
            status_text="Holding",
            event=VisionEvent.ACTION_SUCCESS,
            progress="1/3",
        )
        self.assertEqual(res["mission"], "HEAD")
        self.assertEqual(res["status_text"], "Holding")
        self.assertEqual(res["event"], "ACTION_SUCCESS")
        self.assertEqual(res["progress"], "1/3")


if __name__ == "__main__":
    unittest.main()
