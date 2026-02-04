"""
app.py - Générateur Intelligent de Rapports PFE v2.0
Système professionnel de génération automatique par IA
ENSA Oujda - 2025
"""

import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from flask import Flask, render_template, request, jsonify, send_file, session
from dotenv import load_dotenv
import secrets
import re

# Client Groq AI
try:
    from groq import Groq
except ImportError:
    Groq = None
    logging.error("❌ Module 'groq' non installé. Exécutez: pip install groq")

# ReportLab pour PDF professionnel
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, KeepTogether, Image, Frame
)
from reportlab.lib.units import inch, cm, mm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas

# ==================== CONFIGURATION ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

STATIC_FOLDER = 'static'
OUTPUT_FOLDER = os.path.join(STATIC_FOLDER, 'rapports')
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
groq_client = None

DEFAULT_MODEL = "llama-3.3-70b-versatile"
MAX_RETRIES = 3
RETRY_DELAY = 3  # secondes


def get_groq_client():
    """Initialise et retourne le client Groq avec vérification"""
    global groq_client
    if groq_client is None and GROQ_API_KEY:
        try:
            groq_client = Groq(api_key=GROQ_API_KEY)
            logger.info("✅ Client Groq initialisé")
        except Exception as e:
            logger.error(f"❌ Erreur init Groq: {e}")
    return groq_client


# ==================== MOTEUR IA ROBUSTE ====================

