import os
import time
import json                      
from datetime import datetime     
from google.genai import types     
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
    try:
        with open("master_profil.txt", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return "File master_profil.txt tidak ditemukan."

def get_tanggal_indonesia():
    bulan = [
        "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]
    sekarang = datetime.now()
    return f"{sekarang.day} {bulan[sekarang.month]} {sekarang.year}"

@app.route("/", methods=["GET", "POST"])
def index():
    hasil = None
    error_msg = None
    loker_input = ""

    if request.method == "POST":
        loker_input = request.form.get("loker", "").strip()
        if loker_input:
            master_profil = baca_master_profil()
            tanggal_hari_ini = get_tanggal_indonesia()

            prompt = f"""
            Kamu adalah asisten rekrutmen dan penulis karier profesional.
            Tugasmu adalah menyesuaikan lamaran kerja berdasarkan MASTER PROFIL pelamar dan LOWONGAN KERJA berikut.

            ATURAN KETAT:
            1. Gunakan HANYA fakta yang ada di MASTER PROFIL. JANGAN mengarang skill, pengalaman, atau gelar yang tidak tertulis.
            2. Gunakan tanggal surat: Kebumen, {tanggal_hari_ini}
            3. Kembalikan respons HANYA dalam format JSON yang valid dengan struktur persis seperti berikut:
            {{
                "posisi": "Nama posisi yang dilamar",
                "perusahaan": "Nama perusahaan tujuan",
                "skor_kecocokan": "Persentase kecocokan (contoh: 85%)",
                "analisis_kecocokan": [
                    "Poin analisis 1",
                    "Poin analisis 2",
                    "Poin analisis 3"
                ],
                "surat_lamaran": "Teks lengkap surat lamaran kerja formal dalam bahasa Indonesia (gunakan \\n untuk baris baru, tanpa format markdown ** atau #)",
                "poin_cv": [
                    "Poin pengalaman/skill 1 yang relevan untuk ditonjolkan di CV",
                    "Poin pengalaman/skill 2 yang relevan untuk ditonjolkan di CV",
                    "Poin pengalaman/skill 3 yang relevan untuk ditonjolkan di CV"
                ]
            }}

            MASTER PROFIL:
            {master_profil}

            LOWONGAN KERJA:
            {loker_input}
            """

            daftar_model = [
                "gemini-3.8-flash",
                "gemini-3.7-flash",
                "gemini-3.6-flash",
                "gemini-3.5-flash-lite",
                "gemini-2.5-flash",
                "gemini-2.5-flash-lite"
            ]

            for indeks, model_name in enumerate(daftar_model):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json"
                        )
                    )
                    # Parse string JSON dari AI menjadi dictionary Python
                    hasil = json.loads(response.text)
                    error_msg = None
                    break
                except Exception as e:
                    error_msg = f"Gagal memproses dengan {model_name}: {str(e)}"
                    # Beri jeda 2 detik sebelum mencoba model berikutnya jika masih ada antrean
                    if indeks < len(daftar_model) - 1:
                        time.sleep(2)
                    continue

    return render_template("index.html", hasil=hasil, error_msg=error_msg, loker_input=loker_input)

if __name__ == "__main__":
    app.run(debug=True)