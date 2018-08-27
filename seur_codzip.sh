#!/bin/bash

# convert maestros to UTF-8
iconv -f ISO-8859-15 CPOSTALPC.TXT -t UTF-8 -o seur-codpos.txt
iconv -f ISO-8859-15 DESTINPC.TXT -t UTF-8 -o seur-coddest.txt
