from django.core.files.base import File
import os
import tempfile
import zipfile
from canada_post_dp_shipping.utils import (get_origin, get_destination,
                                           canada_post_api_kwargs)
from django.shortcuts import get_object_or_404, render
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin.sites import site
from django.contrib import admin, messages
from django.http import (HttpResponseRedirect, HttpResponse)

from canada_post.api import CanadaPostAPI
from canada_post_dp_shipping.models import (Box, OrderShippingService,
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
    extra = 0

class OrderShippingAdmin(admin.ModelAdmin):
    """
    Admin for an order's detail
    """
    fields = ['order', 'code']
    inlines = [ParcelInline]
    readonly_fields = ['order']
    list_display = ['__unicode__', 'order', 'code', 'parcel_count']
    actions = [
        'void_shipments',
        'get_labels',
        #'transmit_shipments', # comment out for now
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
            pat(r'create-shipments-form/$', self.create_shipments_forms),
            pat(r'(?P<id>\d+)/get-labels/$', self.get_labels),
            pat(r'(?P<id>\d+)/void-shipments/$', self.void_shipments),
            pat(r'(?P<id>\d+)/transmit-shipments/$', self.transmit_shipments),
        )
        return urlpatterns + super(OrderShippingAdmin, self).get_urls()

    def get_parcels(self):
        pass

    def create_shipments(self, request, queryset=None, id=-1):
        from satchmo_store.shop.models import Config
        if queryset is None:
            queryset = [get_object_or_404(OrderShippingService,
                                          id=id)]
        else:
            queryset = queryset.select_related()
            # in this case, we want to redirect the user

        url = "{}?{}".format(reverse('admin:canada_post_dp_shipping_'
                                     'ordershippingservice_'
                                     'create_shipments_forms'),
                             "&".join("shipments=" + unicode(os.id)
                                      for os in queryset))
        return HttpResponseRedirect(url)

        shop_details = Config.objects.get_current()
        cpa_kwargs = canada_post_api_kwargs(self.settings)
        cpa = CanadaPostAPI(**cpa_kwargs)
        origin = get_origin(shop_details)
        for detail in queryset:
            destination = get_destination(detail.order.contact)
            group = unicode(detail.shipping_group())
            cnt = 0
            for parcel in detail.parceldescription_set.select_related().all():
                shipment = cpa.create_shipment(parcel=parcel.get_parcel(),
                                               origin=origin,
                                               destination=destination,
                                               service=detail.get_service(),
                                               group=group)
                Shipment(shipment=shipment, parcel=parcel).save()
                cnt += 1
            self.message_user(request, _("{count} shipments created for order "
                                         "{order}").format(count=cnt,
                                                           order=detail.order))
        if id >= 0:
            return HttpResponseRedirect("..")
    create_shipments.short_description = _("Create shipments on the "
                                           "Canada Post server for the "
                                           "selected orders")

    def create_shipments_forms(self, request):
        """
        Process the forms for the creation of the shipments for a list of orders

        Gets the list of ShippingServiceDetails to be processed as a GET query
        param `shipments`
        """
        queryset = OrderShippingService.objects.filter(
            id__in=request.REQUEST.getlist('shipments'))

        shipping_service_forms = []
        for order_shipping in queryset:
            initial = []
            for parcel in order_shipping.parceldescription_set.select_related():
                initial.append({
                    'length': parcel.box.length,
                    'width': parcel.box.width,
                    'height': parcel.box.height,
                    'weight': parcel.weight,
                    })

            if request.method == "POST":
                shipping_service_forms.append({
                    'order_shipping': order_shipping,
                    'forms': ParcelDescriptionFormSet(
                        #initial=initial,
                        prefix="parcels-for-{}".format(order_shipping.id),
                        data=request.POST),
                    })

            else:
                shipping_service_forms.append({
                    'order_shipping': order_shipping,
                    'forms': ParcelDescriptionFormSet(
                        initial=initial,
                        prefix="parcels-for-{}".format(order_shipping.id))
                    })

        if request.method == "POST":
            if all(ssf['forms'].is_valid() for ssf in shipping_service_forms):
                for ssf in shipping_service_forms:
                    order_shipment = ssf['order_shipping']
                    destination = get_destination(order_shipment.order.contact)
                    group = unicode(order_shipment.shipping_group())
                    cnt = 0
                    
                    for parcel in order_shipment.parceldescription_set.select_related().all():
                        shipment = cpa.create_shipment(parcel=parcel.get_parcel(),
                                                       origin=origin,
                                                       destination=destination,
                                                       service=order_shipment.get_service(),
                                                       group=group)
                        Shipment(shipment=shipment, parcel=parcel).save()
                        cnt += 1
                    self.message_user(request, _("{count} shipments created for order "
                                                 "{order}").format(count=cnt,
                                                                   order=order_shipment.order))
                return HttpResponseRedirect(reverse(
                    "admin:canada_post_dp_shipping_ordershippingservice_"
                    "changelist"))

        context = {
            'shipping_service_forms': shipping_service_forms,
            # context for django's change_form template
            'app_label': self.model._meta.app_label,
            'original': 'Create shipments',
            'has_add_permission': True,
            'has_change_permission': True,
            'has_delete_permission': True,
            'has_file_field': True, # FIXME - this should check if form or formsets have a FileField,
            'has_absolute_url': hasattr(self.model, 'get_absolute_url'),
            'opts': self.model._meta,
            'content_type_id': ContentType.objects.get_for_model(self.model).id,
            'save_as': self.save_as,
            'save_on_top': self.save_on_top,
            'root_path': self.admin_site.root_path,
            'change': True,
            'is_popup': "_popup" in request.REQUEST,
            }
        return render(request,
                      "canada_post_dp_shipping/admin/create_shipments.html",
                      context)


    def get_labels(self, request, queryset=None, id=-1):
        if queryset is None:
            queryset = [get_object_or_404(OrderShippingService,
                                          id=id)]
        else:
            queryset = queryset.select_related()

        args = canada_post_api_kwargs(self.settings)

        files = []
        orders = []
        for detail in queryset:
            for parcel in detail.parceldescription_set.select_related().all():
                shipment = parcel.shipment
                if not shipment.label:
                    try:
                        shipment.download_label(args['username'], args['password'])
                    except Shipment.Wait:
                        self.message_user(_("Failed downloading label for "
                                            "shipment {id} because the "
                                            "Canada Post server is busy, "
                                            "please wait a couple of minutes "
                                            "and try again").format(
                            id=shipment.id))
                files.append(shipment.label.file)
            orders.append(detail.order)

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
        return response
    get_labels.short_description = _("Get label links for the selected "
                                          "orders")

    def void_shipments(self, request, queryset=None, id=-1):
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
        for detail in queryset:
            for parcel in detail.parceldescription_set.all().select_related():
                shipment = parcel.shipment
                cpa_shipment = shipment.get_shipment()
                if not cpa.void_shipment(cpa_shipment):
                    errcnt += 1
                    self.message_user(request, _("Could not void shipment "
                                                 "{shipment_id} for order "
                                                 "{order_id}").format(
                        shipment_id=shipment.id, order_id=detail.order.id))
                else:
                    gdcnt += 1
                    shipment.delete()

        if not errcnt:
            self.message_user(request, _("All shipments voided"))
        else:
            self.message_user(request, _("{good_count} shipments voided, {bad_count} "
                                "problems").format(good_count=gdcnt,
                                                   bad_count=errcnt))
        if id >= 0:
            return HttpResponseRedirect("..")
    void_shipments.short_description = _("Cancel created shipments for the "
                                         "selected orders")

    def transmit_shipments(self, request, queryset=None, id=-1):
        if id >= 0:
            return HttpResponseRedirect("..")
    transmit_shipments.short_description = _("Transmit shipments for the "
                                             "selected orders")
site.register(OrderShippingService, OrderShippingAdmin)

class ShippingServiceDetailInline(admin.StackedInline):
    model = OrderShippingAdmin
