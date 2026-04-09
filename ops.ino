// B2 Firehound / Marc Girard, Clément Guidat, Paul Scheerlinck, Quentin Blachier / 2026

#include <HardwareSerial.h> // Bibliothèque pour utiliser les ports série de l'ESP32

HardwareSerial ELRS(1); // On crée un port série (UART1)

#define RXD1 16 // Broche de réception (RX) pour le port qu'on a créé
#define TXD1 17 // Broche de transmission (TX) pour le port qu'on a créé

int ch1 = 1500; // Canal 1 de la radio (valeur neutre)
int ch2 = 1500; // Canal 2 de la radio (valeur neutre)

void setup() {
  Serial.begin(115200); // Permet de communiquer avec le PC
  ELRS.begin(420000, SERIAL_8N1, RXD1, TXD1); // On initialise le port en 420000 baud (protocole CRSF)
}

// Fonction pour convertir une valeur en signal RC (entre 1000 et 2000)
int mapAxis(int val, int in_min, int in_max) {
  val = constrain(val, in_min, in_max); // On limite la valeur dans une plage
  return map(val, in_min, in_max, 1000, 2000); // On convertit vers la plage RC standard
}

// Fonction pour envoyer les données au format CRSF (Crossfire)
void sendCRSF(int ch1, int ch2) {
  uint8_t packet[26]; // On crée un tableau de 26 octets (taille d’un paquet CRSF)

  // Début du paquet CRSF
  packet[0] = 0xC8; // Adresse du récepteur
  packet[1] = 24;   // Longueur du message
  packet[2] = 0x16; // Type de message : on envoi des canaux RC (Radio Commande)

  uint16_t channels[16] = {1500}; // On crée 16 canaux initialisés à 1500

  channels[0] = ch1; // On met la valeur du canal 1
  channels[1] = ch2; // On met la valeur du canal 2

  int bitIndex = 0; // ça sert à placer les bits dans le paquet

  // On parcourt les 16 canaux
  for (int i = 0; i < 16; i++) {

    // On convertit le signal RC (1000–2000) vers le format CRSF (172–1811)
    uint16_t val = map(channels[i], 1000, 2000, 172, 1811);

    // Chaque canal est codé sur 11 bits
    for (int b = 0; b < 11; b++) {

      // Si le bit est actif
      if (val & (1 << b)) {
        // On place le bit au bon endroit dans le tableau
        packet[3 + (bitIndex >> 3)] |= (1 << (bitIndex & 7));
      }

      bitIndex++; // On passe au bit suivant
    }
  }

  packet[25] = 0; // CRC (Cyclic Redundancy Check) mis à 0, donc les erreurs de transmission ne sont pas détectées

  ELRS.write(packet, 26); // On envoie le paquet au récepteur
}

void loop() {

  // On vérifie si des données arrivent depuis le PC
  if (Serial.available()) {

    String line = Serial.readStringUntil('\n'); // On lit une ligne complète

    int comma = line.indexOf(','); // On cherche la virgule

    if (comma > 0) {

      // On récupère les deux valeurs
      int x = line.substring(0, comma).toInt();      // Valeur X
      int y = line.substring(comma + 1).toInt();     // Valeur Y

      // On convertit les coordonnées en signaux RC
      ch1 = mapAxis(x, 0, 1920); // Largeur de l'image (1920 px)
      ch2 = mapAxis(y, 0, 1080); // Hauteur de l'image (1080 px)
    }
  }

  sendCRSF(ch1, ch2); // On envoie les commandes au drone

  delay(20); // Pause de 0,02s (environ 50 Hz)
}
