import logging
import os
import sys
from typing import Dict, List

# Add the project root to the Python path so we can import Django modules
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Setup Django environment
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "homeser.settings")
django.setup()

# Import Django modules after setup - this is required for management commands
from django.test import Client  # noqa: E402
from django.urls import get_resolver, get_urlconf  # noqa: E402
from django.urls.resolvers import URLPattern, URLResolver  # noqa: E402

logger = logging.getLogger(__name__)


class ContractCompatibilityTester:
    """
    A tool to test compatibility between frontend API calls and backend contracts
    """

    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.client = Client()
        self.compatibility_results = []

    def get_all_api_endpoints(self) -> List[str]:
        """
        Extracts all API endpoints from Django URL configuration
        """

        def extract_urls(url_patterns, prefix=""):
            urls = []
            for pattern in url_patterns:
                if isinstance(pattern, URLResolver):
                    # Recursively extract from nested URL resolvers
                    nested_urls = extract_urls(
                        pattern.url_patterns, prefix + str(pattern.pattern)
                    )
                    urls.extend(nested_urls)
                elif isinstance(pattern, URLPattern):
                    # Add the full URL pattern
                    urls.append(prefix + str(pattern.pattern))
            return urls

        # Get all URL patterns
        urlconf = get_urlconf()
        resolver = get_resolver(urlconf)
        all_urls = extract_urls(resolver.url_patterns)

        # Filter for API endpoints
        api_endpoints = [
            url for url in all_urls if "api" in url and not url.startswith("^admin/")
        ]

        return api_endpoints

    def test_endpoint_compatibility(self, endpoint: str, method: str = "GET") -> Dict:
        """
        Tests if an endpoint is compatible with contract expectations
        """
        full_url = (
            f"{self.base_url}/api/{endpoint.lstrip('^/').rstrip('$')}"
            if endpoint.startswith("^")
            else f"{self.base_url}/api/{endpoint}"
        )

        try:
            if method.upper() == "GET":
                response = self.client.get(full_url)
            elif method.upper() == "POST":
                response = self.client.post(full_url, content_type="application/json")
            elif method.upper() == "PUT":
                response = self.client.put(full_url, content_type="application/json")
            elif method.upper() == "PATCH":
                response = self.client.patch(full_url, content_type="application/json")
            elif method.upper() == "DELETE":
                response = self.client.delete(full_url)
            else:
                response = self.client.get(full_url)  # Default to GET

            result = {
                "endpoint": endpoint,
                "method": method,
                "url": full_url,
                "status_code": response.status_code,
                "compatible": response.status_code
                in [200, 201, 400, 401, 403, 404, 405],
                "response_headers": dict(response.headers),
                "content_type": response.get("content-type", ""),
                "error": None,
            }

            # Try to parse the response as JSON
            try:
                result["response_data"] = (
                    response.json()
                    if response.get("content-type", "").startswith("application/json")
                    else None
                )
            except Exception:
                result["response_data"] = None

        except Exception as e:
            logger.error(f"Error testing endpoint {full_url}: {e}", exc_info=True)
            result = {
                "endpoint": endpoint,
                "method": method,
                "url": full_url,
                "status_code": None,
                "compatible": False,
                "response_headers": None,
                "content_type": None,
                "response_data": None,
                "error": str(e),
            }

        return result

    def run_compatibility_test(self) -> List[Dict]:
        """
        Runs compatibility tests on all API endpoints
        """
        logger.info("Starting compatibility test for API contracts...")

        # Get all API endpoints
        endpoints = self.get_all_api_endpoints()
        logger.info(f"Found {len(endpoints)} API endpoints to test")

        # Test each endpoint
        for i, endpoint in enumerate(endpoints, 1):
            logger.info(f"Testing ({i}/{len(endpoints)}): {endpoint}")

            # Test with GET method
            result_get = self.test_endpoint_compatibility(endpoint, "GET")
            self.compatibility_results.append(result_get)

            # Only test other methods if GET was successful or had expected response
            if result_get["status_code"] in [200, 401, 403, 404, 405]:
                # Test with POST method if it's a list endpoint or creation endpoint
                if endpoint.endswith("/") or "{" not in endpoint:
                    result_post = self.test_endpoint_compatibility(endpoint, "POST")
                    self.compatibility_results.append(
                        {**result_post, "endpoint_method": f"{endpoint}_POST"}
                    )

            # Print status
            status = "✅" if result_get.get("compatible", False) else "❌"
            logger.info(f"  {status} Status: {result_get.get('status_code', 'ERROR')}")

        return self.compatibility_results

    def generate_report(self) -> str:
        """
        Generates a report of the compatibility test results
        """
        total_endpoints = len(self.compatibility_results)
        compatible_endpoints = sum(
            1 for r in self.compatibility_results if r.get("compatible", False)
        )
        incompatible_endpoints = total_endpoints - compatible_endpoints

        report = f"""
API Contract Compatibility Report
===============================

Total Endpoints Tested: {total_endpoints}
Compatible Endpoints: {compatible_endpoints}
Incompatible Endpoints: {incompatible_endpoints}

Compatibility Rate: {(compatible_endpoints / total_endpoints * 100):.2f}%

Summary:
"""
        for result in self.compatibility_results[:10]:  # Show first 10 results
            status = "✅" if result.get("compatible", False) else "❌"
            report += f"{status} {result['method']} {result['endpoint']} - {result.get('status_code', 'ERROR')}\n"

        if len(self.compatibility_results) > 10:
            report += f"... and {len(self.compatibility_results) - 10} more endpoints\n"

        return report


def main():
    tester = ContractCompatibilityTester()
    tester.run_compatibility_test()
    report = tester.generate_report()

    logger.info(report)

    # Optionally save results to file
    with open("contract_compatibility_report.txt", "w") as f:
        f.write(report)

    logger.info("Report saved to 'contract_compatibility_report.txt'")


if __name__ == "__main__":
    main()
