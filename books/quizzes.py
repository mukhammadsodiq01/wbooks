"""Server-side quiz grading and review snapshots."""
from __future__ import annotations

from .models import QuizQuestion


def grade_quiz(
    questions: list[QuizQuestion], answers: dict[int, int | None]
) -> dict:
    """Grade answers against stored questions and build a stable review.

    ``answers`` maps a question primary key to the selected zero-based option.
    Missing or malformed choices count as unanswered, never as correct.
    """
    review = []
    correct_total = 0

    for question in questions:
        options = list(question.options or [])
        raw_selected = answers.get(question.pk)
        selected = None
        try:
            if raw_selected is not None:
                candidate = int(raw_selected)
                if 0 <= candidate < len(options):
                    selected = candidate
        except (TypeError, ValueError):
            selected = None

        correct_option = int(question.correct_option)
        is_correct = selected is not None and selected == correct_option
        if is_correct:
            correct_total += 1

        review.append(
            {
                "question_id": question.pk,
                "question_text": question.question_text,
                "options": options,
                "selected_option": selected,
                "correct_option": correct_option,
                "is_correct": is_correct,
                "explanation": question.explanation,
            }
        )

    total = len(review)
    percentage = round((correct_total / total) * 100) if total else 0

    return {
        "total_questions": total,
        "correct_answers": correct_total,
        "score_percentage": percentage,
        "review": review,
    }
