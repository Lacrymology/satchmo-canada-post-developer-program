import logging
from django.core.files import File
import requests
from canada_post.api import CanadaPostAPI
from canada_post_dp_shipping.models import Shipment, Manifest
from livesettings import config_get_group
from canada_post_dp_shipping.utils import canada_post_api_kwargs
import os

log = logging.getLogger('canada_post_dp_shipping.tasks')
USE_CELERY = False

def get_manifests(links):
    log.info("Getting manifests from links: %s", links)
    settings = config_get_group('canada_post_dp_shipping')
    cpa_kwargs = canada_post_api_kwargs(settings)
    cpa = CanadaPostAPI(**cpa_kwargs)
    for link in links:
        log.debug("Getting manifest from %s", link['href'])
        cpa_manifest = cpa.get_manifest(link)
        manifest = Manifest(manifest=cpa_manifest)
        manifest_pdf = cpa.get_artifact(cpa_manifest)
        filename = os.path.basename(link.rstrip('/'))
        manifest.artifact = File(manifest_pdf, filename)
        manifest.save()
        shipments = cpa.get_manifest_shipments(cpa_manifest)
        for shipment_id in shipments:
            shipment = Shipment.objects.get(id=shipment_id).select_related()
            shipping_detail = shipment.parcel.shipping_detail
            shipping_detail.manifest = manifest
            shipping_detail.save()

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

    USE_CELERY = True
except ImportError, e:
    log.info("Not using celery: %s", e)
    task = None
