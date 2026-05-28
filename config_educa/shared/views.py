from django.views.generic import TemplateView


def _sparkline_bars(values, max_height=32):
    """Convert raw values to {y, h, v} dicts so the sparkline template stays dumb."""
    peak = max(values) or 1
    return [
        {"v": v, "h": round((v / peak) * max_height), "y": max_height - round((v / peak) * max_height)}
        for v in values
    ]


class ComponentsDebugView(TemplateView):
    template_name = "shared/_components_debug.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["demo_sparkline"] = _sparkline_bars([3, 5, 7, 6, 4, 2, 1, 4, 6, 8, 6, 4, 3, 5])
        ctx["demo_table_headers"] = ["#", "MODULE", "ITEMS", "DURATION"]
        ctx["demo_table_rows"] = [
            ["01", "Functions, closures, scope", "6", "1h 12m"],
            ["02", "Iterators & generators", "5", "0h 58m"],
            ["03", "Decorators", "7", "1h 34m"],
        ]
        ctx["demo_table_numeric"] = [0, 2, 3]
        return ctx
