#!/usr/bin/env python
# utils/benchmarking/database_benchmark.py
# Database benchmarking script for performance testing

import statistics
import time

from django.contrib.auth import get_user_model
from django.db import connection

from orders.models import Order
from services.models import Review, Service

User = get_user_model()


class DatabaseBenchmark:
    """Database benchmarking tool for performance testing."""

    def __init__(self):
        self.results = []

    def benchmark_query(self, name, query_func, iterations=10):
        """Benchmark a database query.

        Args:
            name (str): Name of the query
            query_func (callable): Function that executes the query
            iterations (int): Number of iterations to run

        Returns:
            dict: Benchmark results

        """
        times = []
        errors = 0

        print(f"Benchmarking {name} with {iterations} iterations...")

        for i in range(iterations):
            start_time = time.time()
            try:
                query_func()
                end_time = time.time()
                times.append(end_time - start_time)
            except Exception as e:
                errors += 1
                print(f"Error on iteration {i + 1}: {e}")

        if times:
            return {
                "name": name,
                "iterations": iterations,
                "successful_queries": iterations - errors,
                "error_rate": errors / iterations,
                "avg_query_time": statistics.mean(times),
                "min_query_time": min(times),
                "max_query_time": max(times),
                "median_query_time": statistics.median(times),
                "percentile_95": (
                    sorted(times)[int(0.95 * len(times)) - 1]
                    if len(times) > 1
                    else times[0]
                ),
                "total_time": sum(times),
            }
        return {
            "name": name,
            "iterations": iterations,
            "successful_queries": 0,
            "error_rate": 1.0,
            "avg_query_time": 0,
            "min_query_time": 0,
            "max_query_time": 0,
            "median_query_time": 0,
            "percentile_95": 0,
            "total_time": 0,
        }

    def benchmark_raw_query(self, name, query, params=None, iterations=10):
        """Benchmark a raw SQL query.

        Args:
            name (str): Name of the query
            query (str): SQL query to execute
            params (tuple): Query parameters
            iterations (int): Number of iterations to run

        Returns:
            dict: Benchmark results

        """

        def query_func():
            with connection.cursor() as cursor:
                # Use parameterized queries to prevent SQL injection
                cursor.execute(query, params or [])

        return self.benchmark_query(name, query_func, iterations)

    def run_comprehensive_benchmark(self):
        """Run a comprehensive database benchmark.

        Returns:
            list: List of benchmark results

        """
        results = []

        # ORM Queries
        results.append(
            self.benchmark_query(
                "List Services (ORM)",
                lambda: list(Service.objects.all()),
                20,
            ),
        )

        results.append(
            self.benchmark_query(
                "Get Service Detail with Reviews (ORM)",
                lambda: Service.objects.filter(id=1)
                .select_related()
                .prefetch_related("reviews")
                .first(),
                20,
            ),
        )

        results.append(
            self.benchmark_query(
                "List Orders with Items (ORM)",
                lambda: list(
                    Order.objects.select_related("user").prefetch_related(
                        "items__service",
                    ),
                ),
                20,
            ),
        )

        results.append(
            self.benchmark_query(
                "Create Review (ORM)",
                lambda: Review.objects.create(
                    service_id=1,
                    user_id=1,
                    rating=5,
                    text="Benchmark test review",
                ),
                10,
            ),
        )

        # Clean up test reviews
        Review.objects.filter(text="Benchmark test review").delete()

        # Raw SQL Queries
        results.append(
            self.benchmark_raw_query(
                "List Services (Raw SQL)",
                "SELECT * FROM services_service WHERE is_active = true",
                None,
                20,
            ),
        )

        results.append(
            self.benchmark_raw_query(
                "Get Service with Reviews (Raw SQL)",
                """
            SELECT s.*, AVG(r.rating) as avg_rating, COUNT(r.id) as review_count
            FROM services_service s
            LEFT JOIN services_review r ON s.id = r.service_id
            WHERE s.id = %s
            GROUP BY s.id
            """,
                (1,),
                20,
            ),
        )

        results.append(
            self.benchmark_raw_query(
                "List Orders with Items (Raw SQL)",
                """
            SELECT o.*, oi.service_id, oi.quantity, oi.price
            FROM orders_order o
            LEFT JOIN orders_orderitem oi ON o.id = oi.order_id
            ORDER BY o.created_at DESC
            """,
                None,
                20,
            ),
        )

        return results

    def print_results(self, results):
        """Print benchmark results in a formatted way.

        Args:
            results (list): List of benchmark results

        """
        print("\n" + "=" * 80)
        print("DATABASE BENCHMARK RESULTS")
        print("=" * 80)

        for result in results:
            print(f"\n{result['name']}:")
            print(
                f"  Successful Queries: {result['successful_queries']}/{result['iterations']}",
            )
            print(f"  Error Rate: {result['error_rate']:.2%}")
            print(f"  Average Query Time: {result['avg_query_time']:.4f}s")
            print(f"  Median Query Time: {result['median_query_time']:.4f}s")
            print(f"  95th Percentile: {result['percentile_95']:.4f}s")
            print(
                f"  Min/Max Query Time: {result['min_query_time']:.4f}s / {result['max_query_time']:.4f}s",
            )
            print(f"  Total Time: {result['total_time']:.4f}s")


if __name__ == "__main__":
    # Run the benchmark
    benchmark = DatabaseBenchmark()
    results = benchmark.run_comprehensive_benchmark()
    benchmark.print_results(results)

    # Save results to file
    import json

    with open("database_benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nResults saved to database_benchmark_results.json")
