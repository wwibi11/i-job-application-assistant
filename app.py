from flask import Flask, render_template, request, jsonify
import os

app = Flask(__name__)
# Pastikan folder uploads ada untuk menyimpan file sementara
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    # Menampilkan halaman form upload
    return '''
    <!doctype html>
    <title>Sistem Pelamar Kerja AI</title>
    <h1>Upload Info Loker</h1>
    <form action="/proses" method=post enctype=multipart/form-data>
      <p><textarea name="loker_text" rows="10" cols="50" placeholder="Tempel teks lowongan kerja di sini..."></textarea></p>
      <p>Atau unggah gambar poster loker: <input type=file name=file></p>
      <p><input type=submit value=Proses></p>
    </form>
    '''

@app.route('/proses', methods=['POST'])
def proses_loker():
    # Logika untuk menangkap input
    loker_text = request.form.get('loker_text')
    file = request.files.get('file')
    
    file_path = None
    if file and file.filename != '':
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
    
    if not loker_text and not file_path:
        return "Harap masukkan teks loker atau unggah gambar.", 400

    # Di sini nantinya Anda akan memanggil fungsi AI
    # Contoh pemanggilan dummy:
    # hasil_ai = proses_dengan_gemini(loker_text, file_path)
    
    return jsonify({
        "status": "Berhasil menerima data",
        "teks_diterima": bool(loker_text),
        "file_diterima": file_path
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)