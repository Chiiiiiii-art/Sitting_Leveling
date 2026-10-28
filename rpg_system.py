class RPGSystem:
    def __init__(self, target_weight_loss_kg=1.0, base_muscle_mass_kg=0.0):
        # 目標體重換算總血量 (1公斤 = 7700大卡)
        self.max_hp = int(target_weight_loss_kg * 7700)
        self.current_hp = self.max_hp
        
        # 初始護甲與金幣
        self.armor = 0
        self.coins = 0
        
        # 肌肉量換算傷害加成 (每1公斤多2%加成)
        self.damage_multiplier = 1.0 + (base_muscle_mass_kg * 0.02)

    def add_armor_from_food(self, calories):
        # 將攝取熱量轉化為魔王護甲
        self.armor += calories

    def process_action_success(self, base_calories_burned=10, coin_reward=5):
        # 計算實際傷害並給予金幣獎勵
        actual_damage = int(base_calories_burned * self.damage_multiplier)
        self._apply_damage(actual_damage)
        self.coins += coin_reward
        return actual_damage

    def _apply_damage(self, damage):
        # 優先扣除護甲，若護甲歸零則扣除真實血量
        if self.armor > 0:
            if damage >= self.armor:
                remaining_damage = damage - self.armor
                self.armor = 0
                self.current_hp -= remaining_damage
            else:
                self.armor -= damage
        else:
            self.current_hp -= damage
            
        # 防止血量低於0
        if self.current_hp < 0:
            self.current_hp = 0