import random
from typing import List, Dict, Any


def pick_weak_topic(mastery_rows: List[Dict[str, Any]], epsilon: float = 0.2) -> Dict[str, Any]:
    """Given topics sorted by mastery_score ascending, return the weakest 
    topic with probability (1-epsilon), or randomly pick from the 2nd/3rd 
    weakest with probability epsilon (if at least 2 topics exist).
    
    If mastery_rows is empty, returns {}.
    If only 1 topic exists or epsilon <= 0, returns the weakest (first) topic.
    """
    if not mastery_rows:
        return {}

    if len(mastery_rows) == 1 or epsilon <= 0.0:
        return mastery_rows[0]

    if random.random() < (1.0 - epsilon):
        return mastery_rows[0]

    candidates = mastery_rows[1:min(3, len(mastery_rows))]
    return random.choice(candidates)


def get_difficulty_band(score: float) -> str:
    """Determine problem difficulty band based on user mastery score:
    score < 0.4 -> "Easy"
    0.4 <= score < 0.7 -> "Medium"
    score >= 0.7 -> "Hard"
    """
    if score < 0.4:
        return "Easy"
    elif score < 0.7:
        return "Medium"
    else:
        return "Hard"


