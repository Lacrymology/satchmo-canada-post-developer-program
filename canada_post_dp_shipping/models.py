"""
Models for the canada post developer program's shipping method
"""
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
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

class ShippingServiceDetail(models.Model):
    """
    Save shipping details, such as link and product code
    """
    order = models.ForeignKey(Order, verbose_name=_("order"))
    code = models.CharField(max_length=16, verbose_name=_("code"),
                            help_text=_("Internal Canada Post product code"))
    link = JSONField(max_length=256, verbose_name=_("link"), null=True,
                            help_text=_("Link to create the parcel on the "
                                        "Canada Post API. For internal usage"))

class ParcelDescription(models.Model):
    shipping_detail = models.ForeignKey(ShippingServiceDetail)
    box = models.ForeignKey(Box)
    parcel = models.CharField(max_length=256, verbose_name=_("parcel "
                                                             "description"),
                              editable=False,)

@receiver(post_save, sender=Order)
def create_shipping_details(sender, instance, **kwargs):
    """
    Create a ShippingDetail object and link it to the order being saved
    """
    from shipping.config import shipping_method_by_key
    order = instance
    # we don't want more than one of these, so we overwrite
    shipping_detail, new = ShippingServiceDetail.objects.get_or_create(
        order=order)
    if new:
        shipping_detail.save()
    else:
        # clean old parcel descriptions
        ParcelDescription.objects.all().delete()

    shipper = shipping_method_by_key(order.shipping_model)
    shipper.calculate(OrderCart(order), order.contact)

    for service, parcel, packs in shipper.services:
        box = Box.objects.get(length=parcel.length, width=parcel.width,
                              height=parcel.height)
        description = "[{}]".format(",".join("({})".format(unicode(p))
                                                           for p in packs))
        parcel_description = ParcelDescription(
            shipping_detail=shipping_detail, box=box, parcel=description)
        parcel_description.save()
