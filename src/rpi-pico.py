from machine import Pin, UART, Timer

import time

# CONFIG
TIME_OUT_SECS=5
RETRY_COUNT=3

# PROPs
time_send = None
retried = 0

uart0 = UART(0, 9600, tx=Pin(0), rx=Pin(1))

def listening(timer):
    global time_send
    global retried

    if uart0.any() == 0:
        return
    payload=uart0.read(255)
    if len(payload) == 0:
        return

    cur_seq = payload[0] % 16
    if payload[0] >= 0x10 and payload[0] <= 0x1F and len(payload) >= 2:
        data = payload[2:(payload[1]+2)]
        line = bytes(data).decode('utf-8').rstrip('\n\r')
        print(f"\nDAT{cur_seq}: '{line}'")

        uart0.write(bytes([(0x20 + cur_seq)]))
    elif payload[0] >= 0x20 and payload[0] <= 0x2F:
        diff_timer = time.ticks_diff(time.ticks_ms(), time_send) / 1000
        print(f"\nACK{cur_seq} {diff_timer:.4f}segs")

        time_send = None
        retried = 0
    else:
        line=bytes(payload).decode('utf-8')
        print(f'ERRO: mensagem desconhecida: {line}')


tim = Timer()
tim.init(freq=20, mode=Timer.PERIODIC, callback=listening)

ledPin = Pin('LED', Pin.OUT)
def led_blink(timer):
    ledPin.value((not ledPin.value()) if time_send is not None else 0)

ledtim = Timer()
ledtim.init(freq=5, mode=Timer.PERIODIC, callback=led_blink)

count=0

last_tx_seq = 0
payload = []
while True:
    if time_send is not None:
        diff_timer = time.ticks_diff(time.ticks_ms(), time_send) / 1000
        if diff_timer > (TIME_OUT_SECS * (retried + 1)):
            if retried < RETRY_COUNT:
                retried += 1
                uart0.write(payload)
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
    payload = bytes([(0x10+last_tx_seq), len(data)] + data + [0x01, 0x01])
    last_tx_seq = 1 if last_tx_seq == 0 else 0
    uart0.write(payload)
    time_send = time.ticks_ms()

    time.sleep(0.01)
