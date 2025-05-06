import srt
import sys
from pathlib import Path
import argparse
from datetime import timedelta
import json
import re

def extract_text_from_srt(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        subtitles = list(srt.parse(f.read()))
    full_text = " ".join(sub.content for sub in subtitles)
    return full_text, subtitles

def format_timecode(time):
    """Convertit un objet timedelta en format HH:MM:SS"""
    total_seconds = int(time.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def format_ffmpeg_time(time):
    """Convertit un objet timedelta en format HH:MM:SS.mmm pour FFmpeg"""
    total_seconds = time.total_seconds()
    hours, remainder = divmod(int(total_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((total_seconds - int(total_seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

def analyze_sentiment(text):
    """Analyse basique du sentiment d'un texte"""
    try:
        # Essayer d'utiliser TextBlob si disponible (installation: pip install textblob)
        from textblob import TextBlob
        blob = TextBlob(text)
        return {
            'polarity': blob.sentiment.polarity,  # -1 à 1 (négatif à positif)
            'subjectivity': blob.sentiment.subjectivity,  # 0 à 1 (objectif à subjectif)
            'is_intense': abs(blob.sentiment.polarity) > 0.3 or blob.sentiment.subjectivity > 0.6
        }
    except ImportError:
        # Analyse basique basée sur des mots-clés si TextBlob n'est pas disponible
        positive_words = ['excellent', 'incroyable', 'fantastique', 'génial', 'super', 'important', 
                          'crucial', 'essentiel', 'clé', 'révolutionnaire', 'extraordinaire', 'remarquable']
        negative_words = ['terrible', 'horrible', 'catastrophique', 'désastreux', 'problématique', 
                          'difficile', 'critique', 'grave', 'inquiétant', 'alarmant']
        emphasis_words = ['très', 'extrêmement', 'absolument', 'totalement', 'complètement', 'vraiment']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        emphasis_count = sum(1 for word in emphasis_words if word in text_lower)
        
        total_words = len(re.findall(r'\b\w+\b', text_lower))
        polarity = (positive_count - negative_count) / max(1, total_words) * 5
        intensity = (positive_count + negative_count + emphasis_count) / max(1, total_words) * 5
        
        return {
            'polarity': max(-1, min(1, polarity)),  # Limiter entre -1 et 1
            'subjectivity': intensity,
            'is_intense': polarity > 0.3 or intensity > 0.3
        }

def detect_topic_changes(subtitles, window_size=5):
    """Détecte les changements de sujet dans les sous-titres"""
    if len(subtitles) < window_size * 2:
        return []
    
    topic_changes = []
    
    for i in range(window_size, len(subtitles) - window_size):
        # Texte avant et après la position actuelle
        before_text = " ".join(sub.content for sub in subtitles[i-window_size:i])
        after_text = " ".join(sub.content for sub in subtitles[i:i+window_size])
        
        # Mots uniques avant et après
        before_words = set(re.findall(r'\b\w+\b', before_text.lower()))
        after_words = set(re.findall(r'\b\w+\b', after_text.lower()))
        
        # Calculer la différence entre les ensembles de mots
        if len(before_words) > 0 and len(after_words) > 0:
            common_words = before_words.intersection(after_words)
            all_words = before_words.union(after_words)
            difference_ratio = 1 - (len(common_words) / len(all_words))
            
            # Si la différence est significative, c'est peut-être un changement de sujet
            if difference_ratio > 0.7:  # Seuil ajustable
                topic_changes.append(i)
    
    return topic_changes

def group_subtitles_into_passages(subtitles, max_gap_seconds=3.0, min_passage_length=500, max_passage_length=2000):
    """
    Regroupe les sous-titres consécutifs en passages plus longs et cohérents.
    
    Args:
        subtitles: Liste des sous-titres
        max_gap_seconds: Écart maximal en secondes entre deux sous-titres pour les considérer comme faisant partie du même passage
        min_passage_length: Longueur minimale en caractères pour un passage
        max_passage_length: Longueur maximale en caractères pour un passage
    
    Returns:
        Liste de passages, chaque passage étant un dictionnaire avec le contenu et les timecodes
    """
    if not subtitles:
        return []
    
    passages = []
    current_passage = {
        'content': subtitles[0].content,
        'start_time': subtitles[0].start,
        'end_time': subtitles[0].end,
        'subtitles': [subtitles[0]]
    }
    
    for i in range(1, len(subtitles)):
        current_sub = subtitles[i]
        gap = (current_sub.start - current_passage['end_time']).total_seconds()
        
        # Si l'écart est trop grand ou si le passage devient trop long, on termine le passage actuel
        passage_length = len(current_passage['content'])
        if gap > max_gap_seconds or passage_length + len(current_sub.content) > max_passage_length:
            # Ne garder le passage que s'il est assez long
            if passage_length >= min_passage_length:
                passages.append(current_passage)
            
            # Commencer un nouveau passage
            current_passage = {
                'content': current_sub.content,
                'start_time': current_sub.start,
                'end_time': current_sub.end,
                'subtitles': [current_sub]
            }
        else:
            # Ajouter au passage actuel
            current_passage['content'] += " " + current_sub.content
            current_passage['end_time'] = current_sub.end
            current_passage['subtitles'].append(current_sub)
    
    # Ajouter le dernier passage s'il est assez long
    if len(current_passage['content']) >= min_passage_length:
        passages.append(current_passage)
    
    return passages

def extract_quotes(subtitles, min_length=120, keywords=None, use_sentiment=False, topic_detection=False, group_subtitles=True, max_gap_seconds=3.0):
    """Extrait les citations importantes avec leurs timecodes"""
    quotes = []
    topic_changes = []
    
    if topic_detection:
        topic_changes = detect_topic_changes(subtitles)
    
    # Si on regroupe les sous-titres, on travaille sur des passages plutôt que des sous-titres individuels
    if group_subtitles:
        passages = group_subtitles_into_passages(subtitles, max_gap_seconds=max_gap_seconds)
        
        for passage in passages:
            content = passage['content'].strip()
            
            # Critères de sélection
            is_long_enough = len(content) > min_length
            has_keyword = False
            if keywords:
                has_keyword = any(keyword.lower() in content.lower() for keyword in keywords)
            
            is_intense = False
            sentiment_data = None
            if use_sentiment:
                sentiment_data = analyze_sentiment(content)
                is_intense = sentiment_data['is_intense']
            
            # Vérifier si le passage contient un changement de sujet
            is_topic_change = any(i in topic_changes for i in range(len(passage['subtitles'])))
            
            # Sélectionner si au moins un critère est rempli
            if is_long_enough or has_keyword or is_intense or is_topic_change:
                quote_data = {
                    'content': content,
                    'start_time': passage['start_time'],
                    'end_time': passage['end_time'],
                    'duration': passage['end_time'] - passage['start_time'],
                    'formatted_start': format_timecode(passage['start_time']),
                    'formatted_end': format_timecode(passage['end_time']),
                    'ffmpeg_start': format_ffmpeg_time(passage['start_time']),
                    'ffmpeg_end': format_ffmpeg_time(passage['end_time']),
                    'is_long': is_long_enough,
                    'has_keyword': has_keyword,
                    'is_topic_change': is_topic_change
                }
                
                if sentiment_data:
                    quote_data.update({
                        'sentiment_polarity': sentiment_data['polarity'],
                        'sentiment_subjectivity': sentiment_data['subjectivity'],
                        'is_intense': is_intense
                    })
                
                quotes.append(quote_data)
    else:
        # Méthode originale: traiter chaque sous-titre individuellement
        for i, sub in enumerate(subtitles):
            content = sub.content.strip()
            
            # Critères de sélection
            is_long_enough = len(content) > min_length
            has_keyword = False
            if keywords:
                has_keyword = any(keyword.lower() in content.lower() for keyword in keywords)
            
            is_intense = False
            sentiment_data = None
            if use_sentiment:
                sentiment_data = analyze_sentiment(content)
                is_intense = sentiment_data['is_intense']
            
            is_topic_change = i in topic_changes
            
            # Sélectionner si au moins un critère est rempli
            if is_long_enough or has_keyword or is_intense or is_topic_change:
                quote_data = {
                    'content': content,
                    'start_time': sub.start,
                    'end_time': sub.end,
                    'duration': sub.end - sub.start,
                    'formatted_start': format_timecode(sub.start),
                    'formatted_end': format_timecode(sub.end),
                    'ffmpeg_start': format_ffmpeg_time(sub.start),
                    'ffmpeg_end': format_ffmpeg_time(sub.end),
                    'is_long': is_long_enough,
                    'has_keyword': has_keyword,
                    'is_topic_change': is_topic_change
                }
                
                if sentiment_data:
                    quote_data.update({
                        'sentiment_polarity': sentiment_data['polarity'],
                        'sentiment_subjectivity': sentiment_data['subjectivity'],
                        'is_intense': is_intense
                    })
                
                quotes.append(quote_data)
    
    return quotes

def summarize_text(text, max_sentences=5):
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return " ".join(sentences[:max_sentences])

def export_quotes_to_file(quotes, output_file):
    """Exporte les citations dans un fichier texte formaté"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# MOMENTS FORTS DU PODCAST\n\n")
        
        for i, quote in enumerate(quotes, 1):
            f.write(f"## Moment fort {i}\n")
            f.write(f"- **Timecode**: {quote['formatted_start']} - {quote['formatted_end']}\n")
            f.write(f"- **Durée**: {int(quote['duration'].total_seconds())} secondes\n")
            
            # Ajouter les critères de sélection
            criteria = []
            if quote.get('is_long', False):
                criteria.append("Passage long")
            if quote.get('has_keyword', False):
                criteria.append("Contient un mot-clé")
            if quote.get('is_intense', False):
                polarity = quote.get('sentiment_polarity', 0)
                if polarity > 0:
                    criteria.append(f"Sentiment positif ({polarity:.2f})")
                elif polarity < 0:
                    criteria.append(f"Sentiment négatif ({polarity:.2f})")
                criteria.append(f"Subjectivité: {quote.get('sentiment_subjectivity', 0):.2f}")
            if quote.get('is_topic_change', False):
                criteria.append("Changement de sujet")
            
            if criteria:
                f.write(f"- **Critères**: {', '.join(criteria)}\n")
            
            f.write(f"- **Contenu**: {quote['content']}\n\n")
            
        f.write("\n# Format pour édition vidéo\n\n")
        for i, quote in enumerate(quotes, 1):
            f.write(f"{i}. {quote['formatted_start']} - {quote['formatted_end']} : {quote['content'][:50]}...\n")

def generate_ffmpeg_cut_file(quotes, output_file, padding_seconds=1, add_subtitles=True):
    """Génère un fichier de découpage pour FFmpeg"""
    padding = timedelta(seconds=padding_seconds)
    
    # Format pour FFmpeg concat demuxer
    with open(output_file, 'w', encoding='utf-8') as f:
        for i, quote in enumerate(quotes, 1):
            # Ajouter un padding au début et à la fin
            start_time = max(timedelta(seconds=0), quote['start_time'] - padding)
            
            f.write(f"# Segment {i}: {quote['formatted_start']} - {quote['formatted_end']}\n")
            f.write(f"file 'INPUT_FILE'\n")
            f.write(f"inpoint {format_ffmpeg_time(start_time)}\n")
            f.write(f"outpoint {format_ffmpeg_time(quote['end_time'] + padding)}\n\n")
    
    # Générer aussi un script bash pour faciliter l'utilisation
    script_file = output_file.replace('.txt', '.sh')
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write("#!/bin/bash\n\n")
        f.write("# Script de découpage automatique des moments forts\n\n")
        f.write("if [ $# -ne 2 ]; then\n")
        f.write('    echo "Usage: $0 input_video.mp4 output_directory"\n')
        f.write("    exit 1\n")
        f.write("fi\n\n")
        f.write("INPUT_FILE=$1\n")
        f.write("OUTPUT_DIR=$2\n")
        f.write("mkdir -p $OUTPUT_DIR\n")
        f.write("SRT_FILE=\"${INPUT_FILE%.*}.srt\"\n\n")
        f.write("# Vérifier si le fichier SRT existe à côté de la vidéo\n")
        f.write("if [ ! -f \"$SRT_FILE\" ]; then\n")
        f.write('    echo "Attention: Fichier SRT non trouvé: $SRT_FILE"\n')
        f.write('    echo "Les sous-titres ne seront pas incrustés."\n')
        f.write('    SRT_FILE=""\n')
        f.write("fi\n\n")
        
        for i, quote in enumerate(quotes, 1):
            safe_name = quote['content'][:30].replace(' ', '_').replace("'", "").replace('"', '').replace('?', '').replace('!', '')
            output_file = f"$OUTPUT_DIR/segment_{i:02d}_{safe_name}.mp4"
            start_time = max(timedelta(seconds=0), quote['start_time'] - padding)
            end_time = quote['end_time'] + padding
            duration = end_time - start_time
            duration_seconds = duration.total_seconds()
            
            f.write(f"# Segment {i}: {quote['formatted_start']} - {quote['formatted_end']}\n")
            f.write(f'echo "Extraction du segment {i}..."\n')
            
            # Commande FFmpeg de base
            ffmpeg_cmd = f'ffmpeg -i "$INPUT_FILE" -ss {format_ffmpeg_time(start_time)} -t {format_ffmpeg_time(duration)}'
            
            # Ajouter les sous-titres si demandé et si le fichier SRT existe
            if add_subtitles:
                f.write('if [ -n "$SRT_FILE" ]; then\n')
                # Commande avec sous-titres incrustés
                f.write(f'  {ffmpeg_cmd} \\\n')
                f.write(f'    -vf "subtitles=\'$SRT_FILE\':force_style=\'FontName=Arial,FontSize=24,PrimaryColour=&Hffffff,OutlineColour=&H000000,BackColour=&H80000000,Outline=1,Shadow=0\':enable=between(t\\,0\\,{duration_seconds})"\\\n')
                f.write(f'    -c:v libx264 -c:a aac -strict experimental "{output_file}"\n')
                f.write('else\n')
                # Commande sans sous-titres
                f.write(f'  {ffmpeg_cmd} -c:v libx264 -c:a aac -strict experimental "{output_file}"\n')
                f.write('fi\n\n')
            else:
                # Commande sans sous-titres
                f.write(f'{ffmpeg_cmd} -c:v libx264 -c:a aac -strict experimental "{output_file}"\n\n')
    
    # Rendre le script exécutable
    import os
    os.chmod(script_file, 0o755)
    
    return script_file

def export_json_data(quotes, output_file):
    """Exporte les données au format JSON pour une utilisation ultérieure"""
    # Convertir les objets timedelta en secondes pour la sérialisation JSON
    json_data = []
    for quote in quotes:
        json_quote = {
            'content': quote['content'],
            'start_time_seconds': quote['start_time'].total_seconds(),
            'end_time_seconds': quote['end_time'].total_seconds(),
            'duration_seconds': quote['duration'].total_seconds(),
            'formatted_start': quote['formatted_start'],
            'formatted_end': quote['formatted_end']
        }
        
        # Ajouter les critères de sélection s'ils existent
        for key in ['is_long', 'has_keyword', 'is_intense', 'is_topic_change', 
                   'sentiment_polarity', 'sentiment_subjectivity']:
            if key in quote:
                json_quote[key] = quote[key]
        
        json_data.append(json_quote)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrait les citations importantes d'un fichier SRT")
    parser.add_argument("file", help="Chemin vers le fichier SRT")
    parser.add_argument("-o", "--output", help="Fichier de sortie (par défaut: quotes_output.txt)", default="quotes_output.txt")
    parser.add_argument("-n", "--number", type=int, help="Nombre de citations à extraire", default=10)
    parser.add_argument("-l", "--min-length", type=int, help="Longueur minimale des citations", default=120)
    parser.add_argument("-k", "--keywords", nargs='+', help="Mots-clés à rechercher dans les sous-titres")
    parser.add_argument("-f", "--ffmpeg", action="store_true", help="Générer un fichier de découpage pour FFmpeg")
    parser.add_argument("-p", "--padding", type=int, help="Padding en secondes pour les segments vidéo", default=1)
    parser.add_argument("-j", "--json", action="store_true", help="Exporter les données au format JSON")
    parser.add_argument("-s", "--sentiment", action="store_true", help="Utiliser l'analyse de sentiment pour détecter les moments forts")
    parser.add_argument("-t", "--topic-detection", action="store_true", help="Détecter les changements de sujet")
    parser.add_argument("-g", "--group-subtitles", action="store_true", help="Regrouper les sous-titres consécutifs en passages")
    parser.add_argument("-m", "--max-gap", type=float, help="Écart maximal en secondes entre deux sous-titres pour les considérer comme faisant partie du même passage", default=3.0)
    parser.add_argument("--no-subtitles", action="store_true", help="Ne pas incruster les sous-titres dans les segments vidéo")
    
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Fichier {file_path} introuvable.")
        sys.exit(1)

    full_text, subtitles = extract_text_from_srt(file_path)
    quotes = extract_quotes(subtitles, min_length=args.min_length, keywords=args.keywords, 
                           use_sentiment=args.sentiment, topic_detection=args.topic_detection, group_subtitles=args.group_subtitles, max_gap_seconds=args.max_gap)
    summary = summarize_text(full_text)

    # Trier les citations par score d'importance
    def importance_score(quote):
        score = 0
        # Longueur du contenu
        score += min(5, quote['duration'].total_seconds() / 10)
        # Présence de mots-clés
        if quote.get('has_keyword', False):
            score += 3
        # Intensité du sentiment
        if quote.get('is_intense', False):
            score += 2 + abs(quote.get('sentiment_polarity', 0))
        # Changement de sujet
        if quote.get('is_topic_change', False):
            score += 2
        return score
    
    quotes.sort(key=importance_score, reverse=True)
    
    # Limiter au nombre demandé
    selected_quotes = quotes[:args.number]
    
    # Trier par ordre chronologique pour l'affichage
    selected_quotes.sort(key=lambda x: x['start_time'])
    
    # Exporter dans un fichier
    export_quotes_to_file(selected_quotes, args.output)

    # Générer fichier FFmpeg si demandé
    ffmpeg_script = None
    if args.ffmpeg:
        ffmpeg_file = args.output.replace('.txt', '_ffmpeg.txt')
        ffmpeg_script = generate_ffmpeg_cut_file(selected_quotes, ffmpeg_file, args.padding, not args.no_subtitles)
    
    # Exporter au format JSON si demandé
    if args.json:
        json_file = args.output.replace('.txt', '.json')
        export_json_data(selected_quotes, json_file)
        print(f"Données exportées au format JSON: {json_file}")

    print(f"\n=== Résumé du fichier ===\n")
    print(summary)
    print(f"\n=== {len(selected_quotes)} citations marquantes extraites ===\n")
    for q in selected_quotes:
        criteria = []
        if q.get('is_long', False):
            criteria.append("long")
        if q.get('has_keyword', False):
            criteria.append("mot-clé")
        if q.get('is_intense', False):
            criteria.append(f"sentiment: {q.get('sentiment_polarity', 0):.2f}")
        if q.get('is_topic_change', False):
            criteria.append("changement sujet")
        
        criteria_str = f" [{', '.join(criteria)}]" if criteria else ""
        print(f"- [{q['formatted_start']} - {q['formatted_end']}]{criteria_str} {q['content'][:100]}...")
    
    print(f"\nRésultats exportés dans: {args.output}")
    
    if ffmpeg_script:
        print(f"Fichier de découpage FFmpeg généré: {ffmpeg_script}")
        print(f"Script bash de découpage généré: {ffmpeg_script.replace('.txt', '.sh')}")
        print(f"Pour utiliser le script: bash {ffmpeg_script.replace('.txt', '.sh')} video_input.mp4 dossier_sortie/")
    
    if args.sentiment:
        print("\nNote: Pour une meilleure analyse de sentiment, installez TextBlob: pip install textblob")
