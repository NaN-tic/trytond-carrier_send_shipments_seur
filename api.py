# This file is part of the carrier_send_shipments module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval
import logging

try:
    from seur.picking import *
except ImportError:
    logger = logging.getLogger(__name__)
    message = 'Install Seur from Pypi: pip install seur'
    logger.error(message)
    raise Exception(message)

__all__ = ['CarrierApi']
__metaclass__ = PoolMeta


class CarrierApi:
    __name__ = 'carrier.api'
    seur_franchise = fields.Char('Franchise', states={
            'required': Eval('method') == 'seur',
            }, help='Seur Franchise code')
    seur_seurid = fields.Char('ID', states={
            'required': Eval('method') == 'seur',
            }, help='Seur Description code')
    seur_ci = fields.Char('CI', states={
            'required': Eval('method') == 'seur',
            }, help='Seur Customer Code (ci)')
    seur_ccc = fields.Char('CCC', states={
            'required': Eval('method') == 'seur',
            }, help='Seur Account Code (ccc)')
    seur_printer = fields.Char('Printer', help='Seur Printer')
    seur_printer_model = fields.Char('Printer Model', help='Seur Printer Model')
    seur_ecb_code = fields.Char('ECB Code', help='Seur ECB Code')
    seur_pdf = fields.Boolean('PDF', help='PDF Label')

    @classmethod
    def get_carrier_app(cls):
        '''
        Add Carrier Seur APP
        '''
        res = super(CarrierApi, cls).get_carrier_app()
        res.append(('seur', 'Seur'))
        return res

    def test_seur(self, api):
        '''
        Test Seur connection
        :param api: obj
        '''
        message = 'Connection unknown result'
        
        seur_context = {}
        with API(api.username, api.password, api.vat, api.seur_franchise, api.seur_seurid, \
                api.seur_ci, api.seur_ccc, seur_context) as seur_api:
            message = seur_api.test_connection()
        self.raise_user_error(message)
