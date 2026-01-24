from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Word, ReviewCard
from app.schemas import WordCreate, WordUpdate, WordResponse

router = APIRouter(prefix="/api/words", tags=["words"])


@router.get("", response_model=List[WordResponse])
def get_words(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    words = db.query(Word).offset(skip).limit(limit).all()
    return words


@router.get("/{word_id}", response_model=WordResponse)
def get_word(word_id: int, db: Session = Depends(get_db)):
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    return word


@router.post("", response_model=WordResponse, status_code=201)
def create_word(word: WordCreate, db: Session = Depends(get_db)):
    db_word = Word(
        term=word.term,
        definition=word.definition,
        example=word.example,
    )
    db.add(db_word)
    db.commit()
    db.refresh(db_word)

    # Create review card for the word
    review_card = ReviewCard(word_id=db_word.id)
    db.add(review_card)
    db.commit()
    db.refresh(db_word)

    return db_word


@router.put("/{word_id}", response_model=WordResponse)
def update_word(word_id: int, word: WordUpdate, db: Session = Depends(get_db)):
    db_word = db.query(Word).filter(Word.id == word_id).first()
    if not db_word:
        raise HTTPException(status_code=404, detail="Word not found")

    update_data = word.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_word, field, value)

    db.commit()
    db.refresh(db_word)
    return db_word


@router.delete("/{word_id}", status_code=204)
def delete_word(word_id: int, db: Session = Depends(get_db)):
    db_word = db.query(Word).filter(Word.id == word_id).first()
    if not db_word:
        raise HTTPException(status_code=404, detail="Word not found")

    db.delete(db_word)
    db.commit()
    return None
