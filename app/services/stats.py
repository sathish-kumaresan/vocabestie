"""
Statistics service for tracking streaks, time, and progress.
"""

from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    User, Word, Scenario, WordSkillMastery, UserWordStatus,
    UserStats, DailyPracticeLog
)
from app.services.mastery import PASS_THRESHOLD, SKILL_TYPES, get_word_mastery

# Guest user ID for unauthenticated users
GUEST_USER_ID = 1


def get_or_create_user_stats(db: Session, user_id: int = GUEST_USER_ID) -> UserStats:
    """Get or create user stats record."""
    stats = db.query(UserStats).filter(UserStats.user_id == user_id).first()
    if not stats:
        stats = UserStats(user_id=user_id)
        db.add(stats)
        db.commit()
        db.refresh(stats)
    return stats


def get_or_create_daily_log(
    db: Session,
    user_id: int = GUEST_USER_ID,
    practice_date: date = None
) -> DailyPracticeLog:
    """Get or create daily practice log for a date."""
    if practice_date is None:
        practice_date = date.today()

    log = db.query(DailyPracticeLog).filter(
        DailyPracticeLog.user_id == user_id,
        DailyPracticeLog.practice_date == practice_date
    ).first()

    if not log:
        log = DailyPracticeLog(
            user_id=user_id,
            practice_date=practice_date
        )
        db.add(log)
        db.commit()
        db.refresh(log)
    return log


def update_streak(db: Session, user_id: int = GUEST_USER_ID) -> int:
    """
    Update user's streak based on practice activity.
    Returns the current streak count.
    """
    stats = get_or_create_user_stats(db, user_id)
    today = date.today()

    if stats.last_practice_date is None:
        # First practice ever
        stats.current_streak = 1
        stats.longest_streak = 1
    elif stats.last_practice_date == today:
        # Already practiced today, streak unchanged
        pass
    elif stats.last_practice_date == today - timedelta(days=1):
        # Practiced yesterday, increment streak
        stats.current_streak += 1
        if stats.current_streak > stats.longest_streak:
            stats.longest_streak = stats.current_streak
    else:
        # Missed a day, reset streak
        stats.current_streak = 1

    stats.last_practice_date = today
    stats.updated_at = datetime.utcnow()
    db.commit()

    return stats.current_streak


def record_session_completion(
    db: Session,
    user_id: int = GUEST_USER_ID,
    words_practiced: int = 0,
    exercises_completed: int = 0,
    time_seconds: int = 0,
) -> Dict[str, Any]:
    """
    Record a completed learning session.
    Updates daily log, streak, and overall stats.
    """
    today = date.today()

    # Update daily log
    daily_log = get_or_create_daily_log(db, user_id, today)
    daily_log.words_practiced += words_practiced
    daily_log.exercises_completed += exercises_completed
    daily_log.practice_time_seconds += time_seconds

    # Update streak
    current_streak = update_streak(db, user_id)

    # Update overall stats
    stats = get_or_create_user_stats(db, user_id)
    stats.total_practice_time_seconds += time_seconds

    # Count total mastered words
    stats.total_words_mastered = count_mastered_words(db, user_id)

    db.commit()

    return {
        "current_streak": current_streak,
        "longest_streak": stats.longest_streak,
        "words_practiced_today": daily_log.words_practiced,
        "exercises_completed_today": daily_log.exercises_completed,
        "time_today_seconds": daily_log.practice_time_seconds,
    }


def count_mastered_words(db: Session, user_id: int = GUEST_USER_ID) -> int:
    """Count words where all 4 skills are at or above pass threshold."""
    # Get all words with their skill masteries
    masteries = db.query(
        WordSkillMastery.word_id,
        func.count(WordSkillMastery.skill_type).label('skill_count'),
        func.min(WordSkillMastery.mastery_score).label('min_score')
    ).filter(
        WordSkillMastery.user_id == user_id,
        WordSkillMastery.mastery_score >= PASS_THRESHOLD
    ).group_by(WordSkillMastery.word_id).all()

    # Word is mastered if all 4 skills are passed
    mastered_count = sum(1 for m in masteries if m.skill_count == 4)
    return mastered_count


