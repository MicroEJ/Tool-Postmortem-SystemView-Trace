#
# Python
#
# Copyright 2023 MicroEJ Corp. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be found with this software.
#

import argparse
from pathlib import Path
from scapy.all import LEIntField, XLEIntField, IntField, XIntField, Packet, StrFixedLenField, PacketListField

import logging
import logging.config
import yaml

# Logger configuration for the script execution.
LOGGER_CONFIG = """
version: 1
formatters:
  simple:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
handlers:
  console:
    class: logging.StreamHandler
    level: DEBUG
    formatter: simple
    stream: ext://sys.stdout
loggers:
  simpleExample:
    level: DEBUG
    handlers: [console]
    propagate: no
root:
  level: INFO
  handlers: [console]
  """

__TOOL_NAME__ = Path(__file__).stem


#
# Declaration of classes used to parse and store data from SEGGER RTT buffers.
#

class SEGGER_RTT_BUFFER_DOWN(Packet):
    def extract_padding(self, s):
        return '', s


class SEGGER_RTT_BUFFER_UP(Packet):
    def extract_padding(self, s):
        return '', s


class SEGGER_RTT_CB(Packet):
    def extract_padding(self, s):
        return '', s

"""
    Instantiates the structures used by System View to log data during analysis.
    
    It is composed of three structures:
    - SEGGER_RTT_BUFFER_DOWN: the buffer data structure used by the probe to write to the target.
    - SEGGER_RTT_BUFFER_UP: the buffer data structure used by the target to write to the probe.
    - SEGGER_RTT_CB: Data structure of the Control Block with Up and Down buffer descriptors.
"""
def build_structs(endianess: str):
    logger = logging.getLogger(__TOOL_NAME__)
    logger.info(f"Building struct for {endianess} endianess")
    if endianess == "little":
        int_field = LEIntField
        x_int_field = XLEIntField
    else:
        int_field = IntField
        x_int_field = XIntField

    SEGGER_RTT_BUFFER_DOWN.fields_desc = [
                                            x_int_field(name="sName", default=None),
                                            x_int_field(name="pBuffer", default=None),
                                            int_field(name="SizeOfBuffer", default=None),
                                            int_field(name="WrOff", default=None),
                                            int_field(name="RdOff", default=None),
                                            int_field(name="Flags", default=None),
                                        ]

    SEGGER_RTT_BUFFER_UP.fields_desc = [
                                            x_int_field(name="sName", default=None),
                                            x_int_field(name="pBuffer", default=None),
                                            int_field(name="SizeOfBuffer", default=None),
                                            int_field(name="WrOff", default=None),
                                            int_field(name="RdOff", default=None),
                                            int_field(name="Flags", default=None),
                                        ]
    SEGGER_RTT_CB.fields_desc = [
                                    StrFixedLenField(name="acID", length=16, default=None),
                                    int_field("MaxNumUpBuffers", default=None),
                                    int_field(name="MaxNumDownBuffers", default=None),
                                    PacketListField(name="aUp", pkt_cls=SEGGER_RTT_BUFFER_UP, count_from=lambda pkt: pkt.MaxNumUpBuffers, default=[]),
                                    PacketListField(name="aDown", pkt_cls=SEGGER_RTT_BUFFER_DOWN, count_from=lambda pkt: pkt.MaxNumDownBuffers, default=[])
                                ]

"""
    Converts the content of the input binary file into several files in the System View PC software format.
    
    This function has several steps:
    1. Read the SEGGER RTT Control Block
    2. Search for the SEGGER RTT signature
    3. Parse the binary file and read Up buffers
    4. Generate buffer_x.bin files with the relevant content for each Up buffers.

    One file is generated per non-empty Up buffer read.
"""
def parse_SEGGER_RTT(base_addr: int, raw_file: Path):
    logger = logging.getLogger(__TOOL_NAME__)

    logger.info(f"Reading file {raw_file}")
    data = open(raw_file,"rb").read()
    RTT_HEADER = SEGGER_RTT_CB(_pkt=data)
    logger.debug("\n"+RTT_HEADER.show(dump=True))

    assert RTT_HEADER.acID == b'SEGGER RTT\x00\x00\x00\x00\x00\x00', "SEGGER RTT Tag not found"

    logger.info(f"Maximum number of buffer found : up {RTT_HEADER.MaxNumUpBuffers}  |  down {RTT_HEADER.MaxNumDownBuffers}")
    index = 0
    for buffUp in RTT_HEADER.aUp:
        logger.info(f"Extracting buffer on index {index} into buffer_{index}.bin")
        if buffUp.pBuffer != 0:

            sysview_buffer_offset = buffUp.pBuffer - base_addr

            logger.debug(f"Buffer raw data : {data[sysview_buffer_offset : sysview_buffer_offset + buffUp.SizeOfBuffer]}")

            beg = data[sysview_buffer_offset + buffUp.WrOff: sysview_buffer_offset + buffUp.SizeOfBuffer]

            fin = data[sysview_buffer_offset : sysview_buffer_offset + buffUp.RdOff - 1]
            assert len(beg) + len(fin) == buffUp.SizeOfBuffer, f"Not enough data: missing  {len(beg) + len(fin) - buffUp.SizeOfBuffer} bytes"

            with open(Path(f"buffer_{index}.bin"), "wb") as file:
                file.write(beg)
                file.write(fin)
        else:
            logger.warning(f"Systemview buffer at index {index} not initialized, no file created")
        index += 1



if __name__ == '__main__':

    conf_dict = yaml.full_load(LOGGER_CONFIG)
    logging.config.dictConfig(conf_dict)
    logger = logging.getLogger(__name__)

    # Retrieve and check arguments
    parser = argparse.ArgumentParser(description='Converts raw memory dumps into binaries readable by SystemView.')
    parser.add_argument('base_addr', type=lambda x: int(x,0),
                        help='The base address of _SEGGER_RTT in hexadecimal')
    parser.add_argument('raw_binary', type=Path,
                        help='The memory dump')
    parser.add_argument("--endianess", default="little", type=str, required=False, choices=["little","big"],
                        help='The memory endianess (default: little)')
    args = parser.parse_args()

    # Setup the structures that will store data from the input binary file.
    build_structs(args.endianess)

    # Generate binaries compliant with System View PC software
    parse_SEGGER_RTT(args.base_addr, args.raw_binary)


