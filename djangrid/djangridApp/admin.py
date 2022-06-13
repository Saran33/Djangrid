from django.contrib import admin, messages
from .models import Newsletter, Profile, Segment, Campaign, Attachment

import logging
from django.urls import path
logger = logging.getLogger(__name__)
from django.conf import settings
from django.core import serializers
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render
from django.utils.html import format_html
from django.utils.translation import gettext as _, ngettext
from django.utils.formats import date_format
from django.utils.timezone import now, localtime
from django.urls import reverse
from django.db.utils import IntegrityError
try:
    from django.views.i18n import JavaScriptCatalog
    HAS_CBV_JSCAT = True
except ImportError:  # Django < 1.10
    from django.views.i18n import javascript_catalog
    HAS_CBV_JSCAT = False
from .admin_utils import (ExtendibleModelAdminMixin, make_profile,
    ExportCsvMixin, ExportSegmentCsvMixin, CreateSegmentMixin
)
from .admin_forms import (
    ProfileAdminForm, ImportForm, ConfirmForm, SegmentAdminForm, CampaignAdminForm
)
from .admin_filters import SuppressedListFilter, ProfileAdvancedFiltersMixin

# Construct URL's for icons
ICON_URLS = {
    'yes': '%snewsletter/admin/img/icon-yes.gif' % settings.STATIC_URL,
    'wait': '%snewsletter/admin/img/waiting.gif' % settings.STATIC_URL,
    'submit': '%snewsletter/admin/img/submitting.gif' % settings.STATIC_URL,
    'no': '%snewsletter/admin/img/icon-no.gif' % settings.STATIC_URL
}

def send_newsletter(modeladmin, request, queryset):
    for newsletter in queryset:
        newsletter.send(request)

send_newsletter.short_description = "Send selected Newsletters to all profiles"


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'admin_profiles', # 'admin_messages', 'admin_submissions'
    )
    prepopulated_fields = {'slug': ('title',)}

    """ List extensions """
    def _admin_url(self, obj, model, text):
        url = reverse('admin:%s_%s_changelist' %
                      (model._meta.app_label, model._meta.model_name),
                      current_app=self.admin_site.name)

        return format_html(
            '<a href="{}?newsletter__id={}">{}</a>', url, obj._id, text
        )

    # def admin_messages(self, obj):
    #     return self._admin_url(obj, Message, _("Messages"))
    # admin_messages.short_description = ''

    def admin_profiles(self, obj):
        return self._admin_url(obj, Profile, _("Profiles"))
    admin_profiles.short_description = ''

    # def admin_submissions(self, obj):
    #     return self._admin_url(obj, Campaign, _("Campaigns"))
    # admin_submissions.short_description = ''

    actions = [send_newsletter,]


class NewsletterAdminLinkMixin:
    def admin_newsletter(self, obj):
        opts = Newsletter._meta
        newsletter = obj.newsletter
        url = reverse('admin:%s_%s_change' % (opts.app_label, opts.model_name),
                      args=(newsletter._id,), current_app=self.admin_site.name)

        return format_html('<a href="{}">{}</a>', url, newsletter)
    admin_newsletter.short_description = _('newsletter')


