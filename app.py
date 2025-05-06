import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import tempfile
import json
import srt
from datetime import timedelta
from extract_srt_quotes import extract_text_from_srt, extract_quotes, export_quotes_to_file, generate_ffmpeg_cut_file, export_json_data

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_for_testing')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB max upload

# Créer les dossiers s'ils n'existent pas
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'srt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('Aucun fichier sélectionné')
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        flash('Aucun fichier sélectionné')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Récupérer les paramètres du formulaire
        min_length = int(request.form.get('min_length', 120))
        num_quotes = int(request.form.get('num_quotes', 10))
        keywords = request.form.get('keywords', '').split(',') if request.form.get('keywords') else None
        use_sentiment = 'sentiment' in request.form
        topic_detection = 'topic_detection' in request.form
        generate_ffmpeg = 'ffmpeg' in request.form
        padding = int(request.form.get('padding', 1))
        export_json = 'json' in request.form
        
        # Nouveaux paramètres pour le regroupement des sous-titres
        group_subtitles = 'group_subtitles' in request.form
        max_gap = float(request.form.get('max_gap', 3.0))
        
        # Nouveau paramètre pour l'incrustation des sous-titres
        add_subtitles = 'add_subtitles' in request.form
        
        # Traiter le fichier SRT
        try:
            _, subtitles = extract_text_from_srt(filepath)
            quotes = extract_quotes(subtitles, min_length=min_length, keywords=keywords, 
                                   use_sentiment=use_sentiment, topic_detection=topic_detection,
                                   group_subtitles=group_subtitles, max_gap_seconds=max_gap)
            
            # Trier les citations par importance et limiter au nombre demandé
            quotes = sorted(quotes, key=lambda q: (
                q.get('is_intense', False) * 3 +
                q.get('has_keyword', False) * 2 +
                q.get('is_topic_change', False) * 2 +
                q.get('is_long', False)
            ), reverse=True)[:num_quotes]
            
            # Trier par ordre chronologique
            quotes = sorted(quotes, key=lambda q: q['start_time'])
            
            # Générer les fichiers de sortie
            base_output = os.path.join(app.config['OUTPUT_FOLDER'], os.path.splitext(filename)[0])
            
            # Fichier texte principal
            text_output = f"{base_output}_quotes.txt"
            export_quotes_to_file(quotes, text_output)
            
            # Fichier FFmpeg si demandé
            ffmpeg_script = None
            if generate_ffmpeg:
                ffmpeg_output = f"{base_output}_ffmpeg.txt"
                ffmpeg_script = generate_ffmpeg_cut_file(quotes, ffmpeg_output, padding, add_subtitles)
            
            # Fichier JSON si demandé
            json_output = None
            if export_json:
                json_output = f"{base_output}_quotes.json"
                export_json_data(quotes, json_output)
            
            # Rediriger vers la page de résultats
            return redirect(url_for('results', filename=os.path.splitext(filename)[0]))
            
        except Exception as e:
            flash(f"Erreur lors du traitement du fichier: {str(e)}")
            return redirect(url_for('index'))
    
    flash('Type de fichier non autorisé. Veuillez télécharger un fichier SRT.')
    return redirect(url_for('index'))

@app.route('/results/<filename>')
def results(filename):
    base_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    
    # Vérifier quels fichiers ont été générés
    text_file = f"{base_path}_quotes.txt"
    ffmpeg_file = f"{base_path}_ffmpeg.txt"
    ffmpeg_script = f"{base_path}_ffmpeg.sh"
    json_file = f"{base_path}_quotes.json"
    
    files = {
        'text': os.path.exists(text_file),
        'ffmpeg': os.path.exists(ffmpeg_file),
        'ffmpeg_script': os.path.exists(ffmpeg_script),
        'json': os.path.exists(json_file)
    }
    
    # Lire le contenu du fichier texte pour l'afficher
    quotes_content = None
    if files['text']:
        with open(text_file, 'r', encoding='utf-8') as f:
            quotes_content = f.read()
    
    # Charger les données JSON si disponibles pour l'édition
    quotes_data = None
    if files['json']:
        with open(json_file, 'r', encoding='utf-8') as f:
            quotes_data = json.load(f)
    
    return render_template('results.html', filename=filename, files=files, quotes_content=quotes_content, quotes_data=quotes_data)

