#!/usr/bin/env python3
"""
 Generic Modbus RTU polling script
 Dependencies:
    pip install pymodbus
"""
from pymodbus.client import ModbusSerialClient
import struct
import time
import sys

# ============================================================
# CONFIGURATION SECTION
# ============================================================
MODBUS_RTU_CONFIGS = [
    {
        "name": "w3g630-ns37-05",
        "port": "/dev/ttyUSB0", # or whatever it is
        "baudrate": 9600,
        "parity": "N",      # N, E, or O
        "stopbits": 1,
        "slave": 1,
        "endian": "little",
        "registers": [
            ("MAX_RPM", 100, "float"),
            ("MIN_RPM", 110, "float"),
            ("StatusWord", 200, "word"),
            ("AlarmBits", 210, "bits", 8)
        ]
    },
    {
        "name": "fan_actuator",
        "port": "/dev/ttyUSB1",
        "baudrate": 19200,
        "parity": "E",
        "stopbits": 1,
        "slave": 2,
        "endian": "big",
        "registers": [
            ("Current_RPM", 300, "word"),
            ("Target", 301, "float"),
        ]
    }
]


# ============================================================
# FUNCTIONS
# ============================================================

def read_modbus_value(client, slave, reg, dtype, endian="little", bitcount=8):
    """Read a Modbus register and return the decoded value."""
    if dtype == "word":
        result = client.read_holding_registers(reg, 1, slave=slave)
        if result.isError():
            return None
        return result.registers[0]

    elif dtype == "float":
        result = client.read_holding_registers(reg, 2, slave=slave)
        if result.isError():
            return None
        regs = result.registers
        if endian == "little":
            regs = regs[::-1]
        # Pack into bytes and unpack as float
        packed = struct.pack(">HH", *regs) if endian == "big" else struct.pack("<HH", *regs)
        return struct.unpack(">f" if endian == "big" else "<f", packed)[0]

    elif dtype == "bits":
        result = client.read_coils(reg, bitcount, slave=slave)
        if result.isError():
            return None
        return result.bits[:bitcount]

    else:
        return None


def poll_device(config):
    """Connect to a Modbus RTU device and read configured registers."""
    print(f"\n=== Device: {config['name']} ===")
    client = ModbusSerialClient(
        port=config["port"],
        baudrate=config["baudrate"],
        parity=config["parity"],
        stopbits=config["stopbits"],
        bytesize=8,
        timeout=1
    )

    if not client.connect():
        print(f"Failed to connect to {config['port']}")
        return

    for reg in config["registers"]:
        name = reg[0]
        addr = reg[1]
        dtype = reg[2]
        bitcount = reg[3] if len(reg) > 3 else 8

        val = read_modbus_value(
            client,
            config["slave"],
            addr,
            dtype,
            endian=config.get("endian", "little"),
            bitcount=bitcount
        )

        if val is None:
            print(f"{name:<15} (addr {addr}) -> ERROR")
        elif dtype == "bits":
            bitstr = "".join(str(int(b)) for b in val)
            print(f"{name:<15} (bits {addr}) -> {bitstr}")
        elif dtype == "float":
            print(f"{name:<15} (float {addr}) -> {val:.2f}")
        else:
            print(f"{name:<15} (word {addr}) -> {val}")

    client.close()


# ============================================================
# MAIN LOOP
# ============================================================
def main():
    print("Starting Modbus RTU poller...\n")
    for cfg in MODBUS_RTU_CONFIGS:
        poll_device(cfg)
    print("\nAll devices polled successfully.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
