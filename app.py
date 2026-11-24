import os
import time
from flask import Flask, render_template, request
from dotenv import load_dotenv
from google import genai
from google.genai.errors import ServerError

# 1. Muat API Key dari file .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY tidak ditemukan di file .env!")

# 2. Inisialisasi Client Gemini SDK Baru (tanpa genai.configure)
client = genai.Client(api_key=api_key)

app = Flask(__name__)

def baca_master_profil():
    with open("master_profil.txt", "r", encoding="utf-8") as file:
        return file.read()

@app.route("/", methods=["GET", "POST"])
def index():
    hasil_ai = None
    if request.method == "POST":
        info_loker = request.form.get("info_loker")
        master_profil = baca_master_profil()

        prompt = f"""
        Kamu adalah asisten karier profesional. Tugasmu adalah mencocokkan profil kandidat dengan informasi lowongan kerja di bawah ini, lalu membuatkan draf surat lamaran kerja (Cover Letter) dan poin-poin ringkasan CV yang relevan.

        ATURAN KETAT:
        - Hanya gunakan fakta, pengalaman, dan keahlian yang tertulis di MASTER PROFIL.
        - DILARANG mengarang atau melebih-lebihkan skill yang tidak ada di master profil.
        - Gunakan bahasa Indonesia yang profesional, sopan, dan langsung ke inti (tidak bertele-tele).

        MASTER PROFIL KANDIDAT:
        {master_profil}

        INFORMASI LOWONGAN KERJA:
        {info_loker}

        FORMAT OUTPUT:
        1. Analisis Kecocokan Singkat (2-3 poin)
        2. Draf Surat Lamaran Kerja (Siap kirim)
        3. Poin Pengalaman & Skill yang Harus Ditonjolkan di CV
        """

        daftar_model = [
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gemini-3.5-flash-lite",
            "gemini-flash-lite-latest"
        ]
        
        for nama_model in daftar_model:
            try:
                response = client.models.generate_content(
                    model=nama_model,
                    contents=prompt
                )
                hasil_ai = response.text
                break  # Berhenti jika sudah berhasil
            except ServerError as e:
                if e.code == 503:
                    time.sleep(2)  # Tunggu 2 detik sebelum mencoba model berikutnya
                    continue
                else:
                    hasil_ai = f"Terjadi gangguan server Google: {e}"
                    break
            except Exception as e:
                hasil_ai = f"Terjadi kesalahan: {e}"
                break
        else:
            hasil_ai = "Server AI sedang sangat sibuk di semua model. Silakan coba klik tombol proses beberapa saat lagi."

    return render_template("index.html", hasil_ai=hasil_ai)

if __name__ == "__main__":
    app.run(debug=True)