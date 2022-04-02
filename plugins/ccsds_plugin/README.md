# CCSDS Plugin

The CCSDS Plugin provides interfaces and utilities for CCSDS messages. It is responsible for parsing message structures and constructing messages with the correct header and payload formats.

### Configuration
The CCSDS plugin reads some values from the `[ccsds]` section of CTF config file:
- **CCSDS_header_info_included:** Boolean indicating whether header info is included in the CCSDS exports
- **CCSDS_header_path:** The full file path of the module implementing CCSDS header types. The file does not need to be inside of the CTF directory.
The CCSDS Plugin provides three header implementations: `ccsds_v1`, `ccsds_v2`, and `ccsds_gw`. To provide your own implementation, see [Custom CCSDS Headers](#custom-cccsds-headers) below.


### ValidateCfsCcsdsData
Validates the format of CFS data types by sending one of each known command with an empty (all zeroes) payload.
- **target:** (string) The name of a registered CFS target. See [CFS Plugin](../cfs/README.md) for registering targets.

Example:
<pre><code>
{
    "instruction": "RegisterCfs",
    "data": {
        "target": "cfs_workstation"
    },
    "wait": 1
},
{
    "instruction": "StartCfs",
    "data": {
        "target": "cfs_workstation"
    },
    "wait": 1
},
{
    "instruction": "ValidateCfsCcsdsData",
    "data": {
        "target": "cfs_workstation"
    },
    "wait": 1
}
</code></pre>

### Custom CCSDS Headers
The CCSDS Plugin provides default implementations of CCSDS message headers, and interfaces for implementing your own custom header types.
Follow these steps to implement your own CCSDS header definitions, and refer to any of the provided implementations for further examples.

#### Create a new module
Create a new Python source file in the desired location. Import `ctypes` and declare classes for each of the primary header, a command packet, and a telemetry packet.
These may extend the corresponding types provided by the CCSDS Plugin, or ultimately from `ctypes.Structure`. CCSDS headers typically extend from `ctypes.BigEndianStructure`.

Example:
<pre><code>
import ctypes

from plugins.ccsds_plugin.ccsds_primary_header import CcsdsPrimaryHeaderBase

class MyPrimaryHeader(CcsdsPrimaryHeaderBase):
    pass

class MyCmdPacket(ctypes.Structure):
    pass

class MyTlmPacket(ctypes.Structure):
    pass
</code></pre>

#### Define the fields and methods
Declare fields representing the bit structure of the headers. See `ctypes` documentation for details. Implement the necessary class methods to expose the field values.
`CcsdsPacketInterface` provides an unimplemented interface for your convenience. You may also implement other structures and methods for internal use. At minimum, the following methods must be implemented:

- **Primary Header:** `get_msg_id()`, `is_command()`
- **Command Packet:** `get_msg_id()`, `get_function_code()`
- **Telemetry Packet:** `get_msg_id()`

Example:
<pre><code>
class MyPrimaryHeader(ctypes.BigEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("type", ctypes.c_uint16, 1),  # Packet type:      0 = TLM, 1 = CMD
        ("app_id", ctypes.c_uint16, 11),  # Application ID
        ("length", ctypes.c_uint16, 16)  # total packet length
    ]

    def is_command(self) -> int:
        return self.type

    def get_msg_id(self) -> int:
        return self.app_id
</code></pre>

#### Export the types
Alias your types to `CcsdsPrimaryHeader`, `CcsdsCommand`, `CcsdsTelemetry` respectively for export. CTF will import and reference them by these names.
In the CTF config file, set `ccsds:CCSDS_header_path` to the full path to your module.

Example:
<pre><code>
CcsdsPrimaryHeader = MyPrimaryHeader
CcsdsCommand = MyCmdPacket
CcsdsTelemetry = MyTlmPacket
</code></pre>

#### Test
Use the `ValidateCfsCcsdsData` in a test script to validate the header definitions as shown above.
If the implementing module contains errors or does not meet the minimum requirements of CTF, `RegisterCfs` will fail and print an error message.
Check CFS output to ensure that it recognized each of the messages and MIDs.
