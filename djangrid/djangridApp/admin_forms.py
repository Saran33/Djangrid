import logging

from django import forms

from django.contrib.admin import widgets, options

from django.utils.translation import gettext as _

from .models import Newsletter, Profile, Segment, Campaign
from .addressimport.parsers import parse_csv, parse_vcard, parse_ldif

from django.conf import settings
# from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
User = get_user_model()
from .admin_filters import SuppressedListFilter

logger = logging.getLogger(__name__)


class ImportForm(forms.Form):

    def clean(self):
        # If there are validation errors earlier on, don't bother.
        if not ('address_file' in self.cleaned_data and
                'ignore_errors' in self.cleaned_data):
            return self.cleaned_data
            # TESTME: Should an error be raised here or not?
            # raise forms.ValidationError(_("No file has been specified."))

        ignore_errors = self.cleaned_data['ignore_errors']

        myfield = self.base_fields['address_file']
        myvalue = myfield.widget.value_from_datadict(
            self.data, self.files, self.add_prefix('address_file'))

        content_type = myvalue.content_type
        allowed_types = ('text/plain', 'application/octet-stream',
                         'text/vcard', 'text/directory', 'text/x-vcard',
                         'application/vnd.ms-excel',
                         'text/comma-separated-values', 'text/csv',
                         'application/csv', 'application/excel',
                         'application/vnd.msexcel', 'text/anytext')
        if content_type not in allowed_types:
            raise forms.ValidationError(_(
                "File type '%s' was not recognized.") % content_type)

        ext = myvalue.name.rsplit('.', 1)[-1].lower()
        if ext == 'vcf':
            self.addresses = parse_vcard(
                myvalue.file, ignore_errors)

        elif ext == 'ldif':
            self.addresses = parse_ldif(
                myvalue.file, ignore_errors)

        elif ext == 'csv':
            self.addresses = parse_csv(
                myvalue.file, ignore_errors)

        else:
            raise forms.ValidationError(
                _("File extension '%s' was not recognized.") % ext)

        if len(self.addresses) == 0:
            raise forms.ValidationError(
                _("No entries could found in this file."))

        return self.cleaned_data

    def get_addresses(self):
        return getattr(self, 'addresses', {})

    # try: # Saran
    #     user_default = User.objects.all()[0].pk
    # except IndexError:
    #     user_default =  None

    # user = forms.ModelChoiceField(
    #     label=_("user"),
    #     queryset=User.objects,
    #     # initial=user_default
    #     )
    address_file = forms.FileField(label=_("Address file"))
    ignore_errors = forms.BooleanField(
        label=_("Ignore non-fatal errors"),
        initial=False, required=False)


class ConfirmForm(forms.Form):

    def clean(self):
        value = self.cleaned_data['confirm']

        if not value:
            raise forms.ValidationError(
                _("You should confirm in order to continue."))

    confirm = forms.BooleanField(
        label=_("Confirm import"),
        initial=True, widget=forms.HiddenInput)


class ProfileAdminForm(forms.ModelForm):

    class Meta:
        model = Profile
        fields = '__all__'
        widgets = {
            'unsubscribed': widgets.AdminRadioSelect(
                choices=[
                    (True, _('Unsubscribed')),
                    (False, _('Subscribed'))
                ],
                attrs={
                    'class': options.get_ul_class(options.HORIZONTAL)
                }
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['unsubscribed'].label = _('Status')

    def clean_email_field(self):
        data = self.cleaned_data['email']
        if self.cleaned_data['user'] and data:
            raise forms.ValidationError(_(
                'If a user has been selected this field '
                'should remain empty.'))
        return data

    def clean_name_field(self):
        data = self.cleaned_data['name_field']
        if self.cleaned_data['user'] and data:
            raise forms.ValidationError(_(
                'If a user has been selected '
                'this field should remain empty.'))
        return data

    # def clean_city_field(self):
    #     data = self.cleaned_data['city']
    #     return data

    # def clean_postalCode_field(self):
    #     data = self.cleaned_data['postalCode']
    #     return data

    # def clean_country_field(self):
    #     data = self.cleaned_data['country']
    #     return data

    def clean(self):
        cleaned_data = super().clean()
        if not (cleaned_data.get('user', None) or
                cleaned_data.get('email', None)):

            raise forms.ValidationError(_(
                'Either a user must be selected or an email address must '
                'be specified.')
            )
        return cleaned_data


class SegmentAdminForm(forms.ModelForm):
    # def __init__(self, profile_set, *args,**kwargs):
    #     super (SegmentAdminForm,self ).__init__(*args,**kwargs)
    #     self.fields['profiles'].queryset = Profile.objects.filter(_id__in=profile_set)

    class Meta:
        model = Segment
        fields = '__all__'

    def updated_form(self):
        if self.has_changed():
            data = self.cleaned_data
            return data


class CampaignAdminForm(forms.ModelForm):

    class Meta:
        model = Campaign
        fields = '__all__'

    def clean_publish(self):
        """
        Make sure only one campaign can be published for each message.
        """
        publish = self.cleaned_data['publish']

        if publish and not self.errors:
            emailmsg = self.cleaned_data['emailmsg']
            qs = Campaign.objects.filter(publish=True, emailmsg=emailmsg)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(_(
                    'This message has already been published in another '
                    'campaign. Messages can only be published once.')
                )

        return publish

