from datetime import date

from django.contrib import admin
# from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext as _
import os
import advanced_filters
from advanced_filters.admin import FixAdminAdvancedFiltersMixin

class SuppressedListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('suppressed')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'unsubscribed'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            (False, _('Active')),
            (True, _('Suppressed')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (either True or False)
        # to decide how to filter the queryset.
        if self.value() == False:
            return queryset.filter(
                unsubscribed=False,
            )
        if self.value() == True:
            return queryset.filter(
                unsubscribed=True,
            )

app_name = __package__
adv_filters_path = os.path.dirname(advanced_filters.__file__)
# print (adv_filters_path)

class ProfileAdvancedFiltersMixin(FixAdminAdvancedFiltersMixin):
    def __init__(self, *args, **kwargs):
        super(ProfileAdvancedFiltersMixin, self).__init__(*args, **kwargs)
        self.change_list_template = f"admin/{app_name}/profile/change_list.html"
        self.advanced_change_list_template = adv_filters_path + "/templates/admin/advanced_filters.html"
        if self.change_list_template:
            self.original_change_list_template = self.change_list_template
        else:
            self.original_change_list_template = "admin/change_list.html"
        self.change_list_template = self.advanced_change_list_template

        