@admin.register(Profile)
class ProfileAdmin(CreateSegmentMixin, ExportCsvMixin, ProfileAdvancedFiltersMixin,
                    ExtendibleModelAdminMixin, admin.ModelAdmin):
    def admin_profile(self, obj):
        opts = Profile._meta
        profile = obj.profile
        url = reverse('admin:%s_%s_change' % (opts.app_label, opts.model_name),
                      args=(profile._id,), current_app=self.admin_site.name)

        return format_html('<a href="{}">{}</a>', url, profile)
    admin_profile.short_description = _('profile')
    form = ProfileAdminForm
    list_per_page = 100
    list_display = (
        'name', 'email', 'admin_subscribe_date',
        'admin_unsubscribe_date', 'admin_status_text', 'admin_status'
    )
    list_display_links = ('name', 'email')
    list_filter = (
        SuppressedListFilter, 'confirmed', 'subscribe_date', 'unsubscribed',
    )
    search_fields = (
        'name_field', 'email', 'user__first_name', 'user__last_name',
        'user__email'
    )
    readonly_fields = (
        'ip', 'subscribe_date', 'unsubscribe_date', 'conf_num'
    )
    date_hierarchy = 'subscribe_date'
    actions = ['make_subscribed', 'make_unsubscribed', 'make_confirmed',
                'make_unconfirmed', 'create_segment', 'export_as_csv']
    # exclude = ['unsubscribed']

    advanced_filter_fields = (
            'unsubscribed',
            'city',
            'postalCode',
            'country',
        )

    # @admin.display(description='suppressed')
    # def is_suppressed(self, obj):
    #     if obj.unsubscribed:
    #         return _("Suppressed")
    #     else:
    #         return _("Active")

    """ List extensions """
    def admin_status(self, obj):
        img_tag = '<img src="{}" width="10" height="10" alt="{}"/>'
        alt_txt = self.admin_status_text(obj)
        if not obj.confirmed:
            return format_html(img_tag, ICON_URLS['wait'], alt_txt)
        elif obj.unsubscribed:
            return format_html(img_tag, ICON_URLS['no'], alt_txt)

        else:
            return format_html(img_tag, ICON_URLS['yes'], alt_txt)
    admin_status.short_description = ''

    def admin_status_text(self, obj):
        if not obj.confirmed:
            return _("Unactivated")
        elif obj.unsubscribed:
            return _("Suppressed")
        else:
            return _("Active")

    admin_status_text.short_description = _('Status')

    def admin_subscribe_date(self, obj):
        if obj.subscribe_date:
            return date_format(obj.subscribe_date)
        else:
            return ''
    admin_subscribe_date.short_description = _("subscribe date")

    def admin_unsubscribe_date(self, obj):
        if obj.unsubscribe_date:
            return date_format(obj.unsubscribe_date)
        else:
            return ''
    admin_unsubscribe_date.short_description = _("unsubscribe date")

    """ Actions """
    def make_confirmed(self, request, queryset):
        rows_updated = queryset.update(confirmed=True)
        self.message_user(
            request,
            ngettext(
                "%d user has been successfully confirmed.",
                "%d users have been successfully confirmed.",
                rows_updated
            ) % rows_updated
        )
    make_confirmed.short_description = _("Confirm selected users")

    def make_unconfirmed(self, request, queryset):
        rows_updated = queryset.update(confirmed=False)
        self.message_user(
            request,
            ngettext(
                "%d user has been successfully unconfirmed.",
                "%d users have been successfully unconfirmed.",
                rows_updated
            ) % rows_updated
        )
    make_unconfirmed.short_description = _("Unconfirm selected users")

    def make_subscribed(self, request, queryset):
        rows_updated = queryset.update(unsubscribed=False)
        self.message_user(
            request,
            ngettext(
                "%d user has been successfully subscribed.",
                "%d users have been successfully subscribed.",
                rows_updated
            ) % rows_updated
        )
    make_subscribed.short_description = _("Subscribe selected users")

    def make_unsubscribed(self, request, queryset):
        rows_updated = queryset.update(unsubscribed=True)
        self.message_user(
            request,
            ngettext(
                "%d user has been successfully unsubscribed.",
                "%d users have been successfully unsubscribed.",
                rows_updated
            ) % rows_updated
        )
    make_unsubscribed.short_description = _("Unsubscribe selected users")

    """ Views """
    def update(self, request, object_id):
        segment = self._getobj(request, object_id)

    """ Views """
    def profiles_import(self, request):
        appName = self.model._meta.app_label
        if not request.user.has_perm('newsletter.add_profile'):
            raise PermissionDenied()
        if request.POST:
            form = ImportForm(request.POST, request.FILES)
            if form.is_valid():
                request.session['addresses'] = form.get_addresses()
                # request.session['newsletter_pk'] = \
                #     form.cleaned_data['newsletter'].pk

                confirm_url = reverse(
                    f'admin:{appName}_profile_import_confirm'
                )
                return HttpResponseRedirect(confirm_url)
        else:
            form = ImportForm()

        return render(
            request,
            f"admin/{appName}/profile/importform.html",
            {'form': form},
        )

    def profiles_import_confirm(self, request):
        # If no addresses are in the session, start all over.
        appName = self.model._meta.app_label

        if 'addresses' not in request.session:
            import_url = reverse(f'admin:{appName}_profile_import')
            return HttpResponseRedirect(import_url)

        addresses = request.session['addresses']
        # newsletter = Newsletter.objects.get(
        #     pk=request.session['newsletter_pk']
        # )

        logger.debug('Confirming addresses: %s', addresses)

        if request.POST:
            form = ConfirmForm(request.POST)
            if form.is_valid():
                try:
                    # for email, name, city, postalCode, country in addresses.items():
                    #     try:
                    #         address_inst = make_profile(
                    #             email, name, city, postalCode, country
                    #         )
                    for email in addresses:
                        name = addresses[email]['name']
                        city = addresses[email]['city']
                        postalCode = addresses[email]['postalCode']
                        country = addresses[email]['country']

                        try:
                            address_inst = make_profile(
                                email, name, city, postalCode, country
                            )
                            address_inst.save()
                        except IntegrityError:
                            logging.warning(f'WARNING: email already exists. Dropping duplicate: <{email}>.')
                            logging.info(f'UNIQUE CONSTRAINT FAILED - Dropped duplicate: <{email}>.')
                finally:
                    del request.session['addresses']
                    # del request.session['newsletter_pk']

                messages.success(
                    request,
                    ngettext(
                        "%d profiles have been successfully added.",
                        "%d profiles have been successfully added.",
                        len(addresses)
                    ) % len(addresses)
                )

                changelist_url = reverse(
                    f'admin:{appName}_profile_changelist'
                )
                return HttpResponseRedirect(changelist_url)
        else:
            form = ConfirmForm()

        return render(
            request,
            f"admin/{appName}/profile/confirmimportform.html",
            {'form': form, 'profiles': addresses},
        )

    """ URLs """
    def get_urls(self):
        urls = super().get_urls()
        appName = self.model._meta.app_label

        my_urls = [
            path('import/',
                 self._wrap(self.profiles_import),
                 name=self._view_name('import')),
            path('import/confirm/',
                 self._wrap(self.profiles_import_confirm),
                 name=self._view_name('import_confirm')),
        ]
        # print (self._view_name('import_confirm'))
        # Translated JS strings - these should be app-wide but are
        # only used in this part of the admin. For now, leave them here.
        if HAS_CBV_JSCAT:
            my_urls.append(path('jsi18n/',
                           JavaScriptCatalog.as_view(packages=(appName,)),
                           name=f'{appName}_js18n'))
        else:
            my_urls.append(path('jsi18n/',
                                javascript_catalog,
                                {'packages': (appName,)},
                                name=f'{appName}_js18n'))

        return my_urls + urls


