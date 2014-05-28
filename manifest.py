# This file is part of carrier_send_shipments_seur module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from seur import Picking
from trytond.pool import PoolMeta

__all__ = ['CarrierManifest']
__metaclass__ = PoolMeta


class CarrierManifest:
    __name__ = 'carrier.manifest'

    def get_manifest_seur(self, api, from_date, to_date):
        context = {}
        context['printer'] = api.seur_printer
        context['printer_model'] = api.seur_printer_model
        context['ecb_code'] = api.seur_ecb_code
        with Picking(api.username, api.password, api.vat, api.seur_franchise,
                api.seur_seurid, api.seur_ci, api.seur_ccc,
                context) as picking_api:
            data = {}
            data['expedicion'] = 'S'
            data['public'] = 'N'
            return picking_api.list(data)