def get_user_statistics(db: Session, user_id: int = GUEST_USER_ID) -> Dict[str, Any]:
    """Get comprehensive user statistics for display."""
    stats = get_or_create_user_stats(db, user_id)
    today = date.today()

    # Get today's practice log
    daily_log = db.query(DailyPracticeLog).filter(
        DailyPracticeLog.user_id == user_id,
        DailyPracticeLog.practice_date == today
    ).first()

    # Count words by status
    total_words = db.query(func.count(Word.id)).scalar() or 0

    # Count words with any practice
    words_started = db.query(func.count(func.distinct(WordSkillMastery.word_id))).filter(
        WordSkillMastery.user_id == user_id
    ).scalar() or 0

    # Count mastered words
    mastered_words = count_mastered_words(db, user_id)

    # Count "already known" words
    already_known = db.query(func.count(UserWordStatus.id)).filter(
        UserWordStatus.user_id == user_id,
        UserWordStatus.status == 'already_known'
    ).scalar() or 0

    # Total exercises completed (sum from all daily logs)
    total_exercises = db.query(func.sum(DailyPracticeLog.exercises_completed)).filter(
        DailyPracticeLog.user_id == user_id
    ).scalar() or 0

    # Format practice time
    total_minutes = stats.total_practice_time_seconds // 60
    hours = total_minutes // 60
    minutes = total_minutes % 60

    if hours > 0:
        time_str = f"{hours}h {minutes}m"
    else:
        time_str = f"{minutes} min"

    return {
        "current_streak": stats.current_streak,
        "longest_streak": stats.longest_streak,
        "total_words": total_words,
        "words_started": words_started,
        "words_mastered": mastered_words,
        "words_already_known": already_known,
        "words_not_started": total_words - words_started - already_known,
        "total_practice_time": time_str,
        "total_practice_seconds": stats.total_practice_time_seconds,
        "total_exercises": total_exercises,
        "practiced_today": daily_log is not None,
        "exercises_today": daily_log.exercises_completed if daily_log else 0,
    }


def get_scenario_progress(
    db: Session,
    scenario_id: int,
    user_id: int = GUEST_USER_ID
) -> Dict[str, Any]:
    """Get progress statistics for a specific scenario."""
    # Get all words in scenario
    words = db.query(Word).filter(Word.scenario_id == scenario_id).all()
    total_words = len(words)

    if total_words == 0:
        return {
            "total_words": 0,
            "mastered": 0,
            "in_progress": 0,
            "not_started": 0,
            "already_known": 0,
            "progress_percent": 0,
        }

    mastered = 0
    in_progress = 0
    not_started = 0
    already_known = 0
    total_mastery = 0.0  # Sum of all word masteries for progress calculation

    for word in words:
        # Check for already_known override
        override = db.query(UserWordStatus).filter(
            UserWordStatus.user_id == user_id,
            UserWordStatus.word_id == word.id,
            UserWordStatus.status == 'already_known'
        ).first()

        if override:
            already_known += 1
            total_mastery += 1.0  # Count as 100% mastered
            continue

        # Get skill masteries
        skills = get_word_mastery(db, user_id, word.id)
        avg_skill_mastery = sum(skills.values()) / len(skills) if skills else 0.0
        total_mastery += avg_skill_mastery

        if all(score == 0.0 for score in skills.values()):
            not_started += 1
        elif all(score >= PASS_THRESHOLD for score in skills.values()):
            mastered += 1
        else:
            in_progress += 1

    # Calculate progress based on average mastery across all words
    progress_percent = int((total_mastery / total_words) * 100) if total_words > 0 else 0

    return {
        "total_words": total_words,
        "mastered": mastered,
        "in_progress": in_progress,
        "not_started": not_started,
        "already_known": already_known,
        "progress_percent": progress_percent,
    }


def get_word_status_for_display(
    db: Session,
    word_id: int,
    user_id: int = GUEST_USER_ID
) -> Dict[str, Any]:
    """Get word status and skill details for UI display."""
    # Check for already_known override
    override = db.query(UserWordStatus).filter(
        UserWordStatus.user_id == user_id,
        UserWordStatus.word_id == word_id,
        UserWordStatus.status == 'already_known'
    ).first()

    if override:
        return {
            "status": "already_known",
            "status_label": "Already Known",
            "status_color": "gray",
            "skills": {},
            "overall_progress": 100,
        }

    # Get skill masteries
    skills = get_word_mastery(db, user_id, word_id)

    # Determine status
    if all(score == 0.0 for score in skills.values()):
        status = "not_started"
        status_label = "Not Started"
        status_color = "gray"
    elif all(score >= PASS_THRESHOLD for score in skills.values()):
        status = "mastered"
        status_label = "Mastered"
        status_color = "green"
    else:
        status = "in_progress"
        status_label = "In Progress"
        status_color = "yellow"

    # Calculate overall progress
    avg_mastery = sum(skills.values()) / len(skills) if skills else 0
    overall_progress = int(avg_mastery * 100)

    return {
        "status": status,
        "status_label": status_label,
        "status_color": status_color,
        "skills": {
            "read": int(skills.get("read", 0) * 100),
            "listen": int(skills.get("listen", 0) * 100),
            "speak": int(skills.get("speak", 0) * 100),
            "write": int(skills.get("write", 0) * 100),
        },
        "overall_progress": overall_progress,
    }


