from fastapi import FastAPI, WebSocket, Depends
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect

from database import SessionLocal, engine
from models import Base
from services.game import PlayerStatus
from services.game_service import GameService
from services.stats_service import PlayerStatsService

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()
stats_service = PlayerStatsService(SessionLocal())
game_service = GameService(stats_service)


@app.post("/create_game")
def create_game():
    return {"game_id": game_service.create_game()}


@app.get("/stats/{player_id}")
def get_stats(player_id: str, db: Session = Depends(get_db)):
    stats_service = PlayerStatsService(db)
    return {"player_id": player_id, "wins": stats_service.get_wins(player_id)}


@app.get("/lobbies")
def list_open_lobbies():
    return game_service.get_open_lobbies()


@app.websocket("/ws/{game_id}/{player_id}")
async def websocket_endpoint(
        websocket: WebSocket,
        game_id: str,
        player_id: str,
        db: Session = Depends(get_db)
):
    game = game_service.get_game(game_id)
    if not game:
        await websocket.close(code=1000)
        return

    await game.connect_player(player_id, websocket)

    try:
        while True:
            message = await websocket.receive_json()
            await game.handle_message(player_id, message, db)
    except WebSocketDisconnect:
        if player_id in game.players:
            game.players[player_id].status = PlayerStatus.DISCONNECTED
            await game.broadcast({
                "type": "player_disconnected",
                "data": {"player_id": player_id}
            })
