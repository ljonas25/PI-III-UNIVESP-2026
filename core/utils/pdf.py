import os
from django.conf import settings
from django.contrib.staticfiles import finders

def link_callback(uri, rel):
    # Tenta resolver via staticfiles finders
    result = finders.find(uri)
    if result:
        if not isinstance(result, (list, tuple)):
            result = [result]
        result = [os.path.realpath(p) for p in result]
        return result[0]

    # Trata media e static
    if settings.MEDIA_URL and uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    elif settings.STATIC_URL and uri.startswith(settings.STATIC_URL):
        # Se não houve collectstatic, tenta resolver a partir do BASE_DIR
        candidate = os.path.join(settings.STATIC_ROOT or "", uri.replace(settings.STATIC_URL, ""))
        path = candidate if os.path.isfile(candidate) else os.path.join(settings.BASE_DIR, uri.lstrip("/"))
    else:
        return uri  # URL absoluta (http/https) — evite em PDFs

    return os.path.realpath(path)
