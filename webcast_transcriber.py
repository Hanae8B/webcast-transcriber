import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import queue
from datetime import datetime

import numpy as np
import soundcard as sc
from faster_whisper import WhisperModel


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = "base.en"
# Pour plus de précision :
# MODEL_NAME = "small.en"

SAMPLE_RATE = 16000

# Durée des morceaux envoyés à Whisper
CHUNK_SECONDS = 4

LANGUAGE = "en"

# Nombre maximum de morceaux audio en attente
AUDIO_QUEUE_SIZE = 3


# ============================================================
# VARIABLES GLOBALES
# ============================================================

audio_queue = queue.Queue(maxsize=AUDIO_QUEUE_SIZE)

stop_event = threading.Event()

running = False

capture_thread = None
worker_thread = None


# ============================================================
# AUDIO WINDOWS
# ============================================================

def choose_output_device():
    """
    Retourne le périphérique audio Windows par défaut.
    """

    speaker = sc.default_speaker()

    if speaker is None:
        raise RuntimeError(
            "Aucun périphérique audio Windows par défaut n'a été trouvé."
        )

    return speaker


def get_loopback_device():
    """
    Retourne le périphérique WASAPI loopback correspondant
    au périphérique de sortie Windows par défaut.
    """

    speaker = choose_output_device()

    print()
    print("========================================")
    print("SORTIE AUDIO WINDOWS")
    print("========================================")
    print("Nom :", speaker.name)
    print("ID  :", speaker.id)
    print()

    # IMPORTANT :
    # On utilise le nom du haut-parleur et non son ID.
    loopback = sc.get_microphone(
        id=speaker.name,
        include_loopback=True
    )

    print("========================================")
    print("LOOPBACK")
    print("========================================")
    print(loopback)
    print()

    return loopback


# ============================================================
# CAPTURE AUDIO
# ============================================================

def capture_audio():
    """
    Capture le son sortant de Windows via WASAPI loopback.

    Le son est :
        Windows -> loopback -> numpy -> queue -> Whisper
    """

    global running

    try:

        loopback = get_loopback_device()

        root.after(
            0,
            lambda: status_var.set(
                "Capture du son Windows..."
            )
        )

        # On capture en stéréo.
        with loopback.recorder(
            samplerate=SAMPLE_RATE,
            channels=2,
            blocksize=1024
        ) as recorder:

            buffer = []

            required_samples = SAMPLE_RATE * CHUNK_SECONDS

            while not stop_event.is_set():

                # Lire un petit bloc audio.
                data = recorder.record(
                    numframes=1024
                )

                if data is None:
                    continue

                data = np.asarray(
                    data,
                    dtype=np.float32
                )

                if data.size == 0:
                    continue

                # ------------------------------------------------
                # STÉRÉO -> MONO
                # ------------------------------------------------

                if data.ndim == 2:

                    # Moyenne des canaux gauche/droit.
                    data = np.mean(
                        data,
                        axis=1
                    )

                else:

                    data = data.reshape(-1)

                buffer.append(data)

                total_samples = sum(
                    len(x)
                    for x in buffer
                )

                # ------------------------------------------------
                # Lorsqu'on possède suffisamment de son
                # ------------------------------------------------

                if total_samples >= required_samples:

                    combined = np.concatenate(buffer)

                    # Bloc destiné à Whisper.
                    audio = combined[
                        :required_samples
                    ]

                    # Ce qui reste est conservé pour le bloc suivant.
                    remaining = combined[
                        required_samples:
                    ]

                    buffer = []

                    if len(remaining) > 0:
                        buffer.append(remaining)

                    # ------------------------------------------------
                    # Vérification du niveau audio
                    # ------------------------------------------------

                    rms = float(
                        np.sqrt(
                            np.mean(
                                audio ** 2
                            )
                        )
                    )

                    peak = float(
                        np.max(
                            np.abs(audio)
                        )
                    )

                    print(
                        f"Audio : RMS={rms:.6f} "
                        f"Peak={peak:.6f}"
                    )

                    # Si le son est totalement silencieux,
                    # inutile d'envoyer le bloc à Whisper.
                    if peak < 0.00001:

                        root.after(
                            0,
                            lambda: status_var.set(
                                "Aucun son Windows détecté..."
                            )
                        )

                        continue

                    # ------------------------------------------------
                    # Envoyer le bloc à Whisper
                    # ------------------------------------------------

                    try:

                        audio_queue.put(
                            audio,
                            timeout=0.2
                        )

                    except queue.Full:

                        # Whisper est momentanément occupé.
                        # On abandonne ce bloc plutôt que de bloquer
                        # la capture Windows.
                        print(
                            "Queue audio pleine : bloc ignoré."
                        )

    except Exception as e:

        error_message = str(e)

        print()
        print("ERREUR CAPTURE AUDIO :")
        print(error_message)

        root.after(
            0,
            lambda msg=error_message:
            show_error(
                "Erreur de capture audio",
                msg
            )
        )

        root.after(
            0,
            stop_transcription
        )


