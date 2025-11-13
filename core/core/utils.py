from rest_framework.response import Response
from rest_framework import status

def standardized_response(success, data=None, error=None, message="", meta=None, http_status=status.HTTP_200_OK):
    """
    This function creates our standard JSON response format:
    {
      "success": boolean,
      "data": T | null,
      "error": string | null,
      "message": string,
      "meta": PaginationMeta | null
    }
    """
    response_data = {
        "success": success,
        "data": data,
        "error": error,
        "message": message,
        "meta": meta if meta is not None else {}
    }
    
    return Response(response_data, status=http_status)

class CustomResponseMixin:
    """
    Mixin to override DRF's default response methods to use the standardized format.
    """
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return standardized_response(
                success=True,
                data=serializer.data,
                message="List retrieved successfully.",
                meta=self.get_pagination_meta(page),
                http_status=status.HTTP_200_OK
            )

        serializer = self.get_serializer(queryset, many=True)
        return standardized_response(
            success=True,
            data=serializer.data,
            message="List retrieved successfully.",
            http_status=status.HTTP_200_OK
        )

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return standardized_response(
                success=True,
                data=serializer.data,
                message="Object retrieved successfully.",
                http_status=status.HTTP_200_OK
            )
        except Exception as e:
            return standardized_response(
                success=False,
                error=str(e),
                message="Object not found.",
                http_status=status.HTTP_404_NOT_FOUND
            )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return standardized_response(
            success=True,
            data=serializer.data,
            message="Object created successfully.",
            http_status=status.HTTP_201_CREATED
        )

    # Add other methods (update, destroy) as needed, but for a microservice,
    # we'll focus on the core read/write operations.

    def get_pagination_meta(self, page):
        """Helper to create the PaginationMeta object."""
        return {
            "total": page.paginator.count,
            "limit": page.paginator.per_page,
            "page": page.number,
            "total_pages": page.paginator.num_pages,
            "has_next": page.has_next(),
            "has_previous": page.has_previous(),
        }
    
    def success_response(self, data, message="Operation successful.", http_status=status.HTTP_200_OK):
        """Helper method for success responses"""
        return standardized_response(
            success=True,
            data=data,
            message=message,
            http_status=http_status
        )
    
    def error_response(self, error, message="Operation failed.", http_status=status.HTTP_400_BAD_REQUEST):
        """Helper method for error responses"""
        return standardized_response(
            success=False,
            error=error,
            message=message,
            http_status=http_status
        )
    