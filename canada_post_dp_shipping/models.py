"""
Models for the canada post developer program's shipping method
"""
from os import path
import requests
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from canada_post.service import Service
from canada_post.util.parcel import Parcel
from canada_post.service.contract_shipping import (Shipment as CPAShipment)
from jsonfield.fields import JSONField

from satchmo_store.shop.models import Order, OrderCart

class Box(models.Model):
    """
    These boxes are used for parcel calculation, they need to be filled in
    before the shipping method can be used
    """
    description = models.CharField(verbose_name=_("description"), max_length=64,
                                   help_text=_("Box name"), unique=True)
    length = models.DecimalField(verbose_name=_("length"), max_digits=4,
                                 decimal_places=1,
                                 help_text=_("Longest dimension in cm"))
    width = models.DecimalField(verbose_name=_("width"), max_digits=4,
                                decimal_places=1,
                                help_text=_("Second longest dimension in cm"))
    height = models.DecimalField(verbose_name=_("width"), max_digits=4,
                                decimal_places=1,
                                help_text=_("Shortest dimension in cm"))

    def __unicode__(self):
        return "{} {}x{}x{}".format(self.description, self.length,
                                    self.width, self.height)

    class Meta:
        verbose_name = _("box")
        verbose_name_plural = _("boxes")
        ordering = ['-length', '-width', '-height']
        # each box must be unique
        unique_together = ("length", "width", "height")

    def girth(self):
        return self.length + 2 * (self.width + self.height)

    def volume(self):
        return self.length * self.width * self.height

class OrderShippingService(models.Model):
    """
    Save shipping details, such as link and product code
    """
    order = models.OneToOneField(Order, verbose_name=_("order"), editable=False)
    code = models.CharField(max_length=16, verbose_name=_("code"),
                            help_text=_("Internal Canada Post product code"))

    def get_service(self):
        return Service(data={'code': self.code})

    def parcel_count(self):
        return self.parceldescription_set.count()

    def shipping_group(self):
        """
        Returns a shipping group name to be passed to the Canada Post API.
        alpha-numerical 32 char string
        """
        return "order_{order_id}__{this_id}".format(order_id=self.order.id,
                                                    this_id=self.id)

    def shipments_created(self):
        try:
            return all(bool(parcel.shipment)
                for parcel in self.parceldescription_set.all())
        except Shipment.DoesNotExist:
            return False
    shipments_created.boolean = True

    def has_labels(self):
        try:
            return all(bool(parcel.shipment.label)
                for parcel in self.parceldescription_set.all())
        except Shipment.DoesNotExist:
            return False
    has_labels.boolean = True

    def __unicode__(self):
        return _("Shipping service detail for {order}").format(order=self.order)

class ParcelDescription(models.Model):
    shipping_detail = models.ForeignKey(OrderShippingService)
    box = models.ForeignKey(Box)
    parcel = models.CharField(max_length=256,
                              verbose_name=_("parcel description"),
                              help_text=_("List of packages that go inside "
                                          "this parcel"),)
    weight = models.DecimalField(max_digits=5, decimal_places=3,
                                 verbose_name=_("weight"),
                                 help_text=_("Total weight of the parcel, "
                                             "in kilograms"))

    def __init__(self, *args, **kwargs):
        if 'parcel' in kwargs:
            pass
        elif 'packs' in kwargs:
            packs = kwargs.pop('packs')
            parcel = "[{}]".format(",".join("({})".format(unicode(p))
                for p in packs))
            weight = sum(p.weight for p in packs)
            kwargs.update({
                'parcel': parcel,
                'weight': weight,
                })
        super(ParcelDescription, self).__init__(*args, **kwargs)

    def get_parcel(self):
        return Parcel(length=self.box.length, width=self.box.width,
                      height=self.box.height, weight=self.weight)

    def __unicode__(self):
        return "Parcel({})".format(unicode(self.box))

