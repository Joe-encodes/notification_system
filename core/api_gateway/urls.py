from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.HealthCheckView.as_view(), name='health-check'),
    path('notifications/', views.NotificationAPIView.as_view(), name='send-notification'),
    path('notifications/<str:notification_type>/status/', views.NotificationStatusView.as_view(), name='notification-status'),
]
