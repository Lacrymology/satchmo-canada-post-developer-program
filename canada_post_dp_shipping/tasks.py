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
    USE_CELERY = True
except ImportError, e:
    log.info("Not using celery: %s", e)
    task = None
