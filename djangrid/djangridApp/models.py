import logging
import os
import time
from django.db import models
from django.conf import settings
from django.contrib.sites.models import Site
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from django.core.mail import EmailMessage, EmailMultiAlternatives
# from django.contrib.auth.models import User
import datetime
# import time
# import calendar
from django.template.loader import select_template
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext
from django.utils.timezone import now, localtime
from django.urls import reverse
from .utils import make_activation_code
from django.template import engines

logger = logging.getLogger(__name__)

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


class Profile(models.Model):
    user = models.ForeignKey(
        AUTH_USER_MODEL, blank=True, null=True, verbose_name=_('user'),
        on_delete=models.CASCADE
    )
    name_field = models.CharField(
        db_column='name', max_length=200, blank=True, null=True,
        verbose_name=_('name'), help_text=_('optional')
    )

    def get_name(self):
        if self.user:
            return self.user.get_full_name()
        return self.name_field

    def set_name(self, name):
        if not self.user:
            self.name_field = name

    def get_first_name(self):
        if self.user:
            return self.user.get_short_name()
        return self.name.split()[0] if self.name else ''

    def set_first_name(self):
        if not self.user:
            self.first_name = self.name.split()[0] if self.name else ''

    name = property(get_name, set_name)
    first_name = property(get_first_name, set_first_name)

    email = models.EmailField(
        db_column='email', verbose_name=_('e-mail'), db_index=True,
        blank=True, null=True, unique=True
    )

    def get_email(self):
        if self.user:
            return self.user.email
        return self.email

    def set_email(self, email):
        if not self.user:
            self.email = email
    e_mail = property(get_email, set_email)

    # conf_num = models.CharField(max_length=15)
    confirmed = models.BooleanField(default=False)
    city = models.CharField(max_length=200, null=True, blank=True)
    postalCode = models.CharField(max_length=200, verbose_name=_('post code'), null=True, blank=True)
    country = models.CharField(max_length=200, null=True, blank=True)
    ip = models.GenericIPAddressField(_("IP address"), blank=True, null=True)
    subscribe_date = models.DateTimeField(editable=False, default=now)
    conf_num = models.CharField(
        verbose_name=_('activation code'), max_length=40,
        default=make_activation_code
    )
    unsubscribed = models.BooleanField(
        default=False, verbose_name=_('unsubscribed'), db_index=True
    )
    unsubscribe_date = models.DateTimeField(
        verbose_name=_("unsubscribe date"), null=True, blank=True
    )
    _id = models.AutoField(primary_key=True, editable=False)

    # profiles = models.Manager()
    objects = models.Manager()

    def __str__(self):
        if self.name:
            return self.name + " <"+self.email+">" + " (" + ("not " if not self.confirmed else "") + "confirmed)" + (" (unsubscribed)" if self.unsubscribed else "")

        else:
            return "<"+self.email+">" + " (" + ("not " if not self.confirmed else "") + "confirmed)" + (" (unsubscribed)" if self.unsubscribed else "")

    class Meta:
        verbose_name = _('profile')
        verbose_name_plural = _('profiles')
        unique_together = ('user', 'email')

    def get_recipient_addr(self):
        return get_address(self.name, self.email)


