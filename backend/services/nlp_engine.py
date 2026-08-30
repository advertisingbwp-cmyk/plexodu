"""
Sentiment Analysis Component (NLP Engine)
Implements the algorithm described in SDD Section 5.3 using TextBlob.
Extracts 3 distinct audience sample comments (Positive, Negative, Neutral).
"""

import re
import html
from textblob import TextBlob


def _clean_text(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
    return text.lower().strip()


def _clean_comment_display(comment: str) -> str:
    """Strips HTML tags (<br>, <a>) and unescapes entities for clean UI display."""
    if not comment:
        return ""
    text = html.unescape(comment)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def classify_comment(comment: str):
    """Returns (label, polarity) for a single comment."""
    clean = _clean_text(comment)
    if not clean:
        return "unclassified", 0.0
    polarity = TextBlob(clean).sentiment.polarity  # -1.0 to +1.0
    if polarity > 0.1:
        label = "positive"
    elif polarity < -0.1:
        label = "negative"
    else:
        label = "neutral"
    return label, polarity


def analyze_sentiment(comment_list):
    """
    Processes a list of real YouTube comments and returns aggregate sentiment scores,
    and extracts 3 distinct audience sample comments (positive, negative, neutral).
    """
    counts = {"positive": 0, "negative": 0, "neutral": 0, "unclassified": 0}
    running_total = 0.0

    sample_positive = None
    sample_negative = None
    sample_neutral = None

    for comment in comment_list:
        label, polarity = classify_comment(comment)
        counts[label] += 1
        running_total += polarity

        cleaned_display = _clean_comment_display(comment)
        if not cleaned_display:
            continue

        if label == "positive" and sample_positive is None:
            sample_positive = cleaned_display
        elif label == "negative" and sample_negative is None:
            sample_negative = cleaned_display
        elif label == "neutral" and sample_neutral is None:
            sample_neutral = cleaned_display

    total = max(1, len(comment_list))
    classified_total = max(1, total - counts["unclassified"])

    # Collect 3 distinct sample comments
    sample_comments = []
    if sample_positive:
        sample_comments.append({"sentiment": "positive", "text": sample_positive})
    if sample_negative:
        sample_comments.append({"sentiment": "negative", "text": sample_negative})
    if sample_neutral:
        sample_comments.append({"sentiment": "neutral", "text": sample_neutral})

    # Fill remaining slots up to 3 from comment_list if necessary
    if len(sample_comments) < 3:
        for c in comment_list:
            cleaned = _clean_comment_display(c)
            if cleaned and not any(sc["text"] == cleaned for sc in sample_comments):
                label, _ = classify_comment(c)
                sample_comments.append({"sentiment": label if label != "unclassified" else "neutral", "text": cleaned})
                if len(sample_comments) >= 3:
                    break

    primary_sample = sample_comments[0]["text"] if sample_comments else ""

    return {
        "positive_score": round((counts["positive"] / classified_total) * 100, 2),
        "negative_score": round((counts["negative"] / classified_total) * 100, 2),
        "neutral_score": round((counts["neutral"] / classified_total) * 100, 2),
        "average_polarity": round(running_total / total, 3),
        "dominant_sentiment": max(
            ["positive", "negative", "neutral"],
            key=lambda k: counts[k]
        ),
        "sample_comment": primary_sample,
        "sample_comments": sample_comments[:3],
    }
