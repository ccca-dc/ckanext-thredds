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
import requests
from xml.etree import ElementTree
import urllib

abort = base.abort
redirect = base.redirect
log = logging.getLogger(__name__)


@celery.task(name="NAME.subset_create")
def subset_create(res, ckan_url, params, smtp_server, smtp_send_from, smtp_user, smtp_password, send_to, smtp_starttls):

    req_params = params.copy()
    req_params['response_file'] = "false"
    headers = {"Authorization":""}

    r = requests.get('http://sandboxdc.ccca.ac.at/tds_proxy/ncss/88d350e9-5e91-4922-8d8c-8857553d5d2f', params=req_params, headers=headers)
    print(params)

    tree = ElementTree.fromstring(r.content)
    location = tree.get('location')

    lat_lon_box = tree.findall('LatLonBox')
    params['north'] = lat_lon_box[0].find('north').text
    params['east'] = lat_lon_box[0].find('east').text
    params['south'] = lat_lon_box[0].find('south').text
    params['west'] = lat_lon_box[0].find('west').text

    time_span = tree.findall('TimeSpan')
    params['time_start'] = time_span[0].find('begin').text
    params['time_end'] = time_span[0].find('begin').text

    correct_url = ('%s/tds_proxy/ncss/%s?%s' % (ckan_url, res['id'], urllib.urlencode(params)))

    print(params)
    print(correct_url)

    # sending of email after successful subset creation
    # copied nearly everything from mail_recipient (cannot use method because there is no config)
    subject = 'Subset Download'
    body = 'Your subset is ready to download: ' + location
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
