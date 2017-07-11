# This file is part of the carrier_send_shipments_seur module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# copyright notices and license terms. the full
from trytond.pool import Pool
from . import api
from . import shipment
from . import manifest


def register():
    Pool.register(
        api.CarrierApi,
        api.CarrierApiSeurOffline,
        api.CarrierApiSeurOfflineSendStart,
        api.CarrierApiSeurZip,
        api.LoadCarrierApiSeurZipStart,
        shipment.ShipmentOut,
        module='carrier_send_shipments_seur', type_='model')
    Pool.register(
        api.CarrierApiSeurOfflineSend,
        api.LoadCarrierApiSeurZip,
        manifest.CarrierManifest,
        module='carrier_send_shipments_seur', type_='wizard')