def generate_academic_content(prompt: str, section_name: str = "contenu", 
                             is_json: bool = False) -> Any:
    """
    Génère du contenu académique via Groq avec retry automatique.
    
    Args:
        prompt: Le prompt de génération
        section_name: Nom de la section (pour logs)
        is_json: Force JSON en sortie
    
    Returns:
        Contenu généré (dict si JSON, str sinon)
    """
    client = get_groq_client()
    if not client:
        error_msg = "⚠️ Client Groq non disponible. Vérifiez GROQ_API_KEY dans .env"
        logger.error(error_msg)
        return {} if is_json else error_msg
    
    system_prompt = """Tu es un expert académique de l'ENSA Oujda spécialisé en rédaction de rapports PFE.

🎯 RÈGLES ABSOLUES DE RÉDACTION:

1. STYLE ACADÉMIQUE STRICT
   ✓ Langage soutenu et scientifique
   ✓ Phrases complexes et bien structurées
   ✓ Vocabulaire technique précis du domaine
   ✓ Ton formel et objectif

2. INTERDICTION TOTALE DES LISTES
   ✗ JAMAIS de tirets (-)
   ✗ JAMAIS de puces (•)
   ✗ JAMAIS de numérotations (1., 2., 3.)
   ✓ TOUJOURS des paragraphes narratifs fluides

3. CONSTRUCTION NARRATIVE
   ✓ Connecteurs logiques variés: "Par ailleurs", "En outre", "De surcroît", "Ainsi", "Toutefois", "Néanmoins"
   ✓ Un paragraphe = une idée complète (5-7 phrases minimum)
   ✓ Transitions naturelles entre paragraphes
   ✓ Progression logique du raisonnement

4. DÉVELOPPEMENT TECHNIQUE
   ✓ Base-toi UNIQUEMENT sur les informations fournies
   ✗ N'invente JAMAIS de détails techniques non fournis
   ✓ Si info manquante: reste général et théorique
   ✓ Explique chaque concept introduit

5. STRUCTURE DES PARAGRAPHES
   - Phrase d'introduction du concept
   - Développement technique avec exemples
   - Implications ou conséquences
   - Transition vers idée suivante

6. LONGUEUR ET DENSITÉ
   - Minimum 6 paragraphes substantiels
   - Chaque paragraphe: 5-7 phrases
   - Contenu dense et informatif
   - Éviter les répétitions

EXEMPLE DE PARAGRAPHE ACADÉMIQUE CORRECT:
"La conception hydraulique des barrages nécessite une analyse approfondie des caractéristiques hydrologiques du bassin versant. Dans cette optique, les ingénieurs procèdent à l'étude des débits de crue historiques afin d'établir les courbes de débits-fréquences permettant de dimensionner l'évacuateur de crues. Par ailleurs, la modélisation hydrologique intègre les données pluviométriques sur plusieurs décennies pour estimer les apports en eau et les périodes de remplissage optimales. En outre, l'analyse de la bathymétrie du site permet de déterminer la capacité de stockage en fonction des différentes cotes de retenue, information cruciale pour l'optimisation du volume utile du réservoir."
"""

    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"🔄 Génération [{section_name}] - Tentative {attempt + 1}/{MAX_RETRIES}")
            
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                model=DEFAULT_MODEL,
                temperature=0.4,  # Balance créativité/cohérence
                max_tokens=4096,
                response_format={"type": "json_object"} if is_json else None
            )
            
            content = response.choices[0].message.content
            
            if is_json:
                parsed = json.loads(content)
                logger.info(f"✅ [{section_name}] JSON généré")
                return parsed
            
            # Nettoyage du texte
            content = clean_text(content)
            
            # Validation longueur minimale
            if len(content.strip()) < 200:
                logger.warning(f"⚠️ [{section_name}] Contenu trop court, retry...")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
            
            logger.info(f"✅ [{section_name}] Généré ({len(content)} chars)")
            return content
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ [{section_name}] JSON invalide: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                return {} if is_json else f"Erreur JSON pour {section_name}"
                
        except Exception as e:
            logger.error(f"❌ [{section_name}] Erreur: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                return {} if is_json else f"Erreur de génération pour {section_name}. Veuillez réessayer."
    
    # Fallback après tous les retries
    return {} if is_json else f"Impossible de générer {section_name} après {MAX_RETRIES} tentatives."


def clean_text(text: str) -> str:
    """Nettoie le texte des artefacts markdown et normalise"""
    # Supprimer listes à puces/numéros
    text = re.sub(r'^[\s]*[-•*]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[\s]*\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # Supprimer markdown
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # bold
    text = re.sub(r'\*(.+?)\*', r'\1', text)      # italic
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)  # code blocks
    text = re.sub(r'`(.+?)`', r'\1', text)
    
    # Normaliser espaces
    text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 retours ligne
    text = re.sub(r' {2,}', ' ', text)      # Max 1 espace
    
    return text.strip()


# ==================== ANALYSE & STRUCTURE ====================

def analyze_project(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyse intelligente du projet et génération structure adaptée.
    
    Returns:
        {department, filiere, order_id, structure: [chapitres]}
    """
    analysis_prompt = f"""Analyse ce projet PFE et génère une structure professionnelle adaptée:

📋 DONNÉES PROJET:
- Sujet: {user_data.get('subject', 'Non spécifié')}
- Filière: {user_data.get('student_filiere', 'Non spécifiée')}
- Contexte: {user_data.get('context', '')}
- Technologies: {user_data.get('technologies', '')}
- Objectifs: {user_data.get('objectives', '')}
- Domaine: {user_data.get('domain', '')}

🎯 TÂCHES:

1. IDENTIFICATION DU DÉPARTEMENT
   Déduis le département ENSA Oujda exact parmi:
   - Génie Informatique
   - Génie Civil et Hydraulique
   - Génie Industriel et Logistique
   - Génie Électrique et Télécommunications
   - Génie Mécanique
   Base-toi sur le sujet et les technologies.

2. FILIÈRE PRÉCISE
   Confirme ou corrige la filière (ex: "Génie Hydraulique", "Ingénierie Logicielle")

3. NUMÉRO D'ORDRE
   Format: ENSA-OUD-{datetime.now().year}-XXX
   (XXX = numéro aléatoire 3 chiffres)

4. STRUCTURE INTELLIGENTE (3 chapitres)
   Adapte au domaine:
   
   DOMAINES TECHNIQUES (Info, Élec, Indus):
   - Chapitre 1: Contexte et état de l'art / Étude théorique
   - Chapitre 2: Analyse des besoins et conception
   - Chapitre 3: Réalisation et résultats
   
   DOMAINES SCIENTIFIQUES (Civil, Méca, Hydro):
   - Chapitre 1: État de l'art et contexte
   - Chapitre 2: Étude et dimensionnement
   - Chapitre 3: Modélisation et résultats
   
   Titres SPÉCIFIQUES au projet, pas génériques!

📤 RÉPONSE JSON:
{{
    "department": "Département exact",
    "filiere": "Filière précise",
    "order_id": "ENSA-OUD-YYYY-XXX",
    "structure": [
        {{"id": "chapitre1", "title": "Titre spécifique chapitre 1", "keywords": ["mot-clé1", "mot-clé2"]}},
        {{"id": "chapitre2", "title": "Titre spécifique chapitre 2", "keywords": ["mot-clé1", "mot-clé2"]}},
        {{"id": "chapitre3", "title": "Titre spécifique chapitre 3", "keywords": ["mot-clé1", "mot-clé2"]}}
    ]
}}"""

    result = generate_academic_content(analysis_prompt, "Analyse Structure", is_json=True)
    
    # Valeurs par défaut robustes
    if not result or not isinstance(result, dict):
        logger.warning("⚠️ Structure par défaut utilisée")
        return {
            "department": "Génie Informatique",
            "filiere": user_data.get('student_filiere', 'Cycle Ingénieur'),
            "order_id": f"ENSA-OUD-{datetime.now().year}-{secrets.randbelow(900) + 100:03d}",
            "structure": [
                {"id": "chapitre1", "title": "Contexte général et état de l'art", "keywords": []},
                {"id": "chapitre2", "title": "Analyse et conception", "keywords": []},
                {"id": "chapitre3", "title": "Réalisation et résultats", "keywords": []}
            ]
        }
    
    # Assurer order_id unique
    if 'order_id' not in result:
        result['order_id'] = f"ENSA-OUD-{datetime.now().year}-{secrets.randbelow(900) + 100:03d}"
    
    return result


# ==================== GÉNÉRATION SECTIONS ====================

def generate_all_sections(user_data: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, str]:
    """
    Génère toutes les sections du rapport avec gestion d'erreurs robuste.
    
    Returns:
        Dict[section_id, content]
    """
    sections = {}
    structure = metadata.get('structure', [])
    
    # Construction contexte enrichi
    context_parts = []
    if user_data.get('subject'):
        context_parts.append(f"**Sujet:** {user_data['subject']}")
    if user_data.get('student_filiere'):
        context_parts.append(f"**Filière:** {user_data['student_filiere']}")
    if user_data.get('context'):
        context_parts.append(f"**Contexte:** {user_data['context']}")
    if user_data.get('objectives'):
        context_parts.append(f"**Objectifs:** {user_data['objectives']}")
    if user_data.get('technologies'):
        context_parts.append(f"**Technologies:** {user_data['technologies']}")
    if user_data.get('methodology'):
        context_parts.append(f"**Méthodologie:** {user_data['methodology']}")
    if user_data.get('results'):
        context_parts.append(f"**Résultats attendus:** {user_data['results']}")
    
    project_context = "\n".join(context_parts) if context_parts else "Projet de fin d'études."
    
    # ========== 1. REMERCIEMENTS ==========
    logger.info("📝 Génération: Remerciements")
    remerciements_prompt = f"""Rédige des REMERCIEMENTS formels et chaleureux pour un rapport PFE ENSA Oujda.

**Contexte:**
- Étudiant: {user_data.get('student_name', 'l\'étudiant')}
- Encadrant: {user_data.get('supervisor', 'l\'encadrant académique')}
- Entreprise: {user_data.get('company', '') or 'ENSA Oujda'}
- Jury: {user_data.get('jury', 'les membres du jury')}

**Structure attendue (paragraphes narratifs):**
1. Remerciement sincère à l'encadrant pour guidance et soutien
2. Gratitude envers l'équipe pédagogique et département
3. Remerciement à l'entreprise/organisme d'accueil (si applicable)
4. Reconnaissance envers les membres du jury
5. Remerciement familial et amical

**Consignes:**
- 4-5 paragraphes fluides et personnalisés
- Ton reconnaissant mais professionnel
- Transitions naturelles entre remerciements
- Aucune liste, tout en prose"""

    sections['remerciements'] = generate_academic_content(
        remerciements_prompt, 
        "Remerciements"
    )
    
    # ========== 2. INTRODUCTION GÉNÉRALE ==========
    logger.info("📝 Génération: Introduction Générale")
    intro_prompt = f"""Rédige une INTRODUCTION GÉNÉRALE académique pour un rapport PFE.

{project_context}

**Département:** {metadata.get('department', 'ENSA Oujda')}

**L'introduction doit développer (en paragraphes narratifs):**

1. **Contexte général du domaine**
   - Importance du domaine d'étude
   - État actuel des connaissances
   - Tendances et enjeux

2. **Problématique identifiée**
   - Présentation du problème technique/scientifique
   - Lacunes ou besoins identifiés
   - Justification de l'intérêt du projet

3. **Objectifs du projet**
   - Objectifs généraux et spécifiques
   - Résultats attendus
   - Contributions envisagées

4. **Intérêt et enjeux**
   - Apport technique/scientifique
   - Impact pratique ou industriel
   - Pertinence académique

5. **Annonce du plan**
   - Structure du rapport
   - Logique de présentation

**Consignes:**
- 6-7 paragraphes denses
- Chaque paragraphe: 5-7 phrases
- Style académique soutenu
- Progression logique
- Aucune liste"""

    sections['introduction'] = generate_academic_content(
        intro_prompt,
        "Introduction"
    )
    
    # ========== 3. CHAPITRES ==========
    for i, chap in enumerate(structure, 1):
        logger.info(f"📝 Génération: Chapitre {i} - {chap['title']}")
        
        keywords_str = ", ".join(chap.get('keywords', [])) if chap.get('keywords') else "concepts techniques"
        
        chapitre_prompt = f"""Rédige le CONTENU COMPLET du chapitre suivant pour un rapport PFE:

**CHAPITRE {i}: {chap['title']}**

{project_context}

**Mots-clés à intégrer:** {keywords_str}

**Consignes selon la nature du chapitre:**

Si CHAPITRE 1 (État de l'art/Contexte):
- Revue de littérature approfondie
- État des connaissances actuelles
- Technologies/méthodes existantes
- Positionnement du projet

Si CHAPITRE 2 (Analyse/Conception):
- Analyse des besoins ou étude préliminaire
- Choix méthodologiques justifiés
- Architecture ou modèle proposé
- Spécifications détaillées

Si CHAPITRE 3 (Réalisation/Résultats):
- Description de la mise en œuvre
- Défis techniques rencontrés
- Solutions apportées
- Résultats obtenus et validation

**Exigences:**
- 8-10 paragraphes substantiels minimum
- Chaque paragraphe: 6-8 phrases
- Développement technique dense
- Cohérence et progression logique
- Utilise UNIQUEMENT les infos fournies
- Si infos manquantes: reste théorique et général
- Aucune liste, tout en prose narrative
- Sous-titres possibles avec ## (max 3)

**Style:**
Académique, technique, formel. Connecteurs variés."""

        sections[chap['id']] = generate_academic_content(
            chapitre_prompt,
            f"Chapitre {i}"
        )
    
    # ========== 4. CONCLUSION GÉNÉRALE ==========
    logger.info("📝 Génération: Conclusion Générale")
    conclusion_prompt = f"""Rédige une CONCLUSION GÉNÉRALE pour un rapport PFE.

{project_context}

**La conclusion doit aborder (en paragraphes fluides):**

1. **Synthèse des réalisations**
   - Récapitulatif des travaux effectués
   - Objectifs atteints
   - Résultats marquants

2. **Bilan des compétences**
   - Compétences techniques acquises
   - Savoir-faire développés
   - Méthodes maîtrisées

3. **Difficultés et solutions**
   - Défis rencontrés
   - Solutions apportées
   - Leçons tirées

4. **Apport personnel**
   - Enrichissement professionnel
   - Expérience humaine
   - Vision du métier d'ingénieur

5. **Perspectives et évolutions**
   - Améliorations possibles
   - Extensions envisageables
   - Recherches futures
   - Applications industrielles

**Consignes:**
- 5-6 paragraphes narratifs
- Ton réflexif et prospectif
- Ouverture vers l'avenir
- Aucune liste"""

    sections['conclusion'] = generate_academic_content(
        conclusion_prompt,
        "Conclusion"
    )
    
    # ========== 5. BIBLIOGRAPHIE ==========
    logger.info("📝 Génération: Bibliographie")
    biblio_prompt = f"""Génère une BIBLIOGRAPHIE et WEBOGRAPHIE au format IEEE.

**Sujet:** {user_data.get('subject')}
**Technologies:** {user_data.get('technologies', '')}
**Domaine:** {metadata.get('department', '')}

**Contenu attendu:**

1. **Ouvrages de référence (3-4)**
   - Livres académiques du domaine
   - Manuels techniques
   Format: [X] Auteur, *Titre du livre*, Éditeur, Ville, Année.

2. **Articles scientifiques (2-3)**
   - Publications de conférences
   - Articles de revues
   Format: [X] Auteur, "Titre article", *Nom revue*, vol. X, no. Y, pp. Z, Année.

3. **Ressources web (3-4)**
   - Documentation officielle
   - Sites techniques de référence
   - Standards et normes
   Format: [X] "Titre", URL, consulté le JJ/MM/AAAA.

**Consignes:**
- Références réalistes et pertinentes au domaine
- Numérotation continue [1], [2], etc.
- Présentation en paragraphes avec numéros
- Format IEEE standard strict"""

    sections['biblio'] = generate_academic_content(
        biblio_prompt,
        "Bibliographie"
    )
    
    return sections


# ==================== PDF ENGINE PROFESSIONNEL ====================

class PDFCanvas(canvas.Canvas):
    """Canvas avec numérotation automatique et pieds de page"""
    
    def __init__(self, *args, **kwargs):
        self.student_name = kwargs.pop('student_name', 'Étudiant')
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_footer(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_footer(self, total_pages):
        """Pied de page professionnel"""
        page = self._pageNumber
        if page > 1:  # Pas de footer sur page de garde
            self.saveState()
            # Ligne de séparation
            self.setStrokeColor(colors.HexColor('#002147'))
            self.setLineWidth(0.5)
            self.line(72, 50, A4[0]-72, 50)
            # Texte footer
            self.setFont("Times-Roman", 9)
            self.setFillColor(colors.grey)
            self.drawString(72, 35, f"ENSA Oujda - Rapport de PFE - {self.student_name}")
            self.drawRightString(A4[0]-72, 35, f"Page {page - 1}")
            self.restoreState()


def create_professional_pdf(user_data: Dict[str, Any], sections: Dict[str, str], 
                           metadata: Dict[str, Any]) -> str:
    """
    Génère un PDF académique professionnel complet.
    
    Returns:
        Nom du fichier PDF
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"Rapport_PFE_{timestamp}.pdf"
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    
    # Document
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=2.5*cm,
        leftMargin=2.5*cm,
        topMargin=2.5*cm,
        bottomMargin=3.5*cm
    )
    
    # ==================== STYLES ====================
    
    styles = getSampleStyleSheet()
    
    # Styles page de garde
    st_royaume = ParagraphStyle(
        'Royaume',
        fontSize=11,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        textColor=colors.HexColor('#8B0000'),
        spaceAfter=3
    )
    
    st_univ = ParagraphStyle(
        'Univ',
        fontSize=11,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        textColor=colors.HexColor('#002147'),
        spaceAfter=4
    )
    
    st_meta = ParagraphStyle(
        'Meta',
        fontSize=10,
        fontName='Helvetica',
        spaceAfter=4,
        textColor=colors.HexColor('#333333')
    )
    
    st_doc_type = ParagraphStyle(
        'DocType',
        fontSize=12,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        letterSpacing=1.5,
        spaceAfter=20,
        textColor=colors.HexColor('#002147')
    )
    
    st_title = ParagraphStyle(
        'Title',
        fontSize=16,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        leading=20,
        spaceBefore=10,
        spaceAfter=15,
        textColor=colors.HexColor('#002147'),
        borderWidth=2,
        borderColor=colors.HexColor('#002147'),
        borderPadding=12
    )
    
    st_subtitle = ParagraphStyle(
        'SubTitle',
        fontSize=11,
        fontName='Times-Italic',
        alignment=TA_CENTER,
        spaceAfter=25,
        textColor=colors.grey
    )
    
    st_label = ParagraphStyle(
        'Label',
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=colors.black
    )
    
    # Styles contenu
    st_section_title = ParagraphStyle(
        'SectionTitle',
        fontSize=14,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#002147'),
        spaceBefore=25,
        spaceAfter=15,
        alignment=TA_CENTER,
        borderWidth=1,
        borderColor=colors.HexColor('#002147'),
        borderPadding=8
    )
    
    st_chap_num = ParagraphStyle(
        'ChapterNum',
        fontSize=13,
        fontName='Helvetica-Bold',
        textColor=colors.grey,
        spaceBefore=25,
        spaceAfter=8
    )
    
    st_chap_title = ParagraphStyle(
        'ChapterTitle',
        fontSize=16,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#002147'),
        spaceAfter=20,
        leading=20
    )
    
    st_body = ParagraphStyle(
        'Body',
        fontSize=11,
        fontName='Times-Roman',
        leading=17,
        alignment=TA_JUSTIFY,
        firstLineIndent=18,
        spaceAfter=11,
        textColor=colors.black
    )
    
    st_subsection = ParagraphStyle(
        'SubSection',
        fontSize=12,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1a5490'),
        spaceBefore=15,
        spaceAfter=10
    )
    
    st_toc = ParagraphStyle(
        'TOC',
        fontSize=11,
        fontName='Helvetica',
        leading=16,
        spaceAfter=6
    )
    
    # ==================== CONTENU PDF ====================
    
    story = []
    structure = metadata.get('structure', [])
    
    # ========== PAGE DE GARDE ==========
    
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph("ROYAUME DU MAROC", st_royaume))
    story.append(Paragraph("Université Mohammed Premier", st_univ))
    story.append(Paragraph("École Nationale des Sciences Appliquées - Oujda", st_univ))
    
    story.append(Spacer(1, 0.4*cm))
    
    # Ligne décorative
    line = Table([['']], colWidths=[15*cm])
    line.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 2, colors.HexColor('#002147'))
    ]))
    story.append(line)
    
    story.append(Spacer(1, 0.5*cm))
    
    # Métadonnées
    story.append(Paragraph(
        f"<b>Département :</b> {metadata.get('department', 'N/A')}",
        st_meta
    ))
    story.append(Paragraph(
        f"<b>Filière :</b> {metadata.get('filiere', user_data.get('student_filiere', 'N/A'))}",
        st_meta
    ))
    story.append(Paragraph(
        f"<b>N° d'ordre :</b> {metadata.get('order_id', 'N/A')}",
        st_meta
    ))
    
    story.append(Spacer(1, 1.2*cm))
    
    story.append(Paragraph("MÉMOIRE DE PROJET DE FIN D'ÉTUDE", st_doc_type))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(user_data['subject'].upper(), st_title))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "Soutenu en vue de l'obtention du<br/>Diplôme d'Ingénieur d'État",
        st_subtitle
    ))
    
    story.append(Spacer(1, 1*cm))
    
    # Table intervenants
    interv_data = [
        [Paragraph("<b>Réalisé par :</b>", st_label),
         Paragraph(user_data.get('student_name', 'Étudiant'), st_body)]
    ]
    
    if user_data.get('supervisor'):
        interv_data.append([
            Paragraph("<b>Encadrant(s) :</b>", st_label),
            Paragraph(user_data['supervisor'], st_body)
        ])
    
    if user_data.get('jury'):
        interv_data.append([
            Paragraph("<b>Membres du Jury :</b>", st_label),
            Paragraph(user_data['jury'], st_body)
        ])
    
    t_interv = Table(interv_data, colWidths=[5*cm, 10*cm])
    t_interv.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_interv)
    
    story.append(Spacer(1, 1.3*cm))
    
    # Année
    year = user_data.get('academic_year', f'{datetime.now().year-1}/{datetime.now().year}')
    story.append(Paragraph(
        f"<b>Année Universitaire : {year}</b>",
        ParagraphStyle('Year', parent=st_meta, alignment=TA_CENTER, fontSize=11)
    ))
    
    story.append(PageBreak())
    
    # ========== REMERCIEMENTS ==========
    
    story.append(Paragraph("REMERCIEMENTS", st_section_title))
    story.append(Spacer(1, 0.4*cm))
    
    for para in sections.get('remerciements', '').split('\n\n'):
        if para.strip():
            story.append(Paragraph(para.strip(), st_body))
    
    story.append(PageBreak())
    
    # ========== TABLE DES MATIÈRES ==========
    
    story.append(Paragraph("TABLE DES MATIÈRES", st_section_title))
    story.append(Spacer(1, 0.6*cm))
    
    toc_items = ["I. Introduction Générale"]
    for i, chap in enumerate(structure, 1):
        toc_items.append(f"{i+1}. Chapitre {i} : {chap['title']}")
    toc_items.extend(["Conclusion Générale", "Bibliographie & Webographie"])
    
    for item in toc_items:
        story.append(Paragraph(f"<b>{item}</b>", st_toc))
    
    story.append(PageBreak())
    
    # ========== INTRODUCTION ==========
    
    story.append(Paragraph("INTRODUCTION GÉNÉRALE", st_section_title))
    story.append(Spacer(1, 0.4*cm))
    
    for para in sections.get('introduction', '').split('\n\n'):
        para = para.strip()
        if not para:
            continue
        if para.startswith('##'):
            story.append(Paragraph(para.replace('##', '').strip(), st_subsection))
        else:
            story.append(Paragraph(para, st_body))
    
    story.append(PageBreak())
    
    # ========== CHAPITRES ==========
    
    for i, chap in enumerate(structure, 1):
        story.append(Paragraph(f"CHAPITRE {i}", st_chap_num))
        story.append(Paragraph(chap['title'].upper(), st_chap_title))
        
        chap_line = Table([['']], colWidths=[15*cm])
        chap_line.setStyle(TableStyle([
            ('LINEBELOW', (0,0), (-1,-1), 1.5, colors.HexColor('#002147'))
        ]))
        story.append(chap_line)
        story.append(Spacer(1, 0.4*cm))
        
        content = sections.get(chap['id'], 'Contenu non disponible.')
        for para in content.split('\n\n'):
            para = para.strip()
            if not para:
                continue
            if para.startswith('##'):
                story.append(Paragraph(para.replace('##', '').strip(), st_subsection))
            else:
                story.append(Paragraph(para, st_body))
        
        story.append(PageBreak())
    
    # ========== CONCLUSION ==========
    
    story.append(Paragraph("CONCLUSION GÉNÉRALE", st_section_title))
    story.append(Spacer(1, 0.4*cm))
    
    for para in sections.get('conclusion', '').split('\n\n'):
        para = para.strip()
        if not para:
            continue
        if para.startswith('##'):
            story.append(Paragraph(para.replace('##', '').strip(), st_subsection))
        else:
            story.append(Paragraph(para, st_body))
    
    story.append(PageBreak())
    
    # ========== BIBLIOGRAPHIE ==========
    
    story.append(Paragraph("BIBLIOGRAPHIE & WEBOGRAPHIE", st_section_title))
    story.append(Spacer(1, 0.4*cm))
    
    for para in sections.get('biblio', '').split('\n\n'):
        if para.strip():
            story.append(Paragraph(para.strip(), st_body))
    
    # ========== BUILD ==========
    
    doc.build(
        story,
        canvasmaker=lambda *args, **kwargs: PDFCanvas(
            *args, 
            student_name=user_data.get('student_name', 'Étudiant'),
            **kwargs
        )
    )
    
    logger.info(f"✅ PDF créé: {filename}")
    return filename


