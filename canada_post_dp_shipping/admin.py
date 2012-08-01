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
    fields = ['order', 'code']
    inlines = [ParcelInline]
    readonly_fields = ['order']
    list_display = ['__unicode__', 'order', 'code', 'parcel_count']
    actions = ['void_shipments', 'create_shipments', 'get_labels',
               'transmit_shipments']
    actions_on_bottom = True
    actions_selection_counter = True

    def __init__(self, *args, **kwargs):
        super(DetailAdmin, self).__init__(*args, **kwargs)
        self.settings = config_get_group('canada_post_dp_shipping')

    def get_urls(self):
        from django.conf.urls.defaults import url, patterns
        info = "%s_%s" % (self.model._meta.app_label,
                          self.model._meta.module_name)
        pat = lambda regex, fn: url(regex, self.admin_site.admin_view(fn),
                                    name='%s_%s' % (info, fn.__name__))
        urlpatterns = patterns("",
            pat(r'(?P<id>\d+)/create-shipments/$', self.create_shipments),
            pat(r'(?P<id>\d+)/get-labels/$', self.get_labels),
            pat(r'(?P<id>\d+)/void-shipments/$', self.void_shipments),
            pat(r'(?P<id>\d+)/transmit-shipments/$', self.transmit_shipments),
        )
        return urlpatterns + super(DetailAdmin, self).get_urls()

    def get_parcels(self):
        pass

    def void_shipments(self, request, queryset=None, id=-1):
        return HttpResponseRedirect("..")
    void_shipments.short_description = _("Cancel created shipments for the "
                                         "selected orders")

    def transmit_shipments(self, request, queryset=None, id=-1):
        return HttpResponseRedirect("..")
    transmit_shipments.short_description = _("Transmit shipments for the "
                                             "selected orders")
site.register(ShippingServiceDetail, DetailAdmin)

class ShippingServiceDetailInline(admin.StackedInline):
    model = DetailAdmin
