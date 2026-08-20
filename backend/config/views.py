from django.shortcuts import render, redirect
from django.utils.translation import LANGUAGE_SESSION_KEY, check_for_language, get_language
from django.conf import settings


def language_settings(request):
    if request.method == 'POST':
        lang_code = request.POST.get('language')
        if lang_code and check_for_language(lang_code):
            response = redirect(request.POST.get('next', '/'))
            if hasattr(request, 'session'):
                request.session[LANGUAGE_SESSION_KEY] = lang_code
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                lang_code,
                max_age=365 * 24 * 60 * 60,
                samesite='Lax',
            )
            return response
    current = get_language()
    return render(request, 'language_settings.html', {
        'current_language': current,
    })
