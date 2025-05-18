from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()


class TaskLog(Base):
    __tablename__ = "task_logs"

    task_id = Column(String, primary_key=True, index=True)
    symbol = Column(String)
    year = Column(Integer)
    month = Column(Integer)
    status = Column(String)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)

    def to_dict(self):
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }


class PairStreamerStatus(Base):
    __tablename__ = "pair_streamer_status"

    id = Column(Integer, primary_key=True, index=True)
    pair = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, nullable=False)  # "activate" ou "deactivate"
    updated_at = Column(
        DateTime, default=datetime.datetime.now(), onupdate=datetime.datetime.now()
    )
