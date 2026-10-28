"""RPG game mechanics system for Sitting Leveling."""

from typing import Any, Dict

CALORIES_PER_KG_FAT = 7700
DEFAULT_ACTION_CALORIES = 10
DEFAULT_COIN_REWARD = 5
DEFAULT_MUSCLE_BONUS_PER_KG = 0.02


class RPGSystem:
    """Manages boss health, shield/armor, and player progression rewards."""

    def __init__(
        self,
        target_weight_loss_kg: float = 1.0,
        base_muscle_mass_kg: float = 0.0,
    ) -> None:
        """Initialize RPG state based on physical targets.

        Args:
            target_weight_loss_kg: Target weight reduction in kg (7700 kcal per kg).
            base_muscle_mass_kg: Base muscle mass giving +2% damage multiplier per kg.
        """
        if target_weight_loss_kg <= 0:
            raise ValueError("target_weight_loss_kg must be greater than 0")
        if base_muscle_mass_kg < 0:
            raise ValueError("base_muscle_mass_kg cannot be negative")

        self.max_hp: int = int(target_weight_loss_kg * CALORIES_PER_KG_FAT)
        self.current_hp: int = self.max_hp
        self.armor: int = 0
        self.coins: int = 0
        self.damage_multiplier: float = 1.0 + (base_muscle_mass_kg * DEFAULT_MUSCLE_BONUS_PER_KG)

    def add_armor_from_food(self, calories: int) -> None:
        """Convert consumed food calories into boss armor.

        Args:
            calories: Intake calories added as armor.
        """
        if calories < 0:
            raise ValueError("calories cannot be negative")
        self.armor += calories

    def process_action_success(
        self,
        base_calories_burned: int = DEFAULT_ACTION_CALORIES,
        coin_reward: int = DEFAULT_COIN_REWARD,
    ) -> int:
        """Calculate dealt damage, apply to boss, and grant coins.

        Args:
            base_calories_burned: Base calories burned for a single repetition.
            coin_reward: Coin reward for successful action.

        Returns:
            The actual damage dealt to the boss after multiplier.
        """
        if base_calories_burned < 0 or coin_reward < 0:
            raise ValueError("rewards and calories burned must be non-negative")

        actual_damage = int(base_calories_burned * self.damage_multiplier)
        self._apply_damage(actual_damage)
        self.coins += coin_reward
        return actual_damage

    def _apply_damage(self, damage: int) -> None:
        """Deduct damage first from armor, then from current HP.

        Args:
            damage: Total damage points to apply.
        """
        if damage <= 0:
            return

        if self.armor > 0:
            if damage >= self.armor:
                remaining_damage = damage - self.armor
                self.armor = 0
                self.current_hp = max(0, self.current_hp - remaining_damage)
            else:
                self.armor -= damage
        else:
            self.current_hp = max(0, self.current_hp - damage)

    def get_stats(self) -> Dict[str, Any]:
        """Return a snapshot of current RPG system statistics."""
        return {
            "current_hp": self.current_hp,
            "max_hp": self.max_hp,
            "armor": self.armor,
            "coins": self.coins,
            "damage_multiplier": self.damage_multiplier,
            "is_defeated": self.current_hp == 0,
        }