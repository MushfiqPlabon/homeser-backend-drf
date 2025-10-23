from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from drf_spectacular.views import SpectacularJSONAPIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


class ContractSchemaView(SpectacularJSONAPIView):
    """
    Retrieve the OpenAPI schema in JSON format for contract validation.
    This endpoint serves machine-readable API contracts for frontend validation.
    """

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        # Generate the schema using SpectacularJSONAPIView's method
        schema = self.get_schema(request, self.format_kwarg)

        # Return the schema as JSON
        return JsonResponse(schema, safe=False)


@extend_schema(
    summary="Get all API contracts",
    description="Returns all API contracts in a machine-readable format for contract testing.",
    responses={
        200: {"type": "object", "description": "API contracts in JSON Schema format"}
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
def get_all_contracts(request):
    """
    Returns all API contracts in a machine-readable format for contract testing.
    """
    from drf_spectacular.generators import SchemaGenerator

    # Create schema generator and generate the schema
    generator = SchemaGenerator()
    schema = generator.get_schema(request=request, public=True)

    return JsonResponse(
        {
            "contracts": schema,
            "version": "1.0.0",
            "timestamp": "N/A",
        }
    )
