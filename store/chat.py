# -*- coding: utf-8 -*-
"""دردشة الموقع: الزبون يكتب من نافذة عائمة، والمتجر يرد من لوحة الإدارة.

- المحادثة مربوطة بجلسة الزائر (session['chat_thread_id']) فتبقى معه بين الصفحات.
- الطرفان يسحبان الجديد بالاستطلاع (polling) كل ثوانٍ — لا حاجة لخادم WebSocket.
- أول رسالة غير مقروءة من الزبون ترسل إشعاراً لأجهزة الأدمن.
"""

import json
import logging
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import F
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import ChatMessage, ChatThread, Customer

logger = logging.getLogger(__name__)

MAX_TEXT = 1000
RATE_WINDOW = timedelta(seconds=60)
RATE_MAX = 8                      # رسائل في الدقيقة لكل محادثة
AUTO_REPLY = ('أهلاً بك 👋 وصلتنا رسالتك، وسيرد عليك أحد فريقنا هنا بأسرع وقت '
              '(عادةً خلال دقائق في أوقات الدوام). يمكنك إغلاق النافذة ومتابعة '
              'التسوق — سيظهر الرد هنا تلقائياً.')


def _msg_json(m):
    return {
        'id': m.id,
        'from': m.sender,
        'text': m.text,
        'at': timezone.localtime(m.created_at).strftime('%H:%M'),
        'date': timezone.localtime(m.created_at).strftime('%Y-%m-%d'),
        'auto': m.sender == 'admin' and m.admin_user_id is None,
    }


def _session_thread(request):
    tid = request.session.get('chat_thread_id')
    if not tid:
        return None
    return ChatThread.objects.filter(pk=tid).first()


def _after(request):
    try:
        return max(0, int(request.GET.get('after', 0)))
    except (TypeError, ValueError):
        return 0


def _clean(value, limit):
    return str(value or '').strip()[:limit]


# ---------------------------------------------------------------- الزبون

@require_GET
def chat_state(request):
    """الجديد من الرسائل بعد after. open=1 يعني أن النافذة مفتوحة → الرسائل مقروءة."""
    thread = _session_thread(request)
    if not thread:
        return JsonResponse({'status': 'ok', 'thread': False, 'messages': [], 'unread': 0})
    msgs = list(thread.messages.filter(id__gt=_after(request))[:200])
    if request.GET.get('open') == '1' and thread.customer_unread:
        ChatThread.objects.filter(pk=thread.pk).update(customer_unread=0)
        thread.customer_unread = 0
    return JsonResponse({
        'status': 'ok', 'thread': True,
        'messages': [_msg_json(m) for m in msgs],
        'unread': thread.customer_unread,
        'has_contact': bool(thread.phone),
    })


@require_POST
def chat_send(request):
    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        data = request.POST
    text = _clean(data.get('text'), MAX_TEXT)
    name = _clean(data.get('name'), 120)
    phone = _clean(data.get('phone'), 50)
    page = _clean(data.get('page'), 300)
    if not text and not (name or phone):
        return JsonResponse({'status': 'error', 'error': 'اكتب رسالتك أولاً'}, status=400)

    thread = _session_thread(request)
    created = False
    if thread is None:
        if not text:
            return JsonResponse({'status': 'error', 'error': 'اكتب رسالتك أولاً'}, status=400)
        customer = None
        logged_phone = request.session.get('customer_phone')
        if logged_phone:
            customer = Customer.objects.filter(phone=logged_phone).first()
        thread = ChatThread.objects.create(
            customer=customer,
            name=name or (customer.full_name if customer else ''),
            phone=phone or (logged_phone or ''),
            last_page=page,
        )
        request.session['chat_thread_id'] = thread.pk
        request.session.modified = True
        created = True

    # بيانات التواصل (تُرسل مرة من نموذج «اترك رقمك»)
    updates = {}
    if name and name != thread.name:
        updates['name'] = name
    if phone and phone != thread.phone:
        updates['phone'] = phone
    if page:
        updates['last_page'] = page
    if updates:
        ChatThread.objects.filter(pk=thread.pk).update(**updates)

    if not text:
        return JsonResponse({'status': 'ok', 'messages': []})

    recent = thread.messages.filter(sender='customer',
                                    created_at__gte=timezone.now() - RATE_WINDOW).count()
    if recent >= RATE_MAX:
        return JsonResponse({'status': 'error', 'error': 'أرسلت رسائل كثيرة بسرعة، انتظر قليلاً'},
                            status=429)

    was_unread = thread.admin_unread
    msg = ChatMessage.objects.create(thread=thread, sender='customer', text=text)
    ChatThread.objects.filter(pk=thread.pk).update(
        admin_unread=F('admin_unread') + 1, last_message_at=msg.created_at, is_closed=False)
    out = [msg]
    if created:
        out.append(ChatMessage.objects.create(thread=thread, sender='admin', text=AUTO_REPLY))
        ChatThread.objects.filter(pk=thread.pk).update(customer_unread=0)

    if not was_unread:
        try:
            from .views import send_admin_push
            who = updates.get('name') or thread.name or 'زائر'
            send_admin_push(title=f'💬 رسالة من {who}', body=text[:120],
                            url=f'/admin/store/chatthread/?t={thread.pk}')
        except Exception:
            logger.exception('chat push failed')
    return JsonResponse({'status': 'ok', 'messages': [_msg_json(m) for m in out]})


