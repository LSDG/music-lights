#include <stdio.h>

#include "device.h"
#include "stab.h"
#include "reader.h"

#include "fet.h"

#include "convenience.h"


int setup_rf2500()
{
	const struct device_class *rf2500 = &device_rf2500;

	if(stab_init() < 0)
	{
		printf("stab_init failed!\n");
		fflush(stdout);

		return -1;
	}

	struct device_args devarg = {0};
	devarg.vcc_mv = 3000;
	devarg.requested_serial = NULL;

	device_default = rf2500->open(&devarg);

	if(!device_default)
	{
		printf("rf2500->open failed!\n");
		fflush(stdout);

		stab_exit();
		return -1;
	}

	if(device_probe_id(device_default) < 0)
	{
		printf("warning: device ID probe failed\n");
		fflush(stdout);
	}

	return 0;
}

void teardown_rf2500()
{
	device_destroy();
	stab_exit();
}

int nwrite(address_t length, address_t offset, uint8_t* buf)
{
	if(device_writemem(offset, buf, length) < 0)
	{
		printf("device_writemem failed!\n");
		fflush(stdout);
		return -1;
	}
	return 0;
}

int write1(address_t offset, uint8_t data1)
{
	uint8_t buf[1] = {data1};
	return nwrite(2, offset, buf);
}

int write2(address_t offset, uint8_t data1, uint8_t data2)
{
	uint8_t buf[2] = {data1, data2};
	return nwrite(2, offset, buf);
}
