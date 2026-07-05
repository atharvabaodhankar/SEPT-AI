import json

def load_questions(language):
    """
    Load questions from JSON file and filter by programming language.

    Args:
        language (str): Programming language to filter questions by.

    Returns:
        list: List of questions dictionaries filtered by language.
    """
    with open('data/questions_data.json', 'r') as f:
        all_questions = json.load(f)
    return [q for q in all_questions if q['language'].lower() == language.lower()]