@admin.register(Segment)
class SegmentAdmin(ExportSegmentCsvMixin, ExtendibleModelAdminMixin, admin.ModelAdmin):
    form = SegmentAdminForm
    list_per_page = 100
    list_display = (
        'admin_segment', 'admin_created_at', 'admin_updated_at', 'admin_members_count',
    )
    date_hierarchy = 'created_at'
    list_filter = ('created_at', 'updated_at', )
    save_as = True
    # search_fields = ['name', 'country',]
    filter_horizontal = ('profiles',)
    actions = ['export_as_csv']

    """ List extensions """
    def admin_segment(self, obj):
        return format_html('<a href="{}/">{}</a>', obj._id, obj.segment_name)
    admin_segment.short_description = _('Segment')

    def admin_created_at(self, obj):
        if obj.created_at:
            return date_format(obj.created_at, 'DATETIME_FORMAT')
        else:
            return ''
    admin_created_at.short_description = _("Created")

    def admin_updated_at(self, obj):
        if obj.updated_at:
            return date_format(obj.updated_at, 'DATETIME_FORMAT')
        else:
            return ''
    admin_updated_at.short_description = _("Updated")

    def admin_members_count(self, obj):
        memberscount = obj.members()
        return memberscount
    admin_members_count.short_description = _('Members')

    """ Views """
    def update(self, request, object_id):
        segment = self._getobj(request, object_id)

        # form = SegmentAdminForm()
        # if not form.updated_form():
        #     messages.info(request, _("No changes made."))
        #     change_url = reverse(
        #         f'admin:{self.model._meta.app_label}_segment_change', args=[object_id]
        #     )
        #     return HttpResponseRedirect(change_url)

        segment.updated_at = now()
        segment.save()

        messages.info(request, _("Segment updated."))

        changelist_url = reverse(f'admin:{self.model._meta.app_label}_segment_changelist')
        return HttpResponseRedirect(changelist_url)

    """ URLs """
    def get_urls(self):
        urls = super().get_urls()
        appName = self.model._meta.app_label

        my_urls = [
            path(
                '<object_id>/update/',
                self._wrap(self.update),
                name=self._view_name('update')
            )
        ]

        if HAS_CBV_JSCAT:
            my_urls.append(path('jsi18n/',
                           JavaScriptCatalog.as_view(packages=(appName,)),
                           name='newsletter_js18n'))
        else:
            my_urls.append(path('jsi18n/',
                                javascript_catalog,
                                {'packages': (appName,)},
                                name='newsletter_js18n'))
                                
        return my_urls + urls

