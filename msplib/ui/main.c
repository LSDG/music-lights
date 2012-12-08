/* MSPDebug - debugging tool for MSP430 MCUs
 * Copyright (C) 2009-2012 Daniel Beer
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
 */

#include <stdio.h>
#include <ctype.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <getopt.h>

#include "device.h"
#include "stab.h"
#include "opdb.h"
#include "reader.h"
#include "output.h"
#include "ctrlc.h"

#include "fet.h"

#define OPT_NO_RC		0x01
#define OPT_EMBEDDED		0x02

struct cmdline_args {
	const char		*driver_name;
	int			flags;
	struct device_args	devarg;
};

static const char *version_text =
"Heavily Modified version..."
"MSPDebug version 0.21 - debugging tool for MSP430 MCUs\n"
"Copyright (C) 2009-2012 Daniel Beer <dlbeer@gmail.com>\n"
"This is free software; see the source for copying conditions.  There is NO\n"
"warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR "
"PURPOSE.\n";

int setup_driver(struct cmdline_args *args)
{
	const struct device_class *rf2500 = &device_rf2500;

	if (stab_init() < 0)
		return -1;

	device_default = rf2500->open(&args->devarg);

	if (!device_default) {
		stab_exit();
		return -1;
	}

	return 0;
}

int main(int argc, char **argv)
{
	struct cmdline_args args = {0};
	int ret = 0;

	setvbuf(stderr, NULL, _IOFBF, 0);
	setvbuf(stdout, NULL, _IOFBF, 0);

	opdb_reset();
	ctrlc_init();

	args.devarg.vcc_mv = 3000;
	args.devarg.requested_serial = NULL;

	printc_dbg("%s\n", version_text);
	if (setup_driver(&args) < 0) {
		ret = -1;
		goto fail_driver;
	}

	if (device_probe_id(device_default) < 0)
		printc_err("warning: device ID probe failed\n");

	/* Process commands */
	if (optind < argc) {
		while (optind < argc) {
			if (process_command(argv[optind++]) < 0) {
				ret = -1;
				break;
			}
		}
	} else {
		reader_loop();
	}

	device_destroy();
	stab_exit();
fail_driver:
	/* We need to do this on Windows, because in embedded mode we
	 * may still have a running background thread for input. If so,
	 * returning from main() won't cause the process to terminate.
	 */
#if defined(__Windows__) || defined(__CYGWIN__)
	ExitProcess(ret);
#endif
	return ret;
}
