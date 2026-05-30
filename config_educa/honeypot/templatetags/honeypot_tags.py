"""Template tag that drops a hidden, nofollow tripwire link into a page.

Invisible to humans (off-screen, aria-hidden, not focusable) and nofollow so it
never affects UX or SEO — but a content scraper that harvests links will follow
it, triggering a `tripwire` honeypot event.
"""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

_TRIPWIRE_TOKEN = "a9f3c1"  # opaque; rotate freely, value is irrelevant to logging


@register.simple_tag
def honeypot_tripwire():
    return mark_safe(
        f'<a href="/honeypot/tripwire/{_TRIPWIRE_TOKEN}/" rel="nofollow" '
        'aria-hidden="true" tabindex="-1" '
        'style="position:absolute;left:-9999px;top:auto;width:1px;height:1px;'
        'overflow:hidden">Administrator Console</a>'
    )
