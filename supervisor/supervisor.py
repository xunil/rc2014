#!/usr/bin/env python
import smbus
import string
import sys
import time
from optparse import OptionParser
from ioexpand import *
sys.path.append('../tools')
from hexfile import HexFile

"""
   ixAddr = A15..A0
   ixData = D0..D7, M1, CLK, INT, MREQ, WR, RD IORQ, BUSACK
   ixControl = BUSREQ, RST, CLKEN, CLKOUT
"""

# ixData masks
M1=    0x01
CLK=   0x02
INT=   0x04
MREQ=  0x08
WR=    0x10
RD=    0x20
IORQ=  0x40
BUSACK=0x80

# ixControl masks
BUSREQ=0x01
RESET= 0x02
CLKEN= 0x04
CLKOUT=0x08

# bank port for RAM-ROM board
BANK_PORT=0x38

def bitswap(x):
    y=0
    if (x&128)!=0:
       y=y|1
    if (x&64)!=0:
       y=y|2
    if (x&32)!=0:
       y=y|4
    if (x&16)!=0:
       y=y|8
    if (x&8)!=0:
       y=y|16
    if (x&4)!=0:
       y=y|32
    if (x&2)!=0:
       y=y|64
    if (x&1)!=0:
       y=y|128
    return y

class Supervisor:
    def __init__(self, bus, addr, verbose):
        self.ixData = MCP23017(bus, addr+1)
        self.ixControl = PCF8574(bus, addr+2)
        self.ixAddress = MCP23017(bus, addr+3)
        self.verbose = False

    def log(self, msg):
        if self.verbose:
            print >> sys.stderr, msg

    def delay(self):
        time.sleep(0.001)

    def reset(self):
        self.ixControl.not_gpio(0, RESET)
        self.delay()
        self.ixControl.or_gpio(0, RESET)

    def take_bus(self, setBank=None):
        self.ixControl.not_gpio(0,BUSREQ)
        self.log("wait for busack")
        while True:
            bits=self.ixData.get_gpio(1)
            if (bits & BUSACK) == 0:
                break
        self.log("busack is received")
        self.ixAddress.set_iodir(0,0x00)
        self.ixAddress.set_iodir(1,0x00)
        self.ixData.set_iodir(1, M1 | CLK | INT | BUSACK)
        self.ixData.set_gpio(1, MREQ | WR | RD | IORQ)

        if setBank is not None:
            self.io_write(BANK_PORT, setBank)

    def release_bus(self, reset=False):
        self.ixAddress.set_iodir(0,0xFF)
        self.ixAddress.set_iodir(1,0xFF)
        self.ixData.set_iodir(1, 0xFF)

        # Note on observed reset behavior while BUSREQ is low
        # While reset is LOW, BUSACK will go high. As soon as RESET goes back
        # high, BUSACK will go low again. There is exactly one M1 read cycle
        # at the exact time reset goes high. My assumption is that this
        # means the first instruction is fetched if RESET is pulsed while
        # busreq is held low.

        if reset:
            self.ixControl.not_gpio(0,RESET)
            self.delay()
            self.ixControl.or_gpio(0, RESET)

        self.ixControl.or_gpio(0,BUSREQ)
        self.log("wait for not busack")
        while True:
            bits=self.ixData.get_gpio(1)
            if (bits & BUSACK) != 0:
                break
        self.log("not busack is received")

    def slow_clock(self, rate):
        period = (1.0/float(rate))/2.0
        self.ixControl.not_gpio(0, CLKEN)
        while True:
            self.ixControl.not_gpio(0, CLKOUT)
            time.sleep(period)
            self.ixControl.or_gpio(0, CLKOUT)
            time.sleep(period)

    def normal_clock(self):
        self.ixControl.or_gpio(0, CLKEN)

    def set_address(self, addr):
        self.ixAddress.set_gpio(0, bitswap(addr>>8))
        self.ixAddress.set_gpio(1, bitswap(addr&0xFF))

    def mem_read(self, addr):
        self.set_address(addr)
        self.ixData.not_gpio(1, RD)
        self.ixData.not_gpio(1, MREQ)
        result = self.ixData.get_gpio(0)
        self.ixData.or_gpio(1, RD)
        self.ixData.or_gpio(1, MREQ)
        return result

    def mem_write(self, addr, val):
        self.set_address(addr)
        self.ixData.set_iodir(0, 0x00)
        self.ixData.set_gpio(0, val)
        self.ixData.not_gpio(1, WR)
        self.ixData.not_gpio(1, MREQ)
        self.ixData.or_gpio(1, WR)
        self.ixData.or_gpio(1, MREQ)
        self.ixData.set_iodir(0, 0xFF)

    def io_read(self, addr):
        self.set_address(addr)
        self.ixData.not_gpio(1, RD)
        self.ixData.not_gpio(1, IORQ)
        result = self.ixData.get_gpio(0)
        self.ixData.or_gpio(1, RD)
        self.ixData.or_gpio(1, IORQ)
        return result

    def io_write(self, addr, val):
        self.set_address(addr)
        self.ixData.set_iodir(0, 0x00)
        self.ixData.set_gpio(0, val)
        self.ixData.not_gpio(1, WR)
        self.ixData.not_gpio(1, IORQ)
        self.ixData.or_gpio(1, WR)
        self.ixData.or_gpio(1, IORQ)
        self.ixData.set_iodir(0, 0xFF)

    def singlestep_on(self):
        self.ixData.set_intcon(1, M1)
        self.ixData.set_intdef(1, M1)
        self.ixData.set_interrupt(1, M1)

    def singlestep_off(self):
        self.ixData.set_interrupt(1, 0)

    def autostep(self, rate):
        period = (1.0/float(rate))

        try:
           self.singlestep_on()

           while True:
               tnext = time.time() + period

               # wait for M1 to trigger MCP23017 interrupt
               bits = self.ixData.get_intf(1)
               while (bits & M1) == 0:
                   bits = self.ixData.get_intf(1)

               # clear the interrupt and reset wait
               bits=self.ixData.get_gpio(1)
               while (bits & M1)==0:
                  bits = self.ixData.get_gpio(1)

               while (time.time()<tnext):
                  time.sleep(0.0000001)
        finally:
           self.singlestep_off()

