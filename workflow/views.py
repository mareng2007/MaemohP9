from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponse
from django.db import models
from .models import Task, TaskReview, TaskFile
from .serializers import TaskSerializer, TaskReviewSerializer
from core.models import ScoreTransaction
from .forms import TaskForm, TaskReviewForm, TaskFileForm
import difflib

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

class TaskReviewViewSet(viewsets.ModelViewSet):
    queryset = TaskReview.objects.all()
    serializer_class = TaskReviewSerializer
    permission_classes = [IsAuthenticated]


class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = 'workflow/task_list.html'
    context_object_name = 'tasks'
    paginate_by = 10

    def get_queryset(self):
        qs = Task.objects.select_related('assigned_to', 'assigned_team').order_by('-created_at')
        user = self.request.user
        return qs.filter(
            models.Q(created_by=user) |
            models.Q(assigned_to=user) |
            models.Q(assigned_team__members=user)
        ).distinct()


class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = 'workflow/task_detail.html'
    context_object_name = 'task'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reviews'] = self.object.reviews.select_related('reviewer').order_by('created_at')
        context['review_form'] = TaskReviewForm()
        context['files'] = self.object.files.order_by('version')
        context['file_form'] = TaskFileForm()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if 'comment' in request.POST:
            form = TaskReviewForm(request.POST)
            if form.is_valid():
                review = form.save(commit=False)
                review.task = self.object
                review.reviewer = request.user
                review.save()
                assignee = self.object.assigned_to
                if review.approved:
                    self.object.status = 'Approved'
                    self.object.save(update_fields=['status'])
                    if assignee:
                        ScoreTransaction.transfer(request.user, assignee, 20, reason='Approve task')
                else:
                    if assignee:
                        ScoreTransaction.transfer(assignee, request.user, 5, reason='Request changes')
                return redirect('workflow:task-detail', pk=self.object.pk)
            context = self.get_context_data(object=self.object)
            context['review_form'] = form
            return self.render_to_response(context)
        else:
            file_form = TaskFileForm(request.POST, request.FILES)
            if file_form.is_valid():
                TaskFile.objects.create(
                    task=self.object,
                    file=file_form.cleaned_data['file'],
                    uploaded_by=request.user,
                )
                return redirect('workflow:task-detail', pk=self.object.pk)
            context = self.get_context_data(object=self.object)
            context['file_form'] = file_form
            return self.render_to_response(context)


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'workflow/task_form.html'
    success_url = reverse_lazy('workflow:task-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        assignee = form.instance.assigned_to
        if assignee:
            ScoreTransaction.transfer(self.request.user, assignee, 10, reason='Assign task')
        return response


class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'workflow/task_form.html'
    success_url = reverse_lazy('workflow:task-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class TaskFileDiffView(LoginRequiredMixin, TemplateView):
    template_name = 'workflow/task_file_diff.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        file = get_object_or_404(TaskFile, pk=self.kwargs['pk'])
        prev = TaskFile.objects.filter(task=file.task, version=file.version - 1).first()
        if prev and file.file.name.endswith('.txt') and prev.file.name.endswith('.txt'):
            with prev.file.open("r") as f1, file.file.open("r") as f2:
                lines1 = f1.readlines()
                lines2 = f2.readlines()
            diff = difflib.unified_diff(
                lines1,
                lines2,
                fromfile=f"v{prev.version}",
                tofile=f"v{file.version}",
            )
            context["diff"] = "".join(diff)

            html_diff = difflib.HtmlDiff(wrapcolumn=80)
            context["diff_html"] = html_diff.make_table(
                lines1,
                lines2,
                fromdesc=f"v{prev.version}",
                todesc=f"v{file.version}",
                context=True,
                numlines=5,
            )
        else:
            context["diff"] = "Diff not available."
            context["diff_html"] = None
        context["file"] = file
        context["previous"] = prev
        return context
