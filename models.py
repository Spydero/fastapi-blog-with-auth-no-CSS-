from datetime import datetime, timezone 

from sqlalchemy import String, DateTime, Text, ForeignKey  
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base 

class User(Base):
  __tablename__ = "users"
  
  id: Mapped[int] = mapped_column(primary_key=True)
  username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
  hashed_password: Mapped[str] = mapped_column(String(255))
  role: Mapped[str] = mapped_column(String(20), default="user") # "user" or "admin"
  created_at: Mapped[datetime] = mapped_column(
    DateTime, default=lambda: datetime.now(timezone.utc))
  
  
  
class Session(Base):
  __tablename__ = "sessions"
  
  # The token itself is primary key -- this is the (coat-check)
  id: Mapped[str] = mapped_column(String(64), primary_key=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
  created_at: Mapped[datetime] = mapped_column(
    DateTime, default=lambda: datetime.now(timezone.utc)
  )
  
  # This lets us write `session.user` in Python and get User object
  # instead of manually looking up by user_id every time.
  user: Mapped["User"] = relationship()
  
  

  
class Category(Base):
  __tablename__ = "categories"
  
  id: Mapped[int] = mapped_column(primary_key=True)
  name: Mapped[str] = mapped_column(String(50), unique=True)
  
  
  
class Post(Base):
  __tablename__ = "posts"
  
  id: Mapped[int] = mapped_column(primary_key=True)
  title: Mapped[str] = mapped_column(String(200))
  content: Mapped[str] = mapped_column(Text)
  created_at: Mapped[datetime] = mapped_column(
    DateTime, default=lambda: datetime.now(timezone.utc)
  )
  
  author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
  category_id: Mapped[int] = mapped_column(ForeignKey("categories.id")) 
  
  author: Mapped["User"] = relationship()
  category: Mapped["Category"] = relationship()
  comments: Mapped[list["Comment"]] = relationship(order_by="Comment.created_at")
  

class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    author: Mapped["User"] = relationship()  

  
  
  
