from rest_framework import serializers
from .models import MineProgressReport, DocumentCheck

class MineProgressReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = MineProgressReport
        fields = ['id', 'report_date', 'description', 'progress_pct', 'created_by']
        read_only_fields = ['created_by']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

class DocumentCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentCheck
        fields = ['id', 'report', 'checked_by', 'check_date', 'remarks']
        read_only_fields = ['checked_by', 'check_date']

    def create(self, validated_data):
        validated_data['checked_by'] = self.context['request'].user
        return super().create(validated_data)