def mark_word_as_known(
    db: Session,
    word_id: int,
    user_id: int = GUEST_USER_ID
) -> bool:
    """Mark a word as already known."""
    # Check if override already exists
    override = db.query(UserWordStatus).filter(
        UserWordStatus.user_id == user_id,
        UserWordStatus.word_id == word_id,
    ).first()

    if override:
        override.status = 'already_known'
        override.marked_at = datetime.utcnow()
    else:
        override = UserWordStatus(
            user_id=user_id,
            word_id=word_id,
            status='already_known',
            marked_at=datetime.utcnow()
        )
        db.add(override)

    db.commit()
    return True


def unmark_word_as_known(
    db: Session,
    word_id: int,
    user_id: int = GUEST_USER_ID
) -> bool:
    """Remove the already known status from a word."""
    override = db.query(UserWordStatus).filter(
        UserWordStatus.user_id == user_id,
        UserWordStatus.word_id == word_id,
    ).first()

    if override:
        override.status = 'active'
        override.marked_at = None
        db.commit()

    return True


def get_word_statuses_bulk(
    db: Session,
    word_ids: List[int],
    user_id: int = GUEST_USER_ID
) -> Dict[int, Dict[str, Any]]:
    """
    Get status and skill details for multiple words efficiently.
    Returns a dict mapping word_id to its status dict.
    """
    if not word_ids:
        return {}

    # 1. Fetch all skill masteries for these words
    masteries = db.query(WordSkillMastery).filter(
        WordSkillMastery.user_id == user_id,
        WordSkillMastery.word_id.in_(word_ids)
    ).all()

    # Organize masteries by word_id
    word_skills: Dict[int, Dict[str, float]] = {wid: {} for wid in word_ids}
    for m in masteries:
        if m.word_id in word_skills:
            word_skills[m.word_id][m.skill_type] = m.mastery_score or 0.0

    # 2. Fetch all manual overrides
    overrides = db.query(UserWordStatus).filter(
        UserWordStatus.user_id == user_id,
        UserWordStatus.word_id.in_(word_ids),
        UserWordStatus.status == 'already_known'
    ).all()
    
    known_word_ids = {o.word_id for o in overrides}

    # 3. Build result dict
    results = {}
    
    for word_id in word_ids:
        # Check override first
        if word_id in known_word_ids:
            results[word_id] = {
                "status": "already_known",
                "status_label": "Already Known",
                "status_color": "gray",
                "skills": {},
                "overall_progress": 100,
            }
            continue

        skills = word_skills.get(word_id, {})
        
        # Default empty skills if missing
        skill_values = [skills.get(skill, 0.0) for skill in SKILL_TYPES]
        
        # Determine status
        if all(score == 0.0 for score in skill_values):
            status = "not_started"
            status_label = "Not Started"
            status_color = "gray"
        elif all(score >= PASS_THRESHOLD for score in skill_values):
            status = "mastered"
            status_label = "Mastered"
            status_color = "green"
        else:
            status = "in_progress"
            status_label = "In Progress"
            status_color = "yellow"

        # Calculate overall progress
        avg_mastery = sum(skill_values) / len(SKILL_TYPES) if SKILL_TYPES else 0
        overall_progress = int(avg_mastery * 100)

        results[word_id] = {
            "status": status,
            "status_label": status_label,
            "status_color": status_color,
            "skills": {
                skill: int(skills.get(skill, 0.0) * 100) 
                for skill in SKILL_TYPES
            },
            "overall_progress": overall_progress,
        }

    return results


