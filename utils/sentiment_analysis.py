# utils/sentiment_analysis.py
# Sentiment analysis service for review texts

import logging

from textblob import TextBlob

logger = logging.getLogger(__name__)


class SentimentAnalysisService:
    """Service for performing sentiment analysis on text."""

    @staticmethod
    def analyze_sentiment(text):
        """Analyze the sentiment of a text.

        Args:
            text (str): Text to analyze

        Returns:
            dict: Sentiment analysis results with polarity, subjectivity, and label

        """
        try:
            # Validate input
            if not text or not isinstance(text, str):
                logger.warning("Invalid text input for sentiment analysis")
                return {
                    "polarity": 0,
                    "subjectivity": 0,
                    "sentiment": "neutral",
                    "confidence": 0,
                }

            # Create a TextBlob object
            blob = TextBlob(text)

            # Get sentiment polarity (-1 to 1) and subjectivity (0 to 1)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity

            # Determine sentiment label
            if polarity > 0.1:
                sentiment_label = "positive"
            elif polarity < -0.1:
                sentiment_label = "negative"
            else:
                sentiment_label = "neutral"

            return {
                "polarity": polarity,
                "subjectivity": subjectivity,
                "sentiment": sentiment_label,
                "confidence": abs(polarity),
            }
        except Exception as e:
            logger.error(f"Error analyzing sentiment for text: {e}")
            return {
                "polarity": 0,
                "subjectivity": 0,
                "sentiment": "neutral",
                "confidence": 0,
            }

    @staticmethod
    def get_sentiment_score(text):
        """Get a normalized sentiment score between 0 and 1.

        Args:
            text (str): Text to analyze

        Returns:
            float: Normalized sentiment score (0 = very negative, 1 = very positive)

        """
        try:
            # Validate input
            if not text or not isinstance(text, str):
                logger.warning("Invalid text input for sentiment score calculation")
                return 0.5  # Neutral score

            blob = TextBlob(text)
            # Normalize polarity from [-1, 1] to [0, 1]
            return (blob.sentiment.polarity + 1) / 2
        except Exception as e:
            logger.error(f"Error getting sentiment score for text: {e}")
            return 0.5  # Neutral score

    @staticmethod
    def categorize_sentiment(polarity):
        """Categorize sentiment based on polarity score.

        Args:
            polarity (float): Polarity score between -1 and 1

        Returns:
            str: Sentiment category (very_negative, negative, neutral, positive, very_positive)

        """
        try:
            if polarity <= -0.6:
                return "very_negative"
            if polarity <= -0.2:
                return "negative"
            if polarity < 0.2:
                return "neutral"
            if polarity < 0.6:
                return "positive"
            return "very_positive"
        except Exception as e:
            logger.error(f"Error categorizing sentiment for polarity {polarity}: {e}")
            return "neutral"
