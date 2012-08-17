import logging

log = logging.getLogger('canada_post_dp_shipping.tasks')
USE_CELERY = False
try:
    from celery.task import task
    @task
    def get_label(shipment, username, password):
        return shipment.download_label(username, password)
    USE_CELERY = True
except ImportError, e:
    log.info("Not using celery: %s", e)
    task = None
