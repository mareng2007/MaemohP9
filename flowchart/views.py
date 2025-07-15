from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, FormView
from django.http import HttpResponse
from django.urls import reverse

from .models import Flowchart, FlowchartVersion
from .forms import FlowchartForm, FlowchartVersionForm

class FlowchartListView(ListView):
    model = Flowchart
    template_name = 'flowchart/list.html'

class FlowchartDetailView(DetailView):
    model = Flowchart
    template_name = 'flowchart/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['latest'] = self.object.latest_version()
        context['versions'] = self.object.versions.order_by('-version_number')
        return context

class FlowchartCreateView(CreateView):
    model = Flowchart
    form_class = FlowchartForm
    template_name = 'flowchart/index.html'

    def form_valid(self, form):
        content = form.cleaned_data.pop('content')
        response = super().form_valid(form)
        FlowchartVersion.objects.create(
            flowchart=self.object,
            version_number=1,
            content=content,
        )
        return response

    def get_success_url(self):
        return reverse('flowchart:detail', args=[self.object.pk])

class FlowchartUpdateView(FormView):
    form_class = FlowchartVersionForm
    template_name = 'flowchart/form.html'

    def dispatch(self, request, *args, **kwargs):
        self.flowchart = get_object_or_404(Flowchart, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        latest = self.flowchart.latest_version()
        return {'content': latest.content if latest else ''}

    def form_valid(self, form):
        latest = self.flowchart.latest_version()
        version_num = (latest.version_number if latest else 0) + 1
        FlowchartVersion.objects.create(
            flowchart=self.flowchart,
            version_number=version_num,
            content=form.cleaned_data['content'],
        )
        return redirect('flowchart:detail', pk=self.flowchart.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['flowchart'] = self.flowchart
        return context

class FlowchartExportView(DetailView):
    model = Flowchart

    def get(self, request, *args, **kwargs):
        flowchart = self.get_object()
        version = kwargs.get('version')
        if version:
            version_obj = get_object_or_404(FlowchartVersion, flowchart=flowchart, version_number=version)
        else:
            version_obj = flowchart.latest_version()
        response = HttpResponse(version_obj.content, content_type='text/plain')
        filename = f"{flowchart.name}_v{version_obj.version_number}.mmd"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response