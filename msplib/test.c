#include <stdio.h>
#include "convenience.h"

int runStuff()
{
	return
		write2(0x120, 0x5A, 0x80)  // Disable watchdog timer
		&& write1(0x22, 0xff)      // Set P1 pins to output
		&& write1(0x21, 0xff)      // Set P1 pins high
		;
}

int main(int argc, char **argv)
{
	if(setup_rf2500() < 0)
	{
		printf("setup_rf2500 failed!\n");
		fflush(stdout);
		return -1;
	}

	int retval = runStuff();
	printf("SUCCESS!\n");

	teardown_rf2500();

	return retval;
}
