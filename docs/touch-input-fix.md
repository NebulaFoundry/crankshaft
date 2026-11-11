# Android Auto touch coordinate fix

## Reproduction

On a OnePlus 13, Raspberry Pi 4, and original 800x480 Raspberry Pi touchscreen,
Crankshaft's own buttons worked, but Android Auto app-button taps affected the
map. Press, move, and release reports reached the phone successfully.

A direct tap at the visible Spotify icon's 800x480 coordinate `(774, 220)` did
not open Spotify. The equivalent 1280x720 video coordinate `(1238, 330)` did.
The decoded image had been resized for the screen, while the phone consumed
touch input in its video coordinate space.

## Backend change

The changes are inside the `src/crankshaft-core` Git submodule:

- Snapshot the negotiated video geometry during service discovery.
- Advertise that geometry for both video and touchscreen input.
- Scale UI display coordinates into that video geometry before creating input
  reports. UI display-size updates do not change the session's video geometry.

`TouchCoordinateMapping.h` implements the conversion. Five regression tests in
`test_touch_coordinate_mapping.cpp` cover the reproduced tap, equal resolutions,
display-size changes, bounds, and invalid dimensions.

## Build and tests

With the backend's Linux build dependencies installed:

```bash
cd src/crankshaft-core
cmake -S src -B build-touch -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=ON -DCRANKSHAFT_AASDK_BRANCH=newdev
cmake --build build-touch --target crankshaft-core crankshaft-core-tests -j2
ctest --test-dir build-touch --output-on-failure
```

On the target Pi, compilation succeeded and the full suite reported 46 passes
and one audio test skipped because system audio sockets were present.

With the patched backend running, the original `(774, 220)` screen-space tap
opened Spotify. The backend log confirmed conversion to `(1238, 330)`, and
service discovery advertised 1280x720 touchscreen geometry. The user then
confirmed app switching and media buttons worked on the physical touchscreen.

## Target Pi installation

The test installation uses `/usr/local/libexec/crankshaft-core-touch-fix` and
the systemd override
`/etc/systemd/system/crankshaft-core.service.d/90-touch-coordinate-fix.conf`.
The packaged `/usr/bin/crankshaft-core` remains intact.

To restore the packaged backend:

```bash
sudo rm /etc/systemd/system/crankshaft-core.service.d/90-touch-coordinate-fix.conf
sudo systemctl daemon-reload
sudo systemctl stop crankshaft-ui-slim.service crankshaft-core.service
sudo systemctl start crankshaft-core.service
sudo systemctl start crankshaft-ui-slim.service
```

After a service restart, reconnect the phone and verify app switching,
pause/play, and map dragging on the physical touchscreen.

A separate reconnect limitation was observed: after the USB device disappeared,
input sends failed with AASDK USB_TRANSFER native code `4294967292` (signed
libusb error `-4`, NO_DEVICE), while the service retained its old connection.
A clean stop/start of both services restored projection. USB reconnect recovery
has not been changed by this coordinate patch.

## Other changes in this build

- Android Auto is told that the driver sits on the left.
- Fullscreen has an Exit button in the upper-right corner. The toolbar has a
  Fullscreen button to return to projection.
- The UI service hides the pointer on EGLFS displays.
- Settings has a confirmed Shut Down action. The UI package includes a
  polkit rule that authorizes normal power-off only for the Crankshaft UI
  system service. The action uses systemd-logind and honors shutdown inhibitors.

The image builder installs published Debian packages. To include these source
changes in a new image, build the pinned core and UI packages and make them
available to the image builder.
