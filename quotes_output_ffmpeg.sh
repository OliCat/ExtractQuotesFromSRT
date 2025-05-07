#!/bin/bash

# Script de découpage automatique des moments forts

if [ $# -ne 2 ]; then
    echo "Usage: $0 input_video.mp4 output_directory"
    exit 1
fi

INPUT_FILE=$1
OUTPUT_DIR=$2
mkdir -p $OUTPUT_DIR
# Chercher le fichier SRT à plusieurs endroits
SRT_FILE="${INPUT_FILE%.*}.srt"
BASENAME=$(basename "$INPUT_FILE" .mp4)
UPLOADS_SRT="uploads/${BASENAME}.srt"

# Vérifier si le fichier SRT existe à côté de la vidéo ou dans le dossier uploads/
if [ ! -f "$SRT_FILE" ]; then
    if [ -f "$UPLOADS_SRT" ]; then
        echo "Fichier SRT trouvé dans uploads/: $UPLOADS_SRT"
        SRT_FILE="$UPLOADS_SRT"
    else
        echo "Attention: Fichier SRT non trouvé: $SRT_FILE ni $UPLOADS_SRT"
        echo "Les sous-titres ne seront pas incrustés."
        SRT_FILE=""
    fi
fi

# Segment 1: 00:00:18 - 00:02:07
echo "Extraction du segment 1..."
if [ -n "$SRT_FILE" ]; then
  # Définir le nom du fichier SRT temporaire
  temp_srt="temp_subtitle_1.srt"
  
  # Extraire les sous-titres pour ce segment
  ffmpeg -y -i "$SRT_FILE" -ss 00:00:18.000 -to 00:02:07.000 "$OUTPUT_DIR/$temp_srt"
  
  # Afficher les premiers sous-titres pour vérification
  head -n 20 "$OUTPUT_DIR/$temp_srt"
  
  # Extraire le segment vidéo avec sous-titres
  ffmpeg -y -i "$INPUT_FILE" -ss 00:00:17.000 -to 00:02:08.000 \
    -vf "subtitles=$OUTPUT_DIR/$temp_srt" \
    -c:v libx264 -c:a aac -strict experimental \
    "$OUTPUT_DIR/segment_01_bonjour_à_toutes_bonjour_à_tou.mp4"
else
  # Extraire le segment vidéo sans sous-titres
  ffmpeg -y -i "$INPUT_FILE" -ss 00:00:17.000 -to 00:02:08.000 \
    -c:v libx264 -c:a aac -strict experimental \
    "$OUTPUT_DIR/segment_01_bonjour_à_toutes_bonjour_à_tou.mp4"
fi

# Segment 2: 00:02:05 - 00:03:58
echo "Extraction du segment 2..."
if [ -n "$SRT_FILE" ]; then
  temp_srt="temp_subtitle_2.srt"
  ffmpeg -y -i "$SRT_FILE" -ss 00:02:05.000 -to 00:03:58.000 "$OUTPUT_DIR/$temp_srt"
  ffmpeg -y -i "$INPUT_FILE" -ss 00:02:04.000 -to 00:03:59.000 \
    -vf "subtitles=$OUTPUT_DIR/$temp_srt" \
    -c:v libx264 -c:a aac -strict experimental \
    "$OUTPUT_DIR/segment_02_logiciels_libres_et_services_re.mp4"
else
  ffmpeg -y -i "$INPUT_FILE" -ss 00:02:04.000 -to 00:03:59.000 \
    -c:v libx264 -c:a aac -strict experimental \
    "$OUTPUT_DIR/segment_02_logiciels_libres_et_services_re.mp4"
fi

# Segment 3: 00:03:57 - 00:05:45
echo "Extraction du segment 3..."
if [ -n "$SRT_FILE" ]; then
  temp_srt="temp_subtitle_3.srt"
  ffmpeg -y -i "$SRT_FILE" -ss 00:03:57.000 -to 00:05:45.000 "$OUTPUT_DIR/$temp_srt"
  ffmpeg -y -i "$INPUT_FILE" -ss 00:03:56.000 -to 00:05:46.000 \
    -vf "subtitles=$OUTPUT_DIR/$temp_srt" \
    -c:v libx264 -c:a aac -strict experimental \
    "$OUTPUT_DIR/segment_03_et_plein_de_mots_techniques_que.mp4"
else
  ffmpeg -y -i "$INPUT_FILE" -ss 00:03:56.000 -to 00:05:46.000 \
    -c:v libx264 -c:a aac -strict experimental \
    "$OUTPUT_DIR/segment_03_et_plein_de_mots_techniques_que.mp4"
fi

# Segment 4: 00:05:43 - 00:07:43
echo "Extraction du segment 4..."
if [ -n "$SRT_FILE" ]; then
  temp_srt="temp_subtitle_4.srt"
  ffmpeg -y -i "$SRT_FILE" -ss 00:05:43.000 -to 00:07:43.000 "$OUTPUT_DIR/$temp_srt"
  ffmpeg -y -i "$INPUT_FILE" -ss 00:05:42.000 -to 00:07:44.000 \
    -vf "subtitles=$OUTPUT_DIR/$temp_srt" \
    -c:v libx264 -c:a aac -strict experimental \
    "$OUTPUT_DIR/segment_04_pirate_box_sont_majoritairement_.mp4"
else
  ffmpeg -y -i "$INPUT_FILE" -ss 00:05:42.000 -to 00:07:44.000 \
    -c:v libx264 -c:a aac -strict experimental \
    "$OUTPUT_DIR/segment_04_pirate_box_sont_majoritairement_.mp4"
fi

# Segment 5: 00:07:40 - 00:09:28
echo "Extraction du segment 5..."
if [ -n "$SRT_FILE" ]; then
  temp_srt="temp_subtitle_5.srt"
  ffmpeg -y -i "$SRT_FILE" -ss 00:07:40.000 -to 00:09:28.000 "$OUTPUT_DIR/$temp_srt"
  ffmpeg -y -i "$INPUT_FILE" -ss 00:07:39.000 -to 00:09:29.000 \
    -vf "subtitles=$OUTPUT_DIR/$temp_srt" \
    -c:v libx264 -c:a aac -strict experimental \
    "$OUTPUT_DIR/segment_05_zo_pouf_pouf_donc_tutoriel_tene.mp4"
else
  ffmpeg -y -i "$INPUT_FILE" -ss 00:07:39.000 -to 00:09:29.000 \
    -c:v libx264 -c:a aac -strict experimental \
    "$OUTPUT_DIR/segment_05_zo_pouf_pouf_donc_tutoriel_tene.mp4"
fi

# Segment 6: 00:09:26 - 00:11:02
echo "Extraction du segment 6..."
if [ -n "$SRT_FILE" ]; then
  temp_srt="temp_subtitle_6.srt"
  ffmpeg -y -i "$SRT_FILE" -ss 00:09:26.000 -to 00:11:02.000 "$OUTPUT_DIR/$temp_srt"
  ffmpeg -y -i "$INPUT_FILE" -ss 00:09:25.000 -to 00:11:03.000 \
    -vf "subtitles=$OUTPUT_DIR/$temp_srt" \
    -c:v libx264 -c:a aac -strict experimental \
    "$OUTPUT_DIR/segment_06_des_projets_de_box_et_dérivé_fi.mp4"
else
  ffmpeg -y -i "$INPUT_FILE" -ss 00:09:25.000 -to 00:11:03.000 \
    -c:v libx264 -c:a aac -strict experimental \
    "$OUTPUT_DIR/segment_06_des_projets_de_box_et_dérivé_fi.mp4"
fi

# Segment 7: 00:11:00 - 00:12:15
echo "Extraction du segment 7..."
if [ -n "$SRT_FILE" ]; then
  temp_srt="temp_subtitle_7.srt"
  ffmpeg -y -i "$SRT_FILE" -ss 00:11:00.000 -to 00:12:15.000 "$OUTPUT_DIR/$temp_srt"
  ffmpeg -y -i "$INPUT_FILE" -ss 00:10:59.000 -to 00:12:16.000 \
    -vf "subtitles=$OUTPUT_DIR/$temp_srt" \
    -c:v libx264 -c:a aac -strict experimental \
    "$OUTPUT_DIR/segment_07_recommandées_offre_un_service_p.mp4"
else
  ffmpeg -y -i "$INPUT_FILE" -ss 00:10:59.000 -to 00:12:16.000 \
    -c:v libx264 -c:a aac -strict experimental \
    "$OUTPUT_DIR/segment_07_recommandées_offre_un_service_p.mp4"
fi

# Segment 8: 00:15:13 - 00:17:14
echo "Extraction du segment 8..."
if [ -n "$SRT_FILE" ]; then
  temp_srt="temp_subtitle_8.srt"
  ffmpeg -y -i "$SRT_FILE" -ss 00:15:13.000 -to 00:17:14.000 "$OUTPUT_DIR/$temp_srt"
  ffmpeg -y -i "$INPUT_FILE" -ss 00:15:12.000 -to 00:17:15.000 \
    -vf "subtitles=$OUTPUT_DIR/$temp_srt" \
    -c:v libx264 -c:a aac -strict experimental \
    "$OUTPUT_DIR/segment_08_[Musique]_my_venons_d'écouter_m.mp4"
else
  ffmpeg -y -i "$INPUT_FILE" -ss 00:15:12.000 -to 00:17:15.000 \
    -c:v libx264 -c:a aac -strict experimental \
    "$OUTPUT_DIR/segment_08_[Musique]_my_venons_d'écouter_m.mp4"
fi

# Segment 9: 00:17:12 - 00:18:55
echo "Extraction du segment 9..."
if [ -n "$SRT_FILE" ]; then
  temp_srt="temp_subtitle_9.srt"
  ffmpeg -y -i "$SRT_FILE" -ss 00:17:12.000 -to 00:18:55.000 "$OUTPUT_DIR/$temp_srt"
  ffmpeg -y -i "$INPUT_FILE" -ss 00:17:11.000 -to 00:18:56.000 \
    -vf "subtitles=$OUTPUT_DIR/$temp_srt" \
    -c:v libx264 -c:a aac -strict experimental \
    "$OUTPUT_DIR/segment_09_récemment_le_et_qui_est_en_lie.mp4"
else
  ffmpeg -y -i "$INPUT_FILE" -ss 00:17:11.000 -to 00:18:56.000 \
    -c:v libx264 -c:a aac -strict experimental \
    "$OUTPUT_DIR/segment_09_récemment_le_et_qui_est_en_lie.mp4"
fi

# Segment 10: 00:18:52 - 00:20:35
echo "Extraction du segment 10..."
if [ -n "$SRT_FILE" ]; then
  temp_srt="temp_subtitle_10.srt"
  ffmpeg -y -i "$SRT_FILE" -ss 00:18:52.000 -to 00:20:35.000 "$OUTPUT_DIR/$temp_srt"
  ffmpeg -y -i "$INPUT_FILE" -ss 00:18:51.000 -to 00:20:36.000 \
    -vf "subtitles=$OUTPUT_DIR/$temp_srt" \
    -c:v libx264 -c:a aac -strict experimental \
    "$OUTPUT_DIR/segment_10_euh_assurer_la_continuité_euh_d.mp4"
else
  ffmpeg -y -i "$INPUT_FILE" -ss 00:18:51.000 -to 00:20:36.000 \
    -c:v libx264 -c:a aac -strict experimental \
    "$OUTPUT_DIR/segment_10_euh_assurer_la_continuité_euh_d.mp4"
fi

echo "Tous les segments ont été extraits dans $OUTPUT_DIR"
