#!/usr/bin/env python
# utils/benchmarking/api_benchmark.py
# API benchmarking script for performance testing

import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


class APIBenchmark:
    """API benchmarking tool for performance testing."""

    def __init__(self, base_url="http://localhost:8000/api"):
        self.base_url = base_url
        self.session = requests.Session()

    def benchmark_endpoint(self, endpoint, method="GET", data=None, iterations=10):
        """Benchmark a single API endpoint.

        Args:
            endpoint (str): API endpoint to test
            method (str): HTTP method (GET, POST, etc.)
            data (dict): Data to send with POST/PUT requests
            iterations (int): Number of iterations to run

        Returns:
            dict: Benchmark results

        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        times = []
        errors = 0

        print(f"Benchmarking {method} {url} with {iterations} iterations...")

        for i in range(iterations):
            start_time = time.time()
            try:
                if method == "GET":
                    response = self.session.get(url)
                elif method == "POST":
                    response = self.session.post(url, json=data)
                elif method == "PUT":
                    response = self.session.put(url, json=data)
                elif method == "DELETE":
                    response = self.session.delete(url)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                if response.status_code >= 400:
                    errors += 1

                end_time = time.time()
                times.append(end_time - start_time)

            except Exception as e:
                errors += 1
                print(f"Error on iteration {i + 1}: {e}")

        if times:
            return {
                "endpoint": endpoint,
                "method": method,
                "iterations": iterations,
                "successful_requests": iterations - errors,
                "error_rate": errors / iterations,
                "avg_response_time": statistics.mean(times),
                "min_response_time": min(times),
                "max_response_time": max(times),
                "median_response_time": statistics.median(times),
                "percentile_95": sorted(times)[int(0.95 * len(times)) - 1]
                if len(times) > 1
                else times[0],
                "total_time": sum(times),
            }
        return {
            "endpoint": endpoint,
            "method": method,
            "iterations": iterations,
            "successful_requests": 0,
            "error_rate": 1.0,
            "avg_response_time": 0,
            "min_response_time": 0,
            "max_response_time": 0,
            "median_response_time": 0,
            "percentile_95": 0,
            "total_time": 0,
        }

    def benchmark_concurrent(
        self,
        endpoint,
        method="GET",
        data=None,
        concurrent_requests=5,
        iterations=10,
    ):
        """Benchmark an endpoint with concurrent requests.

        Args:
            endpoint (str): API endpoint to test
            method (str): HTTP method
            data (dict): Data to send with requests
            concurrent_requests (int): Number of concurrent requests
            iterations (int): Number of iterations per concurrent request

        Returns:
            dict: Concurrent benchmark results

        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        times = []
        errors = 0
        total_requests = concurrent_requests * iterations

        print(
            f"Benchmarking {method} {url} with {concurrent_requests} concurrent requests, {iterations} iterations each...",
        )

        def make_request():
            start_time = time.time()
            try:
                if method == "GET":
                    response = self.session.get(url)
                elif method == "POST":
                    response = self.session.post(url, json=data)
                elif method == "PUT":
                    response = self.session.put(url, json=data)
                elif method == "DELETE":
                    response = self.session.delete(url)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                if response.status_code >= 400:
                    return None, True

                end_time = time.time()
                return end_time - start_time, False
            except Exception:
                return None, True

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [executor.submit(make_request) for _ in range(total_requests)]

            for future in as_completed(futures):
                response_time, error = future.result()
                if error:
                    errors += 1
                elif response_time is not None:
                    times.append(response_time)

        end_time = time.time()
        total_time = end_time - start_time

        if times:
            return {
                "endpoint": endpoint,
                "method": method,
                "concurrent_requests": concurrent_requests,
                "iterations_per_request": iterations,
                "total_requests": total_requests,
                "successful_requests": total_requests - errors,
                "error_rate": errors / total_requests,
                "avg_response_time": statistics.mean(times),
                "min_response_time": min(times),
                "max_response_time": max(times),
                "median_response_time": statistics.median(times),
                "percentile_95": sorted(times)[int(0.95 * len(times)) - 1]
                if len(times) > 1
                else times[0],
                "total_time": total_time,
                "requests_per_second": total_requests / total_time,
            }
        return {
            "endpoint": endpoint,
            "method": method,
            "concurrent_requests": concurrent_requests,
            "iterations_per_request": iterations,
            "total_requests": total_requests,
            "successful_requests": 0,
            "error_rate": 1.0,
            "avg_response_time": 0,
            "min_response_time": 0,
            "max_response_time": 0,
            "median_response_time": 0,
            "percentile_95": 0,
            "total_time": total_time,
            "requests_per_second": 0,
        }

    def run_comprehensive_benchmark(self):
        """Run a comprehensive benchmark of all key endpoints.

        Returns:
            dict: Comprehensive benchmark results

        """
        results = []

        # Define endpoints to test
        endpoints = [
            # Public endpoints
            {"endpoint": "services/", "method": "GET", "name": "List Services"},
            {"endpoint": "services/1/", "method": "GET", "name": "Get Service Detail"},
            {"endpoint": "categories/", "method": "GET", "name": "List Categories"},
            # Search endpoint
            {
                "endpoint": "search/advanced/?q=clean",
                "method": "GET",
                "name": "Advanced Search",
            },
        ]

        print("Running comprehensive API benchmark...")

        for endpoint_info in endpoints:
            result = self.benchmark_endpoint(
                endpoint_info["endpoint"],
                endpoint_info["method"],
                endpoint_info.get("data"),
                20,  # iterations
            )
            result["name"] = endpoint_info["name"]
            results.append(result)

            # Also test with concurrent requests
            concurrent_result = self.benchmark_concurrent(
                endpoint_info["endpoint"],
                endpoint_info["method"],
                endpoint_info.get("data"),
                5,  # concurrent requests
                5,  # iterations per request
            )
            concurrent_result["name"] = f"{endpoint_info['name']} (Concurrent)"
            results.append(concurrent_result)

        return results

    def print_results(self, results):
        """Print benchmark results in a formatted way.

        Args:
            results (list): List of benchmark results

        """
        print("\n" + "=" * 80)
        print("API BENCHMARK RESULTS")
        print("=" * 80)

        for result in results:
            print(f"\n{result['name']}:")
            print(f"  Endpoint: {result['endpoint']}")
            print(f"  Method: {result['method']}")
            print(
                f"  Successful Requests: {result['successful_requests']}/{result.get('total_requests', result['iterations'])}",
            )
            print(f"  Error Rate: {result['error_rate']:.2%}")
            print(f"  Average Response Time: {result['avg_response_time']:.4f}s")
            print(f"  Median Response Time: {result['median_response_time']:.4f}s")
            print(f"  95th Percentile: {result['percentile_95']:.4f}s")
            print(
                f"  Min/Max Response Time: {result['min_response_time']:.4f}s / {result['max_response_time']:.4f}s",
            )
            if "requests_per_second" in result:
                print(f"  Requests Per Second: {result['requests_per_second']:.2f}")
            if "total_time" in result:
                print(f"  Total Time: {result['total_time']:.4f}s")


if __name__ == "__main__":
    # Run the benchmark
    benchmark = APIBenchmark()
    results = benchmark.run_comprehensive_benchmark()
    benchmark.print_results(results)

    # Save results to file
    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nResults saved to benchmark_results.json")
