from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Task, TaskReview, TaskFile
from teams.models import Team

User = get_user_model()

class TaskModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='tester')
        self.team = Team.objects.create(name='TeamA', created_by=self.user)
        self.team.members.add(self.user)

    def test_create_task(self):
        task = Task.objects.create(title='Test Task', created_by=self.user)
        self.assertEqual(task.status, 'Open')
        self.assertEqual(task.created_by, self.user)

    def test_review_approval(self):
        task = Task.objects.create(title='Test Task', created_by=self.user)
        review = TaskReview.objects.create(task=task, reviewer=self.user, approved=True)
        self.assertTrue(review.approved)
        self.assertEqual(review.task, task)


class TaskViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='pass')
        self.client.login(username='tester', password='pass')
        self.team = Team.objects.create(name='TeamA', created_by=self.user)
        self.team.members.add(self.user)
        self.task = Task.objects.create(title='Test', created_by=self.user, assigned_team=self.team)

    def test_add_review_via_post(self):
        url = reverse('workflow:task-detail', args=[self.task.pk])
        response = self.client.post(url, {'comment': 'LGTM', 'approved': True})
        self.assertEqual(response.status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'Approved')
        self.assertEqual(self.task.reviews.count(), 1)

    def test_upload_file_versioning(self):
        url = reverse('workflow:task-detail', args=[self.task.pk])
        file1 = SimpleUploadedFile('file.txt', b'hello')
        response = self.client.post(url, {'file': file1})
        self.assertEqual(response.status_code, 302)
        file2 = SimpleUploadedFile('file.txt', b'hello world')
        response = self.client.post(url, {'file': file2})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.task.files.count(), 2)
        versions = list(self.task.files.values_list('version', flat=True))
        self.assertEqual(versions, [1, 2])

    def test_file_diff_view(self):
        url = reverse('workflow:task-detail', args=[self.task.pk])
        file1 = SimpleUploadedFile('file.txt', b'hello')
        self.client.post(url, {'file': file1})
        file2 = SimpleUploadedFile('file.txt', b'hello world')
        self.client.post(url, {'file': file2})
        file_obj = self.task.files.order_by('-version').first()
        diff_url = reverse('workflow:taskfile-diff', args=[file_obj.pk])
        response = self.client.get(diff_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('diff_html', response.context)

