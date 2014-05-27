# This file is part of the carrier_send_shipments_seur module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# copyright notices and license terms. the full
from trytond.pool import Pool
from .api import *
from .shipment import *
from .manifest import *


def register():
    Pool.register(
        CarrierApi,
        ShipmentOut,
        module='carrier_send_shipments_seur', type_='model')
    Pool.register(
        StockManifest,
        module='carrier_send_shipments_seur', type_='wizard')