@admin.register(Campaign)
class CampaignAdmin(ExtendibleModelAdminMixin, admin.ModelAdmin):
    form = CampaignAdminForm
    list_display = (
        'admin_message', 'title', 'admin_publish_date', 'publish',
        'admin_status_text', 'admin_status'
    )
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'publish_date'
    list_filter = ('emailmsg', 'publish', 'sent')
    save_as = True
    filter_horizontal = ('segments',)
    exclude = ['recipients']

    """ List extensions """
    def admin_message(self, obj):
        return format_html('<a href="{}/">{}</a>', obj._id, obj.emailmsg.title)
    admin_message.short_description = _('campaign')

    # def admin_title(self, obj):
    #     if obj.emailmsg:
    #         obj.title = 'Campaign_' + obj.emailmsg.title + str(localtime(now()).strftime("%Y-%m-%d_%H:%M:%S"))
    #     else:
    #         obj.title = 'Campaign_' + str(localtime(now()).strftime("%Y-%m-%d_%H:%M:%S"))
    #     return obj.title
    # admin_title.short_description = _("campaign title")

    def admin_publish_date(self, obj):
        if obj.publish_date:
            return date_format(obj.publish_date, 'DATETIME_FORMAT')
        else:
            return ''
    admin_publish_date.short_description = _("publish date")

    def admin_status(self, obj):
        if obj.prepared:
            if obj.sent:
                return format_html(
                    '<img src="{}" width="10" height="10" alt="{}"/>',
                    ICON_URLS['yes'], self.admin_status_text(obj)
                )
            else:
                if obj.publish_date > now():
                    return format_html(
                        '<img src="{}" width="10" height="10" alt="{}"/>',
                        ICON_URLS['wait'], self.admin_status_text(obj)
                    )
                else:
                    return format_html(
                        '<img src="{}" width="12" height="12" alt="{}"/>',
                        ICON_URLS['wait'], self.admin_status_text(obj)
                    )
        else:
            return format_html(
                '<img src="{}" width="10" height="10" alt="{}"/>',
                ICON_URLS['no'], self.admin_status_text(obj)
            )
    admin_status.short_description = ''

    def admin_status_text(self, obj):
        if obj.prepared:
            if obj.sent:
                return _("Sent.")
            else:
                if obj.publish_date > now():
                    return _("Delayed campaign.")
                else:
                    return _("Submitting.")
        else:
            return _("Not sent.")
    admin_status_text.short_description = _('Status')

    """ Views """
    def submit(self, request, object_id):
        appName = self.model._meta.app_label
        campaign = self._getobj(request, object_id)

        if campaign.sent or campaign.prepared:
            messages.info(request, _("Campaign already sent."))
            change_url = reverse(
                f'admin:{appName}_campaign_change', args=[object_id]
            )
            return HttpResponseRedirect(change_url)

        campaign.prepared = True
        campaign.save()

        messages.info(request, _("Your campaign is being sent."))

        changelist_url = reverse(f'admin:{appName}_campaign_changelist')
        return HttpResponseRedirect(changelist_url)

    """ URLs """
    def get_urls(self):
        urls = super().get_urls()

        my_urls = [
            path(
                '<object_id>/submit/',
                self._wrap(self.submit),
                name=self._view_name('submit')
            )
        ]

        return my_urls + urls


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 1

    def has_change_permission(self, request, obj=None):
        """ Prevent change of the file (instead needs to be deleted) """
        return False


# admin.site.register(Newsletter, NewsletterAdmin)
# admin.site.register(Profile, ProfileAdmin)
# admin.site.register(Segment, SegmentAdmin)
