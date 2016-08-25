This directory contains patches that I have made to assembly source
code on the Internet that I don't necessarily have permission 
to redistribute the original.

dualser.patch:
   Adds support for two 68B50 serial interfaces. Extends basic
   with ISER, OSER, RSER, and BAUD keywords. Assumes a CTC chip
   is available to act as a baud rate generator for the
   second serial port. 

   Original was 32K basic by Grant Searle
   http://searle.hostei.com/grant/z80/sbc_NascomBasic32k.zip