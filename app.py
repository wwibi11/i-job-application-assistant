import os
import time
import json
import io
from datetime import datetime
from flask import Flask, render_template, request, send_file
from docx import Document
from docx.shared import Pt, Cm
from fpdf import FPDF
from dotenv import load_dotenv
from google import genai
from google.genai import types
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
            3. Ekstrak sumber informasi loker (misal: Instagram, LinkedIn, JobStreet, atau "Tidak disebutkan di teks") serta alamat email/link tujuan pengiriman lamaran dari teks LOWONGAN KERJA.
            4. Kembalikan respons HANYA dalam format JSON yang valid dengan struktur persis seperti berikut:
            {{
                "posisi": "Nama posisi yang dilamar",
                "perusahaan": "Nama perusahaan tujuan",
                "sumber_info": "Sumber informasi lowongan (contoh: LinkedIn / Instagram / Tidak disebutkan)",
                "kontak_pengiriman": "Email HRD, link pendaftaran, atau subjek email yang diminta",
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


@app.route("/download/<format_file>", methods=["POST"])
def download_dokumen(format_file):
    surat_teks = request.form.get("surat_teks", "").strip()
    posisi = request.form.get("posisi", "Lamaran_Kerja").strip().replace(" ", "_")
    perusahaan = request.form.get("perusahaan", "Perusahaan").strip().replace(" ", "_")
    nama_file_dasar = f"Surat_Lamaran_{posisi}_{perusahaan}"

    if not surat_teks:
        return "Teks surat kosong.", 400

    # --- OPSI 1: GENERATE WORD (.DOCX) ---
    if format_file == "docx":
        doc = Document()

        # Atur Ukuran Kertas F4 (21.5 cm x 33.0 cm) & Margin Standar Surat Resmi
        section = doc.sections[0]
        section.page_width = Cm(21.5)
        section.page_height = Cm(33.0)
        section.top_margin = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.0)

        # Atur Font Default: Times New Roman 12pt
        style = doc.styles["Normal"]
        style.font.name = "Times New Roman"
        style.font.size = Pt(12)

        # Masukkan tiap baris surat dengan spasi 1.15 yang proporsional
        for baris in surat_teks.split("\n"):
            p = doc.add_paragraph(baris)
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(4)

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{nama_file_dasar}.docx",
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    # --- OPSI 2: GENERATE PDF (.PDF) ---
    elif format_file == "pdf":
        # Ukuran F4 dalam milimeter: 215 mm x 330 mm
        pdf = FPDF(orientation="P", unit="mm", format=(215, 330))
        pdf.set_margins(left=25, top=20, right=20)
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        # FPDF built-in 'Times' adalah Times New Roman standar PDF
        pdf.set_font("Times", size=12)

        # Bersihkan karakter Unicode khusus (seperti tanda kutip lengkung / em-dash) agar aman di font standar PDF
        teks_bersih = (
            surat_teks
            .replace("\u2013", "-")
            .replace("\u2014", "-")
            .replace("\u2018", "'")
            .replace("\u2019", "'")
            .replace("\u201c", '"')
            .replace("\u201d", '"')
            .replace("\u2022", "-")
        )

        # Tulis tiap baris dengan tinggi baris 6 mm (setara spasi 1.15 untuk font 12pt)
        for baris in teks_bersih.split("\n"):
            if baris.strip() == "":
                pdf.ln(4)  # Jarak antar paragraf
            else:
                pdf.multi_cell(w=0, h=6, text=baris)

        pdf_bytes = bytes(pdf.output())
        buffer = io.BytesIO(pdf_bytes)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{nama_file_dasar}.pdf",
            mimetype="application/pdf"
        )

    return "Format tidak didukung.", 400

if __name__ == "__main__":
    app.run(debug=True)