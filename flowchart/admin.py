from django.contrib import admin
from .models import Flowchart, FlowchartVersion

@admin.register(Flowchart)
class FlowchartAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')

@admin.register(FlowchartVersion)
class FlowchartVersionAdmin(admin.ModelAdmin):
    list_display = ('flowchart', 'version_number', 'created_at')
    ordering = ('flowchart', 'version_number')
