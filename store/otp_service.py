import re
import secrets

import requests
from django.conf import settings
from django.utils import timezone

from .models import PhoneOTP


OTP_COOLDOWN_SECONDS = 60
OTP_MAX_PER_HOUR = 3


def normalize_iraqi_phone(phone):
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("00964"):
        digits = digits[5:]
    elif digits.startswith("964"):
        digits = digits[3:]
    if digits.startswith("0"):
        digits = digits[1:]
    return f"964{digits}"


def is_valid_iraqi_phone(phone):
    digits = normalize_iraqi_phone(phone)[3:]
    return len(digits) == 10 and digits.startswith("7")


def display_iraqi_phone(phone):
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("00964"):
        digits = digits[5:]
    elif digits.startswith("964"):
        digits = digits[3:]
    if not digits.startswith("0"):
        digits = f"0{digits}"
    return digits


def generate_otp_code():
    return f"{secrets.randbelow(900000) + 100000:06d}"


def otp_wait_seconds(phone):
    now = timezone.now()
    normalized = normalize_iraqi_phone(phone)
    last = PhoneOTP.objects.filter(phone=normalized).order_by("-created_at").first()
    cooldown = 0
    if last:
        elapsed = (now - last.created_at).total_seconds()
        if elapsed < OTP_COOLDOWN_SECONDS:
            cooldown = int(OTP_COOLDOWN_SECONDS - elapsed) + 1

    hourly = 0
    recent = PhoneOTP.objects.filter(phone=normalized, created_at__gte=now - timezone.timedelta(hours=1))
    if recent.count() >= OTP_MAX_PER_HOUR:
        oldest = recent.order_by("created_at").first()
        if oldest:
            hourly = int(3600 - (now - oldest.created_at).total_seconds()) + 1
    return max(0, cooldown, hourly)


def create_phone_otp(phone):
    normalized = normalize_iraqi_phone(phone)
    code = generate_otp_code()
    PhoneOTP.objects.filter(phone=normalized, is_used=False).update(is_used=True)
    PhoneOTP.objects.create(phone=normalized, code=code)
    return normalized, code


def requester_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def send_otpiq_otp(phone, code, request=None):
    api_key = getattr(settings, "OTPIQ_API_KEY", "")
    if not api_key:
        return False, "OTPIQ_API_KEY is not configured"

    payload = {
        "phoneNumber": normalize_iraqi_phone(phone),
        "smsType": "verification",
        "verificationCode": str(code),
        "provider": getattr(settings, "OTPIQ_PROVIDER", "sms"),
    }
    sender_id = getattr(settings, "OTPIQ_SENDER_ID", "")
    if sender_id:
        payload["senderId"] = sender_id
    if request is not None and getattr(settings, "OTPIQ_ANTI_FRAUD", True):
        ip = requester_ip(request)
        if ip:
            payload["anti_fraud"] = {"requester_ip": ip}

    try:
        response = requests.post(
            getattr(settings, "OTPIQ_API_URL", "https://api.otpiq.com/api/sms"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=getattr(settings, "OTPIQ_TIMEOUT", 15),
        )
    except requests.RequestException as exc:
        return False, f"OTPIQ connection error: {exc}"

    if 200 <= response.status_code < 300:
        return True, ""
    return False, f"OTPIQ {response.status_code}: {response.text[:400]}"
