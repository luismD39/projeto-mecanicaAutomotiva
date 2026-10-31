"""Ícones SVG locais (sem depender de internet). Uso no template: {{ icon("car") }}"""

from markupsafe import Markup

ICONS = {
    "dashboard": '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/>'
    '<rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
    "car": '<path d="M3 13l2-6h14l2 6v5h-2.5"/><path d="M5.5 18H3v-5h18"/><circle cx="7.5" cy="18" r="2"/>'
    '<circle cx="16.5" cy="18" r="2"/><path d="M9.5 18h5"/>',
    "scan": '<path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/>'
    '<path d="M7 12h10"/>',
    "activity": '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    "clipboard": '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V3h6v1"/><path d="M9 13l2 2 4-4"/>',
    "flask": '<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.7 3h10.6a2 2 0 0 0 1.7-3l-5-9V3"/><path d="M7.5 15h9"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "book": '<path d="M4 4h6a2 2 0 0 1 2 2v14a2 2 0 0 0-2-2H4z"/><path d="M20 4h-6a2 2 0 0 0-2 2v14a2 2 0 0 1 2-2h6z"/>',
    "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
    "cpu": '<rect x="6" y="6" width="12" height="12" rx="1"/>'
    '<path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
    "alert": '<path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17h.01"/>',
    "error": '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    "loading": '<path d="M12 3a9 9 0 1 0 9 9"/>',
    "empty": '<path d="M3 13h5l1 3h6l1-3h5"/><path d="M5 5h14l2 8v6H3v-6z"/>',
}


def icon(name: str, extra_class: str = "") -> Markup:
    return Markup(
        f'<svg class="icon {extra_class}" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" '
        f'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>'
    )
