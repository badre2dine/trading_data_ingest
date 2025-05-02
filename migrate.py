from app.models import Base
from app.db import engine

Base.metadata.create_all(bind=engine)
