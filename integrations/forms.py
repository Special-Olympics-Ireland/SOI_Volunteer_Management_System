from django import forms
from .models import IntegrationLog, JustGoSync

class IntegrationLogForm(forms.ModelForm):
    class Meta:
        model = IntegrationLog
        fields = '__all__'

class JustGoSyncForm(forms.ModelForm):
    class Meta:
        model = JustGoSync
        fields = '__all__' 