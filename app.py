import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import tempfile
import json
import srt
from datetime import timedelta
import subprocess
import shutil
import base64
from extract_srt_quotes import extract_text_from_srt, extract_quotes, export_quotes_to_file, generate_ffmpeg_cut_file, export_json_data
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_for_testing')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs')
app.config['MAX_CONTENT_LENGTH'] = 2000 * 1024 * 1024  # 2 GB max upload (augmenté de 100 MB)
app.config['VIDEO_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'videos')

# Créer les dossiers s'ils n'existent pas
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
os.makedirs(app.config['VIDEO_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'srt'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'mov', 'avi', 'mkv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

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
    
    # Vérifier si des extraits vidéo ont été générés
    clips_folder = os.path.join(app.config['OUTPUT_FOLDER'], f"{filename}_clips")
    clips = []
    if os.path.exists(clips_folder):
        for file in os.listdir(clips_folder):
            if file.endswith('.mp4'):
                clip_path = os.path.join(f"{filename}_clips", file)
                clip_url = url_for('download_clip', clip_path=clip_path)
                clips.append({
                    'name': file,
                    'url': clip_url
                })
        # Trier les clips par nom pour les afficher dans l'ordre
        clips.sort(key=lambda x: x['name'])
    
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
    
    return render_template('results.html', filename=filename, files=files, 
                          quotes_content=quotes_content, quotes_data=quotes_data,
                          clips=clips)

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

@app.route('/edit_video/<filename>', methods=['GET'])
def edit_video(filename):
    json_file = os.path.join(app.config['OUTPUT_FOLDER'], f"{filename}_quotes.json")
    
    if not os.path.exists(json_file):
        flash("Fichier de citations non trouvé.")
        return redirect(url_for('index'))
    
    with open(json_file, 'r', encoding='utf-8') as f:
        quotes_data = json.load(f)
    
    # Nettoyer les données pour éviter les problèmes de JSON
    for quote in quotes_data:
        if 'content' in quote:
            # Échapper les caractères spéciaux qui pourraient causer des problèmes
            quote['content'] = quote['content'].replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').replace('\r', '')
    
    # Encoder les données en base64 pour éviter les problèmes de parsing
    quotes_json = json.dumps(quotes_data)
    quotes_base64 = base64.b64encode(quotes_json.encode('utf-8')).decode('utf-8')
    
    # Vérifier si des options de sous-titres sont déjà enregistrées
    subtitle_options_file = os.path.join(app.config['OUTPUT_FOLDER'], f"{filename}_subtitle_options.json")
    subtitle_options = {
        "font": "Arial",
        "size": "24",
        "color": "0xffffff",
        "backgroundColor": "0x000000",
        "opacity": "0.5"
    }
    
    if os.path.exists(subtitle_options_file):
        with open(subtitle_options_file, 'r', encoding='utf-8') as f:
            subtitle_options = json.load(f)
    
    # Encoder les options en base64
    options_json = json.dumps(subtitle_options)
    options_base64 = base64.b64encode(options_json.encode('utf-8')).decode('utf-8')
    
    return render_template('video_editor.html', filename=filename, 
                           quotes_base64=quotes_base64, 
                           options_base64=options_base64)

@app.route('/save_video_edits/<filename>', methods=['POST'])
def save_video_edits(filename):
    try:
        # Récupérer les données éditées
        data = request.json
        edited_quotes = data.get('quotes', [])
        subtitle_options = data.get('subtitleOptions', {})
        
        # Sauvegarder les modifications dans le fichier JSON
        json_file = os.path.join(app.config['OUTPUT_FOLDER'], f"{filename}_quotes.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(edited_quotes, f, ensure_ascii=False, indent=2)
        
        # Sauvegarder les options de sous-titres
        subtitle_options_file = os.path.join(app.config['OUTPUT_FOLDER'], f"{filename}_subtitle_options.json")
        with open(subtitle_options_file, 'w', encoding='utf-8') as f:
            json.dump(subtitle_options, f, ensure_ascii=False, indent=2)
        
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
        
        # Mettre à jour le script FFmpeg avec les nouvelles options de sous-titres
        ffmpeg_file = os.path.join(app.config['OUTPUT_FOLDER'], f"{filename}_ffmpeg.txt")
        ffmpeg_script = os.path.join(app.config['OUTPUT_FOLDER'], f"{filename}_ffmpeg.sh")
        
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
            
            # Générer un nouveau script FFmpeg avec les options de sous-titres
            generate_enhanced_ffmpeg_script(quotes_for_ffmpeg, ffmpeg_script, subtitle_options, 1)
        
        return jsonify({'success': True, 'message': 'Modifications enregistrées avec succès.'})
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())  # Afficher l'erreur complète dans la console
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})

@app.route('/upload_video/<filename>', methods=['POST'])
def upload_video(filename):
    if 'video' not in request.files:
        print("Erreur: Aucun fichier vidéo dans la requête")
        return jsonify({'success': False, 'message': 'Aucun fichier vidéo sélectionné'})
    
    file = request.files['video']
    
    if file.filename == '':
        print("Erreur: Nom de fichier vidéo vide")
        return jsonify({'success': False, 'message': 'Aucun fichier vidéo sélectionné'})
    
    # S'assurer que le dossier videos existe
    os.makedirs(app.config['VIDEO_FOLDER'], exist_ok=True)
    
    if file and allowed_video_file(file.filename):
        video_filename = secure_filename(f"{filename}_video.mp4")
        filepath = os.path.join(app.config['VIDEO_FOLDER'], video_filename)
        
        try:
            file.save(filepath)
            print(f"Vidéo téléchargée avec succès: {filepath}")
            
            # Copier le fichier SRT correspondant s'il existe dans uploads/
            srt_filename = f"{filename}.srt"
            upload_srt_path = os.path.join(app.config['UPLOAD_FOLDER'], srt_filename)
            video_srt_path = os.path.join(app.config['VIDEO_FOLDER'], f"{filename}_video.srt")
            
            if os.path.exists(upload_srt_path):
                print(f"Copie du fichier SRT depuis {upload_srt_path} vers {video_srt_path}")
                shutil.copy2(upload_srt_path, video_srt_path)
                print(f"Fichier SRT copié avec succès")
            else:
                print(f"Aucun fichier SRT trouvé à {upload_srt_path}")
            
            return jsonify({
                'success': True, 
                'message': 'Vidéo téléchargée avec succès',
                'video_url': url_for('get_video', filename=video_filename)
            })
        except Exception as e:
            print(f"Erreur lors de la sauvegarde du fichier vidéo: {str(e)}")
            return jsonify({'success': False, 'message': f'Erreur lors de la sauvegarde: {str(e)}'})
    
    print(f"Type de fichier non autorisé: {file.filename}")
    return jsonify({'success': False, 'message': 'Type de fichier non autorisé'})

@app.route('/videos/<filename>')
def get_video(filename):
    return send_from_directory(app.config['VIDEO_FOLDER'], filename)

@app.route('/generate_all_clips/<filename>')
def generate_all_clips(filename):
    try:
        # Vérifier si le fichier vidéo existe
        video_filename = f"{filename}_video.mp4"
        video_path = os.path.join(app.config['VIDEO_FOLDER'], video_filename)
        
        if not os.path.exists(video_path):
            flash(f"Fichier vidéo non trouvé: {video_path}. Veuillez d'abord télécharger une vidéo.")
            print(f"Erreur: Fichier vidéo non trouvé: {video_path}")
            return redirect(url_for('edit_video', filename=filename))
        
        # S'assurer que le fichier SRT est disponible à côté de la vidéo
        srt_filename = f"{filename}.srt"
        upload_srt_path = os.path.join(app.config['UPLOAD_FOLDER'], srt_filename)
        video_srt_path = os.path.join(app.config['VIDEO_FOLDER'], srt_filename)
        
        # Si le fichier SRT n'existe pas à côté de la vidéo mais existe dans uploads/,
        # le copier à côté de la vidéo
        if not os.path.exists(video_srt_path) and os.path.exists(upload_srt_path):
            shutil.copy2(upload_srt_path, video_srt_path)
            print(f"Fichier SRT copié de {upload_srt_path} vers {video_srt_path}")
        
        # Générer le script FFmpeg
        quotes_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{filename}_quotes.json")
        if not os.path.exists(quotes_file):
            flash(f"Fichier de citations non trouvé: {quotes_file}. Veuillez d'abord extraire des citations.")
            print(f"Erreur: Fichier de citations non trouvé: {quotes_file}")
            return redirect(url_for('edit_video', filename=filename))
        
        with open(quotes_file, 'r', encoding='utf-8') as f:
            quotes = json.load(f)
        
        # Créer le dossier de sortie pour les clips
        output_dir = os.path.join(app.config['OUTPUT_FOLDER'], f"{filename}_clips")
        os.makedirs(output_dir, exist_ok=True)
        
        # Générer le script FFmpeg
        script_path = os.path.join(app.config['BASE_DIR'], "quotes_output_ffmpeg.sh")
        generate_ffmpeg_cut_file(quotes, script_path, add_subtitles=True)
        
        # Exécuter le script FFmpeg
        cmd = f"bash {script_path} {video_path} {output_dir}"
        print(f"Exécution de la commande: {cmd}")
        
        try:
            subprocess.run(cmd, shell=True, check=True)
            flash(f"Clips générés avec succès dans {output_dir}")
        except subprocess.CalledProcessError as e:
            flash(f"Erreur lors de la génération des clips: {str(e)}")
            print(f"Erreur lors de la génération des clips: {str(e)}")
        
        return redirect(url_for('edit_video', filename=filename))
    except Exception as e:
        flash(f"Erreur lors de la génération des clips: {str(e)}")
        print(f"Exception lors de la génération des clips: {str(e)}")
        return redirect(url_for('edit_video', filename=filename))

def generate_enhanced_ffmpeg_script(quotes, output_file, subtitle_options, padding=1):
    """
    Génère un script FFmpeg avancé pour extraire des segments vidéo avec sous-titres synchronisés
    
    Args:
        quotes: Liste des citations à extraire
        output_file: Chemin du fichier de sortie pour le script
        subtitle_options: Options de formatage des sous-titres
        padding: Nombre de secondes à ajouter avant et après chaque extrait
    """
    # Récupérer les options de sous-titres
    font = subtitle_options.get('font', 'Arial')
    font_size = subtitle_options.get('size', '36')
    font_color = subtitle_options.get('color', '0xffffff')
    bg_color = subtitle_options.get('backgroundColor', '0x000000')
    bg_opacity = float(subtitle_options.get('opacity', '0.7'))
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Entête du script
        f.write("#!/bin/bash\n\n")
        f.write("# Script de génération automatique des extraits vidéo\n\n")
        f.write("if [ $# -ne 2 ]; then\n")
        f.write("    echo \"Usage: $0 input_video.mp4 output_directory\"\n")
        f.write("    exit 1\n")
        f.write("fi\n\n")
        f.write("VIDEO_INPUT=$1\n")
        f.write("OUTPUT_DIR=$2\n")
        f.write("mkdir -p \"$OUTPUT_DIR\"\n\n")
        
        for i, quote in enumerate(quotes, 1):
            start_seconds = quote['start_time'].total_seconds() - padding
            if start_seconds < 0:
                start_seconds = 0
                
            duration_seconds = quote['duration'].total_seconds() + (padding * 2)
            
            # Format du timecode pour le nom de fichier
            timecode = quote['formatted_start'].replace(':', '_')
            
            f.write(f"# Extrait {i}: {quote['formatted_start']} - {quote['formatted_end']}\n")
            f.write(f"echo \"Génération de l'extrait {i}...\"\n")
            
            # Créer un fichier SRT temporaire pour cet extrait
            temp_srt = f"temp_subtitle_{i}.srt"  # Utiliser un chemin relatif
            temp_srt_path = f"\"$OUTPUT_DIR/{temp_srt}\""  # Ajouter des guillemets pour protéger le chemin
            
            # Vérifier que le répertoire existe
            f.write(f"# Vérifier que le répertoire de sortie existe\n")
            f.write(f"mkdir -p \"$OUTPUT_DIR\"\n\n")
            
            # Ajouter des commandes de débogage
            f.write(f"# Débogage: afficher le répertoire courant et les permissions\n")
            f.write(f"pwd\n")
            f.write(f"ls -la \"$OUTPUT_DIR\"\n\n")
            
            # Utiliser un chemin absolu pour le fichier SRT temporaire
            f.write(f"TEMP_SRT_PATH=\"$OUTPUT_DIR/{temp_srt}\"\n\n")
            
            # Écrire le contenu dans un fichier temporaire séparé
            f.write(f"cat > \"$TEMP_SRT_PATH\" << 'EOF'\n")
            
            # Diviser le contenu en segments pour une meilleure synchronisation
            content = quote['content']
            # Nettoyer le contenu pour éviter les problèmes d'échappement
            content = content.replace('\n', ' ').replace('\r', ' ')
            content = content.replace('\\', '').replace('$', '\\$')
            content = content.replace("\'", "'").replace('\"', '"')
            content = content.strip()
            
            # Utiliser une taille de segment plus grande pour éviter trop de fragmentation
            max_segment_length = int(subtitle_options.get('maxSegmentLength', '150'))
            segments = split_content_into_segments(content, max_chars=max_segment_length)
            
            # Durée totale en secondes
            total_duration = duration_seconds
            segment_duration = total_duration / max(1, len(segments))
            
            for seg_idx, segment in enumerate(segments, 1):
                start_time = (seg_idx - 1) * segment_duration
                end_time = seg_idx * segment_duration
                
                # S'assurer que le segment n'est pas vide
                segment = segment.strip()
                if not segment:
                    segment = "..."
                
                # Pas besoin d'échapper les caractères pour le heredoc avec des guillemets simples
                f.write(f"{seg_idx}\n")
                f.write(f"{format_timedelta_srt(timedelta(seconds=start_time))} --> {format_timedelta_srt(timedelta(seconds=end_time))}\n")
                f.write(f"{segment}\n\n")
            
            f.write("EOF\n\n")
            
            # Ajouter des commandes de débogage pour vérifier le fichier SRT
            f.write(f"# Débogage: vérifier que le fichier SRT a été créé\n")
            f.write(f"ls -la \"$TEMP_SRT_PATH\"\n")
            f.write(f"cat \"$TEMP_SRT_PATH\"\n\n")
            
            # S'assurer que le fichier est accessible
            f.write(f"# S'assurer que le fichier SRT est accessible\n")
            f.write(f"chmod 644 \"$TEMP_SRT_PATH\"\n\n")
            
            # Copier le fichier SRT dans le répertoire de travail courant
            f.write(f"# Copier le fichier SRT dans le répertoire de travail courant\n")
            f.write(f"cp \"$TEMP_SRT_PATH\" ./temp_subtitle_${i}.srt\n")
            f.write(f"chmod 644 ./temp_subtitle_${i}.srt\n\n")
            
            # Débogage: écrire le contenu original dans un fichier log
            f.write(f"# Contenu original: {content[:50]}...\n")
            
            # Débogage: écrire le nombre de segments
            f.write(f"# Nombre de segments: {len(segments)}\n")
            
            # Méthode avec subtitles filter pour synchronisation
            f.write("ffmpeg -y -i \"$VIDEO_INPUT\" ")
            f.write(f"-ss {start_seconds} -t {duration_seconds} ")
            
            # Méthode principale avec filtre subtitles
            f.write("# Méthode principale avec filtre subtitles\n")
            
            # Créer une variable pour le chemin complet
            f.write("# Créer une variable pour le chemin complet du fichier SRT\n")
            f.write("CURRENT_DIR=\"$(pwd)\"\n")
            f.write("FULL_SRT_PATH=\"$CURRENT_DIR/$OUTPUT_DIR/temp_subtitle_${i}.srt\"\n\n")
            
            # Vérifier que le fichier existe
            f.write("if [ -f \"$TEMP_SRT_PATH\" ]; then\n")
            f.write("    echo \"Fichier SRT temporaire trouvé: $TEMP_SRT_PATH\"\n")
            
            # Utiliser le filtre subtitles avec le chemin absolu
            f.write("    ffmpeg -y -i \"$VIDEO_INPUT\" ")
            f.write(f"-ss {start_seconds} -t {duration_seconds} ")
            f.write("-vf \"")
            f.write("subtitles=temp_subtitle_${i}.srt:force_style='")
            f.write(f"FontName={font},")
            f.write(f"FontSize={font_size},")
            f.write(f"PrimaryColour={font_color.replace('0x', '&H')},")
            f.write(f"BackColour={bg_color.replace('0x', '&H')}{int(bg_opacity*255):02X},")
            f.write(f"BorderStyle=4,")  # Style avec fond (box)
            f.write(f"Outline=1,")
            f.write(f"Alignment=2,")    # Centré en bas
            f.write(f"MarginV=30")      # Marge verticale pour remonter les sous-titres
            f.write("'\" ")
            
            # Paramètres de sortie
            f.write("-c:v libx264 -preset fast -crf 22 -c:a aac -b:a 128k ")
            f.write(f"\"$OUTPUT_DIR/extrait_{i:03d}_{timecode}.mp4\"\n")
            
            # Si le filtre subtitles échoue, utiliser drawtext
            f.write("    if [ $? -ne 0 ]; then\n")
            f.write("        echo \"Échec avec le filtre subtitles, tentative avec drawtext...\"\n")
            f.write("        ffmpeg -y -i \"$VIDEO_INPUT\" ")
            f.write(f"-ss {start_seconds} -t {duration_seconds} ")
            f.write("-vf \"")
            # Utiliser drawtext comme solution de repli
            f.write(f"drawtext=fontfile=")
            # Déterminer le chemin de la police selon le système d'exploitation
            f.write("$(if [ \"$(uname)\" == \"Darwin\" ]; then ")
            f.write("echo \"/System/Library/Fonts/Helvetica.ttc\"; ")
            f.write("elif [ \"$(uname)\" == \"Linux\" ]; then ")
            f.write("echo \"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf\"; ")
            f.write("else ")
            f.write("echo \"/Windows/Fonts/arial.ttf\"; ")
            f.write("fi):")
            f.write(f"fontsize={font_size}:")
            f.write(f"fontcolor={font_color}@1.0:")
            f.write(f"box=1:boxcolor={bg_color}@{bg_opacity}:")
            f.write("boxborderw=15:")
            f.write("text='")
            # Limiter le texte pour drawtext
            short_text = content[:150].replace("'", "\\'").replace('"', '\\"')
            f.write(f"{short_text}")
            f.write("':")
            f.write("x=(w-text_w)/2:y=h*0.75\" ")
            f.write("-c:v libx264 -preset fast -crf 22 -c:a aac -b:a 128k ")
            f.write(f"\"$OUTPUT_DIR/extrait_{i:03d}_{timecode}.mp4\"\n")
            f.write("    fi\n")
            f.write("else\n")
            f.write("    echo \"Fichier SRT temporaire non trouvé: $TEMP_SRT_PATH, utilisation de drawtext...\"\n")
            f.write("    ffmpeg -y -i \"$VIDEO_INPUT\" ")
            f.write(f"-ss {start_seconds} -t {duration_seconds} ")
            f.write("-vf \"")
            # Utiliser drawtext directement si le fichier SRT n'existe pas
            f.write(f"drawtext=fontfile=")
            # Déterminer le chemin de la police selon le système d'exploitation
            f.write("$(if [ \"$(uname)\" == \"Darwin\" ]; then ")
            f.write("echo \"/System/Library/Fonts/Helvetica.ttc\"; ")
            f.write("elif [ \"$(uname)\" == \"Linux\" ]; then ")
            f.write("echo \"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf\"; ")
            f.write("else ")
            f.write("echo \"/Windows/Fonts/arial.ttf\"; ")
            f.write("fi):")
            f.write(f"fontsize={font_size}:")
            f.write(f"fontcolor={font_color}@1.0:")
            f.write(f"box=1:boxcolor={bg_color}@{bg_opacity}:")
            f.write("boxborderw=15:")
            f.write("text='")
            short_text = content[:150].replace("'", "\\'").replace('"', '\\"')
            f.write(f"{short_text}")
            f.write("':")
            f.write("x=(w-text_w)/2:y=h*0.75\" ")
            f.write("-c:v libx264 -preset fast -crf 22 -c:a aac -b:a 128k ")
            f.write(f"\"$OUTPUT_DIR/extrait_{i:03d}_{timecode}.mp4\"\n")
            f.write("fi\n\n")
            
            # Supprimer le fichier SRT temporaire
            f.write("# Supprimer le fichier SRT temporaire\n")
            f.write("rm -f \"$TEMP_SRT_PATH\"\n")
            f.write("rm -f ./temp_subtitle_${i}.srt\n\n")
        
        # Ajouter une commande pour combiner tous les extraits
        f.write("# Demander à l'utilisateur s'il souhaite combiner tous les extraits\n")
        f.write("echo \"Voulez-vous combiner tous les extraits en une seule vidéo ? (o/n)\"\n")
        f.write("read -r COMBINE\n")
        f.write("if [ \"$COMBINE\" = \"o\" ] || [ \"$COMBINE\" = \"O\" ]; then\n")
        f.write("    echo \"Combinaison de tous les extraits...\"\n")
        f.write("    # Créer un fichier de liste pour FFmpeg\n")
        f.write("    LIST_FILE=\"$OUTPUT_DIR/list.txt\"\n")
        f.write("    > \"$LIST_FILE\"\n")
        f.write("    for f in \"$OUTPUT_DIR\"/*.mp4; do\n")
        f.write("        echo \"file '$f'\" >> \"$LIST_FILE\"\n")
        f.write("    done\n")
        f.write("    # Combiner les vidéos\n")
        f.write("    ffmpeg -y -f concat -safe 0 -i \"$LIST_FILE\" -c copy \"$OUTPUT_DIR/tous_les_extraits_combines.mp4\"\n")
        f.write("    echo \"Vidéo combinée créée : $OUTPUT_DIR/tous_les_extraits_combines.mp4\"\n")
        f.write("    # Nettoyer le fichier de liste\n")
        f.write("    rm -f \"$LIST_FILE\"\n")
        f.write("fi\n\n")
        
        # Rendre le script exécutable
        f.write("echo \"Tous les extraits ont été générés dans $OUTPUT_DIR\"\n")
    
    # Rendre le script exécutable
    os.chmod(output_file, 0o755)
    
    return output_file

def split_content_into_segments(content, max_chars=100):
    """
    Divise un texte en segments plus courts pour une meilleure synchronisation des sous-titres
    """
    # Si le contenu est vide ou trop court, le retourner tel quel
    if not content or len(content) <= max_chars:
        return [content]
    
    # Nettoyer le contenu: supprimer les caractères d'échappement et les caractères spéciaux problématiques
    content = content.replace('\n', ' ').replace('\r', ' ')
    content = content.replace('\\', '').replace('$', '\\$')
    content = content.replace("\'", "'").replace('\"', '"')  # Normaliser les apostrophes et guillemets
    
    # Diviser le texte en phrases
    sentences = re.split(r'(?<=[.!?])\s+', content)
    
    segments = []
    current_segment = ""
    
    for sentence in sentences:
        # Si la phrase est très courte, l'ajouter au segment courant
        if len(sentence) < 20:
            if current_segment and len(current_segment + " " + sentence) <= max_chars:
                current_segment += " " + sentence
            else:
                if current_segment:
                    segments.append(current_segment.strip())
                current_segment = sentence
            continue
            
        # Si la phrase est très longue, la découper en morceaux
        if len(sentence) > max_chars:
            # D'abord ajouter le segment courant s'il existe
            if current_segment:
                segments.append(current_segment.strip())
                current_segment = ""
                
            # Puis découper la phrase longue en morceaux
            words = sentence.split()
            temp_segment = ""
            
            for word in words:
                if len(temp_segment) + len(word) + 1 <= max_chars:
                    if temp_segment:
                        temp_segment += " " + word
                    else:
                        temp_segment = word
                else:
                    segments.append(temp_segment.strip())
                    temp_segment = word
            
            # Ajouter le dernier morceau s'il existe
            if temp_segment:
                current_segment = temp_segment
        else:
            # Ajouter la phrase au segment actuel ou créer un nouveau segment
            if current_segment and len(current_segment + " " + sentence) <= max_chars:
                current_segment += " " + sentence
            else:
                if current_segment:
                    segments.append(current_segment.strip())
                current_segment = sentence
    
    # Ajouter le dernier segment s'il existe
    if current_segment:
        segments.append(current_segment.strip())
    
    # S'assurer qu'il y a au moins un segment et qu'aucun n'est vide
    segments = [seg for seg in segments if seg]
    if not segments:
        segments = [content]
    
    return segments

def format_timedelta_srt(td):
    """Convertit un objet timedelta en format SRT (HH:MM:SS,mmm)"""
    total_seconds = td.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    milliseconds = int((total_seconds - int(total_seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

@app.route('/combine_clips/<filename>', methods=['POST'])
def combine_clips(filename):
    try:
        # Récupérer les indices des extraits à combiner
        selected_indices = request.json.get('selected_indices', [])
        
        if not selected_indices or len(selected_indices) < 2:
            return jsonify({'success': False, 'message': 'Sélectionnez au moins deux extraits à combiner'})
        
        # Charger les données des extraits
        json_file = os.path.join(app.config['OUTPUT_FOLDER'], f"{filename}_quotes.json")
        with open(json_file, 'r', encoding='utf-8') as f:
            quotes = json.load(f)
        
        # Trier les indices pour les traiter dans l'ordre chronologique
        selected_indices.sort(key=lambda i: quotes[i]['start_time_seconds'])
        
        # Créer un nouvel extrait combiné
        combined_quote = {
            'content': ' '.join([quotes[i]['content'] for i in selected_indices]),
            'start_time_seconds': quotes[selected_indices[0]]['start_time_seconds'],
            'end_time_seconds': quotes[selected_indices[-1]]['end_time_seconds'],
            'formatted_start': quotes[selected_indices[0]]['formatted_start'],
            'formatted_end': quotes[selected_indices[-1]]['formatted_end'],
            'duration_seconds': quotes[selected_indices[-1]]['end_time_seconds'] - quotes[selected_indices[0]]['start_time_seconds']
        }
        
        # Ajouter le nouvel extrait combiné
        quotes.append(combined_quote)
        
        # Sauvegarder les modifications
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(quotes, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True, 
            'message': 'Extraits combinés avec succès',
            'new_quote': combined_quote,
            'new_index': len(quotes) - 1
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})

@app.route('/download_clip/<path:clip_path>')
def download_clip(clip_path):
    directory = os.path.dirname(clip_path)
    filename = os.path.basename(clip_path)
    return send_from_directory(os.path.join(app.config['OUTPUT_FOLDER'], directory), filename)

if __name__ == '__main__':
    app.run(debug=True) 