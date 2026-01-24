from datetime import date, datetime, timedelta
from app.models.word import ReviewCard


class SpacedRepetitionService:
    """
    SM-2 Spaced Repetition Algorithm Implementation.

    Quality ratings:
    0 - Complete blackout
    1 - Incorrect, but upon seeing correct answer, remembered
    2 - Incorrect, but correct answer seemed easy to recall
    3 - Correct with serious difficulty
    4 - Correct with some hesitation
    5 - Perfect response
    """

    MIN_EASE_FACTOR = 1.3

    @staticmethod
    def calculate_next_review(card: ReviewCard, quality: int) -> tuple[float, int, int, date]:
        """
        Calculate the next review parameters based on quality rating.

        Args:
            card: The current review card
            quality: Rating from 0-5

        Returns:
            Tuple of (ease_factor, interval, repetitions, next_review_date)
        """
        quality = max(0, min(5, quality))  # Clamp to 0-5

        ease_factor = card.ease_factor
        interval = card.interval
        repetitions = card.repetitions

        if quality < 3:
            # Failed - reset repetitions but keep ease factor
            repetitions = 0
            interval = 1
        else:
            # Successful recall
            if repetitions == 0:
                interval = 1
            elif repetitions == 1:
                interval = 6
            else:
                interval = round(interval * ease_factor)

            repetitions += 1

        # Update ease factor
        ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        ease_factor = max(SpacedRepetitionService.MIN_EASE_FACTOR, ease_factor)

        next_review = date.today() + timedelta(days=interval)

        return ease_factor, interval, repetitions, next_review

    @staticmethod
    def update_card(card: ReviewCard, quality: int) -> ReviewCard:
        """
        Update a review card with new SM-2 values.

        Args:
            card: The review card to update
            quality: Rating from 0-5

        Returns:
            The updated review card
        """
        ease_factor, interval, repetitions, next_review = (
            SpacedRepetitionService.calculate_next_review(card, quality)
        )

        card.ease_factor = ease_factor
        card.interval = interval
        card.repetitions = repetitions
        card.next_review = next_review
        card.last_reviewed = datetime.utcnow()

        return card

    @staticmethod
    def get_quality_from_quiz(correct: bool, hesitation: bool = False) -> int:
        """
        Convert quiz result to SM-2 quality rating.

        Args:
            correct: Whether the answer was correct
            hesitation: Whether there was hesitation

        Returns:
            Quality rating from 0-5
        """
        if not correct:
            return 1  # Incorrect but will show correct answer
        elif hesitation:
            return 4  # Correct with hesitation
        else:
            return 5  # Perfect response