def get_cefr_progress(
    db: Session,
    user_id: int = GUEST_USER_ID
) -> Dict[str, Dict[str, Any]]:
    """
    Get aggregated progress statistics for each CEFR difficulty level.
    Returns: { "A1": { "total_words": 1500, "mastered": 300, ... }, "A2": ... }
    """
    # 1. Get total word counts per level (cached or aggregated query)
    # This query groups words by scenario difficulty
    # Since Scenario has difficulty_level, we join Word -> Scenario
    
    # Initialize structure
    levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
    result = {
        level: {
            "total_words": 0,
            "mastered": 0,
            "in_progress": 0,
            "not_started": 0,
            "already_known": 0,
            "progress_percent": 0
        }
        for level in levels
    }
    
    # Aggregated query for total words
    total_counts = db.query(
        Scenario.difficulty_level, func.count(Word.id)
    ).join(Word).group_by(Scenario.difficulty_level).all()
    
    for level, count in total_counts:
        if level in result:
            result[level]["total_words"] = count

    # 2. Get user progress counts
    # We need to count mastered/in_progress/known words per level
    # This is heavy if done naively. 
    # Optimization: Use the bulk fetching logic but aggregated.

    # Fetch all user masteries joined with Word and Scenario
    # This might be big (8k rows) but faster than N+N queries
    # SELECT s.difficulty_level, wm.word_id, count(wm.skill_type), min(wm.mastery_score)
    # FROM word_skill_mastery wm 
    # JOIN words w ON w.id = wm.word_id 
    # JOIN scenarios s ON s.id = w.scenario_id 
    # WHERE wm.user_id = :uid 
    # GROUP BY s.difficulty_level, wm.word_id
    
    mastery_data = db.query(
        Scenario.difficulty_level,
        WordSkillMastery.word_id,
        func.count(WordSkillMastery.skill_type).label('skills_count'),
        func.min(WordSkillMastery.mastery_score).label('min_score'),
        func.avg(WordSkillMastery.mastery_score).label('avg_score')
    ).join(Word, WordSkillMastery.word_id == Word.id)\
     .join(Scenario, Word.scenario_id == Scenario.id)\
     .filter(WordSkillMastery.user_id == user_id)\
     .group_by(Scenario.difficulty_level, WordSkillMastery.word_id).all()

    # Track overall mastery sum for percentage calculation
    level_mastery_sum = {level: 0.0 for level in levels}
    
    # Process mastery data
    # We need to deduplicate by word_id effectively. 
    # Ideally the DB query gives us exactly what we need. 
    # With group_by word_id, we get one row per started word.
    
    for level, word_id, skills_cnt, min_score, avg_score in mastery_data:
        if level not in result:
            continue
            
        # Add to sum (avg_score is per word, approximating 0.25 per skill)
        # The avg_score is only for PRESENT skills. If 1 skill is 1.0, avg is 1.0. 
        # But global mastery assumes 4 skills.
        # So we should sum individual skill scores.
        # Let's approximate: 
        # If we have X skills, sum = avg * X. 
        # Max sum is 4.0. 
        # Word contribution to progress = (avg * count) / 4.0
        word_contribution = (avg_score * skills_cnt) / 4.0
        level_mastery_sum[level] += word_contribution

        # Determine status bucket
        # Known Check comes later (override)
        if skills_cnt == 4 and min_score >= PASS_THRESHOLD:
            result[level]["mastered"] += 1
        else:
            result[level]["in_progress"] += 1

    # 3. Handle Already Known Overrides (Priority)
    # We need to subtract from in_progress/mastered/not_started if 'known'
    # Actually, simpler: compute 'known' count first, then fill the rest?
    # No, 'known' overrides mastery.
    
    known_overrides = db.query(
        Scenario.difficulty_level, func.count(UserWordStatus.word_id)
    ).join(Word, UserWordStatus.word_id == Word.id)\
     .join(Scenario, Word.scenario_id == Scenario.id)\
     .filter(
         UserWordStatus.user_id == user_id, 
         UserWordStatus.status == 'already_known'
     ).group_by(Scenario.difficulty_level).all()
     
    # We would need to know WHICH words are known to subtract correctly from other lists.
    # To keep it efficient (not fetching all IDs):
    # We'll just ADD known count to a separate bucket and effectively "Ignore" them 
    # in the progress calculation? Or count as 100%?
    # Plan: Count as 100% mastery for progress bar. 
    # For buckets: They act as 'already_known' bucket.
    # The counts from Step 2 (Mastery) might overlap with Known. 
    # If a word is both Mastered and Known, it counts as Known.
    # This overlap is rare but possible.
    # For aggregated stats, let's assume overlap is negligible or acceptable error margin for speed
    # OR fetch known word_ids to exclude from step 2.
    
    # Correct approach: fetch known IDs first.
    
    # Let's simplify for V1 of this feature:
    # 1. Total words per level
    # 2. Get aggregated counts from new specialized helper if needed,
    #    OR just iterate all UserWordStatus and WordSkillMastery in Python.
    #    8000 words is small enough for Python iteration if we fetch raw data.
    
    pass 
    
    # Redoing logic for perfect accuracy with 2 queries:
    # Q1: All Words (id, difficulty)
    # Q2: All User Data (word_id, type, score/status)
    
    # Q1
    all_words = db.query(Word.id, Scenario.difficulty_level).join(Scenario).all()
    
    # Q2 (Mastery)
    all_masteries = db.query(WordSkillMastery.word_id, WordSkillMastery.skill_type, WordSkillMastery.mastery_score).filter(WordSkillMastery.user_id == user_id).all()
    
    # Q3 (Known)
    all_known = db.query(UserWordStatus.word_id).filter(UserWordStatus.user_id == user_id, UserWordStatus.status == 'already_known').all()
    known_set = {k[0] for k in all_known}
    
    # Build Map
    word_skills = {}
    for m in all_masteries:
        if m.word_id not in word_skills: word_skills[m.word_id] = []
        word_skills[m.word_id].append(m.mastery_score)
        
    # Aggregate
    final_stats = {
        level: {"total_words": 0, "mastered": 0, "in_progress": 0, "not_started": 0, "already_known": 0, "total_score_sum": 0.0}
        for level in levels
    }
    
    for wid, level in all_words:
        if not level: continue # Should not happen
        if level not in final_stats: continue # Just in case

        stats = final_stats[level]
        stats["total_words"] += 1
        
        if wid in known_set:
            stats["already_known"] += 1
            stats["total_score_sum"] += 1.0
            continue
            
        if wid in word_skills:
            scores = word_skills[wid]
            # Calculate word mastery (avg of 4 skills, missing are 0)
            # Sum of scores / 4
            word_score = sum(scores) / 4.0
            stats["total_score_sum"] += word_score
            
            if len(scores) == 4 and all(s >= PASS_THRESHOLD for s in scores):
                stats["mastered"] += 1
            else:
                stats["in_progress"] += 1
        else:
            stats["not_started"] += 1

    # Finalize percentages
    for level, data in final_stats.items():
        if data["total_words"] > 0:
            data["progress_percent"] = int((data["total_score_sum"] / data["total_words"]) * 100)
        del data["total_score_sum"] # Cleanup
        
    return final_stats


