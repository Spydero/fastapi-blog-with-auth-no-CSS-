from sqlalchemy import create_engine 
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "sqlite:///./blog.db"

engine = create_engine(
  DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
  pass


def get_db():
  """
  FastAPI Dependency -> opens a DB session for a single request, hands it to route function, then closes it afterward -> even if the route raised an error.
  """
  
  db = SessionLocal()
  
  try:
    yield db
  finally:
    db.close()
  
  
  
  



