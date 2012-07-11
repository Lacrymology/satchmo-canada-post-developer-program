"""
This dummy module can be used as a basis for creating your own

- Copy this module to a new name
- Make the changes described below
"""

# Note, make sure you use decimal math everywhere!
import logging
from canada_post.api import CanadaPostAPI
from canada_post.util.address import Origin, Destination
from canada_post.util.parcel import Parcel
from django.core.cache import cache
from django.utils.translation import ugettext as _
from livesettings.functions import config_get_group
from shipping.modules.base import BaseShipper

log = logging.getLogger('canada-post-dev-program.shipper')

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
        self.id = "canadapost-dev-prog-{}".format(self.service_code)
        self.settings = config_get_group('canada_post_dp_shipping')
        super(Shipper, self).__init__(cart=cart, contact=contact)

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
        return _("Canada Post Developer Program")

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
        return self.is_valid

    def calculate(self, cart, contact):
        """
        Here we decide for a packaging solution, generate a call to GetRates and
        cache it, and calculate the cost and transit of the current service, if
        available
        """
        log.debug('Start Canada Post Dev Prog calculation')

        verbose = self.settings.VERBOSE_LOG.value

        self.transit_time = None # unknown transit time, as yet
        self.is_valid, self.service = self.get_rates(cart, contact)
        self._calculated = True

    def get_rates(self, cart, contact):
        from satchmo_store.shop.models import Config
        shop_details = Config.objects.get_current()

        cpa = CanadaPostAPI(self.settings.CUSTOMER_NUMBER.value,
                            self.settings.USERNAME.value,
                            self.settings.PASSWORD.value,)

        parcels = self.make_parcel(cart)
        log.debug("Calculated Parcels: ", parcels)
        origin = Origin(postal_code=shop_details.postal_code)
        destination = Destination(
            postal_code=contact.shipping_address.postal_code)

        my_services = []
        for parcel in parcels:
            # rates depend on dimensions + origin + destination only
            cache_key = "CP-GetRates-{W}-{l}x{w}x{h}-{fr}-{to}".format(
                W=parcel.weight, w=parcel.width, h=parcel.height, l=parcel.length,
                fr=origin.postal_code, to=destination.postal_code
            )
            if cache.has_key(cache_key):
                services = cache.get(cache_key)
            else:
                services = cpa.get_rates(parcel, origin, destination)
                cache.set(cache_key, services)

            my_services.extend(filter(lambda s: s.code == self.service_code,
                                      services))

        service = None
        valid = False
        if len(my_services) == len(parcels):
            service = my_services[0]
            valid = True
        return valid, service

    def make_parcel(self, cart):
        return Parcel()