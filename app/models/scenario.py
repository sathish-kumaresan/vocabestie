from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class Scenario(Base):
    """A scenario groups related words by real-world situation.

    Examples: "At the Office", "At the Doctor", "Shopping"
    """

    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    icon = Column(String(10), nullable=True)  # emoji
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)  # "Daily Life", "Work", "Travel", etc.
    difficulty_level = Column(String(5), nullable=True)  # A1, A2, B1, B2, C1, C2
    word_count = Column(Integer, default=0)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    words = relationship("Word", back_populates="scenario")
