/* MSPDebug - debugging tool for the eZ430
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
 *
 * Various constants and tables come from uif430, written by Robert
 * Kavaler (kavaler@diva.com). This is available under the same license
 * as this program, from www.relavak.com.
 */

#include <stdlib.h>

#include "fet.h"
#include "fet_proto.h"
#include "fet_core.h"
#include "output.h"
#include "comport.h"
#include "ftdi.h"
#include "rf2500.h"
#include "cdc_acm.h"
#include "obl.h"

static device_t fet_open_rf2500(const struct device_args *args)
{
	transport_t trans;

	if (args->flags & DEVICE_FLAG_TTY) {
		printc_err("This driver does not support TTY devices.\n");
		return NULL;
	}

	trans = rf2500_open(args->path, args->requested_serial);
	if (!trans)
		return NULL;

	return fet_open(args, FET_PROTO_SEPARATE_DATA, trans,
			0, &device_rf2500);
}

const struct device_class device_rf2500 = {
	.name		= "rf2500",
	.help		= "eZ430-RF2500 devices. Only USB connection is supported.",
	.open		= fet_open_rf2500,
	.destroy	= fet_destroy,
	.readmem	= fet_readmem,
	.writemem	= fet_writemem,
	.erase		= fet_erase,
	.getregs	= fet_getregs,
	.setregs	= fet_setregs,
	.ctl		= fet_ctl,
	.poll		= fet_poll
};
