import logging
from canada_post_dp_shipping.models import Shipment

log = logging.getLogger('canada_post_dp_shipping.tasks')
USE_CELERY = False
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
