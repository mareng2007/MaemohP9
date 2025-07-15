from django import forms
from .models import Task, TaskReview

class TaskForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['assigned_team'].queryset = user.teams.all()

    class Meta:
        model = Task
        fields = ['title', 'description', 'assigned_to', 'assigned_team', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'assigned_team': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class TaskReviewForm(forms.ModelForm):
    class Meta:
        model = TaskReview
        fields = ['comment', 'approved']
        widgets = {
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'approved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class TaskFileForm(forms.Form):
    file = forms.FileField(widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))



