#!/bin/bash
set -euxo pipefail

source "${WORKDIR}/ci/env.sh"

# implemented it this way, because expansion did not work
binaries=(
  "${WORKDIR}/bin/deps/openvpn/${ARCH}/${OPENVPN_VERSION}/openvpn"
)

for binary in "${binaries[@]}"; do
  if [[ -f "${binary}" ]]; then
    hardening-check -q --nocfprotection "${binary}"
  fi
done

# Stack protection is forcibly disabled when building Go apps
# https://github.com/golang/go/blob/202a1a57064127c3f19d96df57b9f9586145e21c/src/runtime/cgo/cgo.go#L28
binaries=(
  "${WORKDIR}/bin/${ARCH}/nordvpnd"
  "${WORKDIR}/bin/${ARCH}/nordfileshared"
  "${WORKDIR}/bin/${ARCH}/nordvpn"
)

for binary in "${binaries[@]}"; do
  if [[ -f "${binary}" ]]; then
    hardening-check -q --nostackprotector --nocfprotection "${binary}"
  fi
done
