from app import create_app
from models.database import db
from models.entities import Question


def seed_questions():
    app = create_app()

    with app.app_context():
        if Question.query.count() > 0:
            print("Questions already exist, skipping seeding.")
            return

        questions = [
            # Grammar
            {
                "question_text": "Choose the correct option to complete the sentence:\n\n\"She ____ to school every day.\"",
                "option_a": "go",
                "option_b": "goes",
                "option_c": "is go",
                "option_d": "going",
                "correct_answer": "B",
                "category": "grammar",
            },
            {
                "question_text": "Which sentence is grammatically correct?",
                "option_a": "He don't like coffee.",
                "option_b": "He doesn't likes coffee.",
                "option_c": "He doesn't like coffee.",
                "option_d": "He not like coffee.",
                "correct_answer": "C",
                "category": "grammar",
            },
            {
                "question_text": "Choose the correct past form:\n\n\"Yesterday, I ____ to the cinema.\"",
                "option_a": "go",
                "option_b": "went",
                "option_c": "gone",
                "option_d": "was go",
                "correct_answer": "B",
                "category": "grammar",
            },
            # Vocabulary
            {
                "question_text": "Choose the word that best completes the sentence:\n\n\"It is very cold today, please wear a ____ coat.\"",
                "option_a": "thin",
                "option_b": "heavy",
                "option_c": "small",
                "option_d": "slow",
                "correct_answer": "B",
                "category": "vocabulary",
            },
            {
                "question_text": "Which word is closest in meaning to \"happy\"?",
                "option_a": "angry",
                "option_b": "sad",
                "option_c": "joyful",
                "option_d": "tired",
                "correct_answer": "C",
                "category": "vocabulary",
            },
            {
                "question_text": "Choose the best word:\n\n\"She is a very ____ student. She always finishes her homework on time.\"",
                "option_a": "lazy",
                "option_b": "serious",
                "option_c": "hard-working",
                "option_d": "noisy",
                "correct_answer": "C",
                "category": "vocabulary",
            },
            # Reading (short, simple questions)
            {
                "question_text": "Read the text and answer the question:\n\n\"Tom wakes up at 7 a.m. He has breakfast and then walks to school. He starts his first lesson at 8 a.m.\"\n\nWhat time does Tom start his first lesson?",
                "option_a": "7 a.m.",
                "option_b": "8 a.m.",
                "option_c": "6 a.m.",
                "option_d": "9 a.m.",
                "correct_answer": "B",
                "category": "reading",
            },
            {
                "question_text": "Read the text and answer the question:\n\n\"Sara has a small dog. Its name is Max. Every afternoon, she takes Max to the park to play.\"\n\nWhat is the name of Sara's dog?",
                "option_a": "Sara",
                "option_b": "Tom",
                "option_c": "Max",
                "option_d": "Park",
                "correct_answer": "C",
                "category": "reading",
            },
            {
                "question_text": "Read the text and answer the question:\n\n\"The library is open from Monday to Friday. It closes at 6 p.m. on weekdays and is closed on weekends.\"\n\nIs the library open on Sunday?",
                "option_a": "Yes, all day.",
                "option_b": "Yes, until 6 p.m.",
                "option_c": "Only in the morning.",
                "option_d": "No, it is closed.",
                "correct_answer": "D",
                "category": "reading",
            },
        ]

        for q in questions:
            new_q = Question(
                question_text=q["question_text"],
                option_a=q["option_a"],
                option_b=q["option_b"],
                option_c=q["option_c"],
                option_d=q["option_d"],
                correct_answer=q["correct_answer"],
                category=q["category"],
            )
            db.session.add(new_q)

        db.session.commit()
        print(f"Seeded {len(questions)} questions.")


if __name__ == "__main__":
    seed_questions()



