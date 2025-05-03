from sqlalchemy import Column, String, Integer
from database import Base

class PlayerStats(Base):
    __tablename__ = "player_stats"

    player_id = Column(String, primary_key=True, index=True)
    wins = Column(Integer, default=0)