from django.core.files.base import File
import os
import tempfile
import zipfile
from canada_post_dp_shipping.utils import (get_origin, get_destination,
                                           canada_post_api_kwargs)
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin.sites import site
from django.contrib import admin
from django.http import (HttpResponseRedirect, HttpResponse)

from canada_post import PROD, DEV
from canada_post.api import CanadaPostAPI
from canada_post_dp_shipping.models import (Box, ShippingServiceDetail,
                                            ParcelDescription, ShipmentLink,
                                            Shipment)

from livesettings.functions import config_get_group

class BoxAdmin(admin.ModelAdmin):
    """
    Admin for Box model
    """
    list_display = ['__unicode__', 'girth', 'volume']
site.register(Box, BoxAdmin)

class LinkInline(admin.StackedInline):
    model = ShipmentLink
    readonly_fields = ['type', 'data']
    extra = 0

class ShipmentAdmin(admin.ModelAdmin):
    inlines = [LinkInline]
site.register(Shipment, ShipmentAdmin)

class ShipmentInline(admin.StackedInline):
    model = Shipment
    extra = 0

class ParcelAdmin(admin.ModelAdmin):
    readonly_fields = ['parcel']
    inlines = [ShipmentInline]
site.register(ParcelDescription, ParcelAdmin)

class ParcelInline(admin.StackedInline):
    model = ParcelDescription
    readonly_fields = ['parcel', 'box']
    extra = 0

class DetailAdmin(admin.ModelAdmin):
    """
    Admin for an order's detail
    """
    inlines = [ParcelInline]
site.register(ShippingServiceDetail, DetailAdmin)

class ShippingServiceDetailInline(admin.StackedInline):
    model = DetailAdmin
