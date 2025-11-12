import uuid
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .models import UserPreference
from .serializers import (
    UserSerializer, 
    UserCreateSerializer, 
    UserPreferenceSerializer
)
from core.utils import CustomResponseMixin

User = get_user_model()

class UserViewSet(CustomResponseMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'user_id'
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'retrieve']:
            return [permissions.AllowAny()]
        return [permission() for permission in self.permission_classes]
    
    def get_object(self):
        if self.kwargs.get('user_id') == 'me':
            return self.request.user
        return super().get_object()
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get the current authenticated user's profile
        """
        serializer = self.get_serializer(request.user)
        return self.success_response(serializer.data)
    
    @action(detail=False, methods=['get', 'put'], url_path='me/preferences')
    def user_preferences(self, request):
        """
        Get or update the current user's notification preferences
        """
        user = request.user
        preferences, _ = UserPreference.objects.get_or_create(user=user)
        
        if request.method == 'GET':
            serializer = UserPreferenceSerializer(preferences)
            return self.success_response(serializer.data)
        
        elif request.method == 'PUT':
            serializer = UserPreferenceSerializer(
                preferences, 
                data=request.data, 
                partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return self.success_response(serializer.data)
            return self.error_response(
                serializer.errors, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def create(self, request, *args, **kwargs):
        """
        Create a new user with the provided details
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return self.success_response(
                UserSerializer(user).data,
                status=status.HTTP_201_CREATED
            )
        return self.error_response(
            serializer.errors, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    def update(self, request, *args, **kwargs):
        """
        Update user details
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return self.success_response(serializer.data)
        return self.error_response(
            serializer.errors, 
            status=status.HTTP_400_BAD_REQUEST
        )