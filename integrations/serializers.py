from rest_framework import serializers
from .models import IntegrationLog, JustGoSync

class IntegrationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationLog
        fields = '__all__'

class JustGoSyncSerializer(serializers.ModelSerializer):
    class Meta:
        model = JustGoSync
        fields = '__all__' 