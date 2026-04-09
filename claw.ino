// B2 Firehound / Marc Girard, Clément Guidat, Paul Scheerlinck, Quentin Blachier / 2026

#include <ESP32Servo.h> // Bibliothèque pour contrôler les servomoteurs sur ESP32

Servo servo1; // On crée un objet servo pour le canal 1
Servo servo2; // On crée un objet servo pour le canal 2

#define SERVO1_PIN 18 // Broche du servo 1
#define SERVO2_PIN 19 // Broche du servo 2

HardwareSerial ELRS(1); // On crée un port série UART1 pour communiquer avec le récepteur ELRS

#define RXD1 16 // Broche de réception (RX) pour UART1
#define TXD1 17 // Broche de transmission (TX) pour UART1

int ch1 = 1500; // Canal 1 initialisé à 1500
int ch2 = 1500; // Canal 2 initialisé à 1500

void setup() {
  servo1.attach(SERVO1_PIN); // On attache le servo1 à sa broche
  servo2.attach(SERVO2_PIN); // On attache le servo2 à sa broche

  ELRS.begin(420000, SERIAL_8N1, RXD1, TXD1); // On initialise le port ELRS avec protocole CRSF
}

void loop() {
  // On vérifie si un paquet complet (26 octets) est disponible depuis le récepteur ELRS
  if (ELRS.available() >= 26) {
    uint8_t packet[26]; // Tableau pour stocker le paquet
    ELRS.readBytes(packet, 26); // On lit les 26 octets

    // On vérifie que c’est bien un paquet de canaux RC
    if (packet[2] == 0x16) { // Type = RC channels
      int bitIndex = 0; // Pour parcourir les bits du paquet

      // On décode les deux premiers canaux
      for (int i = 0; i < 2; i++) {
        uint16_t val = 0; // Valeur brute du canal

        // Chaque canal est codé sur 11 bits
        for (int b = 0; b < 11; b++) {
          // Si le bit est actif dans le paquet
          if (packet[3 + (bitIndex >> 3)] & (1 << (bitIndex & 7))) {
            val |= (1 << b); // On met le bit dans la valeur
          }
          bitIndex++; // On passe au bit suivant
        }

        // Conversion du format CRSF (172–1811) vers signal RC standard (1000–2000)
        int us = map(val, 172, 1811, 1000, 2000);

        // On met à jour les canaux correspondants
        if (i == 0) ch1 = us;
        if (i == 1) ch2 = us;
      }
    }
  }

  // On envoie les valeurs RC aux servos
  servo1.writeMicroseconds(ch1); // Canal 1 vers servo1
  servo2.writeMicroseconds(ch2); // Canal 2 vers servo2
}