class Shipment(models.Model):
    """
    Shipment data, returned by Canada Post's Create Shipment service
    """
    def label_path(instance, filename):
        """
        Construct the path for the label file
        """
        return ("canada_post_dp_shipping/labels/"
                "order_{order_id}__shipment_{shipment_id}__{filename}").format(
            order_id=instance.parcel.shipping_detail.order.id,
            shipment_id = instance.id, filename=filename)

    id = models.CharField(max_length=32, primary_key=True, editable=False)
    tracking_pin = models.BigIntegerField(blank=True, null=True, default=None)
    return_tracking_pin = models.BigIntegerField(blank=True, null=True,
                                                 default=None)
    status = models.CharField(max_length=14)
    parcel = models.OneToOneField(ParcelDescription, verbose_name=_("parcel"))
    label = models.FileField(upload_to=label_path, blank=True, null=True,
                             verbose_name=_("label"))

    def delete(self, *args, **kwargs):
        if self.label:
            self.label.delete()
        super(Shipment, self).delete(*args, **kwargs)

    def download_label(self, username, password):
        link = self.shipmentlink_set.get(type='label')
        res = requests.get(link.data['href'], auth=(username, password))
        if res.status_code == 202:
            raise Shipment.Wait
        if not res.ok:
            res.raise_for_status()
        img_temp = NamedTemporaryFile(delete=True)
        img_temp.write(res.content)
        img_temp.flush()
        filepath = requests.utils.urlparse(link.data['href']).path
        filename = path.basename(filepath)
        if not filename.lower().endswith('.pdf'):
            filename = filename + ".pdf"
        self.label = File(img_temp, filename)
        self.save()

    def get_shipment(self):
        """
        Creates a canada_post.utils.Shipment object for use with the
        Canada Post API
        """
        # if this instance was created from a Shipment, we've got it saved.
        if getattr(self, 'shipment', None):
            return self.shipment
        # else, we need to construct it
        kwargs = {
            'id': self.id,
            'status': self.status,
            'tracking_pin': self.tracking_pin,
            'return_tracking_pin': self.return_tracking_pin,
            'links': {}
        }
        for link in self.shipmentlink_set.all():
            kwargs['links'][link.type] = link.data
        return CPAShipment(**kwargs)

    def __init__(self, *args, **kwargs):
        if 'shipment' in kwargs:
            shipment = kwargs.pop('shipment')
            kwargs.update({
                'id': shipment.id,
                'status': shipment.status,
                'tracking_pin': getattr(shipment, 'tracking_pin', None),
                'return_tracking_pin': getattr(shipment, 'return_tracking_pin',
                                               None),
                })
            self.shipment = shipment
        super(Shipment, self).__init__(*args, **kwargs)

    def __unicode__(self):
        return "Shipment {} for {}".format(
            self.id, self.parcel.shipping_detail.order)

    class Wait(Exception):
        pass

@receiver(post_save, sender=Shipment)
def create_links(sender, instance, created, **kwargs):
    if created:
        shipment  = getattr(instance, 'shipment', None)
        if shipment:
            for type, link in getattr(shipment, 'links', {}).items():
                link = ShipmentLink(shipment=instance, type=type, data=link)
                link.save()

class ShipmentLink(models.Model):
    """
    Any of a number of links returned by Canada Post at CreateShipment time
    """
    shipment = models.ForeignKey(Shipment)
    type = models.CharField(max_length=16)
    data = JSONField(blank=True)

@receiver(post_save, sender=Order)
def create_shipping_details(sender, instance, **kwargs):
    """
    Create a ShippingDetail object and link it to the order being saved
    """
    from shipping.config import shipping_method_by_key
    order = instance
    if not (order.shipping_model is not None and
            order.shipping_model.startswith("canadapost-dev-prog-")):
        return
    # we don't want more than one of these, so we overwrite
    shipping_detail, new = OrderShippingService.objects.get_or_create(
        order=order)
    if new:
        shipping_detail.save()
    else:
        # clean old parcel descriptions
        shipping_detail.parceldescription_set.all().delete()

    shipper = shipping_method_by_key(order.shipping_model)
    shipper.calculate(OrderCart(order), order.contact)

    for service, parcel, packs in shipper.services:
        # these will be the same every time, but whatever
        shipping_detail.code = service.code

        box = Box.objects.get(length=parcel.length, width=parcel.width,
                              height=parcel.height)
        parcel_description = ParcelDescription(
            shipping_detail=shipping_detail, box=box, packs=packs)
        parcel_description.save()
    shipping_detail.save()
