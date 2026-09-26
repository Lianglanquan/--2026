#!/usr/bin/env bash
set -euo pipefail

# Host-side smoke test for the DJI C Board's official USB CDC device.
# This intentionally sends only PING\n; it never enables or moves an actuator.

vid_pid='0483:5740'
device=''

if command -v lsusb >/dev/null 2>&1; then
    if ! lsusb | grep -q "${vid_pid}"; then
        echo "C Board USB CDC (${vid_pid}) is not enumerated." >&2
        echo "Check the data cable, micro-USB connector, and BOOT0=0." >&2
        exit 2
    fi
fi

for candidate in /dev/serial/by-id/* /dev/ttyACM* /dev/ttyUSB*; do
    [[ -e "${candidate}" ]] || continue
    if udevadm info -q property -n "${candidate}" 2>/dev/null | grep -q 'ID_VENDOR_ID=0483'; then
        device="${candidate}"
        break
    fi
done

if [[ -z "${device}" ]]; then
    echo "USB CDC is present but no 0483 device node was found." >&2
    exit 3
fi

printf 'Using %s\n' "${device}"
stty -F "${device}" 115200 raw -echo -ixon -ixoff 2>/dev/null || true
response_file="$(mktemp)"
cleanup_response() { rm -f "${response_file}"; }
trap cleanup_response EXIT
timeout 2s cat "${device}" >"${response_file}" &
reader_pid=$!
sleep 0.1
printf 'PING\n' >"${device}"
wait "${reader_pid}" || true
response="$(cat "${response_file}")"

if grep -qx 'PONG' <<<"${response}"; then
    echo 'C Board USB CDC PING/PONG: PASS'
    exit 0
fi

printf 'Unexpected response: %q\n' "${response}" >&2
exit 5
