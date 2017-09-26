from ckan.lib.celery_app import celery
import ckan.lib.helpers as h
import ckan.lib.mailer as mailer
import ckan.lib.base as base
import ckan.lib.uploader as uploader
from ckan.common import OrderedDict, _, json, request, c, g, response
from email.mime.text import MIMEText
from email.header import Header
from email import Utils
from time import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.utils import COMMASPACE, formatdate
import socket
import logging

abort = base.abort
redirect = base.redirect
log = logging.getLogger(__name__)


@celery.task(name="NAME.subset_create")
def subset_create(message, res, request, smtp_server, smtp_send_from, smtp_user, smtp_password, send_to, smtp_starttls):
    # sending of email after successful subset creation
    # copied nearly everything from mail_recipient (cannot use method because there is no config)
    subject = 'Subset Download'
    body = 'Your subset is ready to download'
    msg = MIMEText(body.encode('utf-8'), 'plain', 'utf-8')
    subject = Header(subject.encode('utf-8'), 'utf-8')
    msg['Subject'] = subject
    msg['From'] = smtp_send_from
    msg['To'] = Header(send_to, 'utf-8')
    msg['Date'] = Utils.formatdate(time())

    # Send the email using Python's smtplib.
    smtp_connection = smtplib.SMTP()

    try:
        smtp_connection.connect(smtp_server)
    except socket.error, e:
        raise MailerException('SMTP server could not be connected to: "%s" %s'
                              % (smtp_server, e))

    try:
        # Identify ourselves and prompt the server for supported features.
        smtp_connection.ehlo()

        # If 'smtp.starttls' is on in CKAN config, try to put the SMTP
        # connection into TLS mode.
        if smtp_starttls:
            if smtp_connection.has_extn('STARTTLS'):
                smtp_connection.starttls()
                # Re-identify ourselves over TLS connection.
                smtp_connection.ehlo()
            else:
                raise MailerException("SMTP server does not support STARTTLS")

        # If 'smtp.user' is in CKAN config, try to login to SMTP server.
        if smtp_user:
            assert smtp_password, ("If smtp.user is configured then "
                                   "smtp.password must be configured as well.")
            smtp_connection.login(smtp_user, smtp_password)

        smtp_connection.sendmail(smtp_send_from, send_to, msg.as_string())
        log.info("Sent email to {0}".format(send_to))

    except smtplib.SMTPException, e:
        msg = '%r' % e
        log.exception(msg)
        raise MailerException(msg)
    finally:
        smtp_connection.quit()


class MailerException(Exception):
    pass
