# This file is part of the carrier_send_shipments_seur module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
import doctest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase
from trytond.tests.test_tryton import doctest_setup, doctest_teardown
from trytond.tests.test_tryton import doctest_checker
from trytond.modules.carrier_send_shipments_seur.tools import set_seur_reference, \
    seurbarcode


class CarrierSendShipmentsSeurTestCase(ModuleTestCase):
    'Test Carrier Send Shipments Seur module'
    module = 'carrier_send_shipments_seur'

    def seur_reference(self):
        'Seur Reference Offline'
        min_ref = 4900000
        max_ref = 4920999

        r = set_seur_reference(min_ref, max_ref, 1)
        self.assertEqual(r, 4900001)
        r = set_seur_reference(min_ref, max_ref, 4900000)
        self.assertEqual(r, 4907000)
        r = set_seur_reference(min_ref, max_ref, 4906999)
        self.assertEqual(r, 4913999)
        r = set_seur_reference(min_ref, max_ref, 4920100)
        self.assertEqual(r, 4906100)

    def seur_barcode(self):
        'Seur Barcode'
        from_zip = '19005'
        to_zip = '23006'
        reference = '8201977'
        barcode = seurbarcode(from_zip, to_zip, reference)
        self.assertEqual(barcode, '19 230 1 8201977 5')

def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        CarrierSendShipmentsSeurTestCase))
    suite.addTests(doctest.DocFileSuite('scenario_carrier_send_shipments_seur.rst',
            setUp=doctest_setup, tearDown=doctest_teardown, encoding='utf-8',
            checker=doctest_checker,
            optionflags=doctest.REPORT_ONLY_FIRST_FAILURE))
    return suite
