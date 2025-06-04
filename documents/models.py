from django.conf import settings
from django.db import models
from django.core.files.storage import FileSystemStorage

private_storage = FileSystemStorage(location=settings.MEDIA_ROOT)

class Document(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(storage=private_storage, upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name
