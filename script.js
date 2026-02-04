document.addEventListener('DOMContentLoaded', function() {
    // Éléments DOM
    const form = document.getElementById('reportForm');
    const generateBtn = document.getElementById('generateBtn');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const previewContent = document.getElementById('previewContent');
    const previewActions = document.getElementById('previewActions');
    const downloadBtn = document.getElementById('downloadBtn');
    const regenerateBtn = document.getElementById('regenerateBtn');
    const previewBtn = document.getElementById('previewBtn');
    const progressBar = document.getElementById('progressBar');

    // Charger un exemple
    window.loadExample = function() {
        document.getElementById('subject').value = 'Étude et conception d\'un système intelligent de gestion des barrages';
        document.getElementById('description').value = 'Ce projet vise à développer un système intelligent pour la surveillance et la gestion optimale des barrages. L\'objectif est d\'utiliser l\'intelligence artificielle pour prédire les niveaux d\'eau, optimiser la distribution des ressources hydrauliques et prévenir les risques d\'inondation. Le système intégrera des capteurs IoT, des algorithmes de machine learning et une interface web intuitive pour les gestionnaires.';
        document.getElementById('student_name').value = 'Mohamed Lahri';
        document.getElementById('academic_year').value = '2025/2026';
        document.getElementById('supervisor').value = 'Pr. Ahmed Sami';
        document.getElementById('jury').value = 'Pr. Ali Mayo, Dr. Zaki Fati';
        document.getElementById('framework').value = 'STAR';
    };

    // Soumettre le formulaire
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Afficher le chargement
        loadingOverlay.style.display = 'flex';
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Génération...';
        
        // Collecter les données
        const formData = {
            subject: document.getElementById('subject').value,
            description: document.getElementById('description').value,
            student_name: document.getElementById('student_name').value,
            academic_year: document.getElementById('academic_year').value,
            supervisor: document.getElementById('supervisor').value,
            jury: document.getElementById('jury').value,
            framework: document.getElementById('framework').value
        };
        
        try {
            // Envoyer la requête
            const response = await fetch('/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Afficher l'aperçu
                showPreview(result, formData);
                
                // Sauvegarder les données
                localStorage.setItem('lastReport', JSON.stringify({
                    data: formData,
                    result: result
                }));
            } else {
                alert('Erreur: ' + (result.error || 'Une erreur est survenue'));
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Erreur de connexion au serveur');
        } finally {
            // Masquer le chargement
            loadingOverlay.style.display = 'none';
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="fas fa-magic"></i> Générer le Rapport';
        }
    });

    // Afficher l'aperçu
    function showPreview(result, formData) {
        const previewHTML = `
            <div class="report-preview">
                <div class="report-title">
                    <h3>${formData.subject}</h3>
                    <p><strong>Étudiant:</strong> ${formData.student_name || 'Non spécifié'}</p>
                </div>
                
                <div class="report-section">
                    <h4><i class="fas fa-play-circle"></i> Introduction</h4>
                    <p>${result.preview?.introduction || 'Introduction générée...'}</p>
                </div>
                
                <div class="report-section">
                    <h4><i class="fas fa-cogs"></i> Méthodologie (${formData.framework})</h4>
                    <p>${result.preview?.methodologie || 'Méthodologie générée...'}</p>
                </div>
                
                <div class="report-section">
                    <h4><i class="fas fa-check-circle"></i> Rapport Généré avec Succès</h4>
                    <p>Votre rapport de ${formData.subject} a été généré avec la méthodologie ${formData.framework}. 
                    Le document PDF contient toutes les sections nécessaires pour un PFE professionnel.</p>
                </div>
            </div>
        `;
        
        previewContent.innerHTML = previewHTML;
        previewActions.style.display = 'block';
        
        // Mettre à jour le lien de téléchargement
        if (result.pdf_url) {
            downloadBtn.href = result.pdf_url;
            downloadBtn.download = result.filename;
        }
        
        // Faire défiler jusqu'à l'aperçu
        previewContent.scrollIntoView({ behavior: 'smooth' });
    }

    // Régénérer le rapport
    regenerateBtn.addEventListener('click', async function() {
        const lastReport = localStorage.getItem('lastReport');
        if (!lastReport) {
            alert('Aucun rapport précédent trouvé');
            return;
        }
        
        const { data } = JSON.parse(lastReport);
        
        loadingOverlay.style.display = 'flex';
        regenerateBtn.disabled = true;
        regenerateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Régénération...';
        
        try {
            const response = await fetch('/regenerate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                showPreview(result, data);
            } else {
                alert('Erreur lors de la régénération');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Erreur de connexion');
        } finally {
            loadingOverlay.style.display = 'none';
            regenerateBtn.disabled = false;
            regenerateBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Régénérer';
        }
    });

    // Prévisualiser en plein écran
    previewBtn.addEventListener('click', function() {
        const lastReport = localStorage.getItem('lastReport');
        if (lastReport) {
            window.open('/preview', '_blank');
        } else {
            alert('Générez d\'abord un rapport');
        }
    });

    // Animation de progression
    function animateProgress() {
        let width = 0;
        const interval = setInterval(() => {
            if (width >= 100) {
                clearInterval(interval);
            } else {
                width++;
                progressBar.style.width = width + '%';
            }
        }, 50);
    }

    // Démarrer l'animation quand le chargement commence
    generateBtn.addEventListener('click', animateProgress);

    // Charger l'exemple au démarrage
    loadExample();
});


