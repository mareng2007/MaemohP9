from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Document

@login_required
def upload_document(request):
    if request.method == 'POST' and request.FILES.get('file'):
        Document.objects.create(user=request.user, file=request.FILES['file'])
        return redirect('documents:upload_success')
    return render(request, 'documents/upload.html')

@login_required
def upload_success(request):
    return render(request, 'documents/success.html')
