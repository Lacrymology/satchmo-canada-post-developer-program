"""
This dummy module can be used as a basis for creating your own

- Copy this module to a new name
- Make the changes described below
"""

# Note, make sure you use decimal math everywhere!
from decimal import Decimal
import logging
import canada_post
from canada_post.service import rating
from canada_post.util.address import Origin, Destination
from canada_post.util.parcel import Parcel
from django.core.cache import cache
from django.utils.translation import ugettext as _
from livesettings.functions import config_get_group
from satchmo_store.shop.models import Config
from shipping.modules.base import BaseShipper

log = logging.getLogger(__file__)

class Shipper(BaseShipper):

    def __init__(self, cart=None, contact=None, service_type=None):
        """
        Initialize a Shipper for a given service type
        """
        if service_type:
            self.service_code, self.service_text = service_type
        else:
            self.service_code = "BAD.CODE"
            self.service_text = "Uninitialized"
        self.id = "canadapost-dev-prog-{}".format(self.service_text)
        super(BaseShipper, self).__init__(cart=cart, contact=contact)

    def __str__(self):
        """
        This is mainly helpful for debugging purposes
        """
        return "Canada Post Developer Program"
        
    def description(self):
        """
        A basic description that will be displayed to the user when selecting their shipping options
        """
        return _("Canada Post - {service_type}".format(
            service_type=self.service_text))

    def cost(self):
        """
        Complex calculations can be done here as long as the return value is a decimal figure
        """
        assert self._calculated
        return self.charges

    def method(self):
        """
        Describes the actual delivery service (Mail, FedEx, DHL, UPS, etc)
        """
        return _("Canada Post")

    def expectedDelivery(self):
        """
        Can be a plain string or complex calcuation returning an actual date
        """
        if self.transit_time is not None:
            return _("{days} business days".format(days=self.transit_time))
        else:
            return _("Unknown")

    def valid(self, order=None):
        """
        Can do complex validation about whether or not this option is valid.
        For example, may check to see if the recipient is in an allowed country
        or location.
        """
        return True

