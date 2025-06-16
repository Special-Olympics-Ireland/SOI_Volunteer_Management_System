from django import forms
from .models import VolunteerProfile, EOI

class VolunteerProfileForm(forms.ModelForm):
    class Meta:
        model = VolunteerProfile
        fields = '__all__'

class EOIForm(forms.ModelForm):
    class Meta:
        model = EOI
        fields = '__all__' 