; AMFP Mathematical Signal Engine
; Architecture: x86-64 Linux, System V ABI
; Assembler: NASM
;
; int radio_to_math(const Input *input, Output *output)
;
; Input: six 64-bit fields:
;   +0  center_frequency_hz      (uint64)
;   +8  peak_frequency_hz        (uint64)
;   +16 signal_power_mdbm        (int64)
;   +24 noise_power_mdbm         (int64)
;   +32 bandwidth_hz             (uint64)
;   +40 sample_rate_hz           (uint64)
;
; Output: nine 64-bit fields:
;   +0  center_frequency_hz
;   +8  peak_frequency_hz
;   +16 signal_power_mdbm
;   +24 noise_power_mdbm
;   +32 bandwidth_hz
;   +40 sample_rate_hz
;   +48 snr_mdb
;   +56 frequency_offset_hz (signed result)
;   +64 bandwidth_ratio_ppm
;
; Return: 0 success, -1 if sample_rate_hz is zero.
;
; Power values are milli-dBm integers. Example: -60 dBm = -60000.
; This routine processes measurements; it does not receive radio signals.

global radio_to_math

section .text

radio_to_math:
    ; Copy the six input measurements to output.
    mov rax, [rdi]
    mov [rsi], rax

    mov rax, [rdi + 8]
    mov [rsi + 8], rax

    mov rax, [rdi + 16]
    mov [rsi + 16], rax

    mov rax, [rdi + 24]
    mov [rsi + 24], rax

    mov rax, [rdi + 32]
    mov [rsi + 32], rax

    mov rax, [rdi + 40]
    mov [rsi + 40], rax

    ; SNR difference in milli-dB:
    ; signal_power_mdbm - noise_power_mdbm
    mov rax, [rdi + 16]
    sub rax, [rdi + 24]
    mov [rsi + 48], rax

    ; Signed frequency offset:
    ; peak_frequency_hz - center_frequency_hz
    mov rax, [rdi + 8]
    sub rax, [rdi]
    mov [rsi + 56], rax

    ; bandwidth_ratio_ppm =
    ; (bandwidth_hz * 1,000,000) / sample_rate_hz
    mov rcx, [rdi + 40]
    test rcx, rcx
    jz .invalid_input

    mov rax, [rdi + 32]
    xor edx, edx
    mov r8, 1000000
    mul r8                  ; RDX:RAX = RAX * R8
    div rcx                 ; quotient in RAX
    mov [rsi + 64], rax

    xor eax, eax
    ret

.invalid_input:
    mov rax, -1
    ret
