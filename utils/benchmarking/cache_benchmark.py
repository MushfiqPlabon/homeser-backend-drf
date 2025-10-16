#!/usr/bin/env python
# utils/benchmarking/cache_benchmark.py
# Cache benchmarking script for performance testing

import statistics
import time

import redis
from django.conf import settings
from django.core.cache import cache

from utils.advanced_data_structures import (service_bloom_filter,
                                            service_hash_table)


class CacheBenchmark:
    """Cache benchmarking tool for performance testing."""

    def __init__(self):
        self.redis_client = redis.Redis.from_url(
            getattr(settings, "REDIS_URL", "redis://127.0.0.1:6379/1"),
        )

    def benchmark_cache_operation(self, name, operation_func, iterations=100):
        """Benchmark a cache operation.

        Args:
            name (str): Name of the operation
            operation_func (callable): Function that executes the operation
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
                operation_func(i)
                end_time = time.time()
                times.append(end_time - start_time)
            except Exception as e:
                errors += 1
                print(f"Error on iteration {i + 1}: {e}")

        if times:
            return {
                "name": name,
                "iterations": iterations,
                "successful_operations": iterations - errors,
                "error_rate": errors / iterations,
                "avg_operation_time": statistics.mean(times),
                "min_operation_time": min(times),
                "max_operation_time": max(times),
                "median_operation_time": statistics.median(times),
                "percentile_95": (
                    sorted(times)[int(0.95 * len(times)) - 1]
                    if len(times) > 1
                    else times[0]
                ),
                "total_time": sum(times),
                "operations_per_second": iterations / sum(times),
            }
        return {
            "name": name,
            "iterations": iterations,
            "successful_operations": 0,
            "error_rate": 1.0,
            "avg_operation_time": 0,
            "min_operation_time": 0,
            "max_operation_time": 0,
            "median_operation_time": 0,
            "percentile_95": 0,
            "total_time": 0,
            "operations_per_second": 0,
        }

    def run_comprehensive_benchmark(self):
        """Run a comprehensive cache benchmark.

        Returns:
            list: List of benchmark results

        """
        results = []

        # Django Cache Operations
        results.append(
            self.benchmark_cache_operation(
                "Django Cache Set",
                lambda i: cache.set(f"test_key_{i}", f"test_value_{i}", timeout=300),
                100,
            ),
        )

        results.append(
            self.benchmark_cache_operation(
                "Django Cache Get",
                lambda i: cache.get(f"test_key_{i % 10}"),  # Reuse some keys
                100,
            ),
        )

        results.append(
            self.benchmark_cache_operation(
                "Django Cache Delete",
                lambda i: cache.delete(f"test_key_{i}"),
                100,
            ),
        )

        # Redis Operations
        results.append(
            self.benchmark_cache_operation(
                "Redis Set",
                lambda i: self.redis_client.set(
                    f"redis_test_key_{i}",
                    f"redis_test_value_{i}",
                    ex=300,
                ),
                100,
            ),
        )

        results.append(
            self.benchmark_cache_operation(
                "Redis Get",
                lambda i: self.redis_client.get(
                    f"redis_test_key_{i % 10}",
                ),  # Reuse some keys
                100,
            ),
        )

        results.append(
            self.benchmark_cache_operation(
                "Redis Delete",
                lambda i: self.redis_client.delete(f"redis_test_key_{i}"),
                100,
            ),
        )

        # Advanced Data Structures
        results.append(
            self.benchmark_cache_operation(
                "Hash Table Set",
                lambda i: service_hash_table.set(
                    f"hash_key_{i}",
                    {"id": i, "name": f"Service {i}"},
                    timeout=300,
                ),
                100,
            ),
        )

        results.append(
            self.benchmark_cache_operation(
                "Hash Table Get",
                lambda i: service_hash_table.get(
                    f"hash_key_{i % 10}",
                ),  # Reuse some keys
                100,
            ),
        )

        results.append(
            self.benchmark_cache_operation(
                "Bloom Filter Add",
                lambda i: service_bloom_filter.add(f"bloom_item_{i}"),
                100,
            ),
        )

        results.append(
            self.benchmark_cache_operation(
                "Bloom Filter Check",
                lambda i: service_bloom_filter.check(
                    f"bloom_item_{i % 10}",
                ),  # Reuse some items
                100,
            ),
        )

        return results

    def print_results(self, results):
        """Print benchmark results in a formatted way.

        Args:
            results (list): List of benchmark results

        """
        print("\n" + "=" * 80)
        print("CACHE BENCHMARK RESULTS")
        print("=" * 80)

        for result in results:
            print(f"\n{result['name']}:")
            print(
                f"  Successful Operations: {result['successful_operations']}/{result['iterations']}",
            )
            print(f"  Error Rate: {result['error_rate']:.2%}")
            print(f"  Average Operation Time: {result['avg_operation_time']:.6f}s")
            print(f"  Median Operation Time: {result['median_operation_time']:.6f}s")
            print(f"  95th Percentile: {result['percentile_95']:.6f}s")
            print(
                f"  Min/Max Operation Time: {result['min_operation_time']:.6f}s / {result['max_operation_time']:.6f}s",
            )
            print(f"  Total Time: {result['total_time']:.4f}s")
            print(f"  Operations Per Second: {result['operations_per_second']:.2f}")


if __name__ == "__main__":
    # Run the benchmark
    benchmark = CacheBenchmark()
    results = benchmark.run_comprehensive_benchmark()
    benchmark.print_results(results)

    # Save results to file
    import json

    with open("cache_benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nResults saved to cache_benchmark_results.json")
