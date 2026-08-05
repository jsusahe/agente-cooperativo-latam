# audio_generator.py
import os
import subprocess
import json

def generate_audio(summary_text, output_filename="resumen_cooperativo.mp3"):
    """Genera un archivo de audio a partir de un texto usando Edge TTS."""
    if not summary_text:
        print("No hay texto para generar audio.")
        return None

    command = [
        "edge-tts",
        "--text", summary_text[:5000],  # Limitar longitud
        "--voice", "es-CO-SalomeNeural",
        "--write-media", output_filename
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Audio generado exitosamente: {output_filename}")
        return output_filename
    except FileNotFoundError:
        print("Error: 'edge-tts' no está instalado. Instálalo con 'pip install edge-tts'")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error al generar el audio: {e.stderr}")
        return None

if __name__ == '__main__':
    test_text = "Este es un resumen de prueba del sector cooperativo latinoamericano."
    generate_audio(test_text, "test_cooperativo.mp3")