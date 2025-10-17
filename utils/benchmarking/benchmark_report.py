# utils/benchmarking/benchmark_report.py
# Benchmark report generator

import json
import os
from datetime import datetime


class BenchmarkReport:
    """Generate comprehensive benchmark reports."""

    def __init__(self, results_dir="benchmark_results"):
        self.results_dir = results_dir

    def load_results(self):
        """Load benchmark results from files."""
        results = {}

        # Check if results_dir exists
        if not os.path.exists(self.results_dir):
            print(f"Results directory {self.results_dir} not found.")
            return results

        # Load API results
        api_file = os.path.join(self.results_dir, "api_benchmark_results.json")
        if os.path.exists(api_file):
            with open(api_file) as f:
                results["api"] = json.load(f)

        # Load database results
        db_file = os.path.join(self.results_dir, "database_benchmark_results.json")
        if os.path.exists(db_file):
            with open(db_file) as f:
                results["database"] = json.load(f)

        # Load cache results
        cache_file = os.path.join(self.results_dir, "cache_benchmark_results.json")
        if os.path.exists(cache_file):
            with open(cache_file) as f:
                results["cache"] = json.load(f)

        # Load all results
        all_file = os.path.join(self.results_dir, "all_benchmark_results.json")
        if os.path.exists(all_file):
            with open(all_file) as f:
                all_results = json.load(f)
                if "api" in all_results and not results.get("api"):
                    results["api"] = all_results["api"]
                if "database" in all_results and not results.get("database"):
                    results["database"] = all_results["database"]
                if "cache" in all_results and not results.get("cache"):
                    results["cache"] = all_results["cache"]

        return results

    def generate_summary(self, results):
        """Generate a summary of benchmark results."""
        summary = {"generated_at": datetime.now().isoformat(), "summary": {}}

        # Database Summary
        if "database" in results:
            db_results = results["database"]
            total_queries = sum(r.get("iterations", 20) for r in db_results)
            total_errors = sum(
                r["error_rate"] * r.get("iterations", 20) for r in db_results
            )
            avg_query_time = (
                sum(r["avg_query_time"] * r.get("iterations", 20) for r in db_results)
                / total_queries
                if total_queries > 0
                else 0
            )

            summary["summary"]["database"] = {
                "total_queries_tested": len(db_results),
                "total_queries": total_queries,
                "total_errors": int(total_errors),
                "error_rate": total_errors / total_queries if total_queries > 0 else 0,
                "average_query_time": avg_query_time,
                "queries_per_second": (
                    sum(
                        r.get(
                            "operations_per_second",
                            (
                                r.get("iterations", 20) / r["total_time"]
                                if r.get("total_time", 1) > 0
                                else 0
                            ),
                        )
                        for r in db_results
                    )
                    / len(db_results)
                    if db_results
                    else 0
                ),
            }

        # Cache Summary
        if "cache" in results:
            cache_results = results["cache"]
            total_operations = sum(r.get("iterations", 100) for r in cache_results)
            total_errors = sum(
                r["error_rate"] * r.get("iterations", 100) for r in cache_results
            )
            avg_operation_time = (
                sum(
                    r["avg_operation_time"] * r.get("iterations", 100)
                    for r in cache_results
                )
                / total_operations
                if total_operations > 0
                else 0
            )

            summary["summary"]["cache"] = {
                "total_operations_tested": len(cache_results),
                "total_operations": total_operations,
                "total_errors": int(total_errors),
                "error_rate": (
                    total_errors / total_operations if total_operations > 0 else 0
                ),
                "average_operation_time": avg_operation_time,
                "operations_per_second": (
                    sum(r.get("operations_per_second", 0) for r in cache_results)
                    / len(cache_results)
                    if cache_results
                    else 0
                ),
            }

        return summary

    def generate_detailed_report(self, results):
        """Generate a detailed benchmark report."""
        report = f"""
HOMESER PLATFORM BENCHMARK REPORT
=================================
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

"""

        # Database Results
        if "database" in results:
            report += "DATABASE PERFORMANCE BENCHMARK\n"
            report += "-" * 35 + "\n"
            for result in results["database"]:
                report += f"\n{result['name']}:\n"
                report += f"  Queries: {result['successful_queries']}/{result.get('iterations', 20)}\n"
                report += f"  Error Rate: {result['error_rate']:.2%}\n"
                report += f"  Avg Query Time: {result['avg_query_time']:.4f}s\n"
                report += f"  95th Percentile: {result['percentile_95']:.4f}s\n"
                if "operations_per_second" in result:
                    report += (
                        f"  Queries/Second: {result['operations_per_second']:.2f}\n"
                    )
            report += "\n"

        # Cache Results
        if "cache" in results:
            report += "CACHE PERFORMANCE BENCHMARK\n"
            report += "-" * 30 + "\n"
            for result in results["cache"]:
                report += f"\n{result['name']}:\n"
                report += f"  Operations: {result['successful_operations']}/{result.get('iterations', 100)}\n"
                report += f"  Error Rate: {result['error_rate']:.2%}\n"
                report += f"  Avg Operation Time: {result['avg_operation_time']:.6f}s\n"
                report += f"  95th Percentile: {result['percentile_95']:.6f}s\n"
                report += (
                    f"  Operations/Second: {result['operations_per_second']:.2f}\n"
                )
            report += "\n"

        # Summary
        summary = self.generate_summary(results)
        report += "PERFORMANCE SUMMARY\n"
        report += "-" * 20 + "\n"

        if "database" in summary["summary"]:
            db_summary = summary["summary"]["database"]
            report += "\nDatabase Performance:\n"
            report += f"  Total Queries: {db_summary['total_queries']}\n"
            report += f"  Error Rate: {db_summary['error_rate']:.2%}\n"
            report += f"  Avg Query Time: {db_summary['average_query_time']:.4f}s\n"
            report += f"  Queries/Second: {db_summary['queries_per_second']:.2f}\n"

        if "cache" in summary["summary"]:
            cache_summary = summary["summary"]["cache"]
            report += "\nCache Performance:\n"
            report += f"  Total Operations: {cache_summary['total_operations']}\n"
            report += f"  Error Rate: {cache_summary['error_rate']:.2%}\n"
            report += f"  Avg Operation Time: {cache_summary['average_operation_time']:.6f}s\n"
            report += (
                f"  Operations/Second: {cache_summary['operations_per_second']:.2f}\n"
            )

        return report

    def save_report(self, report, filename="benchmark_report.txt"):
        """Save the report to a file."""
        filepath = os.path.join(self.results_dir, filename)
        with open(filepath, "w") as f:
            f.write(report)
        return filepath


if __name__ == "__main__":
    # Generate report
    report_generator = BenchmarkReport()
    results = report_generator.load_results()
    report = report_generator.generate_detailed_report(results)

    # Save report
    report_file = report_generator.save_report(report)
    print(f"Report saved to {report_file}")

    # Also save summary
    summary = report_generator.generate_summary(results)
    summary_file = os.path.join(report_generator.results_dir, "benchmark_summary.json")
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    print("Summary saved to benchmark_summary.json")
