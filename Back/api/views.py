from rest_framework.views import APIView
from rest_framework.response import Response


class HealthCheckView(APIView):
    def get(self, request):
        return Response({
            "status": "ok",
            "message": "Django API 연결 성공"
        })

# Create your views here.
