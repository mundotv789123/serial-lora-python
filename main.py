import threading
import serial
import time

# CONFIG
TIME_OUT_SECS=5
SERIAL_PORT='/dev/ttyAMA0'
RETRY_COUNT=3

# PROPs
time_send = None
retried = 0

try:
    ser = serial.Serial(SERIAL_PORT, 9600, timeout=1)
    print(f"Connected to: {ser.portstr}")

    def listening():
        global time_send
        global retried

        while True:
            if ser.in_waiting == 0:
                continue
            try:
                payload=ser.read(255)
                if len(payload) == 0:
                    continue

                cur_seq = payload[0] % 16
                if payload[0] >= 0x10 and payload[0] <= 0x1F and len(payload) >= 2:
                    data = payload[2:(payload[1]+2)]
                    line = bytes(data).decode('utf-8').rstrip('\n\r')
                    print(f"\nDAT{cur_seq}: '{line}'")

                    ser.write([(0x20 + cur_seq)])
                elif payload[0] >= 0x20 and payload[0] <= 0x2F:
                    diff_timer = time.perf_counter() - time_send
                    print(f"\nACK{cur_seq} {diff_timer:.4f}segs")

                    time_send = None
                    retried = 0
                else:
                    line=bytes(payload).decode('utf-8')
                    print(f'ERRO: mensagem desconhecida: {line}')

            except Exception as e:
                print(f'error! {e}')
            time.sleep(0.1)

    thread = threading.Thread(target=listening)
    thread.start()

    count=0

    last_tx_seq = 0
    payload = []
    while True:
        try:
            if time_send is not None:
                if time.perf_counter() - time_send > (TIME_OUT_SECS * (retried + 1)):
                    if retried < RETRY_COUNT:
                        retried += 1
                        ser.write(payload)
                        continue
                    time_send = None
                    retried = 0
                    print('\nERRO: mensagem não entregue')
                else:
                    count = count + 1 if count < 3 else 0
                    print('\r'+('.'*count)+(' '*(3 - count)), end="")
                    time.sleep(0.25)
                    continue
            
            response = str(input())
            response = f'{response}\n\r'
            data = list(response.encode())
            payload = [(0x10+last_tx_seq), len(data)] + data + [0x01, 0x01]
            last_tx_seq = last_tx_seq + 1 if last_tx_seq < 16 else 0
            ser.write(payload)
            time_send = time.perf_counter()

        except Exception as e:
            print(f'error! {e}')
        time.sleep(0.01)

except serial.SerialException as e:
    print(f"Error: {e}")

finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
        print("Serial port closed.")
