# AMFP: Algebraic Mobile Frequency Patterns

AMFP is a beginner-friendly research prototype for turning **lawfully obtained wireless signal measurements** into mathematical features that can be analyzed for unusual changes.

## Important scope

This project does not unlock or take control of a phone's cellular modem. It does not intercept calls, messages, or private communications. A normal Android app can access only the cellular measurements exposed by Android and the device manufacturer. Raw cellular I/Q samples generally require specialized, supported RF hardware and platform-specific software.

The first version accepts measurements from a trusted source and calculates:
- Signal-to-noise difference (SNR, when signal and noise are expressed in compatible dB units)
- Frequency offset
- Bandwidth-to-sample-rate ratio

These measurements are **features**, not proof of an intrusion. Network handovers, distance, buildings, interference, and device behavior can all cause changes.

## Files

- `amfp_math.asm`: x86-64 Linux NASM function that converts six measurements into nine output fields.
- `test_amfp.py`: Python/ctypes test harness for the assembly function.

## Requirements

- x86-64 Linux
- NASM
- GCC
- Python 3

## Build

From this directory:

```bash
nasm -f elf64 -g -F dwarf amfp_math.asm -o amfp_math.o
gcc -shared -o libamfp.so amfp_math.o
python3 test_amfp.py
```

If your system requires position-independent objects for shared libraries, assemble with `nasm -f elf64 -DPIC` (this source uses no absolute data references).

## Input fields

| Field | Meaning | Unit |
|---|---|---|
| center_frequency_hz | Receiver's selected center frequency | Hz |
| peak_frequency_hz | Measured peak frequency | Hz |
| signal_power_mdbm | Signal power in thousandths of a dBm | milli-dBm |
| noise_power_mdbm | Noise power in thousandths of a dBm | milli-dBm |
| bandwidth_hz | Measured bandwidth | Hz |
| sample_rate_hz | Measurement sample rate | samples/second |

The power fields use milli-dBm integers so the assembly routine can avoid floating-point arithmetic. For example, -60 dBm is -60000 milli-dBm.

## Output fields

- The six original measurements
- `snr_mdb`: signal power minus noise power, in milli-dB
- `frequency_offset_hz`: peak frequency minus center frequency
- `bandwidth_ratio_ppm`: bandwidth divided by sample rate, multiplied by 1,000,000

## Next step: Android measurement input

A future Android client can collect only the cellular metadata made available through Android's telephony APIs and pass supported measurements to this engine. Not every phone exposes every field, and Android generally does not expose raw cellular I/Q samples to ordinary apps. Missing values should remain marked as unavailable rather than being fabricated.

Use only measurements from devices and networks you are authorized to test.
