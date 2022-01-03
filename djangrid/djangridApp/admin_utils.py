from functools import update_wrapper

from django.contrib.admin.utils import unquote
from django.http import Http404
from django.utils.encoding import force_str
from django.utils.translation import gettext as _
from .models import Profile
from django.http import HttpResponse
from django.utils.timezone import now, localtime
import csv

class ExtendibleModelAdminMixin:
    def _getobj(self, request, object_id):
            opts = self.model._meta

            try:
                obj = self.get_queryset(request).get(pk=unquote(object_id))
            except self.model.DoesNotExist:
                # Don't raise Http404 just yet, because we haven't checked
                # permissions yet. We don't want an unauthenticated user to
                # be able to determine whether a given object exists.
                obj = None

            if obj is None:
                raise Http404(
                    _(
                        '%(name)s object with primary key '
                        '\'%(key)s\' does not exist.'
                    ) % {
                        'name': force_str(opts.verbose_name),
                        'key': force_str(object_id)
                    }
                )

            return obj

    def _wrap(self, view):
        def wrapper(*args, **kwargs):
            return self.admin_site.admin_view(view)(*args, **kwargs)
        return update_wrapper(wrapper, view)

    def _view_name(self, name):
        info = self.model._meta.app_label, self.model._meta.model_name, name

        return '%s_%s_%s' % info


def make_profile(email, name=None, city=None, postalCode=None, country=None, ip=None):
    addr = Profile(unsubscribed=False, confirmed=True)

    addr.email = email

    if name:
        addr.name_field = name
    if city:
        addr.city = city
    if postalCode:
        addr.postalCode = postalCode
    if country:
        addr.country = country
    # if ip:
    #     addr.ip = ip

    return addr


class ExportCsvMixin:
    def export_as_csv(self, request, queryset):

        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        file_tag = str(meta).replace('.', '_')
        local_t = localtime(now()).strftime("%Y-%m-%d__%H_%M_%S")
        response['Content-Disposition'] = 'attachment; filename={}_{}.csv'.format(file_tag, local_t)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Export Selected to CSV"

class ExportSegmentCsvMixin:
    def export_as_csv(self, request, queryset):

        meta = self.model._meta
        profile_meta = Profile._meta
        # profiles_email = meta.get_field('profiles__email')
        field_names = [field.name for field in profile_meta.fields]
        mtm_field_names = ["profiles__" + x for x in field_names]

        profiles = queryset.values(*mtm_field_names)

        response = HttpResponse(content_type='text/csv')
        file_tag = str(meta).replace('.', '_')
        local_t = localtime(now()).strftime("%Y-%m-%d__%H_%M_%S")
        response['Content-Disposition'] = 'attachment; filename={}_{}.csv'.format(file_tag, local_t)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in profiles:
            row = writer.writerow([value for value in obj.values()])

        return response

    export_as_csv.short_description = "Export Selected to CSV"