from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from chatbot.views import chat
from classifier.views import classify, guidance, gradcam, lesions
from reports.views import create_report, download_report, view_report


urlpatterns = [
    path('api/classify/', classify, name='classify'),
    path('api/guidance/', guidance, name='guidance'),
    path('api/gradcam/', gradcam, name='gradcam'),
    path('api/lesions/', lesions, name='lesions'),
    path('api/chat/', chat, name='chat'),
    path('api/reports/', create_report, name='create-report'),
    path('api/reports/<uuid:analysis_id>/view/', view_report, name='view-report'),
    path('api/reports/<uuid:analysis_id>/download/', download_report, name='download-report'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)