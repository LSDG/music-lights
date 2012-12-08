from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext


ext_modules = [
        Extension('msplib',
            '''
                msplib.pyx
                util/btree.c
                util/expr.c
                util/list.c
                util/sockets.c
                util/sport.c
                util/usbutil.c
                util/util.c
                util/vector.c
                util/output.c
                util/output_util.c
                util/opdb.c
                util/stab.c
                util/dis.c
                util/dynload.c
                util/demangle.c
                util/powerbuf.c
                util/ctrlc.c
                transport/cdc_acm.c
                transport/rf2500.c
                drivers/device.c
                drivers/fet.c
                drivers/fet_core.c
                drivers/fet_proto.c
                drivers/fet_error.c
                drivers/fet_db.c
                drivers/obl.c
                drivers/devicelist.c
                drivers/jtdev.c
                drivers/jtaglib.c
                ui/flatfile.c
                ui/reader.c
                ui/aliasdb.c
                ui/power.c
                ui/input.c
                ui/input_console.c
                ui/main.c
                convenience.c
                '''.split(),
            include_dirs='''
                drivers
                transport
                ui
                util
                '''.split(),
            libraries='''
                usb
                '''.split(),
            )
        ]

setup(
        name='MSP430 Python interface',
        cmdclass={
            'build_ext': build_ext,
            },
        ext_modules=ext_modules,
        )
