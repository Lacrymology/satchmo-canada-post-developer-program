import logging
from canada_post.service import Option
from canada_post_dp_shipping.forms import ParcelDescriptionForm
from canada_post_dp_shipping.tasks import USE_CELERY, transmit_shipments
from django.core.files.base import File
import os
import tempfile
import zipfile
from canada_post_dp_shipping.utils import (get_origin, get_destination,
                                           canada_post_api_kwargs, time_f)
from django.shortcuts import get_object_or_404, render
from django.utils.translation import ugettext_lazy as _, ungettext_lazy
from django.contrib.admin.sites import site
from django.contrib import admin, messages
from django.http import (HttpResponseRedirect, HttpResponse)

from canada_post.api import CanadaPostAPI
from canada_post_dp_shipping.models import (Box, OrderShippingService,
                                            ParcelDescription, ShipmentLink,
                                            Shipment, Manifest, ManifestLink)

from livesettings.functions import config_get_group

log = logging.getLogger("canada_post_dp_shipping.admin")

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

#class ShipmentAdmin(admin.ModelAdmin):
#    inlines = [LinkInline]
#    readonly_fields = ['parcel', ]
#site.register(Shipment, ShipmentAdmin)

class ShipmentInline(admin.StackedInline):
    model = Shipment
    extra = 0

#class ParcelAdmin(admin.ModelAdmin):
#    readonly_fields = ['shipping_detail', ]
#    inlines = [ShipmentInline]
#site.register(ParcelDescription, ParcelAdmin)

class ParcelInline(admin.StackedInline):
    model = ParcelDescription
    extra = 0
    form = ParcelDescriptionForm