# ============================================================
# WHISPER
# ============================================================

def transcribe_audio():
    """
    Charge Whisper et transcrit les morceaux audio.
    """

    global running

    try:

        # --------------------------------------------------------
        # Chargement du modèle
        # --------------------------------------------------------

        root.after(
            0,
            lambda: status_var.set(
                f"Chargement de Whisper ({MODEL_NAME})..."
            )
        )

        print(
            f"Chargement du modèle {MODEL_NAME}..."
        )

        model = WhisperModel(
            MODEL_NAME,
            device="cpu",
            compute_type="int8"
        )

        print("Whisper chargé.")

        root.after(
            0,
            lambda: status_var.set(
                "Écoute du son Windows..."
            )
        )

        # --------------------------------------------------------
        # Boucle de transcription
        # --------------------------------------------------------

        while not stop_event.is_set():

            try:

                audio = audio_queue.get(
                    timeout=0.2
                )

            except queue.Empty:

                continue

            if stop_event.is_set():
                break

            root.after(
                0,
                lambda: status_var.set(
                    "Transcription en cours..."
                )
            )

            # ----------------------------------------------------
            # Whisper
            # ----------------------------------------------------

            segments, info = model.transcribe(

                audio,

                language=LANGUAGE,

                beam_size=1,

                vad_filter=True,

                condition_on_previous_text=False

            )

            # ----------------------------------------------------
            # Récupération du texte
            # ----------------------------------------------------

            text = " ".join(

                segment.text.strip()

                for segment in segments

                if segment.text.strip()

            ).strip()

            if text:

                add_transcription(
                    text
                )

            root.after(
                0,
                lambda: status_var.set(
                    "Écoute du son Windows..."
                )
            )

    except Exception as e:

        error_message = str(e)

        print()
        print("ERREUR WHISPER :")
        print(error_message)

        root.after(
            0,
            lambda msg=error_message:
            show_error(
                "Erreur Whisper",
                msg
            )
        )

        root.after(
            0,
            stop_transcription
        )


# ============================================================
# AFFICHAGE TRANSCRIPTION
# ============================================================

def add_transcription(text):
    """
    Ajoute le texte dans la fenêtre et dans le fichier.
    """

    timestamp = datetime.now().strftime(
        "%H:%M:%S"
    )

    line = (
        f"[{timestamp}] "
        f"{text}\n"
    )

    def update_interface():

        text_box.insert(
            tk.END,
            line
        )

        text_box.see(
            tk.END
        )

        # Sauvegarde immédiate.
        try:

            filename = current_file.get()

            if filename:

                with open(
                    filename,
                    "a",
                    encoding="utf-8"
                ) as f:

                    f.write(line)

        except Exception as e:

            print(
                "Erreur sauvegarde :",
                e
            )

    root.after(
        0,
        update_interface
    )


# ============================================================
# DÉMARRER
# ============================================================

def start_transcription():

    global running
    global worker_thread
    global capture_thread

    if running:
        return

    # --------------------------------------------------------
    # Vérifier le périphérique audio
    # --------------------------------------------------------

    try:

        speaker = choose_output_device()

        print(
            "Périphérique Windows :",
            speaker.name
        )

    except Exception as e:

        show_error(
            "Audio Windows introuvable",
            str(e)
        )

        return

    # --------------------------------------------------------
    # Choisir le fichier
    # --------------------------------------------------------

    filename = filedialog.asksaveasfilename(

        title="Enregistrer la transcription",

        defaultextension=".txt",

        filetypes=[
            (
                "Fichier texte",
                "*.txt"
            )
        ]

    )

    if not filename:
        return

    current_file.set(
        filename
    )

    # --------------------------------------------------------
    # Vider l'ancienne queue
    # --------------------------------------------------------

    while not audio_queue.empty():

        try:

            audio_queue.get_nowait()

        except queue.Empty:

            break

    # --------------------------------------------------------
    # Réinitialisation
    # --------------------------------------------------------

    stop_event.clear()

    running = True

    # --------------------------------------------------------
    # Interface
    # --------------------------------------------------------

    start_button.config(
        state="disabled"
    )

    stop_button.config(
        state="normal"
    )

    clear_button.config(
        state="disabled"
    )

    status_var.set(
        "Démarrage..."
    )

    # --------------------------------------------------------
    # Création du fichier
    # --------------------------------------------------------

    try:

        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                "TRANSCRIPTION DU WEBCAST\n"
            )

            f.write(
                f"Début : "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )

            f.write(
                "=" * 70
                + "\n\n"
            )

    except Exception as e:

        running = False

        start_button.config(
            state="normal"
        )

        stop_button.config(
            state="disabled"
        )

        clear_button.config(
            state="normal"
        )

        show_error(
            "Erreur fichier",
            str(e)
        )

        return

    # --------------------------------------------------------
    # Threads
    # --------------------------------------------------------

    capture_thread = threading.Thread(
        target=capture_audio,
        daemon=True,
        name="AudioCapture"
    )

    worker_thread = threading.Thread(
        target=transcribe_audio,
        daemon=True,
        name="WhisperWorker"
    )

    capture_thread.start()

    worker_thread.start()


