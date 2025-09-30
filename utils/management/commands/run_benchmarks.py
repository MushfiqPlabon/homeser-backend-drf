# utils/management/commands/run_benchmarks.py
# Management command to run all performance benchmarks

import json
import os

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run comprehensive performance benchmarks"

    def add_arguments(self, parser):
        parser.add_argument(
            "--api-only", action="store_true", help="Run only API benchmarks",
        )
        parser.add_argument(
            "--db-only", action="store_true", help="Run only database benchmarks",
        )
        parser.add_argument(
            "--cache-only", action="store_true", help="Run only cache benchmarks",
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            default=".",
            help="Directory to save benchmark results",
        )

    def handle(self, *args, **options):
        output_dir = options["output_dir"]
        os.makedirs(output_dir, exist_ok=True)

        all_results = {}

        # Run API benchmarks
        if not options["db_only"] and not options["cache_only"]:
            self.stdout.write("Running API benchmarks...")
            try:
                from utils.benchmarking.api_benchmark import APIBenchmark

                api_benchmark = APIBenchmark()
                api_results = api_benchmark.run_comprehensive_benchmark()
                api_benchmark.print_results(api_results)
                all_results["api"] = api_results

                # Save API results
                with open(
                    os.path.join(output_dir, "api_benchmark_results.json"), "w",
                ) as f:
                    json.dump(api_results, f, indent=2)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"API benchmarks failed: {e}"))

        # Run database benchmarks
        if not options["api_only"] and not options["cache_only"]:
            self.stdout.write("Running database benchmarks...")
            try:
                from utils.benchmarking.database_benchmark import DatabaseBenchmark

                db_benchmark = DatabaseBenchmark()
                db_results = db_benchmark.run_comprehensive_benchmark()
                db_benchmark.print_results(db_results)
                all_results["database"] = db_results

                # Save database results
                with open(
                    os.path.join(output_dir, "database_benchmark_results.json"), "w",
                ) as f:
                    json.dump(db_results, f, indent=2)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Database benchmarks failed: {e}"))

        # Run cache benchmarks
        if not options["api_only"] and not options["db_only"]:
            self.stdout.write("Running cache benchmarks...")
            try:
                from utils.benchmarking.cache_benchmark import CacheBenchmark

                cache_benchmark = CacheBenchmark()
                cache_results = cache_benchmark.run_comprehensive_benchmark()
                cache_benchmark.print_results(cache_results)
                all_results["cache"] = cache_results

                # Save cache results
                with open(
                    os.path.join(output_dir, "cache_benchmark_results.json"), "w",
                ) as f:
                    json.dump(cache_results, f, indent=2)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Cache benchmarks failed: {e}"))

        # Save all results
        with open(os.path.join(output_dir, "all_benchmark_results.json"), "w") as f:
            json.dump(all_results, f, indent=2)

        self.stdout.write(
            self.style.SUCCESS(f"Benchmarks completed. Results saved to {output_dir}"),
        )
