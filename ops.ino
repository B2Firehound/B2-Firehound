B2 Firehound / Marc Girard, Clément Guidat, Paul Scheerlinck, Quentin Blachier​ / 2026


#include <HardwareSerial.h>

HardwareSerial ELRS(1); // UART1

#define RXD1 16
#define TXD1 17

int ch1 = 1500;
int ch2 = 1500;

void setup() {
  Serial.begin(115200);   // USB
  ELRS.begin(420000, SERIAL_8N1, RXD1, TXD1); // CRSF = 420k baud
}

int mapAxis(int val, int in_min, int in_max) {
  val = constrain(val, in_min, in_max);
  return map(val, in_min, in_max, 1000, 2000);
}

void sendCRSF(int ch1, int ch2) {
  uint8_t packet[26];

  // Header CRSF
  packet[0] = 0xC8; // adresse
  packet[1] = 24;   // longueur
  packet[2] = 0x16; // RC channels

  uint16_t channels[16] = {1500};

  channels[0] = ch1;
  channels[1] = ch2;

  int bitIndex = 0;

  for (int i = 0; i < 16; i++) {
    uint16_t val = map(channels[i], 1000, 2000, 172, 1811);
    for (int b = 0; b < 11; b++) {
      if (val & (1 << b))
        packet[3 + (bitIndex >> 3)] |= (1 << (bitIndex & 7));
      bitIndex++;
    }
  }

  // CRC simple (à améliorer si besoin)
  packet[25] = 0;

  ELRS.write(packet, 26);
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');

    int comma = line.indexOf(',');
    if (comma > 0) {
      int x = line.substring(0, comma).toInt();
      int y = line.substring(comma + 1).toInt();

      ch1 = mapAxis(x, 0, 1920);
      ch2 = mapAxis(y, 0, 1080);
    }
  }

  sendCRSF(ch1, ch2);
  delay(20); // ~50Hz
}

