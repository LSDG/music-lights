# MSPDebug - debugging tool for the eZ430
# Copyright (C) 2009, 2010 Daniel Beer
# Copyright (C) 2010 Andrew Armenia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

#CC ?= gcc
CC = colorgcc
INSTALL = /usr/bin/install
PREFIX ?= /usr/local
LDFLAGS ?= -s

BINDIR = ${PREFIX}/bin/
MANDIR = ${PREFIX}/share/man/man1
LIBDIR = ${PREFIX}/lib/


WITHOUT_READLINE ?= 1
ifdef WITHOUT_READLINE
        READLINE_CFLAGS =
        READLINE_LIBS =
else
        READLINE_CFLAGS = -DUSE_READLINE
        READLINE_LIBS = -lreadline
endif

UNAME_S := $(shell sh -c 'uname -s')
UNAME_O := $(shell sh -c 'uname -o 2> /dev/null')

ifeq ($(UNAME_S),Darwin) # Mac OS X/MacPorts stuff
    PORTS_CFLAGS := -I/opt/local/include
    PORTS_LDFLAGS := -L/opt/local/lib
else
    ifeq ($(UNAME_S),OpenBSD) # OpenBSD Ports stuff
        PORTS_CFLAGS := $(shell pkg-config --cflags libusb)
        PORTS_LDFLAGS := $(shell pkg-config --libs libusb) -ltermcap -pthread
    else
        PORTS_CFLAGS :=
        PORTS_LDFLAGS :=
    endif
endif

ifeq ($(OS),Windows_NT)
    MSPDEBUG_CC = gcc
    BINARY = libmspdebug.dll

    ifneq ($(UNAME_O),Cygwin)
        OS_LIBS = -lws2_32 -lregex
        OS_CFLAGS = -D__Windows__
    endif
else
    MSPDEBUG_CC = $(CC)
    BINARY = libmspdebug.so

    ifneq ($(filter $(UNAME_S),OpenBSD),)
        OS_LIBS =
    else ifneq ($(filter $(UNAME_S),FreeBSD),)
        OS_CFLAGS = -pthread
        OS_LIBS = -lpthread
    else
        OS_LIBS = -lpthread -ldl
    endif
endif

INCLUDES = -I. -Isimio -Iformats -Itransport -Idrivers -Iutil -Iui
GCC_CFLAGS = -O1 -Wall -Wno-char-subscripts -ggdb
CONFIG_CFLAGS = -DLIB_DIR=\"$(LIBDIR)\"

MSPDEBUG_TEST_LDFLAGS = $(LDFLAGS) $(PORTS_LDFLAGS)
MSPDEBUG_LDFLAGS = $(LDFLAGS) $(PORTS_LDFLAGS) -shared -Wl,-soname,$(BINARY)
MSPDEBUG_LIBS = -lusb $(READLINE_LIBS) $(OS_LIBS)
MSPDEBUG_CFLAGS = $(CFLAGS) $(READLINE_CFLAGS) $(PORTS_CFLAGS) $(GCC_CFLAGS) $(INCLUDES) $(CONFIG_CFLAGS) $(OS_CFLAGS) -fPIC

all: $(BINARY) test_msp

clean:
	rm -f *.o
	rm -f */*.o
	rm -f $(BINARY) test_msp

install: $(BINARY) mspdebug.man
	mkdir -p $(DESTDIR)$(BINDIR)
	$(INSTALL) -m 0755 $(BINARY) $(DESTDIR)$(BINDIR)
	mkdir -p $(DESTDIR)$(MANDIR)
	$(INSTALL) -m 0644 mspdebug.man $(DESTDIR)$(MANDIR)/mspdebug.1
	mkdir -p $(DESTDIR)$(LIBDIR)/mspdebug
	$(INSTALL) -m 0644 ti_3410.fw.ihex \
		$(DESTDIR)$(LIBDIR)/mspdebug/ti_3410.fw.ihex

.SUFFIXES: .c .o

OBJ=\
    util/btree.o \
    util/expr.o \
    util/list.o \
    util/sockets.o \
    util/sport.o \
    util/usbutil.o \
    util/util.o \
    util/vector.o \
    util/output.o \
    util/output_util.o \
    util/opdb.o \
    util/prog.o \
    util/stab.o \
    util/dis.o \
    util/dynload.o \
    util/demangle.o \
    util/powerbuf.o \
    util/ctrlc.o \
    transport/cdc_acm.o \
    transport/ftdi.o \
    transport/rf2500.o \
    transport/comport.o \
    drivers/device.o \
    drivers/fet.o \
    drivers/fet_core.o \
    drivers/fet_proto.o \
    drivers/fet_error.o \
    drivers/fet_db.o \
    drivers/obl.o \
    drivers/devicelist.o \
    drivers/jtdev.o \
    drivers/jtaglib.o \
    formats/coff.o \
    formats/elf32.o \
    formats/ihex.o \
    formats/symmap.o \
    formats/srec.o \
    formats/titext.o \
    ui/flatfile.o \
    ui/reader.o \
    ui/aliasdb.o \
    ui/power.o \
    ui/input.o \
    ui/input_console.o \
    ui/main.o \
    convenience.o

$(BINARY): $(OBJ)
	$(MSPDEBUG_CC) $(MSPDEBUG_LDFLAGS) -o $@ $^ $(MSPDEBUG_LIBS)

test_msp: test.o $(BINARY)
	$(MSPDEBUG_CC) $(MSPDEBUG_TEST_LDFLAGS) -o $@ $^ $(MSPDEBUG_LIBS)

.c.o:
	$(MSPDEBUG_CC) $(MSPDEBUG_CFLAGS) -o $@ -c $*.c
