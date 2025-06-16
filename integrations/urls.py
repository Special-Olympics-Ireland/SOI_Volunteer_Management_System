from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'integrations'

router = DefaultRouter()
# router.register(r'logs', views.IntegrationLogViewSet)
# router.register(r'justgo-sync', views.JustGoSyncViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
] 