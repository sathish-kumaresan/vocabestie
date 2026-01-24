from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, Date, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class QuizType(enum.Enum):
    multiple_choice = "multiple_choice"
    fill_blank = "fill_blank"


class Word(Base):
    __tablename__ = "words"

    id = Column(Integer, primary_key=True, index=True)
    term = Column(String(255), nullable=False, index=True)
    definition = Column(Text, nullable=False)
    example = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    review_card = relationship("ReviewCard", back_populates="word", uselist=False, cascade="all, delete-orphan")
    quiz_attempts = relationship("QuizAttempt", back_populates="word", cascade="all, delete-orphan")


class ReviewCard(Base):
    __tablename__ = "review_cards"

    id = Column(Integer, primary_key=True, index=True)
    word_id = Column(Integer, ForeignKey("words.id"), unique=True, nullable=False)
    ease_factor = Column(Float, default=2.5)
    interval = Column(Integer, default=0)  # days
    repetitions = Column(Integer, default=0)
    next_review = Column(Date, default=date.today)
    last_reviewed = Column(DateTime, nullable=True)

    word = relationship("Word", back_populates="review_card")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    correct = Column(Boolean, nullable=False)
    quiz_type = Column(Enum(QuizType), nullable=False)
    attempted_at = Column(DateTime, default=datetime.utcnow)

    word = relationship("Word", back_populates="quiz_attempts")
