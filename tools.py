# This file is part carrier_send_shipments_seur module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

def set_seur_reference(min_ref, max_ref, reference):
    modul = max_ref - min_ref + 1
    return (min_ref + (reference % modul))

def seurbarcode(from_zip, to_zip, reference, transport=1):
    base = '%s%s' % (from_zip[:2], reference)

    even = 0
    odd = 0
    for i in range(0, len(base)):
        digit = int(base[i])
        if (i +1 ) % 2 == 0:
            even += digit
        else:
            odd += digit

    odd = odd * 3
    total = even + odd

    last = int(str(total)[-1:])
    if last == 0:
        control = 9
    else:
        control = (10 - last) - 1

    return '%(from_zip)s %(to_zip)s %(transport)s %(reference)s %(control)s' % {
        'from_zip': from_zip[:2],
        'to_zip': to_zip[:3],
        'transport': transport,
        'reference': reference,
        'control': control,
        }