class Segment(models.Model):
    segment_name = models.CharField(max_length=200, verbose_name=_('list segment name'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    _id = models.AutoField(primary_key=True, editable=False)
    profiles = models.ManyToManyField(
        'Profile',
        help_text=_('Create a dynamic segment of people based on their behaviour or properties.'),
        blank=True, db_index=True, verbose_name=_('profiles'),
        limit_choices_to={'unsubscribed': False}
    )
    # segments = models.Manager()
    objects = models.Manager()

    def members(self):
        return self.profiles.all().count()

    def __str__(self):
        return self.segment_name + " " + self.created_at.strftime("%B %d, %Y")

    class Meta:
        verbose_name = _('segment')
        verbose_name_plural = _('segments')


class Newsletter(models.Model):
    title = models.CharField(max_length=200, verbose_name=_('newsletter title'))
    slug = models.SlugField(db_index=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    subject = models.CharField(max_length=150)
    contents = models.FileField(upload_to='uploaded_newsletters/')
    _id = models.AutoField(primary_key=True, editable=False)

    objects = models.Manager()

    def __str__(self):
        return self.title + " " + self.created_at.strftime("%B %d, %Y")

    class Meta:
        verbose_name = _('newsletter')
        verbose_name_plural = _('newsletters')

    def get_absolute_url(self):
        return reverse('newsletter_detail', kwargs={'newsletter_slug': self.slug})

    def subscribe_url(self):
        return reverse('newsletter_subscribe_request', kwargs={'newsletter_slug': self.slug})

    def unsubscribe_url(self):
        return reverse('newsletter_unsubscribe_request', kwargs={'newsletter_slug': self.slug})

    def update_url(self):
        return reverse('newsletter_update_request', kwargs={'newsletter_slug': self.slug})

    def archive_url(self):
        return reverse('newsletter_archive', kwargs={'newsletter_slug': self.slug})

    def get_sender(self):
        return get_address(settings.SENDER_NAME, settings.FROM_EMAIL)

    @classmethod
    def get_default(cls):
        try:
            return cls.objects.all()[0].pk
        except IndexError:
            return None

    def send(self, request):
        contents = self.contents.read().decode('utf-8')
        profiles = Profile.objects.filter(confirmed=True, unsubscribed=False)
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        from_email = (settings.FROM_EMAIL, settings.SENDER_NAME)
        # print(from_email)
        django_engine = engines['django']
        template = django_engine.from_string(contents)
        for sub in profiles:
            context = {'first_name': sub.first_name}
            html_body = template.render(context=context, request=None)
            message = Mail(
                    from_email=from_email,
                    to_emails=sub.email,
                    subject=self.subject,
                    html_content=html_body + (
                        # '<br><a href="{}/delete/?email={}&conf_num={}">Unsubscribe</a>.').format(
                            # request.build_absolute_uri(''),
                        '<br><br><br><small><a href="{}?email={}&conf_num={}">Unsubscribe</a><small>').format(
                            request.build_absolute_uri('/newsletter/delete/'),
                            sub.email,
                            sub.conf_num))
            sg.send(message)

def get_address(name, email):
    if name:
        return '%s <%s>' % (name, email)
    else:
        return '%s' % email

    # def send(self, request):
    #     contents = self.contents.read().decode('utf-8')
    #     profiles = Profile.objects.filter(confirmed=True)
    #     from_email = (settings.FROM_EMAIL, settings.SENDER_NAME)
    #     # print(from_email)
    #     for sub in profiles:
    #         msg = EmailMessage(
    #                 from_email=from_email,
    #                 to=sub.email,
    #                 subject=self.subject,
    #                 body=contents + (
    #                     # '<br><a href="{}/delete/?email={}&conf_num={}">Unsubscribe</a>.').format(
    #                         # request.build_absolute_uri(''),
    #                     '<br><a href="{}?email={}&conf_num={}">Unsubscribe</a>.').format(
    #                         request.build_absolute_uri('/delete/'),
    #                         sub.email,
    #                         sub.conf_num))
    #         msg.reply_to = settings.REPLY_TO
    #         # msg.send_each_at
    #         send_dt = datetime.utcnow()
    #         msg.send_at = calendar.timegm(send_dt.utctimetuple())
    #         # msg.template_id = "your-dynamic-template-id"
    #         # msg.dynamic_template_data = {"title": foo}
    #         # msg.ip_pool_name = 'my-ip-pool'

    #         msg.send(fail_silently=False)


class Campaign(models.Model):
    """
    A communication campaign is a Newsletter either scheduled
    or immediately sent to a list or segment of user profiles.
    """
    _id = models.AutoField(primary_key=True, editable=False)

    emailmsg = models.ForeignKey(
        Newsletter, verbose_name=_('newsletter'), editable=True, null=False,
        on_delete=models.CASCADE
    )
    @property
    def emailmsgtitle(self):
        if self.emailmsg:
            emailmsgtitle = self.emailmsg.title
        else:
            emailmsgtitle = ''
        return emailmsgtitle

    title = models.CharField(max_length=200, verbose_name=_('campaign title'),
        editable=True, null=False,
        default='Campaign_' + str(localtime(now()).strftime("%Y-%m-%d_%H:%M:%S")))

    segments = models.ManyToManyField(
        'Segment',
        help_text=_('If you select none, the system will automatically find '
                    'the segments for you.'),
        blank=True, db_index=True, verbose_name=_('segments'),
    )

    recipients = models.ManyToManyField(
        'Profile',
        help_text=_('If you select none, the system will automatically find '
                    'the recipients for you.'),
        blank=True, db_index=True, verbose_name=_('recipients'),
        limit_choices_to={'unsubscribed': False}
    )

    send_plain = models.BooleanField(
        default=True, verbose_name=_('send plaintext'),
        help_text=_('Whether or not to send plaintext versions of e-mail.')
    )

    send_html = models.BooleanField(
        default=True, verbose_name=_('send html'),
        help_text=_('Whether or not to send HTML versions of e-mail.')
    )

    use_template = models.BooleanField(
        default=False, verbose_name=_('use html template'),
        help_text=_('Whether or not to format the html e-mail from a library template (if not uploading a html file).')
    )

    publish_date = models.DateTimeField(
        verbose_name=_('publication date'), blank=True, null=True,
        default=now, db_index=True
    )
    publish = models.BooleanField(
        default=True, verbose_name=_('publish'),
        help_text=_('Publish in archive.'), db_index=True
    )

    prepared = models.BooleanField(
        default=False, verbose_name=_('prepared'),
        db_index=True, editable=False
    )
    sent = models.BooleanField(
        default=False, verbose_name=_('sent'),
        db_index=True, editable=False
    )
    sending = models.BooleanField(
        default=False, verbose_name=_('sending'),
        db_index=True, editable=False
    )

    slug = models.SlugField(db_index=True, unique=True)

    objects = models.Manager()

    class Meta:
        verbose_name = _('campaign')
        verbose_name_plural = _('campaigns')

    def __str__(self):
        return _("%(newsletter)s on %(publish_date)s") % {
            'newsletter': self.emailmsg,
            'publish_date': self.publish_date
        }

    @cached_property
    def extra_headers(self):
        return {
            'List-Unsubscribe': 'http://%s%s' % (
                Site.objects.get_current().domain,
                reverse('newsletter_unsubscribe_request',
                        args=[self.emailmsg.slug])
            ),
        }


    def get_sender(self):
        return get_address(settings.SENDER_NAME, settings.FROM_EMAIL)


    def get_recipients(self):
        logger.debug('Looking up members of chosen segments for %s', self)
        segments = self.segments.all()
        # print ('SEGMENTS:', segments)
        profiles = segments.values('profiles___id')
        # print ("Profiles:", profiles)
        recipient_ids = [[id for key, id in profile.items()] for profile in profiles]
        # print("IDs:", recipient_ids)
        recipients = list(dict.fromkeys([i[0] for i in recipient_ids]))
        # print ("recipients", recipients)
        for recipient in recipients:
            self.recipients.add(recipient)
        return self.recipients

    def get_templates(self, action):
        """
        Return a subject, text, HTML tuple with e-mail templates for
        a particular action. Returns a tuple with subject, text and e-mail
        template.
        """

        assert action in ('message',), 'Unknown action: %s' % action
        
        # Common substitutions for filenames
        tpl_subst = {
            'action': action,
            'campaign_slug': self.slug
        }

        # Common root path for all the templates
        LETTER_TEMPLATE_DIR = f'templates/admin/{self._meta.app_label}/message_templates/'
        tpl_root = os.path.join(settings.SITE_ROOT,LETTER_TEMPLATE_DIR)
        # print ("tpl_root", tpl_root)

        subject_template = select_template([
            tpl_root + '%(campaign_slug)s/%(action)s_subject.txt' % tpl_subst,
            tpl_root + '%(action)s_subject.txt' % tpl_subst,
        ])
        # print ("subject_template", tpl_root + '%(campaign_slug)s/%(action)s_subject.txt' % tpl_subst)

        if self.send_plain:
            text_template = select_template([
                tpl_root + '%(campaign_slug)s/%(action)s.txt' % tpl_subst,
                tpl_root + '%(action)s.txt' % tpl_subst,
            ])
        else:
            text_template = None

        if (self.send_html) and (self.use_template):
            html_template = select_template([
                tpl_root + '%(campaign_slug)s/%(action)s.html' % tpl_subst,
                tpl_root + '%(action)s.html' % tpl_subst,
            ])
            # print ("html_template", tpl_root + '%(campaign_slug)s/%(action)s.html' % tpl_subst)
        else:
            html_template = None

        return subject_template, text_template, html_template

    def submit(self, request=None):
        self.get_recipients()
        recipients = self.recipients.filter(unsubscribed=False)

        logger.info(
            gettext("Submitting %(campaign)s to %(count)d people"),
            {'campaign': self, 'count': recipients.count()}
        )

        assert self.publish_date < now(), \
            'Error -  campaign creation time in the future.'

        self.sending = True
        self.save()

        site_url = Site.objects.get_current().domain
        print (site_url)
        if request:
            abs_uri = request.build_absolute_uri('/newsletter/delete/')
        else:
            site_url = 'http://127.0.0.1:8000/'  # REMOVE IN PRODUCTION
            abs_uri = f'{site_url}/newsletter/delete/'
            abs_uri = abs_uri.replace('//', '/')
            print(abs_uri)

        subject = self.emailmsg.subject.strip()
        contents = self.emailmsg.contents.read().decode('utf-8')

        (subject_template, text_template, html_template) = \
            self.get_templates('message')

        try:
            for idx, recipient in enumerate(recipients, start=1):
                if hasattr(settings, 'NEWSLETTER_EMAIL_DELAY'):
                    time.sleep(settings.NEWSLETTER_EMAIL_DELAY)
                if hasattr(settings, 'NEWSLETTER_BATCH_SIZE') and settings.NEWSLETTER_BATCH_SIZE > 0:
                    if idx % settings.NEWSLETTER_BATCH_SIZE == 0:
                        time.sleep(settings.NEWSLETTER_BATCH_DELAY)
                self.send_message(recipient, subject, contents, abs_uri, subject_template, text_template, html_template)
                print (recipient) # Saran
            self.sent = True

        finally:
            self.sending = False
            self.save()

    def send_message(self, recipient, subject, contents, abs_uri, subject_template, text_template, html_template):
        unsub_url = ("{}?email={}&conf_num={}").format(abs_uri, recipient.email, recipient.conf_num)
        message_dict = {
            'recipient': recipient,
            'site': Site.objects.get_current(),
            'campaign': self,
            'subject': subject,
            'message': self.emailmsg,
            'contents': contents,
            'date': self.publish_date,
            'STATIC_URL': settings.STATIC_URL,
            'MEDIA_URL': settings.MEDIA_URL,
            'unsub_url': unsub_url,
            'first_name':recipient.first_name
        }
        unsub = ('<br><br><br><small><a href="{}">Unsubscribe</a><small>').format(unsub_url)

        if self.send_plain:
            plaintext = text_template.render(message_dict)

            message = EmailMultiAlternatives(
                subject, plaintext,
                from_email=self.get_sender(),
                # to=[[recipient.get_recipient_addr() for recipient in self.recipients.all()]],
                to=[recipient.get_recipient_addr()],
                # headers=self.extra_headers,
            )

            if self.send_html:
                if self.use_template:
                    html_content = html_template.render(message_dict)
                else:
                    django_engine = engines['django']
                    template = django_engine.from_string(contents)
                    context = {'first_name':recipient.first_name}
                    html_body = template.render(context=context, request=None)
                    html_content = html_body + unsub

                message.attach_alternative(html_content, "text/html")
        
        else:
            django_engine = engines['django']
            template = django_engine.from_string(contents)
            context = {'first_name':recipient.first_name}
            html_body = template.render(context=context, request=None)
            html_content = html_body + unsub
            message = EmailMessage(
                subject, html_content,
                from_email=self.get_sender(),
                # to=[[recipient.get_recipient_addr() for recipient in self.recipients.all()]],
                to=[recipient.get_recipient_addr()],
            )
            message.content_subtype = "html"

        attachments = Attachment.objects.filter(campaign_id=self._id)

        for attachment in attachments:
            message.attach_file(attachment.file.path)

        try:
            logger.debug(
                gettext('Submitting message to: %s.'),
                recipient
            )
            print (f'Submitting message to: {recipient}')

            message.send(fail_silently=False)

        except Exception as e:
            # TODO: Test coverage for this branch.
            logger.error(
                gettext('Message %(recipients)s failed '
                        'with error: %(error)s'),
                {'recipients': recipient,
                 'error': e}
            )

    @classmethod
    def submit_queue(cls):
        todo = cls.objects.filter(
            prepared=True, sent=False, sending=False,
            publish_date__lt=now()
        )

        for campaign in todo:
            campaign.submit()

    @classmethod
    def from_message(cls, emailmsg, recipients):
        logger.debug(gettext('Campaign for emailmsg %s'), emailmsg)
        campaign = cls()
        campaign.emailmsg = emailmsg
        campaign.save()
        try:
            campaign.recipients.set(recipients)
        except AttributeError:  # Django < 1.10
            campaign.recipients = recipients
        return campaign

    def save(self, **kwargs):
        """ Set the newsletter from associated message upon saving. """
        assert self.emailmsg

        self.emailmsg = self.emailmsg

        return super().save()

    def get_absolute_url(self):
        assert self.emailmsg.slug

        return reverse(
            'newsletter_archive_detail', kwargs={
                'newsletter_slug': self.emailmsg.slug,
                'year': self.publish_date.year,
                'month': self.publish_date.month,
                'day': self.publish_date.day,
                'slug': self.slug
            }
        )


def attachment_upload_to(instance, filename):
    return os.path.join(
        'newsletter', 'attachments',
        datetime.utcnow().strftime('%Y-%m-%d'),
        str(instance.campaign._id),
        filename
    )


class Attachment(models.Model):
    """ Attachment for a Message. """

    campaign = models.ForeignKey(
        'Newsletter', verbose_name=_('campaign'), on_delete=models.CASCADE, related_name='attachments',
    )

    class Meta:
        verbose_name = _('attachment')
        verbose_name_plural = _('attachments')

    def __str__(self):
        return _("%(file_name)s on %(campaign)s") % {
            'file_name': self.file_name,
            'campaign': self.campaign
        }

    file = models.FileField(
        upload_to=attachment_upload_to,
        blank=False, null=False,
        verbose_name=_('attachment')
    )

    @property
    def file_name(self):
        return os.path.split(self.file.name)[1]
    

# from django.db import models
# from django.conf import settings
# from sendgrid import SendGridAPIClient
# from sendgrid.helpers.mail import Mail
# # from django.contrib.auth.models import User

# from django.core.mail import EmailMessage
# import datetime
# # import time
# import calendar

# class Profile(models.Model):
#     # user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
#     email = models.EmailField(unique=True)
#     conf_num = models.CharField(max_length=15)
#     confirmed = models.BooleanField(default=False)
#     _id = models.AutoField(primary_key=True, editable=False)

#     def __str__(self):
#         return self.email + " (" + ("not " if not self.confirmed else "") + "confirmed)"


# class Newsletter(models.Model):
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     subject = models.CharField(max_length=150)
#     contents = models.FileField(upload_to='uploaded_newsletters/')

#     def __str__(self):
#         return self.subject + " " + self.created_at.strftime("%B %d, %Y")

#     def send(self, request):
#         contents = self.contents.read().decode('utf-8')
#         profiles = Profile.objects.filter(confirmed=True)
#         sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
#         from_email = (settings.FROM_EMAIL, settings.SENDER_NAME)
#         # print(from_email)
#         for sub in profiles:
#             message = Mail(
#                     from_email=from_email,
#                     to_emails=sub.email,
#                     subject=self.subject,
#                     html_content=contents + (
#                         # '<br><a href="{}/delete/?email={}&conf_num={}">Unsubscribe</a>.').format(
#                             # request.build_absolute_uri(''),
#                         '<br><a href="{}?email={}&conf_num={}">Unsubscribe</a>.').format(
#                             request.build_absolute_uri('/delete/'),
#                             sub.email,
#                             sub.conf_num))
#             sg.send(message)


#     # def send(self, request):
#     #     contents = self.contents.read().decode('utf-8')
#     #     profiles = Profile.objects.filter(confirmed=True)
#     #     from_email = (settings.FROM_EMAIL, settings.SENDER_NAME)
#     #     # print(from_email)
#     #     for sub in profiles:
#     #         msg = EmailMessage(
#     #                 from_email=from_email,
#     #                 to=sub.email,
#     #                 subject=self.subject,
#     #                 body=contents + (
#     #                     # '<br><a href="{}/delete/?email={}&conf_num={}">Unsubscribe</a>.').format(
#     #                         # request.build_absolute_uri(''),
#     #                     '<br><a href="{}?email={}&conf_num={}">Unsubscribe</a>.').format(
#     #                         request.build_absolute_uri('/delete/'),
#     #                         sub.email,
#     #                         sub.conf_num))
#     #         msg.reply_to = settings.REPLY_TO
#     #         # msg.send_each_at
#     #         send_dt = datetime.utcnow()
#     #         msg.send_at = calendar.timegm(send_dt.utctimetuple())
#     #         # msg.template_id = "your-dynamic-template-id"
#     #         # msg.dynamic_template_data = {"title": foo}
#     #         # msg.ip_pool_name = 'my-ip-pool'

#     #         msg.send(fail_silently=False)