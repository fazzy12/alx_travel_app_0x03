from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


@api_view(['GET'])
@permission_classes([AllowAny])
def home(request):
    """
    A simple view that returns a welcome message.
    """
    return Response({"message": "Welcome to the ALX Airbnb API!"})


