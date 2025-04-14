"""
Simulación de Torneo de Fútbol - Modelo Completo

Supuestos:
1. Distribución de Poisson para goles con λ basado en fuerza ofensiva/defensiva
2. Bonificaciones tácticas: +10% ataque (Counterattack), +10% defensa (High Press)
3. Penales determinados por habilidad específica (penalty_skill)
4. Fatiga acumulativa (máx 30%) y lesiones (-5% por jugador)
5. Consistencia afecta variabilidad en rendimiento (0.7-1.0)
"""

import numpy as np
from simpy import Environment

class Team:
    def __init__(self, name, base_strength):
        self.name = name
        self.base_strength = base_strength
        self.attack_strength = np.clip(base_strength + np.random.randint(-10, 10), 50, 100)
        self.defense_strength = np.clip(base_strength + np.random.randint(-10, 10), 50, 100)
        self.consistency = np.random.uniform(0.7, 1.0)
        self.play_style = np.random.choice(["Possession", "Counterattack", "High Press"])
        self.penalty_skill = np.random.randint(50, 100)
        self.fatigue = 0.0
        self.injuries = 0
        self.points = 0
        self.goals_for = 0
        self.goals_against = 0
        self.stage_reached = "Group"
        self.group = None

    def adjusted_attack(self):
        injury_penalty = 0.05 * self.injuries
        adjusted = self.attack_strength * (1 - injury_penalty - self.fatigue)
        
        if self.play_style == "Counterattack":
            adjusted *= 1.1
        elif self.play_style == "Possession":
            adjusted *= 0.9  # -10% ataque por estilo conservador
        
        return adjusted * self.consistency

    def adjusted_defense(self):
        injury_penalty = 0.05 * self.injuries
        adjusted = self.defense_strength * (1 - injury_penalty - self.fatigue)
        if self.play_style == "High Press":
            adjusted *= 1.25
        return adjusted * self.consistency

class MatchRecord:
    def __init__(self, team_a, team_b, stage):
        self.team_a = team_a.name
        self.team_b = team_b.name
        self.style_a = team_a.play_style
        self.style_b = team_b.play_style
        self.goals_a = 0
        self.goals_b = 0
        self.stage = stage

class PenaltyRecord:
    def __init__(self, team_a, team_b, winner):
        self.team_a = team_a.name
        self.team_b = team_b.name
        self.skill_a = team_a.penalty_skill
        self.skill_b = team_b.penalty_skill
        self.winner = winner.name

class SimulationResult:
    def __init__(self):
        self.match_data = []
        self.penalty_data = []
        self.team_records = []
        self.tournament_winners = []

class Tournament:
    def __init__(self, teams, group_size=4, injury_prob=0.05, fatigue_effect=0.02):
        self.env = Environment()
        self.teams = teams
        self.group_size = group_size
        self.injury_prob = injury_prob
        self.fatigue_effect = fatigue_effect
        self.groups = []
        self.champion = None
        self.sim_result = SimulationResult()

    def _generate_groups(self):
        np.random.shuffle(self.teams)
        group_num = 1
        self.groups = []
        for i in range(0, len(self.teams), self.group_size):
            group = self.teams[i:i+self.group_size]
            for team in group:
                team.group = group_num
            self.groups.append(group)
            group_num += 1

    def _update_fatigue(self, team):
        team.fatigue += self.fatigue_effect
        team.fatigue = min(team.fatigue, 0.3)

    def _simulate_injuries(self, team):
        if np.random.rand() < self.injury_prob:
            team.injuries += 1

    def simulate_match(self, team_a, team_b, is_knockout=False):
        attack_a = team_a.adjusted_attack()
        defense_b = team_b.adjusted_defense()
        attack_b = team_b.adjusted_attack()
        defense_a = team_a.adjusted_defense()
        
        lambda_a = 2.5 * (attack_a / (attack_a + defense_b))
        lambda_b = 2.5 * (attack_b / (attack_b + defense_a))
        
        goals_a = np.random.poisson(lambda_a)
        goals_b = np.random.poisson(lambda_b)
        
        team_a.goals_for += goals_a
        team_a.goals_against += goals_b
        team_b.goals_for += goals_b
        team_b.goals_against += goals_a

        match_record = MatchRecord(team_a, team_b, "Knockout" if is_knockout else "Group")
        match_record.goals_a = goals_a
        match_record.goals_b = goals_b
        self.sim_result.match_data.append(match_record)

        winner = None

        if goals_a > goals_b:
            team_a.points += 3
            winner = team_a
        elif goals_b > goals_a:
            team_b.points += 3
            winner = team_b
        else:
            team_a.points += 1
            team_b.points += 1
            if is_knockout:
                prob_a = self.calculate_penalty_prob(team_a.penalty_skill, team_b.penalty_skill)
                winner = team_a if np.random.rand() < prob_a else team_b
                penalty_record = PenaltyRecord(team_a, team_b, winner)
                self.sim_result.penalty_data.append(penalty_record)

        for team in [team_a, team_b]:
            self._update_fatigue(team)
            self._simulate_injuries(team)

        return winner

    def calculate_penalty_prob(self, skill_a, skill_b):
        # Escala la diferencia de habilidad (mayor peso a valores altos)
        diff = (skill_a - skill_b) / 20  # Normaliza la diferencia (ej: 90-70 = 1.0)
        return 1 / (1 + np.exp(-diff))

    def group_stage(self):
        self._generate_groups()
        for group in self.groups:
            for i in range(len(group)):
                for j in range(i+1, len(group)):
                    self.simulate_match(group[i], group[j])

    def knockout_stage(self, teams):
        stage_names = {8: "Quarter-finals", 4: "Semi-finals", 2: "Final"}
        while len(teams) > 1:
            current_stage = stage_names.get(len(teams), f"Round of {len(teams)}")
            winners = []
            np.random.shuffle(teams)
            for i in range(0, len(teams), 2):
                team_a = teams[i]
                team_b = teams[i+1]
                winner = self.simulate_match(team_a, team_b, is_knockout=True)
                loser = team_b if winner == team_a else team_a
                loser.stage_reached = current_stage
                winners.append(winner)
            teams = winners
        if teams:
            teams[0].stage_reached = "Champion"
            self.champion = teams[0]

    def run(self):
        self.group_stage()
        advancing = []
        for group in self.groups:
            group.sort(key=lambda x: (-x.points, -(x.goals_for - x.goals_against)))
            advancing.extend(group[:2])
        self.knockout_stage(advancing)
        self.sim_result.team_records = self.teams
        self.sim_result.tournament_winners.append(self.champion)