# ============================================================
# ARRÊTER
# ============================================================

def stop_transcription():

    global running

    if not running:
        return

    stop_event.set()

    running = False

    start_button.config(
        state="normal"
    )

    stop_button.config(
        state="disabled"
    )

    clear_button.config(
        state="normal"
    )

    status_var.set(
        "Arrêté"
    )


# ============================================================
# EFFACER
# ============================================================

def clear_text():

    if running:
        return

    text_box.delete(
        "1.0",
        tk.END
    )


# ============================================================
# ERREUR
# ============================================================

def show_error(
    title,
    message
):

    messagebox.showerror(
        title,
        message
    )


# ============================================================
# FERMETURE
# ============================================================

def on_close():

    stop_event.set()

    root.destroy()


# ============================================================
# INTERFACE TKINTER
# ============================================================

root = tk.Tk()

root.title(
    "Webcast → Texte (anglais)"
)

root.geometry(
    "900x600"
)

root.minsize(
    650,
    400
)


# ------------------------------------------------------------
# Variables Tkinter
# ------------------------------------------------------------

current_file = tk.StringVar(
    value=""
)

status_var = tk.StringVar(
    value="Prêt"
)


# ------------------------------------------------------------
# TITRE
# ------------------------------------------------------------

title = ttk.Label(

    root,

    text="🎙️ Transcription du webcast",

    font=(
        "Segoe UI",
        18,
        "bold"
    )

)

title.pack(
    padx=15,
    pady=(15, 5),
    anchor="w"
)


# ------------------------------------------------------------
# DESCRIPTION
# ------------------------------------------------------------

info = ttk.Label(

    root,

    text=(
        "Le programme capture le son sortant de Windows "
        "et transcrit l'anglais localement avec Whisper."
    ),

    wraplength=850

)

info.pack(
    padx=15,
    pady=(0, 12),
    anchor="w"
)


# ------------------------------------------------------------
# ZONE TEXTE
# ------------------------------------------------------------

frame = ttk.Frame(
    root
)

frame.pack(
    fill="both",
    expand=True,
    padx=15,
    pady=5
)


scrollbar = ttk.Scrollbar(
    frame
)

scrollbar.pack(
    side="right",
    fill="y"
)


text_box = tk.Text(

    frame,

    wrap="word",

    font=(
        "Consolas",
        11
    ),

    yscrollcommand=scrollbar.set

)

text_box.pack(
    side="left",
    fill="both",
    expand=True
)


scrollbar.config(
    command=text_box.yview
)


# ------------------------------------------------------------
# BARRE DU BAS
# ------------------------------------------------------------

bottom = ttk.Frame(
    root
)

bottom.pack(
    fill="x",
    padx=15,
    pady=12
)


# ------------------------------------------------------------
# BOUTON DÉMARRER
# ------------------------------------------------------------

start_button = ttk.Button(

    bottom,

    text="▶ Démarrer",

    command=start_transcription

)

start_button.pack(
    side="left",
    padx=(0, 8)
)


# ------------------------------------------------------------
# BOUTON ARRÊTER
# ------------------------------------------------------------

stop_button = ttk.Button(

    bottom,

    text="■ Arrêter",

    command=stop_transcription,

    state="disabled"

)

stop_button.pack(
    side="left",
    padx=8
)


# ------------------------------------------------------------
# BOUTON EFFACER
# ------------------------------------------------------------

clear_button = ttk.Button(

    bottom,

    text="Effacer",

    command=clear_text

)

clear_button.pack(
    side="left",
    padx=8
)


# ------------------------------------------------------------
# STATUT
# ------------------------------------------------------------

status_label = ttk.Label(

    bottom,

    textvariable=status_var

)

status_label.pack(
    side="right"
)


# ------------------------------------------------------------
# FERMETURE
# ------------------------------------------------------------

root.protocol(
    "WM_DELETE_WINDOW",
    on_close
)


# ============================================================
# DÉMARRAGE
# ============================================================

root.mainloop()