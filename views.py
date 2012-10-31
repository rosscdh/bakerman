from feincms.module.page.models import Page
from bakery.views import BuildableDetailView, BuildableListView

class PageListView(BuildableListView):
    """
    A list of all tables.
    """
    queryset = Page.objects.all()


class PageDetailView(BuildableDetailView):
    """
    All about one table.
    """
    queryset = Page.objects.all()