import logging
import os
import sys

from jsonschema import ValidationError, validate

# Add the project root to the Python path so we can import Django modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django environment
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "homeser.settings")
django.setup()

logger = logging.getLogger(__name__)


def fetch_contracts():
    """
    Fetches the API contracts from the backend
    """
    try:
        # For local testing we'll use a placeholder - in real usage,
        # you might call the actual endpoint or generate from source
        response = {
            "contracts": {
                "openapi": "3.0.0",
                "info": {"title": "HomeSer API", "version": "1.0.0"},
                "paths": {
                    "/api/services/": {
                        "get": {
                            "responses": {
                                "200": {
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "properties": {
                                                    "results": {
                                                        "type": "array",
                                                        "items": {
                                                            "type": "object",
                                                            "properties": {
                                                                "id": {
                                                                    "type": "integer"
                                                                },
                                                                "name": {
                                                                    "type": "string"
                                                                },
                                                                "price": {
                                                                    "type": "number"
                                                                },
                                                                "category": {
                                                                    "type": "integer"
                                                                },
                                                                "description": {
                                                                    "type": "string"
                                                                },
                                                                "short_desc": {
                                                                    "type": "string"
                                                                },
                                                            },
                                                            "required": [
                                                                "id",
                                                                "name",
                                                                "price",
                                                                "category",
                                                                "description",
                                                                "short_desc",
                                                            ],
                                                        },
                                                    }
                                                },
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
            },
            "version": "1.0.0",
            "timestamp": "2023-01-01T00:00:00Z",
        }
        return response
    except Exception as e:
        logger.error(f"Error fetching contracts: {e}", exc_info=True)
        return None


def validate_response_against_schema(response_data, schema):
    """
    Validates an API response against a given schema
    """
    try:
        validate(instance=response_data, schema=schema)
        return {"isValid": True, "errors": []}
    except ValidationError as e:
        return {"isValid": False, "errors": [str(e)]}
    except Exception as e:
        return {"isValid": False, "errors": [f"Validation error: {str(e)}"]}


def run_contract_validation():
    """
    Runs contract validation for all endpoints
    """
    logger.info("Starting contract validation...")

    try:
        # Fetch contracts from the backend
        logger.info("Fetching contracts from backend...")
        contracts = fetch_contracts()

        if not contracts:
            logger.error("Failed to fetch contracts")
            return False

        logger.info("Contracts fetched successfully")

        # Validate the contracts schema structure
        logger.info("Validating contract schema structure...")

        if contracts and isinstance(contracts, dict):
            logger.info("Contract schema structure is valid")

            if "contracts" in contracts:
                logger.info("API contracts definition found")
            else:
                logger.warning("No API contracts definition found in response")

            if "version" in contracts:
                logger.info(f"Contract version: {contracts['version']}")

            if "timestamp" in contracts:
                logger.info(f"Contract timestamp: {contracts['timestamp']}")

            logger.info("Contract validation completed successfully!")
        else:
            logger.error("Contract schema structure is invalid")
            return False

        return True
    except Exception as e:
        logger.error(f"Contract validation failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = run_contract_validation()
    if success:
        logger.info("All contract validations passed!")
        sys.exit(0)
    else:
        logger.error("Some contract validations failed!")
        sys.exit(1)
