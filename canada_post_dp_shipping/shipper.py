"""
This dummy module can be used as a basis for creating your own

- Copy this module to a new name
- Make the changes described below
"""

# Note, make sure you use decimal math everywhere!
from decimal import Decimal
from itertools import product
import logging
from canada_post.errors import CanadaPostError
from canada_post_dp_shipping.errors import ParcelDimensionError
from canada_post_dp_shipping.utils import (get_origin, get_destination,
                                           canada_post_api_kwargs)
from django.core.cache import cache
from django.utils.translation import ugettext as _
from livesettings.functions import config_get_group
from shipping.modules.base import BaseShipper
from satchmo_store.mail import send_store_mail

from canada_post.api import CanadaPostAPI
from canada_post.util.parcel import Parcel
from canada_post_dp_shipping.models import Box
from canada_post_dp_shipping.utils.binpack_simple import binpack
from canada_post_dp_shipping.utils.package import Package

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
        self.id = "canadapost-dp-{}".format(self.service_code)
        self.settings = config_get_group('canada_post_dp_shipping')
        super(Shipper, self).__init__(cart=cart, contact=contact)

    def __unicode__(self):
        """
        This is mainly helpful for debugging purposes
        """
        return "Canada Post Developer Program"
        
    def description(self):
        """
        A basic description that will be displayed to the user when selecting
        their shipping options
        """
        return _(u"CP - {service_type}".format(
            service_type=self.service_text))

    def cost(self):
        """
        Complex calculations can be done here as long as the return value is a
        decimal figure
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
            return _(u"{days} business days".format(days=self.transit_time))
        else:
            return None

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
        self.is_valid, self.charges, self.services = self.get_rates(cart,
                                                                   contact)
        if self.services:
            self.transit_time = max(s.transit_time for s, p, d in self.services)
        self._calculated = True

    def get_rates(self, cart, contact):
        from satchmo_store.shop.models import Config
        error_ret = False, None, []
        shop_details = Config.objects.get_current()

        # always use production api keys for get_rates, you don't get charged
        #  anyways
        cpa_kwargs = canada_post_api_kwargs(self.settings, production=True)

        cpa = CanadaPostAPI(**cpa_kwargs)

        # parcels is a list of (Parcel, pack(dimensions))
        parcels, rest = self.make_parcels(cart)
        if rest:
            from django.contrib.sites.models import Site
            site = Site.objects.get_current()
            error_message = (u"There's not boxes big enough for some of these "
                             u"products: ({})").format(u", ".join(
                u"Package({})".format(unicode(p)) for p in rest))
            subject = u"There's not boxes big enough for some products"
            send_store_mail(subject, context={ 'site': site,
                                               'product_list': rest },
                            template=("canada_post_dp_shipping/admin/mail/"
                                      "add_boxes.txt"), send_to_store=True)
            raise ParcelDimensionError, error_message
        log.debug(u"Calculated Parcels: [%s]", u",".join(u"({},[{}])".format(
            pr, ",".join(unicode(pk) for pk in pks)) for pr, pks in parcels))
        origin = get_origin(shop_details)
        destination = get_destination(contact)

        services = []
        for parcel, packs in parcels:
            # rates depend on dimensions + origin + destination only
            cache_key = "CP-GetRates-{W}-{l}x{w}x{h}-{fr}-{to}".format(
                W=parcel.weight, w=parcel.width, h=parcel.height, l=parcel.length,
                fr=origin.postal_code, to=destination.postal_code
            )
            if cache.has_key(cache_key):
                parcel_services = cache.get(cache_key)
            else:
                try:
                    parcel_services = cpa.get_rates(parcel, origin, destination)
                except CanadaPostError, e:
                    if self.settings.RAISE_TOO_LARGE.value and e.code == 9111:
                        raise ParcelDimensionError, e.message
                    else:
                        log.error("Canada Post returned with error: %s|%s",
                                  e.code, e.message)
                    parcel_services = []
                cache.set(cache_key, parcel_services)

            # so services is [(Service, parcel, [packs]),...]
            services.extend(product(filter(lambda s: s.code == self.service_code,
                                      parcel_services), [parcel], [packs]))

        if len(services) != len(parcels):
            # Not all parcels can be sent through this service
            return error_ret
        cost = Decimal("0.00")
        for service, parcel, packs in services:
            cost += service.price.total
        return True, cost, services

    def make_parcels(self, cart):
        items = cart.get_shipment_by_amount()
        packages = []
        for amt, item in items:
            length = item.smart_attr("length")
            width = item.smart_attr("width")
            height = item.smart_attr("height")
            weight = item.smart_attr("weight")
            if not all((length, width, height, weight)):
                log.error("Dimensions error in item %s(#%d): (%s, %s, %s, %s)",
                          item, item.id, length, width, height, weight)
                raise ParcelDimensionError, (u"Dimension errors in item {}: "
                                       u"({},{},{},{})").format(item, length,
                                                               width, height,
                                                               weight)
            for _ in range(amt):
                packages.append(Package((length, width, height), weight=weight, description=u"{}(#{})".format(item.name, item.id)))

        boxes = []
        for box in Box.objects.all():
            boxes.append(Package((box.length, box.width, box.height)))
        packed, rest = binpack(packages, boxes)
        parcels = []
        if not rest:
            for packs, bin in packed:
                for pack in packs:
                    weight = sum(p.weight for p in pack)
                    parcels.append((Parcel(length = bin[0], width=bin[1],
                                           height=bin[2], weight=weight),pack))
        return parcels, rest