# ==================== ROUTES ====================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
    """Endpoint principal de génération"""
    try:
        data = request.json
        logger.info(f"🚀 Nouvelle génération: {data.get('subject', 'Sans titre')}")
        
        # Validation
        required = ['subject', 'student_name', 'supervisor']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Champ requis: {field}'}), 400
        
        # ÉTAPE 1: Analyse
        logger.info("📊 Analyse du projet...")
        metadata = analyze_project(data)
        
        # ÉTAPE 2: Génération sections
        logger.info("✍️ Génération du contenu...")
        sections = generate_all_sections(data, metadata)
        
        # ÉTAPE 3: PDF
        logger.info("📄 Création du PDF...")
        pdf_filename = create_professional_pdf(data, sections, metadata)
        
        return jsonify({
            'success': True,
            'pdf_url': f'/static/rapports/{pdf_filename}',
            'filename': pdf_filename,
            'metadata': metadata
        })
    
    except Exception as e:
        logger.error(f"❌ Erreur: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/download/<filename>')
def download(filename):
    """Téléchargement PDF"""
    try:
        filepath = os.path.join(OUTPUT_FOLDER, filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'Fichier introuvable'}), 404
        return send_file(filepath, mimetype='application/pdf', as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== MAIN ====================

if __name__ == '__main__':
    if not GROQ_API_KEY:
        logger.warning("=" * 70)
        logger.warning("⚠️  GROQ_API_KEY NON CONFIGURÉE!")
        logger.warning("   1. Créez un fichier .env")
        logger.warning("   2. Ajoutez: GROQ_API_KEY=votre_clé")
        logger.warning("   3. Obtenez une clé sur: https://console.groq.com")
        logger.warning("=" * 70)
    else:
        logger.info("✅ Groq API configurée")
    
    logger.info(f"📂 Rapports: {OUTPUT_FOLDER}")
    logger.info(f"🌐 Serveur: http://127.0.0.1:5000")
    logger.info("=" * 70)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
