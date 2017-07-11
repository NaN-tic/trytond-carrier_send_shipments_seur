====================================
Carrier Send Shipments Seur Scenario
====================================

"""
Create a shipment and send to Seur Offine
- Create Seur carrier (offline)
- Create a shipment related with Seur
- Generate label
"""

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from proteus import config, Model, Wizard
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax, set_tax_code
    >>> from.trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences, create_payment_term
    >>> today = datetime.date.today()
    >>> yesterday = today - relativedelta(days=1)

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install stock Module::

    >>> Module = Model.get('ir.module')
    >>> module, = Module.find([('name', '=', 'carrier_send_shipments_seur')])
    >>> module.click('install')
    >>> Wizard('ir.module.install_upgrade').execute('upgrade')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')
    >>> period = fiscalyear.periods[0]

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> receivable = accounts['receivable']
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> account_tax = accounts['tax']

Reload the context::

    >>> User = Model.get('res.user')
    >>> config._context = User.get_preferences(True, config.context)

Create country:

    >>> Country = Model.get('country.country')
    >>> country = Country()
    >>> country.name = 'Spain'
    >>> country.code = 'ES'
    >>> country.save()

Create customer::

    >>> Party = Model.get('party.party')
    >>> Address = Model.get('party.address')
    >>> customer = Party(name='Customer')
    >>> address = Address()
    >>> address.delivery = True
    >>> address.street = 'Delivery address'
    >>> address.zip = '08000'
    >>> address.city = 'Barcelona'
    >>> address.country = country
    >>> customer.addresses.append(address)
    >>> customer.save()

Create category::

    >>> ProductCategory = Model.get('product.category')
    >>> category = ProductCategory(name='Category')
    >>> category.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> product = Product()
    >>> template = ProductTemplate()
    >>> template.name = 'Product'
    >>> template.category = category
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.salable = True
    >>> template.account_revenue = revenue
    >>> template.list_price = Decimal('20')
    >>> template.cost_price = Decimal('8')
    >>> template.save()
    >>> product.template = template
    >>> product.save()

Create product delivery::

    >>> delivery = Product()
    >>> tdelivery = ProductTemplate()
    >>> tdelivery.name = 'Delivery'
    >>> tdelivery.category = category
    >>> tdelivery.default_uom = unit
    >>> tdelivery.type = 'service'
    >>> tdelivery.salable = True
    >>> tdelivery.account_revenue = revenue
    >>> tdelivery.list_price = Decimal('10')
    >>> tdelivery.cost_price = Decimal('2')
    >>> tdelivery.save()
    >>> delivery.template = tdelivery
    >>> delivery.save()

Create Carrier::

    >>> Carrier = Model.get('carrier')
    >>> party_seur = Party(name='Seur')
    >>> party_seur.save()
    >>> carrier_seur = Carrier()
    >>> carrier_seur.party = party_seur
    >>> carrier_seur.carrier_product = delivery
    >>> carrier_seur.carrier_cost_method = 'product'
    >>> carrier_seur.save()

Create API Carrier and services::

    >>> CarrierAPI = Model.get('carrier.api')
    >>> CarrierApiService = Model.get('carrier.api.service')
    >>> Sequence = Model.get('ir.sequence')
    >>> sequence, = Sequence.find([('code', '=', 'carrier.api.seur')])
    >>> carrier_api = CarrierAPI()
    >>> carrier_api.method = 'seur'
    >>> carrier_api.carriers.append(carrier_seur)
    >>> carrier_api.vat = '123456'
    >>> carrier_api.url = 'http://cit.seur.com/CIT-war/services/'
    >>> carrier_api.username = 'myuser'
    >>> carrier_api.password = 'mypassword'
    >>> carrier_api.seur_franchise = '123'
    >>> carrier_api.seur_seurid = '123'
    >>> carrier_api.seur_ci = '123'
    >>> carrier_api.seur_ccc = '123'
    >>> carrier_api.seur_offline = True
    >>> carrier_api.seur_reference = sequence
    >>> carrier_api.seur_minimum_reference = 4900000
    >>> carrier_api.seur_maximun_reference = 4920999
    >>> carrier_api.seur_email = 'test@domain.com'
    >>> carrier_api.seur_filename = '2_10007'
    >>> cservice1 = CarrierApiService()
    >>> carrier_api.services.append(cservice1)
    >>> cservice1.code = '031'
    >>> cservice1.name = 'Seur 24'
    >>> cservice2 = CarrierApiService()
    >>> carrier_api.services.append(cservice2)
    >>> cservice2.code = '013'
    >>> cservice2.name = 'Seur 72'
    >>> cservice3 = CarrierApiService()
    >>> carrier_api.services.append(cservice3)
    >>> cservice3.code = '003'
    >>> cservice3.name = 'Seur 10'
    >>> carrier_api.save()
    >>> carrier_api.reload()
    >>> carrier_api.default_service = carrier_api.services[0]
    >>> carrier_api.save()

Get stock locations::

    >>> Location = Model.get('stock.location')
    >>> warehouse_loc, = Location.find([('code', '=', 'WH')])
    >>> supplier_loc, = Location.find([('code', '=', 'SUP')])
    >>> customer_loc, = Location.find([('code', '=', 'CUS')])
    >>> output_loc, = Location.find([('code', '=', 'OUT')])
    >>> storage_loc, = Location.find([('code', '=', 'STO')])

Add wareahouse address::

    >>> company_address, = company.party.addresses
    >>> company_address.stret = 'Street'
    >>> company_address.zip = '08000'
    >>> company_address.city = 'Barcelona'
    >>> company_address.country = country
    >>> company_address.save()
    >>> warehouse_loc.address = company_address
    >>> warehouse_loc.save()
    >>> warehouse_loc.reload()

Fill storage::

    >>> StockMove = Model.get('stock.move')
    >>> incoming_move = StockMove()
    >>> incoming_move.product = product
    >>> incoming_move.uom = unit
    >>> incoming_move.quantity = 1
    >>> incoming_move.from_location = supplier_loc
    >>> incoming_move.to_location = storage_loc
    >>> incoming_move.planned_date = today
    >>> incoming_move.effective_date = today
    >>> incoming_move.company = company
    >>> incoming_move.unit_price = Decimal('10')
    >>> incoming_move.currency = company.currency
    >>> incoming_moves = [incoming_move]
    >>> StockMove.click(incoming_moves, 'do')

Create payment term::

    >>> payment_term = create_payment_term()
    >>> payment_term.save()

Create a Sale::

    >>> Sale = Model.get('sale.sale')
    >>> SaleLine = Model.get('sale.line')
    >>> sale = Sale()
    >>> sale.party = customer
    >>> sale.payment_term = payment_term
    >>> sale.shipment_method = 'order'
    >>> line = SaleLine()
    >>> sale.lines.append(line)
    >>> line.product = product
    >>> line.quantity = 1.0
    >>> sale.carrier = carrier_seur
    >>> sale.save()
    >>> sale.click('quote')
    >>> sale.click('confirm')
    >>> sale.click('process')
    >>> shipment, = sale.shipments

Confirm Shipment Out::

    >>> shipment.click('wait')
    >>> shipment.click('assign_try')
    True
    >>> shipment.click('pack')
    >>> shipment.state
    u'packed'
    >>> carrier_shipment = Wizard('carrier.send.shipments', [shipment])
    >>> carrier_shipment.execute('send')
    >>> carrier_shipment.form.info
    u'Successfully:\n4900001\n\nErrors:\n'
