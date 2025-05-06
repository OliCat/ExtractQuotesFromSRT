import unittest
import sys
import os
from datetime import timedelta
import tempfile

# Ajuster le chemin pour importer le module à tester
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from extract_srt_quotes import (
    format_timecode, 
    format_ffmpeg_time, 
    analyze_sentiment,
    group_subtitles_into_passages
)

# Classe factice pour simuler les sous-titres
class MockSubtitle:
    def __init__(self, content, start, end):
        self.content = content
        self.start = start
        self.end = end

class TestTimecodeFormatting(unittest.TestCase):
    
    def test_format_timecode(self):
        """Tester la fonction format_timecode"""
        # 1h 2m 3s
        td = timedelta(hours=1, minutes=2, seconds=3)
        self.assertEqual(format_timecode(td), "01:02:03")
        
        # 0h 5m 9s
        td = timedelta(minutes=5, seconds=9)
        self.assertEqual(format_timecode(td), "00:05:09")
        
        # 12h 34m 56s
        td = timedelta(hours=12, minutes=34, seconds=56)
        self.assertEqual(format_timecode(td), "12:34:56")
    
    def test_format_ffmpeg_time(self):
        """Tester la fonction format_ffmpeg_time"""
        # 1h 2m 3s 456ms
        td = timedelta(hours=1, minutes=2, seconds=3, milliseconds=456)
        self.assertEqual(format_ffmpeg_time(td), "01:02:03.456")
        
        # 0h 5m 9s 0ms
        td = timedelta(minutes=5, seconds=9)
        self.assertEqual(format_ffmpeg_time(td), "00:05:09.000")

class TestSentimentAnalysis(unittest.TestCase):
    
    def test_basic_sentiment_analysis(self):
        """Tester l'analyse de sentiment basique"""
        # Texte positif
        result = analyze_sentiment("Excellent podcast, vraiment fantastique !")
        self.assertGreater(result['polarity'], 0)
        
        # Texte négatif
        result = analyze_sentiment("Terrible épisode, vraiment horrible.")
        self.assertLess(result['polarity'], 0)
        
        # Texte neutre
        result = analyze_sentiment("Aujourd'hui nous allons parler de l'actualité.")
        self.assertAlmostEqual(result['polarity'], 0, delta=0.3)

class TestGroupSubtitles(unittest.TestCase):
    
    def test_group_subtitles_basic(self):
        """Tester le regroupement basique des sous-titres"""
        # Créer quelques sous-titres consécutifs
        subtitles = [
            MockSubtitle("Premier sous-titre", timedelta(seconds=0), timedelta(seconds=2)),
            MockSubtitle("Deuxième sous-titre", timedelta(seconds=2.2), timedelta(seconds=4)),
            MockSubtitle("Troisième sous-titre", timedelta(seconds=4.5), timedelta(seconds=6)),
            # Grand écart
            MockSubtitle("Quatrième sous-titre", timedelta(seconds=10), timedelta(seconds=12)),
        ]
        
        # Regrouper avec un écart max de 1 seconde (devrait donner 3 passages)
        passages = group_subtitles_into_passages(
            subtitles, 
            max_gap_seconds=1.0,
            min_passage_length=0,  # Ne pas filtrer par longueur pour ce test
            max_passage_length=1000
        )
        
        # On attend 3 passages
        self.assertEqual(len(passages), 3)
        
        # Le premier passage devrait contenir les 2 premiers sous-titres
        self.assertEqual(len(passages[0]['subtitles']), 2)
        self.assertEqual(passages[0]['subtitles'][0].content, "Premier sous-titre")
        self.assertEqual(passages[0]['subtitles'][1].content, "Deuxième sous-titre")
        
        # Le deuxième passage devrait contenir le troisième sous-titre
        self.assertEqual(len(passages[1]['subtitles']), 1)
        self.assertEqual(passages[1]['subtitles'][0].content, "Troisième sous-titre")
        
        # Le troisième passage devrait contenir le quatrième sous-titre
        self.assertEqual(len(passages[2]['subtitles']), 1)
        self.assertEqual(passages[2]['subtitles'][0].content, "Quatrième sous-titre")
    
    def test_group_subtitles_min_length(self):
        """Tester le filtre de longueur minimale des passages"""
        # Créer quelques sous-titres
        subtitles = [
            MockSubtitle("Court", timedelta(seconds=0), timedelta(seconds=2)),
            # Grand écart
            MockSubtitle("Long passage avec beaucoup de mots", timedelta(seconds=5), timedelta(seconds=7)),
        ]
        
        # Regrouper avec une longueur minimale qui exclut le premier sous-titre
        passages = group_subtitles_into_passages(
            subtitles, 
            max_gap_seconds=1.0,
            min_passage_length=10,  # Le premier sous-titre est trop court
            max_passage_length=1000
        )
        
        # On attend 1 passage (le deuxième)
        self.assertEqual(len(passages), 1)
        self.assertEqual(passages[0]['subtitles'][0].content, "Long passage avec beaucoup de mots")

if __name__ == '__main__':
    unittest.main() 