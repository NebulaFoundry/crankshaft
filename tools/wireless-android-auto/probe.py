"""Test the Bluetooth handoff to Crankshaft's Android Auto TCP listener."""

import argparse
import socket
import struct
import threading

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib


PROFILE_UUID = "4de17a00-52cb-11e6-bdf4-0800200c9a66"
PROFILE_PATH = "/org/crankshaft/WirelessAndroidAuto"
PROFILE_INTERFACE = "org.bluez.Profile1"


def varint(value):
    result = bytearray()
    while value >= 128:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return bytes(result)


def field(number, value):
    if isinstance(value, int):
        return varint(number << 3) + varint(value)
    value = value.encode()
    return varint((number << 3) | 2) + varint(len(value)) + value


def read_exact(connection, size):
    result = bytearray()
    while len(result) < size:
        chunk = connection.recv(size - len(result))
        if not chunk:
            raise EOFError
        result.extend(chunk)
    return bytes(result)


def send_frame(connection, kind, payload):
    connection.sendall(struct.pack(">HH", len(payload), kind) + payload)


class Profile(dbus.service.Object):
    def __init__(self, bus, loop, phone, endpoint, credentials):
        super().__init__(bus, PROFILE_PATH)
        self.bus = bus
        self.loop = loop
        self.phone = phone
        self.endpoint = endpoint
        self.credentials = credentials
        self.active = None

    def require_bluez(self, sender):
        if sender != self.bus.get_name_owner("org.bluez"):
            raise dbus.exceptions.DBusException(
                "Only BlueZ can open the profile.", name="org.bluez.Error.Rejected"
            )

    @dbus.service.method(PROFILE_INTERFACE, in_signature="", out_signature="",
                         sender_keyword="sender")
    def Release(self, sender=None):
        self.require_bluez(sender)
        self.loop.quit()

    @dbus.service.method(PROFILE_INTERFACE, in_signature="oha{sv}", out_signature="",
                         sender_keyword="sender")
    def NewConnection(self, device, fd, properties, sender=None):
        self.require_bluez(sender)
        if device.rsplit("/", 1)[-1] != self.phone or self.active is not None:
            raise dbus.exceptions.DBusException(
                "A different phone or connection is active.", name="org.bluez.Error.Rejected"
            )
        self.active = socket.socket(fileno=fd.take())
        threading.Thread(target=self.exchange, args=(self.active,), daemon=True).start()

    @dbus.service.method(PROFILE_INTERFACE, in_signature="o", out_signature="",
                         sender_keyword="sender")
    def RequestDisconnection(self, device, sender=None):
        self.require_bluez(sender)
        if device.rsplit("/", 1)[-1] == self.phone and self.active is not None:
            try:
                self.active.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def exchange(self, connection):
        try:
            with connection:
                connection.settimeout(60)
                print("Phone opened the Android Auto Bluetooth profile", flush=True)
                send_frame(connection, 1, self.endpoint)
                # The legacy WPP exchange uses the field layout documented in
                # open-android-auto/docs/wireless-bluetooth-setup.md.
                while True:
                    size, kind = struct.unpack(">HH", read_exact(connection, 4))
                    payload = read_exact(connection, size)
                    print(f"Phone sent Bluetooth message type {kind}", flush=True)
                    if kind == 2:
                        send_frame(connection, 3, self.credentials)
                        print("Sent the hotspot details to the paired phone", flush=True)
                    elif kind == 8:
                        send_frame(connection, 9, payload)
        except (EOFError, OSError):
            print("Phone Bluetooth session ended", flush=True)
        finally:
            GLib.idle_add(self.clear_connection)

    def clear_connection(self):
        self.active = None
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phone", required=True, help="Paired phone Bluetooth address")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=5277)
    parser.add_argument("--ssid", required=True)
    parser.add_argument("--bssid", required=True)
    parser.add_argument("--password-file", required=True)
    parser.add_argument("--seconds", type=int, default=180)
    args = parser.parse_args()
    with open(args.password_file, encoding="utf-8") as source:
        password = source.read().strip()
    credentials = (
        field(1, args.ssid) + field(2, password) + field(3, args.bssid.upper())
        + field(4, 8) + field(5, 1)
    )
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    loop = GLib.MainLoop()
    phone = "dev_" + args.phone.upper().replace(":", "_")
    profile = Profile(bus, loop, phone, field(1, args.host) + field(2, args.port), credentials)
    manager = dbus.Interface(bus.get_object("org.bluez", "/org/bluez"), "org.bluez.ProfileManager1")
    manager.RegisterProfile(PROFILE_PATH, PROFILE_UUID, {
        "Name": "Wireless Android Auto",
        "Role": "server",
        "Channel": dbus.UInt16(23),
        "ServiceRecord": """<record>
<attribute id="0x0001">
<sequence>
<uuid value="4de17a00-52cb-11e6-bdf4-0800200c9a66"/>
</sequence>
</attribute>
<attribute id="0x0004">
<sequence>
<sequence>
<uuid value="0x0100"/>
</sequence>
<sequence>
<uuid value="0x0003"/>
<uint8 value="0x17"/>
</sequence>
</sequence>
</attribute>
<attribute id="0x0005">
<sequence>
<uuid value="0x1002"/>
</sequence>
</attribute>
<attribute id="0x0100">
<text value="Android Auto Wireless"/>
</attribute>
</record>""",
        "RequireAuthentication": dbus.Boolean(True),
        "RequireAuthorization": dbus.Boolean(False),
    })
    print("Android Auto Bluetooth profile registered", flush=True)
    GLib.timeout_add_seconds(args.seconds, loop.quit)
    try:
        loop.run()
    finally:
        manager.UnregisterProfile(PROFILE_PATH)
        profile.remove_from_connection()


if __name__ == "__main__":
    main()
