import logging
from django.contrib.sites.models import Site
from django.core.files import File
from django.template import Context
from django.template.loader import get_template
from canada_post.api import CanadaPostAPI
from canada_post_dp_shipping.models import (Shipment, Manifest,
                                            OrderShippingService)
from livesettings import config_get_group
from canada_post_dp_shipping.utils import (canada_post_api_kwargs, get_origin,
                                           time_f)
from django.utils.translation import ungettext_lazy
import os
from satchmo_store.mail import send_store_mail

log = logging.getLogger('canada_post_dp_shipping.tasks')
USE_CELERY = False

def get_manifests(links):
    log.info("Getting manifests from links: %s", links)
    settings = config_get_group('canada_post_dp_shipping')
    cpa_kwargs = canada_post_api_kwargs(settings)
    cpa = CanadaPostAPI(**cpa_kwargs)
    manifests = []
    for link in links:
        log.debug("Getting manifest from %s", link['href'])
        cpa_manifest = time_f(cpa.get_manifest,
                              'canada-post-dp-shipping.get-manifest', link)
        manifest = Manifest(manifest=cpa_manifest)
        manifest_pdf = time_f(cpa.get_artifact,
                              'canada-post-dp-shipping.get-artifact',
                              cpa_manifest)
        filename = os.path.basename(link['href'].rstrip('/'))
        if not filename.endswith('.pdf'):
            filename += '.pdf'
        manifest.artifact = File(manifest_pdf, filename)
        manifest.save()
        shipments = time_f(cpa.get_manifest_shipments,
                           'canada-post-dp-shipping.get-manifest-shipments',
                           cpa_manifest)
        for shipment_id in shipments:
            log.info("Setting manifest for shipment %s", shipment_id)
            try:
                shipment = Shipment.objects.select_related().get(id=shipment_id)
                shipping_detail = shipment.parcel.shipping_detail
                shipping_detail.manifest = manifest
                shipping_detail.save()
            except Shipment.DoesNotExist:
                log.error("Requested shipment does not exist")
        manifests.append(manifest)

    subject_template = get_template(
        'canada_post_dp_shipping/admin/mail/manifests_subject.txt')
    subject = subject_template.render(Context({
        'manifests': manifests
    })).strip()

    site = Site.objects.get_current()
    send_store_mail(subject, context={ 'site': site,
                                       'manifests': manifests },
                    template=("canada_post_dp_shipping/admin/mail/"
                              "manifests_body.txt"), send_to_store=True)

def transmit_shipments(queryset=None, send_msg=None):
    log.info("transmit_shipments invoked")
    log.debug("queryset: %s", str(queryset))
    if send_msg is None:
        send_msg = lambda x: x

    if queryset is None:
        queryset = OrderShippingService.objects.all()

    from satchmo_store.shop.models import Config
    shop_details = Config.objects.get_current()
    settings = config_get_group('canada_post_dp_shipping')
    cpa_kwargs = canada_post_api_kwargs(settings)
    cpa = CanadaPostAPI(**cpa_kwargs)
    origin = get_origin(shop_details)

    groups = []
    order_shippings = []

    for order_shipping in queryset.filter(
            transmitted=False):
        log.debug("processing order shipping: %s", order_shipping)
        if order_shipping.shipments_created():
            log.debug("shipments created")
            group = unicode(order_shipping.shipping_group())
            groups.append(group)
            order_shippings.append(order_shipping)
        else:
            log.debug("shipments not created")
    log.debug("using groups: %s", groups)
    if groups:
        log.info("transmitting shipments")
        links = time_f(cpa.transmit_shipments,
                       'canada-post-dp-shipping.transmit-shipments',
                       origin, groups)
        log.debug("received manifests: %s", links)
        log.debug("marking order shippings as transmitted")
        for order_shipping in order_shippings:
            order_shipping.transmitted = True
            order_shipping.save()
        manifest_count = len(links)
        log.info("received %d manifests", manifest_count)
        send_msg(ungettext_lazy(
            "{count} manifest generated. It will be sent via email in a "
            "couple of minutes".format(count=manifest_count),
            "{count} manifests generated. They will be sent via email in a "
            "couple of minutes".format(count=manifest_count), manifest_count))
        if USE_CELERY:
            get_manifests_async.apply_async(args=(links,), cowntdown=1)
        else:
            get_manifests(links)

    group_count = len(groups)
    send_msg(ungettext_lazy(
        "Transmitted shipments for {count} group".format(count=group_count),
        "Transmitted shipments for {count} groups".format(count=group_count),
        group_count))

try:
    from celery.task import task
    @task
    def get_label(shipment_id, username, password):
        try:
            shipment = Shipment.objects.get(id=shipment_id)
            return shipment.download_label(username, password)
        except Shipment.DoesNotExist:
            log.warning("Shipment %s doesn't exist. Has it been canceled?",
                        shipment_id)

    @task
    def get_manifests_async(*args, **kwargs):
        return get_manifests(*args, **kwargs)

    @task
    def transmit_shipments_async(*args, **kwargs):
        return transmit_shipments(*args, **kwargs)

    USE_CELERY = True
except ImportError, e:
    log.info("Not using celery: %s", e)
    task = None
