"""
Models for the canada post developer program's shipping method
"""
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from satchmo_store.shop.models import Order
from shipping.config import shipping_method_by_key

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
    max_weight = models.DecimalField(verbose_name=_("max weight"), max_digits=5,
                                     decimal_places=3,
                                     help_text=_("max weight this box can "
                                                 "carry in kg"))

    def __unicode__(self):
        return "{} {}x{}x{}({}kg)".format(self.description, self.length,
                                          self.width, self.height,
                                          self.max_weight)

    class Meta:
        verbose_name = _("box")
        verbose_name_plural = _("boxes")
        ordering = ['-length', '-width', '-height', '-max_weight']
        # each box must be unique
        unique_together = ("length", "width", "height", "max_weight")

    def girth(self):
        return self.length + 2 * (self.width + self.height)

    def volume(self):
        return self.length * self.width * self.height

class ShippingDetail(models.Model):
    """
    Save shipping details, such as link and product code
    """
    order = models.ForeignKey(Order, verbose_name=_("order"))
    link = models.CharField(max_length=128, verbose_name=_("link"),
                            help_text=_("Link to create the parcel on the "
                                        "Canada Post API. For internal usage"))
    code = models.CharField(max_length=16, verbose_name=_("code"),
                            help_text=_("Internal Canada Post product code"))

@receiver(post_save, sender=Order)
def create_shipping_details(sender, instance, **kwargs):
    """
    Create a ShippingDetail object and link it to the order being saved
    """
    order = instance
    shipping_detail = ShippingDetail.objects.get_or_create(order=order)[0]
    shipper = shipping_method_by_key(order.shipping_model)
    shipper.calculate()