import array


cdef extern from "convenience.h":
    ctypedef unsigned char uint8_t
    ctypedef unsigned int uint32_t
    ctypedef uint32_t address_t

    cdef int c_setup_rf2500 "setup_rf2500" ()
    cdef void c_teardown_rf2500 "teardown_rf2500" ()

    cdef int c_nwrite "nwrite" (address_t length, address_t offset, uint8_t* buf)


cdef class MSP430:
    def __init__(self):
        if c_setup_rf2500() < 0:
            raise RuntimeError("Error setting up rf2500 driver!")

    def __dealloc__(self):
        c_teardown_rf2500()

    def nwrite(self, length, offset, buf):
        if isinstance(buf, basestring):
            return c_nwrite(length, offset, <unsigned char *>buf) >= 0
        else:
            # Assume a list of bytes.
            return c_nwrite(length, offset, <uint8_t *>(<unsigned char *>buf)) >= 0

    def write(self, offset, *args):
        if len(args) == 1 and isinstance(args[0], basestring):
            self.nwrite(len(args[0]), offset, args[0])
        else:
            self.nwrite(len(args), offset, array.array('B', args).tostring())

#    if(setup_driver() < 0)
#    {
#        printf("setup_driver failed!\n");
#        fflush(stdout);
#        return -1;
#    }
#
#    if(device_probe_id(device_default) < 0)
#    {
#        printf("warning: device ID probe failed\n");
#    }
#
#    int retval = runStuff();
#    printf("SUCCESS!\n");
#
#    device_destroy();
#    stab_exit();
#
#    return retval;
