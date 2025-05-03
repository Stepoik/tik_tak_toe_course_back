from typing import Dict, Optional
from uuid import uuid4

from services.game import Game, PlayerStatus
from services.stats_service import PlayerStatsService


class GameService:
    def __init__(self, stats_service: PlayerStatsService):
        self.games: Dict[str, Game] = {}
        self.stats_service = stats_service

    def create_game(self) -> str:
        game_id = str(uuid4())
        self.games[game_id] = Game(game_id, self.stats_service)
        return game_id

    def get_game(self, game_id: str) -> Optional[Game]:
        return self.games.get(game_id)

    def get_open_lobbies(self) -> list:
        open_games = []
        for game_id, game in self.games.items():
            if not game.started:
                players = game.players.values()
                if len(players) < 2:
                    open_games.append({
                        "game_id": game_id,
                        "players": [p.id for p in players],
                        "ready": [p.status == PlayerStatus.READY for p in players],
                        "player_count": len(players)
                    })
        return open_games
