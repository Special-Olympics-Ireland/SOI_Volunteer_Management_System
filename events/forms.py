from django import forms
from .models import Event, Venue, Role, Assignment

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = '__all__'

class VenueForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = '__all__'

class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = '__all__'

class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = '__all__' 