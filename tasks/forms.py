from django import forms
from .models import Task, TaskCompletion

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = '__all__'

class TaskCompletionForm(forms.ModelForm):
    class Meta:
        model = TaskCompletion
        fields = '__all__' 