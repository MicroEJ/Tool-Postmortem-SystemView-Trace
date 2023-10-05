<!-- Copyright 2020-2023 MicroEJ Corp. All rights reserved. -->
<!-- Use of this source code is governed by a BSD-style license that can be found with this software. -->

# SEGGER SystemView Postmortem Trace Retriever

## Brief

This MicroEJ tool can be used to extract and format the Segger System View circular buffer in a dumped embedded SystemView's memory to feed the [SystemView desktop application](https://www.segger.com/products/development-tools/systemview/).

This tool only implements the restructuring of the SystemView data described in the *Get postmortem data from the system* section of the [SEGGER SystemView User Guide](https://www.segger.com/downloads/systemview/UM08027). It does not run on the embedded target.

In this document:

* *SystemView's memory*: is the SystemView memory range in the embedded target.
* *SystemView Postmortem Trace Retriever*: or *SystemView PTR* is this Python tool addressed in this readme.

## Requirements

* Software: SystemView version 2.52a
* Hardware: a CPU capable of logging the SystemView events in a RAM buffer, and a output interface to dump the buffer (e.g. JLINK debugger or UART serial output)

For more information on SystemView requirements, please read the section "*What resources are required on the target side?*" of [SEGGER SystemView User Guide](https://www.segger.com/downloads/systemview/UM08027).

### PC

* Install Python 3.10 or later. Please follow the Python installation guide available [here](https://www.python.org/downloads/).
* SystemView PTR dependencies 
```pip install -r requirements.txt```

## Setup

The following steps are required:

### Embeded Software

This procedure assumes that the SystemView source code is correctly integrated and configured in the software of the embedded target.
If not, please refer to [procedure](https://docs.microej.com/en/latest/PlatformDeveloperGuide/systemView.html#installation) to integrate and configure it for your project.

To enable the postmortem mode, you will need to change the macros `SEGGER_SYSVIEW_POST_MORTEM_MODE` to `1` in the `SEGGER_SYSVIEW_configuration.h` file. You will also need to adjust the macro `SEGGER_SYSVIEW_SYNC_PERIOD_SHIFT` to have at least one sync available in the SystemView buffer.
For more information please see the *postmortem analysis* section in the [SEGGER SystemView User Guide](https://www.segger.com/downloads/systemview/UM08027)

Also, do not forget to activate SystemView by calling `SEGGER_SYSVIEW_Start()` in your embedded program.

## How to use

You will need to have a memory dump of the SystemView's memory (Usually, the memory is mapped to the `_SEGGER_RTT` symbol). The only constraint is the first byte of the dump needs to be the first byte of the SystemView's memory. You can dump the exact memory dump or more.
You will need at least the following memory sections (The addresses and size may change):

```
 .bss           0x0000000020011ce4      0x4b9 ./systemview/src/SEGGER_RTT.o
                0x0000000020011ce4                _SEGGER_RTT
 *fill*         0x000000002001219d        0x3 
 .bss           0x00000000200121a0     0x211c ./systemview/src/SEGGER_SYSVIEW.o
```

This dump can be fed directly to the SystemView PTR; which will extract all the configured SystemView circular buffers detected.

 ```                                        |
                EMBEDDED WORLD           |          PC WORLD
                                         |
                                         |
                                         |
            +----MEMORY----+             |
            |              |             |
            |              |             |
            |              |             |
            |              |             |
            |              |             |
            |              |             |
            |              |             |
_SEGGER_RTT+--------------+X--------+   |
            |SV MEMORY BUF |         |   |          chunck.bin
            |              |Get memory   |          +-----+
            | # Buffer0    |         |   |          |BIN  |
            |              |chunk via+---+--------> |FILE |
            | # Buffer1    |         |   |          |     |
            |              |any means|   |          |     |
            | # Buffer2    |             |          +--+--+
            |              |         |   |             |
            +--------------+             |             |
            |              |         |   |   +---------+-----------+
            |              |X-------     |   |     SystemView      |
            |              |             |   |        PTR          |
            |              |             |   +---------+-----------+
            |              |             |             |
            |              |             |             |
            |              |             |    +--------+---------+
            |              |             |    |        |         |
            |              |             | +--+--+   +-+---+   +-+---+
            +--------------+             | |BIN  |   |BIN  |   |BIN  |
                                         | |FILE |   |FILE |   |FILE |
          +----LEGEND-----------+        | |     |   |     |   |     |
          | # Circular buffer   |        | |     |   |     |   |     |
          |                     |        | +-----+   +-----+   +-----+
          |                     |        | Buffer0   Buffer1   Buffer2
          |                     |        |
          +---------------------+        |
                                         |  Above file usable by SystemView PC app
                                         |

```

Here is the output of the help option:

```
usage: sysview_postmortem_retriever.py [-h] [--endianess {little,big}] base_addr raw_binary

Converts raw memory dumps into binaries readable by SystemView.

positional arguments:
  base_addr             The base address of _SEGGER_RTT in hexadecimal
  raw_binary            The memory dump

options:
  -h, --help            show this help message and exit
  --endianess {little,big}
                        The memory endianess (default: little)
```

Example of call
```bash
python .\sysview_postmortem_trace_retriever.py 0x200119f4 dump_raw.bin --endianess little
```
Example of log
```
2022-06-24 14:51:37,826 - sysview_postmortem_trace_retriever - INFO - Building struct for little endianess
2022-06-24 14:51:37,827 - sysview_postmortem_trace_retriever - INFO - Reading file raw.bin
2022-06-24 14:51:37,830 - sysview_postmortem_trace_retriever - INFO - Maximum number of buffer found : up 3  |  down 3
2022-06-24 14:51:37,830 - sysview_postmortem_trace_retriever - INFO - Extracting buffer on index 0 into buffer_0.bin
2022-06-24 14:51:37,830 - sysview_postmortem_trace_retriever - INFO - Extracting buffer on index 1 into buffer_1.bin
2022-06-24 14:51:37,831 - sysview_postmortem_trace_retriever - INFO - Extracting buffer on index 2 into buffer_2.bin
2022-06-24 14:51:37,831 - sysview_postmortem_trace_retriever - WARNING - Systemview buffer at index 2 not initialized, no file created
```
A file by buffer will be created (except if the buffer is not initialized, like above for the buffer 2). The created files can be directly read by the SystemView PC application.

*Note*: Usually, by default, the SystemView RTT buffer is the `buffer_1`.

### Open in SystemView

To open a file in the SystemView PC application, open the application, go to `File -> Load Data (ctrl + O)` and select the generated file you want to open, `buffer_1` by default.

## Troubleshoot

### SEGGER RTT Tag not found

In that case, the tool did not detect the SEGGER RTT Tag in the beginning of the file.
This might be caused by a wrong address memory dump.

### Not enough data

In that case, the tool has not enough data to complete the buffer extract.
This might be caused by a too small memory dump. Please check the memory dump size is at least the size of the section described [here](#How-to-use).

Another reason can be that there are not enough data in the circular buffer. In order to identify this issue, make sure to add more events before the next memory dump and retry to run `sysview_postmortem_trace_retriever.py`.


### Timestamps at 0 when opening SystemView PC app

If all the events in SystemView have a timestamps at zero, some timestamps configuration may be missing in the embedded card.

As written in the section *SEGGER_SYSVIEW_GET_TIMESTAMP()* of the [SEGGER SystemView User Guide](https://www.segger.com/downloads/systemview/UM08027), for the Cortex-M3/4/7, SystemView uses the Cortex-M cycle counter. By default, this counter is not enable.
Here is an example to enable it on a STM32F7508-DK board:

```C
#include "stm32f7xx.h"
CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
/*
* Magic number described in section B2.3.10 of
* ARM CoreSight Architecture Specification document (v3.0)
*/
DWT->LAR = 0xC5ACCE55; 
DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
```

On other devices, you will need to provide an implementation of the function `SEGGER_SYSVIEW_X_GetTimestamp()`.
