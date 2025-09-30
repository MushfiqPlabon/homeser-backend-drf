# utils/management/commands/analyze_reviews.py
# Management command to analyze existing reviews and populate sentiment analysis fields

from django.core.management.base import BaseCommand

from services.models import Review
from utils.sentiment_analysis import SentimentAnalysisService


class Command(BaseCommand):
    help = "Analyze existing reviews and populate sentiment analysis fields"

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of reviews to process in each batch (default: 100)",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        total_reviews = Review.objects.count()

        self.stdout.write(
            f"Analyzing {total_reviews} reviews in batches of {batch_size}...",
        )

        processed = 0
        failed = 0

        # Process reviews in batches
        for i in range(0, total_reviews, batch_size):
            batch = Review.objects.all()[i : i + batch_size]

            for review in batch:
                try:
                    # Only process reviews that don't have sentiment analysis data
                    if (
                        review.sentiment_polarity == 0
                        and review.sentiment_subjectivity == 0
                    ):
                        sentiment = SentimentAnalysisService.analyze_sentiment(
                            review.text,
                        )
                        review.sentiment_polarity = sentiment["polarity"]
                        review.sentiment_subjectivity = sentiment["subjectivity"]
                        review.sentiment_label = sentiment["sentiment"]
                        review.save(
                            update_fields=[
                                "sentiment_polarity",
                                "sentiment_subjectivity",
                                "sentiment_label",
                            ],
                        )
                    processed += 1
                except Exception as e:
                    failed += 1
                    self.stdout.write(
                        self.style.ERROR(f"Failed to analyze review {review.id}: {e}"),
                    )

            # Show progress
            self.stdout.write(
                f"Processed {min(i + batch_size, total_reviews)}/{total_reviews} reviews...",
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully analyzed {processed} reviews, {failed} failed",
            ),
        )
