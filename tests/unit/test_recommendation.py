from memory.recommendation import pick_weak_topic, get_difficulty_band


def test_pick_weak_topic_epsilon_zero():
    topics = [
        {"slug": "arrays", "mastery_score": 0.1},
        {"slug": "trees", "mastery_score": 0.4},
        {"slug": "graphs", "mastery_score": 0.8},
    ]
    # When epsilon=0, always return the 1st (weakest) topic
    for _ in range(10):
        selected = pick_weak_topic(topics, epsilon=0.0)
        assert selected["slug"] == "arrays"


def test_pick_weak_topic_single_topic():
    topics = [{"slug": "arrays", "mastery_score": 0.2}]
    # Single topic list should return the single topic even with epsilon > 0
    selected_eps0 = pick_weak_topic(topics, epsilon=0.0)
    assert selected_eps0["slug"] == "arrays"

    selected_eps05 = pick_weak_topic(topics, epsilon=0.5)
    assert selected_eps05["slug"] == "arrays"


def test_pick_weak_topic_empty_list():
    assert pick_weak_topic([], epsilon=0.2) == {}


def test_difficulty_progression_easy():
    assert get_difficulty_band(0.3) == "Easy"


def test_difficulty_progression_medium():
    assert get_difficulty_band(0.55) == "Medium"


def test_difficulty_progression_hard():
    assert get_difficulty_band(0.8) == "Hard"

