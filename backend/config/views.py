from django.shortcuts import render, redirect
from django.utils.translation import get_language


def language_settings(request):
    if request.method == 'POST':
        next_url = request.POST.get('next', '/')
        response = redirect(next_url)
        lang_code = request.POST.get('language')
        if lang_code:
            response.set_cookie(
                'django_language',
                lang_code,
                max_age=365 * 24 * 60 * 60,
                samesite='Lax',
            )
            if hasattr(request, 'session') and request.session.session_key:
                request.session['django_language'] = lang_code
        return response
    current = get_language()
    return render(request, 'language_settings.html', {
        'current_language': current,
    })
