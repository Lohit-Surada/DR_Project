import json
import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .models import ChatConversation, ChatMessage
from .services.chatbot_service import answer
from .services.domain_guard import classify_topic

LOGGER = logging.getLogger(__name__)
MAX_MESSAGE_LENGTH = 1200


def _error(message, status):
    return JsonResponse({'success': False, 'error': message}, status=status)


def _cors(response):
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Headers'] = 'Content-Type, X-Chat-Client-ID'
    response['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
    return response


@require_http_methods(['GET', 'POST', 'DELETE', 'OPTIONS'])
def chat(request):
    if request.method == 'OPTIONS':
        return _cors(JsonResponse({}, status=204))
    user_id = request.headers.get('X-Chat-Client-ID', '').strip()[:128] or 'anonymous'

    if request.method == 'GET':
        conversation_id = request.GET.get('conversation_id')
        conversation = ChatConversation.objects.filter(id=conversation_id, user_id=user_id).first() if conversation_id else None
        if not conversation:
            return _cors(JsonResponse({'success': True, 'conversation_id': None, 'messages': []}))
        messages = list(conversation.messages.order_by('created_at').values('role', 'content', 'category', 'created_at'))
        for item in messages:
            item['created_at'] = item['created_at'].isoformat()
        return _cors(JsonResponse({'success': True, 'conversation_id': str(conversation.id), 'messages': messages}))

    if request.method == 'DELETE':
        conversation_id = request.GET.get('conversation_id')
        ChatConversation.objects.filter(id=conversation_id, user_id=user_id).delete()
        return _cors(JsonResponse({'success': True}))

    window_key = f'chatbot-rate:{user_id}'
    request_count = cache.get(window_key, 0)
    if request_count >= settings.CHATBOT_RATE_LIMIT:
        return _cors(_error('Too many requests right now. Please wait a moment and try again.', 429))
    cache.set(window_key, request_count + 1, 60)
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return _cors(_error('Send a valid JSON request.', 400))
    message = str(payload.get('message', '')).strip()
    classification = payload.get('classification')
    if not message and classification:
        message = 'Please provide recovery guidance based on my classification.'
    if not message or len(message) > MAX_MESSAGE_LENGTH:
        return _cors(_error(f'Your message must be between 1 and {MAX_MESSAGE_LENGTH} characters.', 400))
    conversation_id = payload.get('conversation_id')
    conversation = ChatConversation.objects.filter(id=conversation_id, user_id=user_id).first() if conversation_id else None
    if conversation_id and not conversation:
        return _cors(_error('That conversation could not be found.', 404))
    conversation = conversation or ChatConversation.objects.create(user_id=user_id)
    recent = list(conversation.messages.order_by('-created_at')[:settings.CHATBOT_MAX_HISTORY])
    recent.reverse()
    history = [{'role': item.role, 'content': item.content} for item in recent]
    category = classify_topic(message, [item['content'] for item in history])
    started_at = time.perf_counter()
    try:
        response = answer(message, history, category, classification=classification)
        ChatMessage.objects.create(conversation=conversation, role='user', content=message, category=category)
        ChatMessage.objects.create(conversation=conversation, role='assistant', content=response, category=category)
    except Exception:
        LOGGER.exception('Chatbot response failed for user %s.', user_id)
        return _cors(_error("I'm having trouble connecting to the AI assistant right now. Please try again in a moment.", 503))
    LOGGER.info('Chatbot response user=%s category=%s model=%s duration=%.3f', user_id, category, settings.GROQ_MODEL, time.perf_counter() - started_at)
    return _cors(JsonResponse({'success': True, 'response': response, 'conversation_id': str(conversation.id), 'category': category}))