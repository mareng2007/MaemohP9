from django.db import models

class Flowchart(models.Model):
    """เก็บข้อมูลผังงานแต่ละชุด"""
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def latest_version(self):
        return self.versions.order_by('-version_number').first()


class FlowchartVersion(models.Model):
    """บันทึกแต่ละเวอร์ชันของผังงาน"""
    flowchart = models.ForeignKey(Flowchart, on_delete=models.CASCADE, related_name='versions')
    version_number = models.PositiveIntegerField()
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('flowchart', 'version_number')
        ordering = ['version_number']

    def __str__(self):
        return f"{self.flowchart.name} v{self.version_number}"