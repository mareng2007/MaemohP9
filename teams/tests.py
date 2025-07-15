from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Team

User = get_user_model()

class TeamTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='pass')
        self.user2 = User.objects.create_user(username='user2', password='pass')
        self.client.login(username='user1', password='pass')

    def test_create_team_and_add_member(self):
        response = self.client.post(reverse('teams:team-create'), {'name': 'Team A'})
        self.assertEqual(response.status_code, 302)
        team = Team.objects.get(name='Team A')
        self.assertIn(self.user1, team.members.all())
        detail_url = reverse('teams:team-detail', args=[team.pk])
        response = self.client.post(detail_url, {'user': self.user2.id})
        self.assertEqual(response.status_code, 302)
        self.assertIn(self.user2, team.members.all())
