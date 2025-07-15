"""
URL configuration for cashcrm_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),

    # หน้าเว็บหลัก (Core)
    path('', include('core.urls', namespace='core')),

    # JWT สำหรับ API
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # API endpoints ของแต่ละแอป
    path('api/core/', include('core.urls', namespace='core-api')),           # เช่น /api/core/users/
    path('api/revenue/', include('revenue.urls', namespace='revenue-api')),  # เช่น /api/revenue/jobs/
    path('api/workflow/', include('workflow.urls', namespace='workflow-api')),
    # path('api/loans/', include('loans.urls', namespace='loans-api')),
    # path('api/payables/', include('payables.urls', namespace='payables-api')),
    # path('api/cashflow/', include('cashflow.urls', namespace='cashflow-api')),
    # path('api/fleet/', include('fleet.urls', namespace='fleet-api')),
    # path('api/mineprogress/', include('mineprogress.urls', namespace='mineprogress-api')),
    
    # Frontend URLs ของแต่ละแอป (Web)
    path('revenue/', include('revenue.urls', namespace='revenue')),
    path('workflow/', include('workflow.urls', namespace='workflow')),
    path('teams/', include('teams.urls', namespace='teams')),
    path('flowchart/', include('flowchart.urls', namespace='flowchart')),
    # path('loans/', include('loans.urls', namespace='loans')),
    # path('payables/', include('payables.urls', namespace='payables')),
    # path('cashflow/', include('cashflow.urls', namespace='cashflow')),
    # path('fleet/', include('fleet.urls', namespace='fleet')),
    # path('mineprogress/', include('mineprogress.urls', namespace='mineprogress')),
]

# เสิร์ฟ media ไฟล์เฉพาะตอน DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)