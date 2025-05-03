from enum import Enum
from typing import Optional, Dict

from sqlalchemy.orm import Session
from starlette.websockets import WebSocket

from services.stats_service import PlayerStatsService


class PlayerStatus(str, Enum):
    CONNECTED = "connected"
    READY = "ready"
    DISCONNECTED = "disconnected"


class Player:
    def __init__(self, player_id: str, websocket: WebSocket):
        self.id = player_id
        self.websocket = websocket
        self.status = PlayerStatus.CONNECTED


class Game:
    def __init__(self, game_id: str, stats_service: PlayerStatsService):
        self.id = game_id
        self.players: Dict[str, Player] = {}
        self.board = [["" for _ in range(3)] for _ in range(3)]
        self.turn: Optional[str] = None
        self.started = False
        self.stats_service = stats_service

    async def connect_player(self, player_id: str, websocket: WebSocket):
        await websocket.accept()
        if player_id in self.players and self.started:
            player_type = ""
            try:
                if list(self.players.keys())[0] == player_id:
                    player_type = "X"
                elif list(self.players.keys())[1] == player_id:
                    player_type = "O"
            except Exception as e:
                print(e)
            await websocket.send_json({
                "type": "game_start",
                "data": {"this_player": player_type}
            })
            await websocket.send_json(self.get_game_update())
        self.players[player_id] = Player(player_id, websocket)
        await self.broadcast({
            "type": "player_joined",
            "data": {"player_id": player_id}
        })
        await self.check_start()

    async def set_ready(self, player_id: str):
        print(f"Player ready: {player_id}")
        player = self.players.get(player_id)
        if player:
            player.status = PlayerStatus.READY
            await self.broadcast({
                "type": "player_ready",
                "data": {"player_id": player_id}
            })
            await self.check_start()

    async def check_start(self):
        if len(self.players) == 2 and all(p.status == PlayerStatus.READY for p in self.players.values()):
            self.started = True
            self.turn = "X"
            self.board = [["" for _ in range(3)] for _ in range(3)]
            for index, player_token in enumerate(self.players.keys()):
                player = self.players[player_token]
                player_type = ""
                if index == 0:
                    player_type = "X"
                elif index == 1:
                    player_type = "O"
                await player.websocket.send_json({
                    "type": "game_start",
                    "data": {"this_player": player_type}
                })

    async def handle_message(self, player_id: str, message: dict, db: Session):
        if message["type"] == "ready":
            await self.set_ready(player_id)
        elif message["type"] == "move" and self.started:
            row, col = message["data"]["row"], message["data"]["col"]
            symbol = "X" if player_id == list(self.players.keys())[0] else "O"
            if self.turn == symbol and self.board[row][col] == "":
                symbol = "X" if player_id == list(self.players.keys())[0] else "O"
                self.board[row][col] = symbol

                winner = self.check_winner()
                if winner:
                    await self.broadcast(self.get_game_update())
                    await self.broadcast({
                        "type": "game_over",
                        "data": {"winner": winner}
                    })
                    players = list(self.players.keys())
                    winner_player = players[0] if winner == "X" else players[1]
                    self.stats_service.record_win(winner_player)
                    self.started = False
                elif self.is_draw():
                    await self.broadcast(self.get_game_update())
                    await self.broadcast({
                        "type": "game_over",
                        "data": {"winner": None}
                    })
                    self.started = False
                else:
                    self.turn = "O" if self.turn == "X" else "X"
                    await self.broadcast(self.get_game_update())

    def check_winner(self) -> Optional[str]:
        lines = self.board + list(map(list, zip(*self.board)))  # rows + cols
        lines += [[self.board[i][i] for i in range(3)], [self.board[i][2 - i] for i in range(3)]]  # diagonals

        for line in lines:
            if line[0] != "" and line.count(line[0]) == 3:
                symbol = line[0]
                for pid, player in self.players.items():
                    expected_symbol = "X" if pid == list(self.players.keys())[0] else "O"
                    if symbol == expected_symbol:
                        return symbol
        return None

    def is_draw(self) -> bool:
        return all(cell != "" for row in self.board for cell in row)

    def get_game_update(self) -> dict:
        return {
            "type": "game_update",
            "data": {"board": self.board, "turn": self.turn}
        }

    async def broadcast(self, event: dict):
        for player in self.players.values():
            try:
                await player.websocket.send_json(event)
            except Exception as e:
                print(f"Error sending to player {player.id}: {e}")