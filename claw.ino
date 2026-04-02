#include <ESP32Servo.h>

Servo servo1;
Servo servo2;

#define SERVO1_PIN 18
#define SERVO2_PIN 19

HardwareSerial ELRS(1);

#define RXD1 16
#define TXD1 17

int ch1 = 1500;
int ch2 = 1500;

void setup() {
  servo1.attach(SERVO1_PIN);
  servo2.attach(SERVO2_PIN);

  ELRS.begin(420000, SERIAL_8N1, RXD1, TXD1);
}

void loop() {
  if (ELRS.available() >= 26) {
    uint8_t packet[26];
    ELRS.readBytes(packet, 26);

    if (packet[2] == 0x16) { // RC channels
      int bitIndex = 0;

      for (int i = 0; i < 2; i++) {
        uint16_t val = 0;

        for (int b = 0; b < 11; b++) {
          if (packet[3 + (bitIndex >> 3)] & (1 << (bitIndex & 7))) {
            val |= (1 << b);
          }
          bitIndex++;
        }

        int us = map(val, 172, 1811, 1000, 2000);

        if (i == 0) ch1 = us;
        if (i == 1) ch2 = us;
      }
    }
  }

  servo1.writeMicroseconds(ch1);
  servo2.writeMicroseconds(ch2);
}