@app.route('/download/<filetype>/<filename>')
def download(filetype, filename):
    base_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    
    if filetype == 'text':
        return send_from_directory(app.config['OUTPUT_FOLDER'], f"{filename}_quotes.txt", as_attachment=True)
    elif filetype == 'ffmpeg':
        return send_from_directory(app.config['OUTPUT_FOLDER'], f"{filename}_ffmpeg.txt", as_attachment=True)
    elif filetype == 'ffmpeg_script':
        return send_from_directory(app.config['OUTPUT_FOLDER'], f"{filename}_ffmpeg.sh", as_attachment=True)
    elif filetype == 'json':
        return send_from_directory(app.config['OUTPUT_FOLDER'], f"{filename}_quotes.json", as_attachment=True)
    elif filetype == 'srt':
        return send_from_directory(app.config['OUTPUT_FOLDER'], f"{filename}_edited.srt", as_attachment=True)
    
    return redirect(url_for('index'))

@app.route('/edit/<filename>', methods=['GET'])
def edit_quotes(filename):
    json_file = os.path.join(app.config['OUTPUT_FOLDER'], f"{filename}_quotes.json")
    
    if not os.path.exists(json_file):
        flash("Fichier de citations non trouvé.")
        return redirect(url_for('index'))
    
    with open(json_file, 'r', encoding='utf-8') as f:
        quotes_data = json.load(f)
    
    return render_template('edit.html', filename=filename, quotes=quotes_data)

@app.route('/save_edits/<filename>', methods=['POST'])
def save_edits(filename):
    try:
        # Récupérer les données éditées
        edited_quotes = request.json
        
        # Sauvegarder les modifications dans le fichier JSON
        json_file = os.path.join(app.config['OUTPUT_FOLDER'], f"{filename}_quotes.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(edited_quotes, f, ensure_ascii=False, indent=2)
        
        # Mettre à jour le fichier texte
        text_file = os.path.join(app.config['OUTPUT_FOLDER'], f"{filename}_quotes.txt")
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write("# MOMENTS FORTS DU PODCAST (ÉDITÉS)\n\n")
            
            for i, quote in enumerate(edited_quotes, 1):
                f.write(f"## Moment fort {i}\n")
                f.write(f"- **Timecode**: {quote['formatted_start']} - {quote['formatted_end']}\n")
                f.write(f"- **Durée**: {int(quote['duration_seconds'])} secondes\n")
                f.write(f"- **Contenu**: {quote['content']}\n\n")
        
        # Générer un fichier SRT édité
        srt_file = os.path.join(app.config['OUTPUT_FOLDER'], f"{filename}_edited.srt")
        subtitles = []
        
        for i, quote in enumerate(edited_quotes, 1):
            start_time = timedelta(seconds=quote['start_time_seconds'])
            end_time = timedelta(seconds=quote['end_time_seconds'])
            
            subtitle = srt.Subtitle(
                index=i,
                start=start_time,
                end=end_time,
                content=quote['content']
            )
            subtitles.append(subtitle)
        
        with open(srt_file, 'w', encoding='utf-8') as f:
            f.write(srt.compose(subtitles))
        
        # Mettre à jour le script FFmpeg si nécessaire
        ffmpeg_file = os.path.join(app.config['OUTPUT_FOLDER'], f"{filename}_ffmpeg.txt")
        if os.path.exists(ffmpeg_file):
            # Convertir les données JSON en format compatible avec generate_ffmpeg_cut_file
            quotes_for_ffmpeg = []
            for quote in edited_quotes:
                start_time = timedelta(seconds=quote['start_time_seconds'])
                end_time = timedelta(seconds=quote['end_time_seconds'])
                
                quote_data = {
                    'content': quote['content'],
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': end_time - start_time,
                    'formatted_start': quote['formatted_start'],
                    'formatted_end': quote['formatted_end'],
                }
                quotes_for_ffmpeg.append(quote_data)
            
            # Générer un nouveau script FFmpeg
            generate_ffmpeg_cut_file(quotes_for_ffmpeg, ffmpeg_file, 1, True)
        
        return jsonify({'success': True, 'message': 'Modifications enregistrées avec succès.'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True) 