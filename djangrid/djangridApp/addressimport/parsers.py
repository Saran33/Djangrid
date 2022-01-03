import logging
logger = logging.getLogger(__name__)

import io

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.translation import gettext as _

from djangridApp.models import Profile


class AddressList(object):
    """ List with unique addresses. """

    def __init__(self, ignore_errors=False):
        self.ignore_errors = ignore_errors
        self.addresses = {}

    def add(self, email, name=None, city=None, postalCode=None, country=None, location='unknown location',):
        """ Add name to list. """

        logger.debug("Going to add %s <%s>", name, email)

        name = check_name(name, ignore_errors=self.ignore_errors)
        email = check_field(email, field_name='email', ignore_errors=self.ignore_errors)
        city = check_field(city, field_name='city', ignore_errors=self.ignore_errors)
        postalCode = check_field(postalCode, field_name='postalCode', ignore_errors=self.ignore_errors)
        country = check_field(country, field_name='country', ignore_errors=self.ignore_errors)

        try:
            validate_email(email)
        except ValidationError:
            logger.warning(
                "Entry '%s' does not contain a valid e-mail address at %s."
                % (email, location)
            )

            if not self.ignore_errors:
                raise forms.ValidationError(_(
                    "Entry '%s' does not contain a valid "
                    "e-mail address.") % name
                )

            # Skip this entry
            return

        if email in self.addresses:
            logger.warning(
                "Entry '%s' contains a duplicate entry at %s."
                % (email, location)
            )

            if not self.ignore_errors:
                raise forms.ValidationError(_(
                    "The address file contains duplicate entries "
                    "for '%s'.") % email)

            # Skip this entry
            return

        if profile_exists(email, name):
            logger.warning(
                "Entry '%s' is already subscribed to at %s."
                % (email, location)
            )

            if not self.ignore_errors:
                raise forms.ValidationError(
                    _("Some entries are already subscribed to."))

            # Skip this entry
            return

        # self.addresses[email] = name

        self.addresses[email] = {}
        self.addresses[email]['name'] = name
        self.addresses[email]['city'] = city
        self.addresses[email]['postalCode'] = postalCode
        self.addresses[email]['country'] = country
        

def profile_exists(email, name=None):
    """
    Return wheter or not a profile exists.
    """
    qs = Profile.objects.filter(
        email=email,
        )

    return qs.exists()


def check_email(email, ignore_errors=False):
    """
    Check (length of) email address.

    TODO: Update this to perform full validation on email.
    """

    logger.debug("Checking e-mail address %s", email)

    email_length = Profile._meta.get_field('email').max_length

    # Get rid of leading/trailing spaces
    email = email.strip()

    if len(email) <= email_length or ignore_errors:
        return email[:email_length]
    else:
        raise forms.ValidationError(
            _(
                "E-mail address %(email)s too long, maximum length is "
                "%(email_length)s characters."
            ) % {
                "email": email,
                "email_length": email_length
            }
        )


def check_name(name, ignore_errors=False):
    """
    Check (length of) name.

    TODO: Update this to perform full validation on name.
    """
    logger.debug("Checking name: %s", name)

    name_length = Profile._meta.get_field('name_field').max_length

    # Get rid of leading/trailing spaces
    name = name.strip()

    if len(name) <= name_length or ignore_errors:
        return name[:name_length]
    else:
        raise forms.ValidationError(
            _(
                "Name %(name)s too long, maximum length is "
                "%(name_length)s characters."
            ) % {
                "name": name,
                "name_length": name_length
            }
        )

def check_field(field, field_name, ignore_errors=False):
    """
    Check (length of) a field.

    TODO: Update this to perform full validation on fields.
    """
    logger.debug("Checking %s: %s", field_name, field)

    field_length = Profile._meta.get_field(field_name).max_length

    # Get rid of leading/trailing spaces
    field = field.strip()

    if len(field) <= field_length or ignore_errors:
        # print('\n', field_name, field, '\n')
        return field[:field_length]
    else:
        cap_field_name = field_name.capitalize()
        raise forms.ValidationError(
            _(
                "%(cap_field_name)s: %(field)s too long, maximum length is "
                "%(field_length)s characters."
            ) % {
                "cap_field": cap_field_name,
                "name": field,
                "name_length": field_length
            }
        )


def get_encoding(myfile):
    """ Returns encoding of file, rewinding the file after detection. """

    # Detect encoding
    from chardet.universaldetector import UniversalDetector

    detector = UniversalDetector()

    for line in myfile.readlines():
        detector.feed(line)
        if detector.done:
            break

    detector.close()
    encoding = detector.result['encoding']

    # Reset the file index
    myfile.seek(0)

    return encoding


