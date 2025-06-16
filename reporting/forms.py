from django import forms
from .models import Report, ReportSchedule

class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = '__all__'

class ReportScheduleForm(forms.ModelForm):
    class Meta:
        model = ReportSchedule
        fields = '__all__' 