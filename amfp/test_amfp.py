import ctypes
from pathlib import Path


class Input(ctypes.Structure):
    _fields_ = [
        ("center_frequency_hz", ctypes.c_uint64),
        ("peak_frequency_hz", ctypes.c_uint64),
        ("signal_power_mdbm", ctypes.c_int64),
        ("noise_power_mdbm", ctypes.c_int64),
        ("bandwidth_hz", ctypes.c_uint64),
        ("sample_rate_hz", ctypes.c_uint64),
    ]


class Output(ctypes.Structure):
    _fields_ = [
        ("center_frequency_hz", ctypes.c_uint64),
        ("peak_frequency_hz", ctypes.c_uint64),
        ("signal_power_mdbm", ctypes.c_int64),
        ("noise_power_mdbm", ctypes.c_int64),
        ("bandwidth_hz", ctypes.c_uint64),
        ("sample_rate_hz", ctypes.c_uint64),
        ("snr_mdb", ctypes.c_int64),
        ("frequency_offset_hz", ctypes.c_int64),
        ("bandwidth_ratio_ppm", ctypes.c_uint64),
    ]


library_path = Path(__file__).with_name("libamfp.so")
if not library_path.exists():
    raise SystemExit(
        "Missing libamfp.so. Build it first using the commands in README.md."
    )

library = ctypes.CDLL(str(library_path))
radio_to_math = library.radio_to_math
radio_to_math.argtypes = [
    ctypes.POINTER(Input),
    ctypes.POINTER(Output),
]
radio_to_math.restype = ctypes.c_int


# Example measurements only; these are not live phone readings.
measurements = Input(
    center_frequency_hz=900_000_000,
    peak_frequency_hz=900_010_000,
    signal_power_mdbm=-60_000,  # -60 dBm
    noise_power_mdbm=-95_000,   # -95 dBm
    bandwidth_hz=200_000,
    sample_rate_hz=2_000_000,
)

result = Output()
status = radio_to_math(
    ctypes.byref(measurements),
    ctypes.byref(result),
)

if status != 0:
    raise SystemExit("AMFP assembly function reported invalid input.")

print("AMFP mathematical signal report")
print("--------------------------------")
print(f"Center frequency: {result.center_frequency_hz:,} Hz")
print(f"Peak frequency:   {result.peak_frequency_hz:,} Hz")
print(f"Signal power:     {result.signal_power_mdbm / 1000:.3f} dBm")
print(f"Noise power:      {result.noise_power_mdbm / 1000:.3f} dBm")
print(f"Bandwidth:        {result.bandwidth_hz:,} Hz")
print(f"Sample rate:      {result.sample_rate_hz:,} samples/s")
print(f"SNR difference:   {result.snr_mdb / 1000:.3f} dB")
print(f"Frequency offset: {result.frequency_offset_hz:,} Hz")
print(f"Bandwidth ratio:  {result.bandwidth_ratio_ppm:,} ppm")