def parse_csv(myfile, ignore_errors=False):
    """
    Parse addresses from CSV file-object into list.

    Returns a dictionary mapping email addresses into Profile objects.
    """

    import unicodecsv

    encoding = get_encoding(myfile)

    # Attempt to detect the dialect
    # Ref: https://bugs.python.org/issue5332
    encodedfile = io.TextIOWrapper(myfile, encoding=encoding, newline='')
    dialect = unicodecsv.Sniffer().sniff(encodedfile.read(1024))

    # Reset the file index
    myfile.seek(0)

    logger.info('Detected encoding %s and dialect %s for CSV file',
                encoding, dialect)

    myreader = unicodecsv.reader(myfile, dialect=dialect, encoding=encoding)

    firstrow = next(myreader)

    # Find name column
    colnum = 0
    namecol = None
    for column in firstrow:
        if "name" in column.lower() or _("name") in column.lower():
            namecol = colnum

            if "display" in column.lower() or \
                    _("display") in column.lower():
                break

        colnum += 1

    if namecol is None:
        raise forms.ValidationError(_(
            "Name column not found. The name of this column should be "
            "either 'name' or '%s'.") % _("name")
        )

    logger.debug("Name column found: '%s'", firstrow[namecol])

    # Find email column
    colnum = 0
    mailcol = None
    for column in firstrow:
        if 'email' in column.lower() or \
                'e-mail' in column.lower() or \
                _("e-mail") in column.lower():

            mailcol = colnum

            break

        colnum += 1

    if mailcol is None:
        raise forms.ValidationError(_(
            "E-mail column not found. The name of this column should be "
            "either 'email', 'e-mail' or '%(email)s'.") %
            {'email': _("e-mail")}
        )

    logger.debug("E-mail column found: '%s'", firstrow[mailcol])

    if namecol == mailcol:
        raise forms.ValidationError(
            _(
                "Could not properly determine the proper columns in the "
                "CSV-file. There should be a field called 'name' or "
                "'%(name)s' and one called 'e-mail' or '%(email)s'."
            ) % {
                "name": _("name"),
                "email": _("e-mail")
            }
        )

    # Find city column
    colnum = 0
    citycol = None
    for column in firstrow:
        if 'city' in column.lower() or \
            _("city") in column.lower():

            citycol = colnum

            break

        colnum += 1

    # if citycol is None:
    #     raise forms.ValidationError(_(
    #         "City column not found. The name of this column should be "
    #         "either 'city', 'city' or '%(city)s'.") %
    #         {'city': _("city")}
    #     )

    logger.debug("City column found: '%s'", firstrow[citycol])

    # Find Post Code column
    colnum = 0
    postalcol = None
    for column in firstrow:
        if 'postalcode' in column.lower() or \
            'post code' in column.lower() or \
                'postal code' in column.lower() or \
                    _("post code") in column.lower():

            postalcol = colnum

            break

        colnum += 1

    # if postalcol is None:
    #     raise forms.ValidationError(_(
    #         "Postal Code column not found. The name of this column should be "
    #         "either 'postalCode', 'Post Code' or '%(postalCode)s'.") %
    #         {'postalCode': _("postalCode")}
    #     )

    logger.debug("postalCode column found: '%s'", firstrow[postalcol])

    # Find country column
    colnum = 0
    countrycol = None
    for column in firstrow:
        if 'country' in column.lower() or \
            _("country") in column.lower():

            countrycol = colnum

            break

        colnum += 1

    # if countrycol is None:
    #     raise forms.ValidationError(_(
    #         "Country column not found. The name of this column should be "
    #         "either 'country', or '%(country)s'.") %
    #         {'country': _("country")}
    #     )


    logger.debug('Extracting data.')

    address_list = AddressList(ignore_errors)

    for row in myreader:
        if not max(namecol, mailcol) < len(row):
            logger.warning(
                "Column count does not match for row number %d",
                myreader.line_num, extra=dict(data={'row': row})
            )

            if ignore_errors:
                # Skip this record
                continue
            else:
                raise forms.ValidationError(_(
                    "Row with content '%(row)s' does not contain a name and "
                    "email field.") % {'row': row}
                )

        address_list.add(
            # row[mailcol], row[namecol], location="line %d" % myreader.line_num
            row[mailcol], row[namecol], row[citycol], row[postalcol], row[countrycol], location="line %d" % myreader.line_num
        )

    # print ("address_list_items:", address_list.addresses.items())
    return address_list.addresses


def parse_vcard(myfile,ignore_errors=False):
    """
    Parse addresses from vCard file-object into profiles.

    Returns a dictionary mapping email addresses into Profile objects.
    """
    import card_me

    encoding = get_encoding(myfile)
    encodedfile = io.TextIOWrapper(myfile, encoding=encoding)

    try:
        myvcards = card_me.readComponents(encodedfile)
    except card_me.VObjectError as e:
        raise forms.ValidationError(
            _("Error reading vCard file: %s" % e)
        )

    address_list = AddressList(ignore_errors)

    for myvcard in myvcards:
        if hasattr(myvcard, 'fn'):
            name = myvcard.fn.value
        else:


            name = None

        # Do we have an email address?
        # If not: either continue to the next vcard or raise validation error.
        if hasattr(myvcard, 'email'):
            email = myvcard.email.value
        elif not ignore_errors:
            raise forms.ValidationError(
                _("Entry '%s' contains no email address.") % name)
        else:
            continue

        address_list.add(email, name)

    return address_list.addresses


def parse_ldif(myfile, ignore_errors=False):
    """
    Parse addresses from LDIF file-object into profiles.

    Returns a dictionary mapping email addresses into Profile objects.
    """

    from ldif3 import LDIFParser

    address_list = AddressList(ignore_errors)

    try:
        parser = LDIFParser(myfile)

        for dn, entry in parser.parse():
            if 'mail' in entry:
                email = entry['mail'][0]

                if 'cn' in entry:
                    name = entry['cn'][0]
                else:
                    name = None

                address_list.add(email, name)

            elif not ignore_errors:
                raise forms.ValidationError(
                    _("Some entries have no e-mail address."))

    except ValueError as e:
        if not ignore_errors:
            raise forms.ValidationError(e)

    return address_list.addresses