def get_scenarios_progress_bulk(
    db: Session,
    scenario_ids: List[int],
    user_id: int = GUEST_USER_ID
) -> Dict[int, Dict[str, Any]]:
    """
    Get progress for multiple scenarios efficiently.
    Returns: { scenario_id: { "progress_percent": 50, ... } }
    """
    # Similar logic to get_cefr_progress but grouped by scenario_id
    
    # 1. Get words for these scenarios
    words = db.query(Word.id, Word.scenario_id)\
        .filter(Word.scenario_id.in_(scenario_ids)).all()
        
    # 2. Get user data (we can afford to get all user data again or filter)
    # Filtering is safer for data volume if users have tons of data eventually
    
    word_ids = [w.id for w in words]
    if not word_ids:
        return {sid: {"total_words": 0, "progress_percent": 0} for sid in scenario_ids}
        
    # Batch fetch mastery
    masteries = db.query(WordSkillMastery.word_id, WordSkillMastery.mastery_score)\
        .filter(WordSkillMastery.user_id == user_id, WordSkillMastery.word_id.in_(word_ids)).all()
        
    # Batch fetch known
    known = db.query(UserWordStatus.word_id)\
        .filter(UserWordStatus.user_id == user_id, UserWordStatus.status == 'already_known', UserWordStatus.word_id.in_(word_ids)).all()
    known_set = {k[0] for k in known}
    
    # Build maps
    word_score_sum = {} # wid -> sum of skill scores
    for m in masteries:
        word_score_sum[m.word_id] = word_score_sum.get(m.word_id, 0.0) + m.mastery_score
        
    # Aggregate per scenario
    scenario_stats = {sid: {"total_words": 0, "total_score_sum": 0.0} for sid in scenario_ids}
    
    for wid, sid in words:
        stats = scenario_stats[sid]
        stats["total_words"] += 1
        
        if wid in known_set:
            stats["total_score_sum"] += 1.0
        elif wid in word_score_sum:
            # Normalized score (sum / 4 skills)
            stats["total_score_sum"] += (word_score_sum[wid] / 4.0)
            
    # Finalize
    results = {}
    for sid, data in scenario_stats.items():
        pct = 0
        if data["total_words"] > 0:
            pct = int((data["total_score_sum"] / data["total_words"]) * 100)
            
        results[sid] = {
            "total_words": data["total_words"],
            "progress_percent": pct,
            # We can add mastered/in_progress counts if needed for UI details
        }
        
    return results
