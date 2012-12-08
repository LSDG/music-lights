#ifndef __CONVENIENCE_H__
#define __CONVENIENCE_H__

#include <stdio.h>

#include "util/util.h"


int setup_rf2500();
void teardown_rf2500();

int nwrite(address_t length, address_t offset, uint8_t* buf);

int write1(address_t offset, uint8_t data1);

int write2(address_t offset, uint8_t data1, uint8_t data2);

#endif // __CONVENIENCE_H__