class OrderShippingAdmin(admin.ModelAdmin):
    """
    Admin for an order's detail
    """
    fields = ['order', 'code']
    inlines = [ParcelInline]
    readonly_fields = ['order', 'transmitted']
    list_display = ['__unicode__', 'order', 'code', 'parcel_count',
                    'shipments_created', 'has_labels', 'transmitted']
    actions = [
        'void_shipments',
        'get_labels',
        'transmit_shipments',
               ]
    actions_on_bottom = True
    actions_selection_counter = True

    def __init__(self, *args, **kwargs):
        super(OrderShippingAdmin, self).__init__(*args, **kwargs)
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
        return urlpatterns + super(OrderShippingAdmin, self).get_urls()

    def get_parcels(self):
        pass

    def create_shipments(self, request, id):
        log.info("Creating shipments for %s", str(id))
        from satchmo_store.shop.models import Config
        order_shipping = get_object_or_404(OrderShippingService, id=id)
        log.debug("Got OrderShippingService: %s", order_shipping)

        if request.method == 'GET':
            log.debug("GET. Ask for confirmation")
            opts = self.model._meta
            title = _("Please confirm the parcels size and weight")
            object_name = unicode(opts.verbose_name)
            app_label = opts.app_label
            context = {
                "title": title,
                "object_name": object_name,
                "object": order_shipping,
                "opts": opts,
                "root_path": self.admin_site.root_path,
                "app_label": app_label,
                }
            return render(request,
                          ("canada_post_dp_shipping/admin/"
                           "confirm_shipments.html"),
                          context)
        elif request.REQUEST.get('post', None) == "yes":
            log.debug("POST with value=yes")
            # else method is POST
            shop_details = Config.objects.get_current()
            cpa_kwargs = canada_post_api_kwargs(self.settings)
            cpa = CanadaPostAPI(**cpa_kwargs)
            origin = get_origin(shop_details)

            destination = get_destination(order_shipping.order.contact)
            options = None
            if destination.country_code != 'CA':
                # TODO: make this selectable through website
                options = [Option(code='RASE')]
            group = unicode(order_shipping.shipping_group())
            cnt = 0
            exs = 0
            for parcel in (order_shipping.parceldescription_set
                           .select_related().all()):
                log.debug("Creating shipment for parcel %s", parcel)
                try:
                    if parcel.shipment:
                        log.warn("Shipment already existed in DB! %s",
                                 parcel.shipment)
                        exs += 1
                except Shipment.DoesNotExist:
                    log.debug("Creating shipment")
                    cpa_ship = time_f(
                        cpa.create_shipment,
                        'canada-post-dp-shipping.create-shipping',
                        parcel=parcel.get_parcel(), origin=origin,
                        destination=destination,
                        service=order_shipping.get_service(), group=group,
                        options=options)
                    shipment = Shipment(shipment=cpa_ship, parcel=parcel)
                    shipment.save()
                    log.debug("Shipment created: %s", shipment)
                    if USE_CELERY:
                        from canada_post_dp_shipping.tasks import get_label
                        log.debug("Calling get_label celery task")
                        get_label.apply_async(args=(shipment.id,
                                                    cpa.auth.username,
                                                    cpa.auth.password),
                                              # download labels in 3 minutes
                                              countdown=3*60)

                cnt += 1
            log.info("%d shipments created for order %s",
                     cnt, order_shipping.order)
            self.message_user(request, _(u"{count} shipments created for order "
                                         u"{order}").format(
                count=cnt, order=order_shipping.order))
            if USE_CELERY:
                log.debug("Using celery. Task to download labels should run in "
                          "3 minutes")
                self.message_user(request, _(u"Shipping labels will be "
                                             u"automatically downloaded in "
                                             u"three minutes"))
            if exs > 0:
                log.warn("%d shipments already existed for order %s",
                         exs, order_shipping.order)
                messages.warning(request, _(u"{count} shipments already existed "
                                            u"for {order}").format(
                    count=exs, order=order_shipping.order))
        else:
            messages.error(request, _("Unexpected error, please retry"))
        return HttpResponseRedirect("..")
    create_shipments.short_description = _("Create shipments on the "
                                           "Canada Post server for the "
                                           "selected orders")

    def get_labels(self, request, queryset=None, id=-1):
        log.info("get_labels for %s", queryset or str(id))
        if queryset is None:
            queryset = [get_object_or_404(OrderShippingService,
                                          id=id)]
        else:
            queryset = queryset.select_related()

        args = canada_post_api_kwargs(self.settings)

        files = []
        orders = []
        for shipping_service in queryset:
            log.debug("processing shipping service %s", shipping_service)
            try:
                for parcel in (shipping_service.parceldescription_set
                               .select_related().all()):
                    log.debug("processing parcel %s", parcel)
                    shipment = parcel.shipment
                    log.debug("shipment: %s", shipment)
                    if not shipment.label:
                        log.debug("No label, downloading")
                        try:
                            shipment.download_label(args['username'],
                                                    args['password'])
                        except Shipment.Wait:
                            log.debug("Failed downloading label. "
                                      "Ask user to retry")
                            self.message_user(_("Failed downloading label for "
                                                "shipment {id} because the "
                                                "Canada Post server is busy, "
                                                "please wait a couple of "
                                                "minutes and try again").format(
                                id=shipment.id))
                    files.append(shipment.label.file)
                    log.debug("Got file (%d)", len(files))
            except Shipment.DoesNotExist:
                log.debug("Requested labels, but shipment had not been created "
                          "yet")
                messages.error(request, _("One or more shipments for {order} "
                                          "haven't been yet created").format(
                    order=shipping_service.order))

            orders.append(shipping_service.order)

        if files:
            log.debug("has files, making zip")
            tmp = tempfile.mkstemp(suffix=".zip")
            tf = zipfile.ZipFile(tmp[1], mode="w")
            for fileobj in files:
                filename = os.path.basename(fileobj.name)
                tf.write(fileobj.name, filename)
            tf.close()

            response = HttpResponse(File(file(tmp[1])), mimetype="application/zip")
            response['Content-disposition'] = ('attachment; '
                                               'filename='
                                               '"labels_for_orders_{}.zip"').format(
                "-".join(str(o.id) for o in orders))
        else:
            log.debug("no files..")
            response = HttpResponseRedirect(request.path_info)
        return response
    get_labels.short_description = _("Get label links for the selected "
                                          "orders")

    def void_shipments(self, request, queryset=None, id=-1):
        log.info("void shipments %s", queryset or str(id))
        if queryset is None:
            if queryset is None:
                queryset = [get_object_or_404(OrderShippingService,
                                              id=id)]
            else:
                queryset = queryset.select_related()

        cpa_kwargs = canada_post_api_kwargs(self.settings)
        cpa = CanadaPostAPI(**cpa_kwargs)
        errcnt = 0
        gdcnt = 0
        dne = 0
        for detail in queryset:
            log.debug('Processing detail: %s', detail)
            for parcel in detail.parceldescription_set.all().select_related():
                log.debug("Processing parcel: %s", parcel)
                try:
                    shipment = parcel.shipment
                    log.debug("Got shipment %s", shipment)
                    cpa_shipment = shipment.get_shipment()
                    if not time_f(cpa.void_shipment,
                                  'canada-post-dp-shipping.void-shipment',
                                  cpa_shipment):
                        log.warn("Problem voiding shipment: %s", cpa_shipment)
                        errcnt += 1
                        self.message_user(request, _("Could not void shipment "
                                                     "{shipment_id} for order "
                                                     "{order_id}").format(
                            shipment_id=shipment.id, order_id=detail.order.id))
                    else:
                        log.debug("Shipment voided, deleting from DB")
                        gdcnt += 1
                        shipment.delete()
                except Shipment.DoesNotExist:
                    log.debug("Shipment does not exist!")
                    dne += 1

        if not errcnt:
            log.info("All shipments voided")
            self.message_user(request, _("All shipments voided"))
        else:
            log.warn("%d shipments voided, %d problems", gdcnt, errcnt)
            messages.warning(request, _("{good_count} shipments voided, "
                                        "{bad_count} problems").format(
                good_count=gdcnt, bad_count=errcnt))
        if dne:
            log.debug("%d shipments didn't exist", dne)
            self.message_user(request, _("{count} shipments didn't "
                                         "exist").format(count=dne))
        if id >= 0:
            return HttpResponseRedirect("..")
    void_shipments.short_description = _("Cancel created shipments for the "
                                         "selected orders")

    def transmit_shipments(self, request, queryset=None, id=-1):
        log.info("transmit_shipments %s", queryset or str(id))
        if id >= 0:
            log.debug("got id, this should be called on the list view only")
            self.message_user(request, "Transmit shipments should not be "
                                       "called on individual shipment views")
            return HttpResponseRedirect("..")

        send_msg = lambda message: self.message_user(request, message)

        transmit_shipments(queryset, send_msg=send_msg)

    transmit_shipments.short_description = _("Transmit shipments for the "
                                             "selected orders")
site.register(OrderShippingService, OrderShippingAdmin)

class ShippingServiceDetailInline(admin.StackedInline):
    model = OrderShippingService
    extra = 0

class ManifestLinkInline(admin.StackedInline):
    model = ManifestLink
    extra = 0

class ManifestAdmin(admin.ModelAdmin):
    inlines = [ManifestLinkInline, ShippingServiceDetailInline,]
    list_display = ['__unicode__', 'has_artifact']

site.register(Manifest, ManifestAdmin)
