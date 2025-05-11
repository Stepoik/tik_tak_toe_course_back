from sqlalchemy import desc
from sqlalchemy.orm import Session
from models import PlayerStats
from typing import List

LEADERBOARD_PAGING_LIMIT = 50


class PlayerStatsService:
    def __init__(self, db: Session):
        self.db = db

    def record_win(self, player_id: str):
        stats = self.db.query(PlayerStats).filter(PlayerStats.player_id == player_id).first()
        if stats:
            stats.wins += 1
        else:
            stats = PlayerStats(player_id=player_id, wins=1)
            self.db.add(stats)
        self.db.commit()

    def get_wins(self, player_id: str) -> int:
        stats = self.db.query(PlayerStats).filter(PlayerStats.player_id == player_id).first()
        return stats.wins if stats else 0

    def get_leaderboard(self, offset: int) -> List[PlayerStats]:
        stats = self.db.query(PlayerStats)\
            .order_by(desc(PlayerStats.wins))\
            .offset(offset)\
            .limit(LEADERBOARD_PAGING_LIMIT)\
            .all()
        return stats
