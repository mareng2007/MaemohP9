from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
from .models import Team
from core.models import ScoreTransaction
from .forms import TeamForm, TeamAddMemberForm

class TeamListView(LoginRequiredMixin, ListView):
    model = Team
    template_name = 'teams/team_list.html'
    context_object_name = 'teams'

    def get_queryset(self):
        return Team.objects.filter(members=self.request.user) | Team.objects.filter(created_by=self.request.user)

class TeamCreateView(LoginRequiredMixin, CreateView):
    model = Team
    form_class = TeamForm
    template_name = 'teams/team_form.html'
    success_url = reverse_lazy('teams:team-list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        self.object.members.add(self.request.user)
        return response

class TeamDetailView(LoginRequiredMixin, DetailView):
    model = Team
    template_name = 'teams/team_detail.html'
    context_object_name = 'team'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['members'] = self.object.members.all()
        context['form'] = TeamAddMemberForm()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if 'remove_user' in request.POST:
            User = get_user_model()
            user = get_object_or_404(User, pk=request.POST['remove_user'])
            self.object.members.remove(user)
            # heavy penalty
            ScoreTransaction.transfer(request.user, user, 20, reason='Kick from team')
            return redirect('teams:team-detail', pk=self.object.pk)

        form = TeamAddMemberForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            self.object.members.add(user)
            ScoreTransaction.transfer(request.user, user, 5, reason='Invite to team')
            return redirect('teams:team-detail', pk=self.object.pk)
        context = self.get_context_data(object=self.object)
        context['form'] = form
        return self.render_to_response(context)
