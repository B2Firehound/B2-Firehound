# B2 Firehound / Marc Girard, Clément Guidat, Paul Scheerlinck, Quentin Blachier / 2026

from ultralytics import YOLO                  # Import de la librairie YOLO
import os                                     # Import d'une librairie pour gérer des paramètres système
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'   # Évite un bug de conflit de librairies

if __name__ == '__main__':                    # Lance le code seulement si il est exécuté directement
    model = YOLO("best.pt")                   # On charge le modèle YOLO

    model.train(                              # Lance l’entraînement du modèle
        data="C:/Users/Utilisateur/Downloads/RAPACE_dataset/drone.yaml",  # Chemin vers le dataset
        epochs=150,                           # Nombre de cycles d’entrainement
        imgsz=640,                            # Taille des images utilisées
        batch=16,                             # Nombre d’images traitées en même temps
        lr0=0.001,                            # Vitesse d’apprentissage
        optimizer="AdamW",                    # Algorithme d’optimisation pour améliorer la convergence
        mosaic=0.8,                           # Mélange d’images pour améliorer l'entrainement (Image inversée ou tournée)
        scale=0.5,                            # Zoom aléatoire sur les images
        fliplr=0.5,                           # Flip horizontal aléatoire (sur 50% des images)
    )
