from django import forms
from .models import Flowchart

class FlowchartForm(forms.ModelForm):
    content = forms.CharField(
        label='Mermaid Code',
        widget=forms.Textarea(attrs={'rows': 6, 'class': 'form-control'})
    )

    class Meta:
        model = Flowchart
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'})
        }

class FlowchartVersionForm(forms.Form):
    content = forms.CharField(
        label='Mermaid Code',
        widget=forms.Textarea(attrs={'rows': 6, 'class': 'form-control'})
    )