def main():
    parser = OptionParser(usage="supervisor [options] command",
            description="Commands: ...")

    parser.add_option("-A", "--addr", dest="addr",
         help="address", metavar="ADDR", type="int", default=0)
    parser.add_option("-C", "--count", dest="count",
         help="count", metavar="ADDR", type="int", default=65536)
    parser.add_option("-V", "--value", dest="value",
         help="value", metavar="VAL", type="int", default=0)
    parser.add_option("-R", "--rate", dest="rate",
         help="rate for slow clock", metavar="HERTZ", type="int", default=10)
    parser.add_option("-B", "--bank", dest="bank",
         help="bank number to select on ram-rom board", metavar="NUMBER", type="int", default=None)
    parser.add_option("-v", "--verbose", dest="verbose",
         help="verbose", action="store_true", default=False)
    parser.add_option("-f", "--filename", dest="filename",
         help="filename", default=None)
    parser.add_option("-r", "--reset", dest="reset_on_release",
         help="reset on release of bus", action="store_true", default=False)
    parser.add_option("-n", "--norelease", dest="norelease",
         help="do not release bus", action="store_true", default=False)

    #parser.disable_interspersed_args()

    (options, args) = parser.parse_args(sys.argv[1:])

    cmd = args[0]
    args=args[1:]

    bus = smbus.SMBus(1)
    super = Supervisor(bus, 0x20, options.verbose)

    if (cmd=="reset"):
        super.reset()

    elif (cmd=="memdump"):
        try:
            super.take_bus(setBank=options.bank)
            for i in range(options.addr, options.addr+options.count, 16):
                start = i
                end = min(options.addr+options.count,i+16)
                # This buffer allows us to avoid reading bytes from the
                # RC2014 RAM twice.
                valbuf = list()
                print "%04X:%04X " % (start, end),
                for j in range(start, end):
                    valbuf.append(super.mem_read(j))
                    print "%02X" % valbuf[-1],
                if (end - start < 16):
                    sys.stdout.write('   ' * (16 - (end - start)))
                    sys.stdout.write(' ')
                print "  ",
                for j in range(0, (end - start)):
                    val = valbuf[j]
                    sys.stdout.write(chr(val) if val < 127 and val >= 32 else '.')
                print
        finally:
            if not options.norelease:
                super.release_bus()

    elif (cmd=="savehex"):
        hexdumper = HexFile(options.addr)
        try:
            super.take_bus(setBank=options.bank)
            for i in range(options.addr,options.addr+options.count):
                val = super.mem_read(i)
                hexdumper.write(val)
        finally:
            if not options.norelease:
                super.release_bus()

        if options.filename:
            file(options.filename,"w").write(hexdumper.to_str())
        else:
            sys.stdout.write(hexdumper.to_str())

        # a little self-test ...
        h2 = HexFile(None)
        h2.from_str(hexdumper.to_str())
        print "okay?", h2.to_str() == hexdumper.to_str()


    elif (cmd=="loadhex"):
        hexloader = HexFile(None)
        if options.filename:
            hexloader.from_str(file(options.filename,"r").read())
        else:
            hexloader.from_str(sys.stdin.read())

        try:
            super.take_bus(setBank=options.bank)
            offset = hexloader.addr
            for val in hexloader.bytes:
                super.mem_write(offset, val)
                offset = offset + 1
        finally:
            if not options.norelease:
                super.release_bus(reset=options.reset_on_release)


    elif (cmd=="peek"):
        try:
            super.take_bus(setBank=options.bank)
            print "%02X" % super.mem_read(options.addr)
        finally:
            if not options.norelease:
                super.release_bus()

    elif (cmd=="poke"):
        try:
            super.take_bus(setBank=options.bank)
            super.mem_write(options.addr, options.value)
        finally:
            if not options.norelease:
                super.release_bus()

    elif (cmd=="ioread"):
        try:
            super.take_bus(setBank=options.bank)
            print "%02X" % super.io_read(options.addr)
        finally:
            if not options.norelease:
                super.release_bus()

    elif (cmd=="iowatch"):
        last=None
        try:
            super.take_bus(setBank=options.bank)
            while True:
                x=super.io_read(options.addr)
                if (x!=last):
                    print "%02X" % x
                    last=x
        finally:
            if not options.norelease:
                super.release_bus()

    elif (cmd=="iowrite"):
        try:
            super.take_bus(setBank=options.bank)
            super.io_write(options.addr, options.value)
        finally:
            if not options.norelease:
                super.release_bus()

    elif (cmd=="slowclock"):
        try:
            super.slow_clock(rate=options.rate)
        finally:
            super.normal_clock()

    elif (cmd=="singlestep"):
        try:
            from getch import getch
            super.singlestep_on()
            while True:
                print "press `s` to step, 'q' to quit",
                ch = getch()
                if ch=="s":
                    # Reading gpio will clear interrupt, but the problem is that
                    # M1 may still be low and will immediately re-interrupt.
                    bits=super.ixData.get_gpio(1)
                    while (bits & M1)==0:
                       bits = super.ixData.get_gpio(1)

                    print ""
                if ch=="q":
                    break
        finally:
            super.singlestep_off()

    elif (cmd=="singlestep"):
        try:
            from getch import getch
            super.singlestep_on()
            while True:
                print "press `s` to step, 'q' to quit",
                ch = getch()
                if ch=="s":
                    # Reading gpio will clear interrupt, but the problem is that
                    # M1 may still be low and will immediately re-interrupt. So
                    # keep reading it until we see that M1 has gone high.
                    bits=super.ixData.get_gpio(1)
                    while (bits & M1)==0:
                       bits = super.ixData.get_gpio(1)

                    print ""
                if ch=="q":
                    break
        finally:
            super.singlestep_off()

    elif (cmd=="autostep"):
        try:
            super.autostep(rate=options.rate)
        finally:
            super.normal_clock()

    elif (cmd=="showint"):
        last=None
        while True:
            v = ((super.ixData.get_gpio(1)&INT) !=0)
            if v!=last:
                print v
                last=v


if __name__=="__main__":
    main()
