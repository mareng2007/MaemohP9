from django.test import TestCase
from .models import Flowchart, FlowchartVersion

class FlowchartModelTest(TestCase):
    def test_create_flowchart_and_version(self):
        chart = Flowchart.objects.create(name='Test')
        FlowchartVersion.objects.create(flowchart=chart, version_number=1, content='graph TD;A-->B')
        self.assertEqual(chart.versions.count(), 1)
        self.assertEqual(chart.latest_version().version_number, 1)