# ---------------------------------------------------------------- الأدمن

def _thread_json(t, last=None):
    return {
        'id': t.pk,
        'name': t.name or (t.phone or f'زائر #{t.pk}'),
        'phone': t.phone,
        'page': t.last_page,
        'unread': t.admin_unread,
        'closed': t.is_closed,
        'last': (last.text[:80] if last else ''),
        'last_from': (last.sender if last else ''),
        'at': timezone.localtime(t.last_message_at).strftime('%m-%d %H:%M'),
    }


@staff_member_required
@require_GET
def admin_threads(request):
    show = request.GET.get('show', 'open')
    qs = ChatThread.objects.all()
    if show == 'open':
        qs = qs.filter(is_closed=False)
    q = _clean(request.GET.get('q'), 60)
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(name__icontains=q) | Q(phone__icontains=q) | Q(messages__text__icontains=q)).distinct()
    threads = list(qs[:100])
    lasts = {}
    for t in threads:
        lasts[t.pk] = t.messages.order_by('-id').first()
    return JsonResponse({
        'status': 'ok',
        'threads': [_thread_json(t, lasts.get(t.pk)) for t in threads],
        'unread_total': sum(ChatThread.objects.filter(admin_unread__gt=0).values_list('admin_unread', flat=True)),
    })


@staff_member_required
@require_GET
def admin_messages(request, pk):
    thread = ChatThread.objects.filter(pk=pk).first()
    if not thread:
        return JsonResponse({'status': 'error', 'error': 'not found'}, status=404)
    msgs = list(thread.messages.filter(id__gt=_after(request))[:300])
    if thread.admin_unread:
        ChatThread.objects.filter(pk=pk).update(admin_unread=0)
    return JsonResponse({'status': 'ok', 'thread': _thread_json(thread),
                         'messages': [_msg_json(m) for m in msgs]})


@staff_member_required
@require_POST
def admin_reply(request, pk):
    thread = ChatThread.objects.filter(pk=pk).first()
    if not thread:
        return JsonResponse({'status': 'error', 'error': 'not found'}, status=404)
    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        data = request.POST
    action = data.get('action')
    if action in ('close', 'reopen'):
        ChatThread.objects.filter(pk=pk).update(is_closed=(action == 'close'))
        return JsonResponse({'status': 'ok'})
    text = _clean(data.get('text'), MAX_TEXT)
    if not text:
        return JsonResponse({'status': 'error', 'error': 'empty'}, status=400)
    msg = ChatMessage.objects.create(thread=thread, sender='admin', text=text,
                                     admin_user=request.user)
    ChatThread.objects.filter(pk=pk).update(
        customer_unread=F('customer_unread') + 1, admin_unread=0,
        last_message_at=msg.created_at, is_closed=False)
    return JsonResponse({'status': 'ok', 'messages': [_msg_json(msg)]})
