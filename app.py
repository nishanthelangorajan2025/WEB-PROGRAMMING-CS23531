import json
import os
import sqlite3
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

DB_FILE = "medixai.db"
PORT = 8000

# ---------------------------------------------------------------------------
# EXPANDED CLINICAL KNOWLEDGE BASE (80 Diseases, 200+ Symptoms)
# ---------------------------------------------------------------------------
INITIAL_KB = {
    # --- RESPIRATORY & PULMONOLOGY ---
    "Common Cold": {
        "category": "Respiratory", "severity": "Low", "emergency": False,
        "description": "A mild viral upper respiratory infection affecting the nose and throat.",
        "symptoms": {"runny_nose": 10, "sneezing": 9, "dry_cough": 8, "sore_throat": 7, "low_grade_fever": 5, "headache": 4},
        "required": ["runny_nose", "sneezing"],
        "treatment": "Rest, hydration, saline nasal spray, steam inhalation, and supportive care.",
        "precaution": "Wash hands frequently, cover mouth when coughing, and stay hydrated."
    },
    "Influenza": {
        "category": "Respiratory", "severity": "Moderate", "emergency": False,
        "description": "An acute viral respiratory infection marked by rapid-onset high fever and myalgia.",
        "symptoms": {"high_fever": 10, "body_pain": 9, "fatigue": 8, "dry_cough": 7, "chills": 8, "headache": 6, "sore_throat": 5},
        "required": ["high_fever", "body_pain", "fatigue"],
        "treatment": "Bed rest, oral fluids, paracetamol for fever relief, and clinical evaluation.",
        "precaution": "Isolate during fever spike and watch for secondary respiratory complications."
    },
    "COVID-19": {
        "category": "Respiratory", "severity": "Moderate", "emergency": False,
        "description": "A contagious coronavirus infection with systemic and respiratory manifestations.",
        "symptoms": {"fever": 8, "dry_cough": 8, "loss_of_smell": 10, "loss_of_taste": 10, "fatigue": 7, "shortness_of_breath": 9, "headache": 5},
        "required": ["fever", "dry_cough"],
        "treatment": "Supportive hydration, prone resting, antipyretics, and oxygen saturation monitoring.",
        "precaution": "Strict isolation; seek immediate emergency review if SpO2 drops below 94%."
    },
    "Pneumonia": {
        "category": "Respiratory", "severity": "Serious", "emergency": True,
        "description": "Infection inflaming air sacs in one or both lungs, which may fill with fluid or purulent material.",
        "symptoms": {"fever": 8, "shortness_of_breath": 10, "chest_pain": 9, "wet_cough": 9, "fatigue": 6, "rapid_breathing": 9, "chills": 7},
        "required": ["fever", "shortness_of_breath"],
        "treatment": "Prompt medical evaluation, sputum culture, targeted antibiotics or antivirals, and supplemental oxygen.",
        "precaution": "Urgent hospitalization flag; do not delay clinical consultation."
    },
    "Asthma": {
        "category": "Respiratory", "severity": "Moderate", "emergency": False,
        "description": "A chronic inflammatory disorder causing reversible bronchial hyperresponsiveness and airflow obstruction.",
        "symptoms": {"wheezing": 10, "shortness_of_breath": 10, "chest_tightness": 8, "cough": 7, "night_symptoms": 8, "trigger_exposure": 6},
        "required": ["wheezing", "shortness_of_breath"],
        "treatment": "Inhaled short-acting beta-agonists (SABA), trigger avoidance, and maintenance corticosteroid inhalers.",
        "precaution": "Keep rescue inhaler readily accessible and avoid smoke or allergen triggers."
    },
    "Acute Bronchitis": {
        "category": "Respiratory", "severity": "Moderate", "emergency": False,
        "description": "Acute inflammation of the tracheobronchial tree, commonly following an upper respiratory viral syndrome.",
        "symptoms": {"persistent_cough": 10, "wet_cough": 9, "chest_tightness": 7, "low_grade_fever": 6, "fatigue": 6, "mucus": 8},
        "required": ["persistent_cough"],
        "treatment": "Expectorants, hydration, humidified air, and supportive rest.",
        "precaution": "Evaluate for pneumonia if high fever or bloody sputum develops."
    },
    "Chronic Obstructive Pulmonary Disease": {
        "category": "Respiratory", "severity": "Serious", "emergency": True,
        "description": "Progressive, irreversible lung condition causing chronic airflow limitation (emphysema/chronic bronchitis).",
        "symptoms": {"chronic_cough": 10, "shortness_of_breath": 10, "wheezing": 8, "excess_mucus": 9, "fatigue": 7, "cyanosis": 9},
        "required": ["chronic_cough", "shortness_of_breath"],
        "treatment": "Bronchodilators, pulmonary rehabilitation, supplemental oxygen, and clinical monitoring.",
        "precaution": "Immediate smoking cessation; monitor for sudden hypercapnic exacerbations."
    },
    "Pulmonary Embolism": {
        "category": "Respiratory", "severity": "Emergency", "emergency": True,
        "description": "Sudden blockage in a pulmonary artery caused by a detached thromboembolism from deep veins.",
        "symptoms": {"sudden_shortness_of_breath": 10, "sharp_chest_pain": 10, "coughing_blood": 9, "rapid_heart_rate": 8, "dizziness": 8, "leg_swelling": 7},
        "required": ["sudden_shortness_of_breath", "sharp_chest_pain"],
        "treatment": "Immediate emergency room activation, intravenous anticoagulation, or thrombolytic therapy.",
        "precaution": "High fatality risk without emergency intervention; do not ambulate patient."
    },
    "Sinusitis": {
        "category": "Respiratory", "severity": "Low", "emergency": False,
        "description": "Inflammation of paranasal mucous membranes causing localized pressure and facial fullness.",
        "symptoms": {"sinus_pain": 10, "nasal_congestion": 9, "runny_nose": 8, "headache": 7, "post_nasal_drip": 7, "fever": 5},
        "required": ["sinus_pain", "nasal_congestion"],
        "treatment": "Nasal decongestants, warm compresses, saline irrigation, and pain relief.",
        "precaution": "Seek medical review if periorbital swelling or double vision occurs."
    },
    "Allergic Rhinitis": {
        "category": "Respiratory", "severity": "Low", "emergency": False,
        "description": "IgE-mediated inflammatory response of the nasal mucosa to airborne environmental allergens.",
        "symptoms": {"sneezing": 10, "runny_nose": 9, "itchy_eyes": 9, "nasal_congestion": 7, "watery_eyes": 8, "no_fever": 6},
        "required": ["sneezing", "runny_nose"],
        "treatment": "Oral antihistamines, intranasal corticosteroid sprays, and allergen avoidance.",
        "precaution": "Minimize outdoor exposure during high pollen counts."
    },
    "Strep Throat": {
        "category": "Respiratory", "severity": "Moderate", "emergency": False,
        "description": "Bacterial pharyngitis caused by Streptococcus pyogenes, presenting without classic viral cough.",
        "symptoms": {"severe_sore_throat": 10, "difficulty_swallowing": 9, "fever": 8, "swollen_tonsils": 9, "white_patches_throat": 9, "headache": 5},
        "required": ["severe_sore_throat", "difficulty_swallowing"],
        "treatment": "Oral penicillin or amoxicillin course upon clinical confirmation, and warm salt gargles.",
        "precaution": "Complete full antibiotic course to prevent acute rheumatic fever or glomerulonephritis."
    },
    "Pleurisy": {
        "category": "Respiratory", "severity": "Moderate", "emergency": False,
        "description": "Inflammation of the pleural tissues that line the chest wall and envelop the lungs.",
        "symptoms": {"sharp_chest_pain": 10, "pain_with_breathing": 10, "shallow_breathing": 8, "dry_cough": 6, "fever": 6},
        "required": ["sharp_chest_pain", "pain_with_breathing"],
        "treatment": "Nonsteroidal anti-inflammatory drugs (NSAIDs) and targeted management of primary etiology.",
        "precaution": "Rule out underlying pneumonia, pneumothorax, or pulmonary embolism."
    },

    # --- CARDIOVASCULAR & CIRCULATORY ---
    "Myocardial Infarction": {
        "category": "Cardiovascular", "severity": "Emergency", "emergency": True,
        "description": "Ischemia and acute myocardial necrosis due to critical coronary arterial occlusion.",
        "symptoms": {"crushing_chest_pain": 10, "radiating_arm_pain": 10, "sweating": 9, "shortness_of_breath": 9, "nausea": 7, "dizziness": 8},
        "required": ["crushing_chest_pain", "radiating_arm_pain"],
        "treatment": "Immediate emergency dispatch, 300mg chewable aspirin, coronary angioplasty / catheterization.",
        "precaution": "Life-threatening emergency; call 108/911 immediately without waiting for pain to pass."
    },
    "Angina Pectoris": {
        "category": "Cardiovascular", "severity": "Serious", "emergency": True,
        "description": "Transient myocardial ischemia producing oppressive substernal pressure during exertion or emotional stress.",
        "symptoms": {"chest_tightness": 10, "pain_with_exertion": 10, "radiating_jaw_pain": 8, "shortness_of_breath": 8, "fatigue": 6},
        "required": ["chest_tightness", "pain_with_exertion"],
        "treatment": "Sublingual nitroglycerin, rest, cardiological workup, and beta-blocker therapy.",
        "precaution": "If symptoms persist beyond 10 minutes after rest/nitroglycerin, treat as acute infarction."
    },
    "Congestive Heart Failure": {
        "category": "Cardiovascular", "severity": "Serious", "emergency": True,
        "description": "Inability of cardiac ventricles to pump blood efficiently, causing systemic and pulmonary venous congestion.",
        "symptoms": {"orthopnea": 10, "ankle_swelling": 10, "shortness_of_breath": 9, "fatigue": 8, "rapid_weight_gain": 8, "persistent_cough": 7},
        "required": ["orthopnea", "ankle_swelling"],
        "treatment": "Diuretics, ACE inhibitors/ARBs, strict dietary sodium restriction, and cardiology follow-up.",
        "precaution": "Weigh daily; sudden gain of 1.5–2 kg in 48 hours requires immediate dosage titration."
    },
    "Hypertension Crisis": {
        "category": "Cardiovascular", "severity": "Emergency", "emergency": True,
        "description": "Acute elevation of blood pressure exceeding 180/120 mmHg associated with imminent end-organ damage.",
        "symptoms": {"severe_headache": 10, "blurred_vision": 9, "chest_pain": 9, "dizziness": 8, "shortness_of_breath": 8, "confusion": 9},
        "required": ["severe_headache", "blurred_vision"],
        "treatment": "Intravenous antihypertensive infusions in an intensive care setting.",
        "precaution": "Do not lower blood pressure precipitously to avoid cerebral hypoperfusion."
    },
    "Atrial Fibrillation": {
        "category": "Cardiovascular", "severity": "Moderate", "emergency": False,
        "description": "Supraventricular tachyarrhythmia characterized by uncoordinated atrial activation and irregular ventricular response.",
        "symptoms": {"palpitations": 10, "irregular_pulse": 10, "dizziness": 8, "fatigue": 7, "shortness_of_breath": 7, "weakness": 6},
        "required": ["palpitations", "irregular_pulse"],
        "treatment": "Rate or rhythm control pharmacotherapy, anticoagulation to prevent stroke, and cardioversion.",
        "precaution": "Maintain regular INR/anticoagulation checks; high risk of embolic cerebrovascular stroke."
    },
    "Pericarditis": {
        "category": "Cardiovascular", "severity": "Moderate", "emergency": False,
        "description": "Inflammation of the fibroelastic pericardial sac surrounding the heart, causing postural precordial pain.",
        "symptoms": {"sharp_chest_pain": 10, "pain_relieved_leaning_forward": 10, "fever": 7, "palpitations": 7, "weakness": 6},
        "required": ["sharp_chest_pain", "pain_relieved_leaning_forward"],
        "treatment": "Colchicine, high-dose NSAIDs, resting, and echocardiographic monitoring for effusion.",
        "precaution": "Urgent review if signs of cardiac tamponade (hypotension, jugular venous distention) arise."
    },
    "Infective Endocarditis": {
        "category": "Cardiovascular", "severity": "Serious", "emergency": True,
        "description": "Microbial infection of the endothelial surface of heart valves producing vegetations.",
        "symptoms": {"sustained_fever": 10, "heart_murmur": 10, "night_sweats": 8, "fatigue": 8, "weight_loss": 7, "splinter_hemorrhages": 8},
        "required": ["sustained_fever", "heart_murmur"],
        "treatment": "Prolonged intravenous bactericidal antibiotic therapy guided by serial blood cultures.",
        "precaution": "Patients with prosthetic valves require prompt cardiac surgical consultation."
    },
    "Peripheral Artery Disease": {
        "category": "Cardiovascular", "severity": "Moderate", "emergency": False,
        "description": "Atherosclerotic narrowing of peripheral arteries, predominantly causing lower limb ischemia.",
        "symptoms": {"intermittent_claudication": 10, "cold_feet": 9, "weak_pedal_pulse": 9, "leg_cramps_walking": 9, "slow_healing_sores": 8},
        "required": ["intermittent_claudication", "leg_cramps_walking"],
        "treatment": "Antiplatelet agents, statins, supervised exercise programs, and vascular evaluation.",
        "precaution": "Inspect feet daily for non-healing pressure ulcers or necrotic changes."
    },

    # --- GASTROINTESTINAL & HEPATIC ---
    "Food Poisoning": {
        "category": "Digestive", "severity": "Moderate", "emergency": False,
        "description": "Acute toxin-mediated gastroenteropathy resulting from ingestion of contaminated food.",
        "symptoms": {"vomiting": 10, "diarrhea": 10, "abdominal_pain": 8, "nausea": 9, "weakness": 7, "low_grade_fever": 5},
        "required": ["vomiting", "diarrhea"],
        "treatment": "Oral rehydration solution (ORS), gut rest, light diet, and electrolyte replacement.",
        "precaution": "Monitor urine output; seek medical advice if unable to retain fluids for 12 hours."
    },
    "Gastritis": {
        "category": "Digestive", "severity": "Low", "emergency": False,
        "description": "Inflammation or erosion of the gastric mucosal barrier causing epigastric pain.",
        "symptoms": {"epigastric_pain": 10, "heartburn": 9, "nausea": 8, "bloating": 7, "loss_of_appetite": 6, "burping": 6},
        "required": ["epigastric_pain", "heartburn"],
        "treatment": "Proton pump inhibitors (PPI), antacids, small bland meals, and avoiding spicy/acidic foods.",
        "precaution": "Avoid NSAIDs, alcohol, and caffeine, which exacerbate mucosal irritation."
    },
    "Gastroenteritis": {
        "category": "Digestive", "severity": "Moderate", "emergency": False,
        "description": "Enteric infection causing diffuse mucosal inflammation of both stomach and intestines.",
        "symptoms": {"vomiting": 10, "watery_diarrhea": 10, "abdominal_cramps": 8, "fever": 6, "weakness": 7, "dehydration": 8},
        "required": ["vomiting", "watery_diarrhea"],
        "treatment": "Electrolyte replacement, zinc supplementation, hydration maintenance, and rest.",
        "precaution": "Avoid anti-motility drugs if high fever or dysentery is present."
    },
    "GERD": {
        "category": "Digestive", "severity": "Low", "emergency": False,
        "description": "Chronic retrograde flow of acidic gastroduodenal contents into the esophagus.",
        "symptoms": {"heartburn": 10, "acid_reflux": 10, "burping": 8, "chest_discomfort": 7, "sour_taste": 8, "bloating": 6},
        "required": ["heartburn", "acid_reflux"],
        "treatment": "H2-receptor antagonists or PPIs, head-of-bed elevation, and lifestyle modifications.",
        "precaution": "Do not lie down within 3 hours after meals; avoid late-night eating."
    },
    "Peptic Ulcer": {
        "category": "Digestive", "severity": "Moderate", "emergency": False,
        "description": "Well-defined mucosal breach in the stomach or duodenum, commonly associated with H. pylori or NSAIDs.",
        "symptoms": {"burning_stomach_pain": 10, "black_stool": 9, "loss_of_appetite": 8, "heartburn": 7, "bloating": 6, "nausea": 6},
        "required": ["burning_stomach_pain", "black_stool"],
        "treatment": "H. pylori eradication therapy (triple/quadruple regimen), PPIs, and mucosal protectants.",
        "precaution": "Black tarry stool (melena) indicates upper GI bleeding requiring immediate hospitalization."
    },
    "Acute Appendicitis": {
        "category": "Digestive", "severity": "Emergency", "emergency": True,
        "description": "Acute lumen obstruction and inflammation of the vermiform appendix, risking perforation.",
        "symptoms": {"right_lower_quadrant_pain": 10, "periumbilical_pain_shift": 10, "nausea": 8, "vomiting": 7, "low_grade_fever": 7, "loss_of_appetite": 8},
        "required": ["right_lower_quadrant_pain", "periumbilical_pain_shift"],
        "treatment": "Immediate surgical evaluation for laparoscopic or open appendectomy; nil-by-mouth.",
        "precaution": "Do NOT apply heat pads or take enemas/laxatives, which precipitate appendix rupture."
    },
    "Acute Cholecystitis": {
        "category": "Digestive", "severity": "Serious", "emergency": True,
        "description": "Acute inflammation of the gallbladder, almost always secondary to cystic duct gallstone impaction.",
        "symptoms": {"right_upper_quadrant_pain": 10, "murphys_sign": 10, "radiating_shoulder_pain": 8, "fever": 8, "nausea": 8, "vomiting": 7},
        "required": ["right_upper_quadrant_pain", "murphys_sign"],
        "treatment": "Urgent ultrasound, bowel rest, intravenous antibiotics, and early cholecystectomy.",
        "precaution": "Monitor for jaundice indicating common bile duct stone (choledocholithiasis)."
    },
    "Acute Pancreatitis": {
        "category": "Digestive", "severity": "Emergency", "emergency": True,
        "description": "Autodigestion and acute inflammatory destruction of pancreatic parenchyma, commonly from alcohol or gallstones.",
        "symptoms": {"severe_epigastric_pain": 10, "radiating_back_pain": 10, "persistent_vomiting": 9, "abdominal_tenderness": 9, "tachycardia": 8, "fever": 7},
        "required": ["severe_epigastric_pain", "radiating_back_pain"],
        "treatment": "Immediate hospital admission, aggressive intravenous fluid resuscitation, analgesia, and bowel rest.",
        "precaution": "High systemic inflammation risk; requires close ICU/HDU monitoring."
    },
    "Irritable Bowel Syndrome": {
        "category": "Digestive", "severity": "Low", "emergency": False,
        "description": "A functional gastrointestinal disorder characterized by recurrent abdominal pain associated with altered bowel habits.",
        "symptoms": {"abdominal_cramping": 10, "bloating": 9, "alternating_bowel_habits": 10, "gas": 8, "relief_after_defecation": 8},
        "required": ["abdominal_cramping", "alternating_bowel_habits"],
        "treatment": "Low-FODMAP diet, antispasmodics, fiber adjustment, and stress-reduction therapy.",
        "precaution": "Investigate alarm symptoms (weight loss, rectal bleeding, nocturnal diarrhea) for organic bowel disease."
    },
    "Crohns Disease": {
        "category": "Digestive", "severity": "Serious", "emergency": False,
        "description": "Transmural, granulomatous inflammatory bowel disease capable of affecting any segment of the GI tract.",
        "symptoms": {"chronic_diarrhea": 10, "crampy_abdominal_pain": 9, "weight_loss": 9, "fatigue": 8, "fever": 6, "mouth_sores": 7},
        "required": ["chronic_diarrhea", "weight_loss"],
        "treatment": "Corticosteroids, immunomodulators (azathioprine), biologics (anti-TNF), and nutritional support.",
        "precaution": "Screen regularly for intestinal fistulae, strictures, or abscess formation."
    },
    "Ulcerative Colitis": {
        "category": "Digestive", "severity": "Serious", "emergency": False,
        "description": "Chronic continuous mucosal ulceration and inflammation restricted to the colon and rectum.",
        "symptoms": {"bloody_diarrhea": 10, "rectal_urgency": 10, "tenesmus": 9, "cramping_pain": 8, "fatigue": 7, "weight_loss": 7},
        "required": ["bloody_diarrhea", "rectal_urgency"],
        "treatment": "5-ASA aminosalicylates (mesalamine), topical/oral steroids, and biologics.",
        "precaution": "Monitor for toxic megacolon; long-term surveillance colonoscopy required for dysplasia."
    },
    "Liver Cirrhosis": {
        "category": "Digestive", "severity": "Serious", "emergency": True,
        "description": "Late-stage hepatic fibrosis resulting in diffuse architecture disruption, portal hypertension, and liver dysfunction.",
        "symptoms": {"jaundice": 10, "ascites": 10, "spider_angiomas": 8, "fatigue": 8, "easy_bruising": 8, "confusion": 9},
        "required": ["jaundice", "ascites"],
        "treatment": "Diuretics, dietary sodium restriction, non-selective beta-blockers for varices, and liver transplant evaluation.",
        "precaution": "Signs of confusion indicate hepatic encephalopathy requiring immediate lactulose and urgent care."
    },
    "Celiac Disease": {
        "category": "Digestive", "severity": "Moderate", "emergency": False,
        "description": "Autoimmune enteropathy triggered by dietary gluten ingestion in genetically susceptible individuals.",
        "symptoms": {"chronic_diarrhea": 9, "bloating": 9, "weight_loss": 8, "fatigue": 8, "anemia": 8, "steatorrhea": 9},
        "required": ["chronic_diarrhea", "steatorrhea"],
        "treatment": "Strict life-long gluten-free diet and nutritional supplementation.",
        "precaution": "Check labels for hidden gluten cross-contamination in processed foods and medicines."
    },

    # --- NEUROLOGICAL & PSYCHOLOGICAL ---
    "Migraine": {
        "category": "Neurological", "severity": "Moderate", "emergency": False,
        "description": "A primary neurovascular headache disorder with unilateral throbbing pain, sensory hypersensitivity, and nausea.",
        "symptoms": {"severe_throbbing_headache": 10, "sensitivity_to_light": 10, "sensitivity_to_sound": 9, "nausea": 8, "vomiting": 7, "aura": 7},
        "required": ["severe_throbbing_headache", "sensitivity_to_light"],
        "treatment": "Triptans, NSAIDs, resting in a dark quiet room, and preventive beta-blockers/CGRP antagonists.",
        "precaution": "Identify personal triggers (tyramine, lack of sleep, hormonal shifts, caffeine withdrawal)."
    },
    "Tension Headache": {
        "category": "Neurological", "severity": "Low", "emergency": False,
        "description": "The most common primary headache, characterized by bilateral non-pulsating band-like pressure.",
        "symptoms": {"headache": 10, "neck_tightness": 9, "muscle_tightness": 8, "stress": 8, "mild_dizziness": 5},
        "required": ["headache", "neck_tightness"],
        "treatment": "Paracetamol, NSAIDs, hydration, stress management, and physical therapy posture correction.",
        "precaution": "Avoid daily analgesic overuse which can induce medication-overuse rebound headaches."
    },
    "Cluster Headache": {
        "category": "Neurological", "severity": "Serious", "emergency": False,
        "description": "Severe strictly unilateral trigeminal autonomic cephalalgia causing piercing orbital or temporal agony.",
        "symptoms": {"excruciating_eye_pain": 10, "unilateral_lacrimation": 10, "nasal_congestion": 8, "restlessness": 9, "ptosis": 8},
        "required": ["excruciating_eye_pain", "unilateral_lacrimation"],
        "treatment": "100% high-flow normobaric oxygen via non-rebreather mask, subcutaneous sumatriptan, and verapamil prophylaxis.",
        "precaution": "Patients exhibit extreme pacing/agitation; keep abortive oxygen cylinders accessible."
    },
    "Vertigo": {
        "category": "Neurological", "severity": "Moderate", "emergency": False,
        "description": "Vestibular disturbance causing an erroneous illusion of environmental rotation or spinning.",
        "symptoms": {"spinning_sensation": 10, "loss_of_balance": 10, "nausea": 8, "vomiting": 7, "nystagmus": 8, "ear_fullness": 6},
        "required": ["spinning_sensation", "loss_of_balance"],
        "treatment": "Vestibular rehabilitation, Epley repositioning maneuvers for BPPV, and short-term antihistaminic vestibular suppressants.",
        "precaution": "Use assistive support when standing or walking to prevent fall injuries."
    },
    "Bacterial Meningitis": {
        "category": "Neurological", "severity": "Emergency", "emergency": True,
        "description": "Purulent bacterial infection of the leptomeninges and subarachnoid space.",
        "symptoms": {"severe_headache": 10, "neck_stiffness": 10, "high_fever": 9, "confusion": 9, "sensitivity_to_light": 9, "vomiting": 8, "petechial_rash": 8},
        "required": ["severe_headache", "neck_stiffness", "high_fever"],
        "treatment": "Immediate empirical intravenous ceftriaxone, vancomycin, dexamethasone, and urgent lumbar puncture.",
        "precaution": "Critical life-threatening neurological emergency; droplet isolation precautions required."
    },
    "Stroke": {
        "category": "Neurological", "severity": "Emergency", "emergency": True,
        "description": "Acute focal neurological deficit due to ischemic infarction or intracerebral hemorrhage.",
        "symptoms": {"facial_droop": 10, "one_sided_weakness": 10, "slurred_speech": 10, "sudden_confusion": 9, "vision_loss": 8, "loss_of_balance": 8},
        "required": ["facial_droop", "one_sided_weakness", "slurred_speech"],
        "treatment": "Immediate emergency CT scan, intravenous tPA (if ischemic and within 4.5h window), or endovascular thrombectomy.",
        "precaution": "Time is brain. Act FAST: Face, Arms, Speech, Time. Call emergency services immediately."
    },
    "Parkinsons Disease": {
        "category": "Neurological", "severity": "Moderate", "emergency": False,
        "description": "Neurodegenerative disorder involving progressive loss of dopaminergic neurons in the substantia nigra.",
        "symptoms": {"resting_tremor": 10, "bradykinesia": 10, "muscle_rigidity": 9, "shuffling_gait": 9, "micrographia": 7, "loss_of_smell": 6},
        "required": ["resting_tremor", "bradykinesia"],
        "treatment": "Levodopa-carbidopa, dopamine agonists, physical therapy, and deep brain stimulation evaluation.",
        "precaution": "High fall risk; install safety grab-rails at home and monitor medication off-time."
    },
    "Multiple Sclerosis": {
        "category": "Neurological", "severity": "Serious", "emergency": False,
        "description": "Chronic autoimmune demyelinating disease of the central nervous system.",
        "symptoms": {"numbness_tingling": 10, "optic_neuritis": 10, "muscle_weakness": 9, "spasticity": 8, "extreme_fatigue": 8, "loss_of_balance": 8},
        "required": ["numbness_tingling", "optic_neuritis"],
        "treatment": "High-dose intravenous methylprednisolone for acute relapses, and disease-modifying therapies (DMTs).",
        "precaution": "Avoid heat exposure (Uhthoff's phenomenon) which temporarily worsens demyelinating symptoms."
    },
    "Epilepsy": {
        "category": "Neurological", "severity": "Serious", "emergency": True,
        "description": "Neurological condition characterized by recurrent, unprovoked paroxysmal cerebral seizures.",
        "symptoms": {"recurrent_seizures": 10, "loss_of_consciousness": 10, "muscle_convulsions": 9, "postictal_confusion": 9, "tongue_biting": 8},
        "required": ["recurrent_seizures", "loss_of_consciousness"],
        "treatment": "Anti-epileptic drugs (AEDs: levetiracetam, carbamazepine, sodium valproate), and seizure first aid.",
        "precaution": "During seizure: place in lateral recovery position, cushion head, do NOT insert objects into mouth."
    },
    "Trigeminal Neuralgia": {
        "category": "Neurological", "severity": "Moderate", "emergency": False,
        "description": "Neuropathic disorder causing paroxysmal lancinating, electric shock-like facial pain.",
        "symptoms": {"electric_facial_pain": 10, "pain_triggered_by_touch": 10, "unilateral_pain": 9, "facial_muscle_twitch": 7},
        "required": ["electric_facial_pain", "pain_triggered_by_touch"],
        "treatment": "Carbamazepine, oxcarbazepine, gabapentin, or microvascular decompression surgery.",
        "precaution": "Avoid mechanical triggers such as light touching, shaving, cold wind, or chewing on affected side."
    },

    # --- INFECTIOUS, VIRAL & BACTERIAL ---
    "Dengue Fever": {
        "category": "Viral", "severity": "Serious", "emergency": True,
        "description": "Flavivirus transmitted by Aedes mosquitoes causing breakbone fever and severe thrombocyte drops.",
        "symptoms": {"high_fever": 10, "severe_body_pain": 10, "retro_orbital_pain": 9, "rash": 8, "chills": 7, "nausea": 7, "bleeding_gums": 8},
        "required": ["high_fever", "severe_body_pain"],
        "treatment": "Meticulous fluid resuscitation, paracetamol for fever, and continuous platelet count monitoring.",
        "precaution": "Strictly AVOID aspirin and NSAIDs (ibuprofen) due to severe risk of hemorrhagic complications."
    },
    "Malaria": {
        "category": "Viral", "severity": "Serious", "emergency": True,
        "description": "Protozoan parasitic infection transmitted by female Anopheles mosquitoes causing paroxysmal febrile rigors.",
        "symptoms": {"cyclic_chills_and_fever": 10, "profuse_sweating": 10, "headache": 8, "fatigue": 8, "splenomegaly": 7, "nausea": 7},
        "required": ["cyclic_chills_and_fever", "profuse_sweating"],
        "treatment": "Artemisinin-based combination therapy (ACT), oral chloroquine (if sensitive), and bed-net vector controls.",
        "precaution": "Monitor closely for cerebral malaria manifestations (delirium, convulsions, coma)."
    },
    "Typhoid Fever": {
        "category": "Bacterial", "severity": "Serious", "emergency": True,
        "description": "Systemic bacterial infection caused by Salmonella enterica serotype Typhi through fecal-oral route.",
        "symptoms": {"step_ladder_fever": 10, "abdominal_pain": 9, "rose_spots_rash": 9, "weakness": 8, "constipation": 7, "bradycardia": 8},
        "required": ["step_ladder_fever", "abdominal_pain"],
        "treatment": "Oral/IV fluoroquinolones (ciprofloxacin) or azithromycin/ceftriaxone, and rehydration.",
        "precaution": "High risk of intestinal perforation in 3rd week; seek urgent surgical care if sudden acute peritonitis develops."
    },
    "Tuberculosis": {
        "category": "Bacterial", "severity": "Serious", "emergency": True,
        "description": "Chronic necrotizing granulomatous infection caused by Mycobacterium tuberculosis, primarily pulmonary.",
        "symptoms": {"chronic_cough_over_3_weeks": 10, "hemoptysis": 10, "night_sweats": 9, "unexplained_weight_loss": 9, "low_grade_evening_fever": 8, "chest_pain": 7},
        "required": ["chronic_cough_over_3_weeks", "unexplained_weight_loss"],
        "treatment": "Directly Observed Therapy Short-Course (DOTS): rifampicin, isoniazid, pyrazinamide, ethambutol (RIPE).",
        "precaution": "Negative-pressure respiratory airborne isolation; complete full 6-month regimen to prevent multi-drug resistance."
    },
    "Chickenpox": {
        "category": "Viral", "severity": "Moderate", "emergency": False,
        "description": "Primary Varicella-Zoster virus infection producing itchy pleomorphic rash ('dewdrops on rose petals').",
        "symptoms": {"pruritic_blister_rash": 10, "rash_on_trunk": 10, "fever": 7, "fatigue": 6, "loss_of_appetite": 6},
        "required": ["pruritic_blister_rash", "rash_on_trunk"],
        "treatment": "Oral acyclovir (for adults/severe cases), calamine lotion, antihistamines, and paracetamol.",
        "precaution": "Do not give aspirin to children due to fatal Reye syndrome risk; isolate until all blisters crust."
    },
    "Measles": {
        "category": "Viral", "severity": "Serious", "emergency": True,
        "description": "Highly contagious paramyxovirus causing the 3 Cs (cough, coryza, conjunctivitis) and maculopapular rash.",
        "symptoms": {"high_fever": 10, "koplik_spots": 10, "maculopapular_rash": 9, "cough": 8, "runny_nose": 8, "conjunctivitis": 9},
        "required": ["high_fever", "koplik_spots"],
        "treatment": "Vitamin A therapy, antipyretics, hydration, and observation for secondary encephalitis or giant-cell pneumonia.",
        "precaution": "Highly infectious airborne spread; isolate immediately and verify vaccination of contacts."
    },
    "Mumps": {
        "category": "Viral", "severity": "Moderate", "emergency": False,
        "description": "Acute viral illness causing painful swelling of one or both parotid salivary glands.",
        "symptoms": {"parotid_swelling": 10, "ear_jaw_pain": 9, "fever": 7, "headache": 6, "orchitis_pain": 7},
        "required": ["parotid_swelling"],
        "treatment": "Analgesics, cold or warm jaw compresses, soft food diet, and hydration.",
        "precaution": "Post-pubertal males should report testicular swelling (orchitis) to prevent fertility complications."
    },
    "Cholera": {
        "category": "Bacterial", "severity": "Emergency", "emergency": True,
        "description": "Acute enterotoxin infection from Vibrio cholerae causing catastrophic fluid and electrolyte depletion.",
        "symptoms": {"rice_water_diarrhea": 10, "rapid_severe_dehydration": 10, "vomiting": 9, "muscle_cramps": 8, "hypovolemic_shock": 9},
        "required": ["rice_water_diarrhea", "rapid_severe_dehydration"],
        "treatment": "Immediate aggressive IV Ringer's lactate fluid resuscitation, oral rehydration solution, and doxycycline.",
        "precaution": "Can cause fatal hypovolemic shock within hours; treat fluid deficits as a critical emergency."
    },
    "Chikungunya": {
        "category": "Viral", "severity": "Moderate", "emergency": False,
        "description": "Alphavirus transmitted by Aedes mosquitoes characterized by severe, debilitating, prolonged polyarthralgia.",
        "symptoms": {"sudden_high_fever": 10, "severe_joint_pain": 10, "swollen_joints": 8, "maculopapular_rash": 7, "headache": 6},
        "required": ["sudden_high_fever", "severe_joint_pain"],
        "treatment": "NSAIDs, paracetamol, joint mobilization physiotherapy, and rest.",
        "precaution": "Joint pain can persist for months or years; monitor for chronic arthropathy."
    },
    "Lyme Disease": {
        "category": "Bacterial", "severity": "Moderate", "emergency": False,
        "description": "Tick-borne zoonosis caused by Borrelia burgdorferi transmitted by Ixodes ticks.",
        "symptoms": {"erythema_migrans_bullseye": 10, "fatigue": 8, "fever": 7, "joint_aches": 8, "headache": 7, "stiff_neck": 7},
        "required": ["erythema_migrans_bullseye"],
        "treatment": "Oral doxycycline (2–3 weeks) or amoxicillin upon tick exposure and rash appearance.",
        "precaution": "Perform complete skin checks after traversing woody or tall-grass environments."
    },
    "Infectious Mononucleosis": {
        "category": "Viral", "severity": "Moderate", "emergency": False,
        "description": "Epstein-Barr virus infection presenting with the classic triad of fever, pharyngitis, and lymphadenopathy.",
        "symptoms": {"severe_fatigue": 10, "exudative_pharyngitis": 10, "swollen_cervical_lymph_nodes": 9, "fever": 8, "splenomegaly": 8},
        "required": ["severe_fatigue", "exudative_pharyngitis"],
        "treatment": "Supportive rest, hydration, analgesics, and avoidance of ampicillin/amoxicillin (causes rash).",
        "precaution": "Strictly avoid contact sports for 4 weeks to prevent catastrophic splenic rupture."
    },
    "Tetanus": {
        "category": "Bacterial", "severity": "Emergency", "emergency": True,
        "description": "Neurological intoxication by Clostridium tetani tetanospasmin producing intense muscular spasms.",
        "symptoms": {"trismus_lockjaw": 10, "risus_sardonicus": 10, "muscle_rigidity": 9, "painful_spasms": 9, "autonomic_instability": 8},
        "required": ["trismus_lockjaw", "risus_sardonicus"],
        "treatment": "Human tetanus immunoglobulin (HTIG), wound debridement, IV metronidazole, benzodiazepines, and ICU sedation.",
        "precaution": "Protect from noise and light stimuli which trigger violent generalized spasms."
    },
    "Rabies": {
        "category": "Viral", "severity": "Emergency", "emergency": True,
        "description": "Encephalitic rhabdovirus infection transmitted by animal bites, almost 100% fatal once clinical symptoms start.",
        "symptoms": {"hydrophobia": 10, "aerophobia": 10, "agitation": 9, "excessive_salivation": 9, "animal_bite_history": 10, "fever": 7},
        "required": ["hydrophobia", "animal_bite_history"],
        "treatment": "Immediate post-exposure prophylaxis (PEP: wound washing, rabies vaccine, rabies immunoglobulin).",
        "precaution": "Fatal once clinical signs manifest; immediate wound disinfection and PEP is mandatory post-bite."
    },
    "Hand Foot and Mouth Disease": {
        "category": "Viral", "severity": "Moderate", "emergency": False,
        "description": "Coxsackievirus infection causing vesicular ulcerations in mouth and papules on palms and soles.",
        "symptoms": {"mouth_sores": 10, "vesicular_rash_hands_feet": 10, "fever": 8, "loss_of_appetite": 7, "irritability": 6},
        "required": ["mouth_sores", "vesicular_rash_hands_feet"],
        "treatment": "Oral hydration, soothing throat sprays, paracetamol, and barrier hygiene.",
        "precaution": "Highly contagious in child care centers; keep child home until all vesicles dry."
    },

    # --- DERMATOLOGICAL & SKIN ---
    "Eczema": {
        "category": "Skin", "severity": "Low", "emergency": False,
        "description": "Chronic pruritic inflammatory dermatosis characterized by impaired epidermal skin barrier.",
        "symptoms": {"intense_itching": 10, "dry_skin": 9, "erythema": 8, "skin_lichenification": 8, "flexural_crease_rash": 9},
        "required": ["intense_itching", "dry_skin"],
        "treatment": "Liberal emollient application, topical corticosteroid ointments, and avoiding harsh soaps.",
        "precaution": "Keep fingernails trimmed; secondary bacterial infection (impetiginization) can occur from scratching."
    },
    "Psoriasis": {
        "category": "Skin", "severity": "Moderate", "emergency": False,
        "description": "Immune-mediated dermatosis characterized by well-demarcated erythematous plaques with silvery scales.",
        "symptoms": {"silvery_scales": 10, "salmon_colored_plaques": 10, "extensor_surface_plaques": 9, "skin_itching": 7, "nail_pitting": 8},
        "required": ["silvery_scales", "salmon_colored_plaques"],
        "treatment": "Topical vitamin D analogues, topical potent corticosteroids, phototherapy, and biologic agents.",
        "precaution": "Inspect joints for psoriatic arthritis; avoid sudden systemic corticosteroid withdrawal."
    },
    "Ringworm": {
        "category": "Skin", "severity": "Low", "emergency": False,
        "description": "Dermatophyte fungal skin infection forming characteristic advancing annular lesions with central clearing.",
        "symptoms": {"ring_shaped_lesion": 10, "scaly_raised_borders": 10, "itching": 8, "central_clearing": 9},
        "required": ["ring_shaped_lesion", "scaly_raised_borders"],
        "treatment": "Topical antifungal creams (terbinafine, clotrimazole) applied 2 cm beyond the border for 2–4 weeks.",
        "precaution": "Do not share towels, combs, or sports clothing; keep skin clean and completely dry."
    },
    "Scabies": {
        "category": "Skin", "severity": "Moderate", "emergency": False,
        "description": "Cutaneous infestation caused by Sarcoptes scabiei mite burrowing into the stratum corneum.",
        "symptoms": {"nocturnal_intense_itching": 10, "mite_burrows": 10, "web_space_papules": 9, "excoriations": 8},
        "required": ["nocturnal_intense_itching", "mite_burrows"],
        "treatment": "5% Permethrin cream neck-down overnight (repeated in 7 days), or oral ivermectin.",
        "precaution": "Treat ALL household contacts simultaneously; wash clothes and bedding in hot water."
    },
    "Shingles": {
        "category": "Skin", "severity": "Moderate", "emergency": False,
        "description": "Reactivation of latent Varicella-Zoster virus in sensory dorsal root ganglia producing dermatomal pain and vesicles.",
        "symptoms": {"unilateral_dermatomal_pain": 10, "grouped_vesicles": 10, "allodynia": 9, "burning_stabbing_pain": 9, "low_grade_fever": 5},
        "required": ["unilateral_dermatomal_pain", "grouped_vesicles"],
        "treatment": "Early oral antiviral therapy (valacyclovir/famciclovir within 72h), analgesics, and gabapentin.",
        "precaution": "Prompt ophthalmology referral if ophthalmic division (tip of nose lesion: Hutchinson's sign) is involved."
    },
    "Urticaria": {
        "category": "Skin", "severity": "Low", "emergency": False,
        "description": "Cutaneous vascular reaction marked by transient, intensely pruritic wheals and erythematous flares.",
        "symptoms": {"evanescent_wheals": 10, "intense_pruritus": 10, "skin_flushing": 8, "dermographism": 7},
        "required": ["evanescent_wheals", "intense_pruritus"],
        "treatment": "Second-generation non-sedating oral H1 antihistamines (cetirizine, fexofenadine).",
        "precaution": "If accompanied by lip/tongue swelling or breathing difficulty, treat immediately as anaphylaxis."
    },
    "Cellulitis": {
        "category": "Skin", "severity": "Serious", "emergency": True,
        "description": "Acute spreading bacterial dermis and subcutaneous tissue infection, predominantly by Strep or Staph.",
        "symptoms": {"spreading_erythema": 10, "localized_heat": 9, "edema_skin": 9, "severe_tenderness": 9, "fever": 8},
        "required": ["spreading_erythema", "localized_heat"],
        "treatment": "Oral or intravenous beta-lactam antibiotics (cephalexin/cefazolin), limb elevation, and marking margins.",
        "precaution": "Mark the erythema boundary with a surgical marker to monitor rapid spreading."
    },
    "Alopecia Areata": {
        "category": "Skin", "severity": "Low", "emergency": False,
        "description": "Autoimmune condition targeting hair follicles causing discrete, non-scarring circular patches of hair loss.",
        "symptoms": {"patchy_hair_loss": 10, "smooth_scalp": 9, "exclamation_mark_hairs": 9, "nail_dystrophy": 6},
        "required": ["patchy_hair_loss", "smooth_scalp"],
        "treatment": "Intralesional triamcinolone corticosteroid injections, topical minoxidil, or JAK inhibitors.",
        "precaution": "Screen for co-existing autoimmune diseases such as vitiligo and Hashimoto's thyroiditis."
    },

    # --- ENDOCRINE & METABOLIC ---
    "Type 1 Diabetes": {
        "category": "Endocrine", "severity": "Serious", "emergency": False,
        "description": "Autoimmune destruction of pancreatic beta-cells causing absolute insulin deficiency.",
        "symptoms": {"excessive_thirst": 10, "frequent_urination": 10, "rapid_weight_loss": 9, "polyphagia": 8, "fatigue": 8, "blurred_vision": 7},
        "required": ["excessive_thirst", "frequent_urination", "rapid_weight_loss"],
        "treatment": "Subcutaneous basal-bolus insulin regimens, carbohydrate counting, and continuous glucose monitoring.",
        "precaution": "Requires lifelong insulin; skipping injections rapidly precipitates diabetic ketoacidosis."
    },
    "Type 2 Diabetes": {
        "category": "Endocrine", "severity": "Moderate", "emergency": False,
        "description": "Metabolic disorder characterized by peripheral insulin resistance paired with progressive secretory defect.",
        "symptoms": {"increased_thirst": 9, "nocturia": 9, "fatigue": 8, "slow_wound_healing": 8, "acanthosis_nigricans": 7, "recurrent_infections": 7},
        "required": ["increased_thirst", "nocturia"],
        "treatment": "Metformin, SGLT2 inhibitors/GLP-1 agonists, weight loss, exercise, and glycemic monitoring.",
        "precaution": "Annual screening for retinopathy, nephropathy, and diabetic neuropathy."
    },
    "Diabetic Ketoacidosis": {
        "category": "Endocrine", "severity": "Emergency", "emergency": True,
        "description": "Acute life-threatening metabolic complication of diabetes with ketoacidosis, dehydration, and hyperglycemia.",
        "symptoms": {"kussmaul_breathing": 10, "fruity_breath_odor": 10, "high_blood_sugar": 9, "nausea_vomiting": 9, "confusion": 9, "abdominal_pain": 8},
        "required": ["kussmaul_breathing", "fruity_breath_odor"],
        "treatment": "Intravenous isotonic fluid resuscitation, continuous IV regular insulin infusion, and potassium repletion.",
        "precaution": "ICU admission mandatory; never stop insulin without checking blood pH and ketone levels."
    },
    "Hyperthyroidism": {
        "category": "Endocrine", "severity": "Moderate", "emergency": False,
        "description": "Clinical syndrome resulting from hypermetabolism and elevated circulating free thyroid hormones.",
        "symptoms": {"heat_intolerance": 10, "unexplained_weight_loss": 10, "palpitations": 9, "hand_tremors": 9, "diarrhea": 7, "goiter": 8, "exophthalmos": 8},
        "required": ["heat_intolerance", "unexplained_weight_loss"],
        "treatment": "Antithyroid drugs (methimazole/propylthiouracil), beta-blockers for symptoms, or radioactive iodine ablation.",
        "precaution": "Watch for thyroid storm: extreme tachycardia, high fever, delirium requiring immediate emergency care."
    },
    "Hypothyroidism": {
        "category": "Endocrine", "severity": "Low", "emergency": False,
        "description": "Deficiency of thyroid hormone production leading to generalized hypometabolism.",
        "symptoms": {"cold_intolerance": 10, "weight_gain": 9, "constipation": 8, "dry_coarse_skin": 8, "facial_puffiness": 8, "bradycardia": 7, "chronic_fatigue": 8},
        "required": ["cold_intolerance", "weight_gain"],
        "treatment": "Levothyroxine monotherapy taken on an empty stomach with a glass of water 60 minutes before breakfast.",
        "precaution": "Recheck serum TSH every 6–8 weeks during dosage titration."
    },
    "Cushings Syndrome": {
        "category": "Endocrine", "severity": "Moderate", "emergency": False,
        "description": "Prolonged exposure to inappropriately high levels of free plasma glucocorticoids.",
        "symptoms": {"moon_face": 10, "buffalo_hump": 10, "purple_abdominal_striae": 9, "central_obesity": 9, "proximal_muscle_weakness": 8, "easy_bruising": 7},
        "required": ["moon_face", "buffalo_hump"],
        "treatment": "Surgical resection of causative adrenal or pituitary adenoma, or gradual taper of exogenous corticosteroids.",
        "precaution": "Never abruptly withdraw long-term corticosteroids; can trigger fatal adrenal crisis."
    },
    "Addisons Disease": {
        "category": "Endocrine", "severity": "Serious", "emergency": True,
        "description": "Primary chronic adrenocortical insufficiency leading to cortisol and aldosterone deficiency.",
        "symptoms": {"hyperpigmentation_skin": 10, "salt_craving": 10, "chronic_fatigue": 9, "orthostatic_hypotension": 9, "weight_loss": 8, "hypoglycemia": 7},
        "required": ["hyperpigmentation_skin", "salt_craving"],
        "treatment": "Lifelong replacement therapy with oral hydrocortisone and fludrocortisone.",
        "precaution": "Double or triple hydrocortisone 'sick-day rules' during acute fever, trauma, or illness."
    },
    "Gout": {
        "category": "Endocrine", "severity": "Moderate", "emergency": False,
        "description": "Monosodium urate crystal deposition disease causing excruciating monoarticular inflammatory arthritis.",
        "symptoms": {"first_toe_severe_pain": 10, "podagra_swelling": 10, "exquisite_joint_tenderness": 10, "erythematous_hot_joint": 9, "tophi": 7},
        "required": ["first_toe_severe_pain", "podagra_swelling"],
        "treatment": "Colchicine, NSAIDs, or oral steroids for acute flares; allopurinol/febuxostat for uric acid lowering.",
        "precaution": "Avoid high-purine foods (red meat, seafood, organ meats, beer) and maintain copious hydration."
    },

    # --- URINARY & NEPHROLOGY ---
    "Urinary Tract Infection": {
        "category": "Urinary", "severity": "Moderate", "emergency": False,
        "description": "Bacterial proliferation in the bladder mucosa causing frequency, dysuria, and pelvic discomfort.",
        "symptoms": {"dysuria_burning": 10, "urinary_frequency": 9, "cloudy_urine": 8, "suprapubic_pain": 7, "strong_urine_odor": 6, "urgency": 8},
        "required": ["dysuria_burning", "urinary_frequency"],
        "treatment": "Short-course oral antibiotics (nitrofurantoin, fosfomycin), hydration, and urinary analgesics.",
        "precaution": "Prompt evaluation if flank pain or high fever develops, signaling acute ascending pyelonephritis."
    },
    "Kidney Stones": {
        "category": "Urinary", "severity": "Serious", "emergency": True,
        "description": "Nephrolithiasis / urolithiasis causing severe ureteral colic obstruction.",
        "symptoms": {"severe_flank_pain": 10, "hematuria_blood_in_urine": 10, "radiating_groin_pain": 9, "nausea_vomiting": 8, "urinary_urgency": 7},
        "required": ["severe_flank_pain", "hematuria_blood_in_urine"],
        "treatment": "Parenteral NSAIDs, alpha-blockers (tamsulosin), intravenous hydration, or extracorporeal shock wave lithotripsy.",
        "precaution": "Immediate urological intervention required if stone is paired with fever/infection (infected hydronephrosis)."
    },
    "Acute Pyelonephritis": {
        "category": "Urinary", "severity": "Serious", "emergency": True,
        "description": "Exudative bacterial infection of the renal parenchyma and pelvicalyceal system.",
        "symptoms": {"high_spiking_fever": 10, "costovertebral_angle_tenderness": 10, "flank_pain": 9, "chills_rigors": 9, "dysuria": 7, "nausea": 7},
        "required": ["high_spiking_fever", "costovertebral_angle_tenderness"],
        "treatment": "Empirical intravenous or high-potency oral antibiotics (ceftriaxone, fluoroquinolones) for 10–14 days.",
        "precaution": "Hospitalize patients with persistent vomiting, sepsis signs, or pregnancy."
    },
    "Chronic Kidney Disease": {
        "category": "Urinary", "severity": "Serious", "emergency": False,
        "description": "Longstanding, irreversible deterioration of renal filtration function leading to uremia.",
        "symptoms": {"periorbital_edema": 9, "generalized_pruritus": 9, "fatigue": 8, "anorexia": 8, "nocturia": 8, "frothy_protein_urine": 9, "hypertension": 8},
        "required": ["periorbital_edema", "frothy_protein_urine"],
        "treatment": "Blood pressure control (ACEi/ARBs), dietary protein and potassium restriction, and dialysis/transplant planning.",
        "precaution": "Avoid all nephrotoxic agents including NSAIDs, intravenous radiocontrast, and aminoglycosides."
    },
    "Benign Prostatic Hyperplasia": {
        "category": "Urinary", "severity": "Moderate", "emergency": False,
        "description": "Non-malignant adenomatous proliferation of prostate stroma obstructing the bladder outlet.",
        "symptoms": {"hesitancy_starting_urine": 10, "weak_urinary_stream": 10, "nocturia": 9, "dribbling_after_urination": 8, "urinary_urgency": 7},
        "required": ["hesitancy_starting_urine", "weak_urinary_stream"],
        "treatment": "Alpha-1 adrenergic antagonists (tamsulosin), 5-alpha-reductase inhibitors (finasteride), or TURP surgery.",
        "precaution": "Avoid anticholinergic and decongestant cold medications which can precipitate acute urinary retention."
    },
    "Glomerulonephritis": {
        "category": "Urinary", "severity": "Serious", "emergency": True,
        "description": "Immune-mediated inflammation of glomeruli producing nephritic syndrome.",
        "symptoms": {"cola_colored_urine": 10, "facial_edema": 9, "hypertension": 9, "oliguria": 8, "proteinuria": 8},
        "required": ["cola_colored_urine", "facial_edema"],
        "treatment": "Corticosteroids, immunosuppressives, loop diuretics, and sodium restriction.",
        "precaution": "Monitor 24-hour urine output and daily weights closely."
    },

    # --- MUSCULOSKELETAL & RHEUMATOLOGY ---
    "Rheumatoid Arthritis": {
        "category": "Musculoskeletal", "severity": "Moderate", "emergency": False,
        "description": "Chronic systemic autoimmune synovitis producing symmetric, erosive joint destruction.",
        "symptoms": {"morning_stiffness_over_1hr": 10, "symmetric_joint_swelling": 10, "hand_wrist_pain": 9, "rheumatoid_nodules": 8, "joint_warmth": 7, "fatigue": 7},
        "required": ["morning_stiffness_over_1hr", "symmetric_joint_swelling"],
        "treatment": "Disease-modifying antirheumatic drugs (DMARDs: methotrexate), biologic TNF inhibitors, and short bridging steroids.",
        "precaution": "Early aggressive treatment prevents irreversible joint deformity and disability."
    },
    "Osteoarthritis": {
        "category": "Musculoskeletal", "severity": "Low", "emergency": False,
        "description": "Degenerative 'wear and tear' joint disorder causing progressive articular cartilage breakdown.",
        "symptoms": {"joint_pain_worse_with_use": 10, "crepitus_grating": 10, "heberdens_nodes": 9, "short_morning_stiffness_under_30min": 8, "knee_hip_pain": 9},
        "required": ["joint_pain_worse_with_use", "crepitus_grating"],
        "treatment": "Weight management, low-impact exercise (swimming/cycling), topical NSAIDs, and joint replacement for end-stage.",
        "precaution": "Avoid high-impact joint loading and prolonged immobilization."
    },
    "Fibromyalgia": {
        "category": "Musculoskeletal", "severity": "Moderate", "emergency": False,
        "description": "Central pain sensitization syndrome presenting with widespread musculoskeletal pain and unrefreshing sleep.",
        "symptoms": {"widespread_body_pain": 10, "tender_trigger_points": 10, "unrefreshing_sleep": 9, "fibro_fog_confusion": 8, "chronic_exhaustion": 9},
        "required": ["widespread_body_pain", "tender_trigger_points"],
        "treatment": "Aerobic exercise, cognitive behavioral therapy, SNRIs (duloxetine), or pregabalin.",
        "precaution": "Opioids are ineffective and contraindicated; focus on restorative sleep and conditioning."
    },
    "Ankylosing Spondylitis": {
        "category": "Musculoskeletal", "severity": "Moderate", "emergency": False,
        "description": "Chronic inflammatory seronegative spondyloarthropathy affecting the sacroiliac joints and axial spine.",
        "symptoms": {"chronic_low_back_stiffness": 10, "pain_improves_with_exercise": 10, "buttock_pain": 9, "bamboo_spine_rigidity": 8, "anterior_uveitis": 7},
        "required": ["chronic_low_back_stiffness", "pain_improves_with_exercise"],
        "treatment": "Continuous physical therapy, NSAIDs as first line, and biologic anti-TNF or IL-17 inhibitors.",
        "precaution": "Strict smoking cessation; maintain daily spinal posture extension exercises."
    },
    "Carpal Tunnel Syndrome": {
        "category": "Musculoskeletal", "severity": "Low", "emergency": False,
        "description": "Entrapment neuropathy caused by compression of the median nerve within the carpal tunnel of the wrist.",
        "symptoms": {"median_nerve_numbness": 10, "wrist_tinel_phalen_positive": 10, "hand_tingling_at_night": 9, "thenar_muscle_weakness": 8},
        "required": ["median_nerve_numbness", "wrist_tinel_phalen_positive"],
        "treatment": "Neutral wrist splinting at night, ergonomic keyboard adjustments, steroid injection, or carpal tunnel release.",
        "precaution": "Avoid sustained awkward wrist flexion or repetitive high-vibration power tools."
    },
    "Osteoporosis": {
        "category": "Musculoskeletal", "severity": "Moderate", "emergency": False,
        "description": "Systemic skeletal disease characterized by low bone mass and microarchitectural deterioration.",
        "symptoms": {"fragility_fracture": 10, "loss_of_height": 9, "dorsal_kyphosis_dowagers_hump": 9, "back_pain": 7},
        "required": ["fragility_fracture", "loss_of_height"],
        "treatment": "Oral/IV bisphosphonates (alendronate/zoledronic acid), calcium, vitamin D, and resistance exercise.",
        "precaution": "Implement fall-prevention home safety adjustments (remove rugs, install stair lighting)."
    },

    # --- HEMATOLOGY & ONCOLOGY ---
    "Iron Deficiency Anemia": {
        "category": "Hematological", "severity": "Moderate", "emergency": False,
        "description": "Microcytic hypochromic anemia resulting from inadequate total body iron stores.",
        "symptoms": {"extreme_fatigue": 10, "pale_conjunctiva": 10, "brittle_spoon_nails_koilonychia": 9, "pica_ice_craving": 8, "shortness_of_breath": 8, "headache": 6},
        "required": ["extreme_fatigue", "pale_conjunctiva"],
        "treatment": "Oral ferrous sulfate/ascorbic acid, iron-rich diet, and identifying GI or menstrual blood loss etiology.",
        "precaution": "Take iron with vitamin C on an empty stomach; avoid co-administering with calcium or tea."
    },
    "Vitamin B12 Deficiency": {
        "category": "Hematological", "severity": "Moderate", "emergency": False,
        "description": "Macrocytic megaloblastic anemia and subacute combined spinal cord degeneration from B12 deficiency.",
        "symptoms": {"beefy_red_tongue_glossitis": 10, "peripheral_neuropathy": 10, "gait_ataxia": 9, "fatigue": 8, "memory_fog": 8},
        "required": ["beefy_red_tongue_glossitis", "peripheral_neuropathy"],
        "treatment": "Intramuscular hydroxycobalamin or cyanocobalamin injections, followed by high-dose oral supplementation.",
        "precaution": "Never treat B12 deficiency with folate alone; this masks anemia while allowing neurological degeneration to progress."
    },
    "Thrombocytopenia": {
        "category": "Hematological", "severity": "Serious", "emergency": True,
        "description": "Abnormally low circulating blood platelet count exposing patient to spontaneous cutaneous and visceral bleeding.",
        "symptoms": {"petechiae_pinpoint_rash": 10, "easy_severe_bruising": 10, "spontaneous_nosebleeds": 9, "bleeding_gums": 8, "heavy_menses": 8},
        "required": ["petechiae_pinpoint_rash", "easy_severe_bruising"],
        "treatment": "Corticosteroids, IVIG, platelet transfusions if actively bleeding, and discontinuing culprit drugs.",
        "precaution": "Avoid intramuscular injections, contact sports, and antiplatelet drugs (aspirin)."
    },
    "Sickle Cell Crisis": {
        "category": "Hematological", "severity": "Emergency", "emergency": True,
        "description": "Vaso-occlusion by rigid polymerizing sickle erythrocytes causing profound tissue ischemia and infarction.",
        "symptoms": {"severe_bone_joint_pain": 10, "dactylitis_hand_swelling": 10, "jaundice": 8, "fever": 7, "fatigue": 8, "chest_pain": 8},
        "required": ["severe_bone_joint_pain", "dactylitis_hand_swelling"],
        "treatment": "Aggressive IV opioid analgesia, oxygen, rapid hydration, hydroxyurea, and transfusion therapy.",
        "precaution": "Sudden chest pain, cough, and hypoxia indicate acute chest syndrome requiring emergency ICU review."
    },

    # --- SYSTEMIC, EMERGENCY & TOXICOLOGY ---
    "Heat Stroke": {
        "category": "Emergency", "severity": "Emergency", "emergency": True,
        "description": "Life-threatening thermoregulatory failure causing core hyperthermia (>40°C) with central nervous system dysfunction.",
        "symptoms": {"core_hyperthermia_above_40c": 10, "hot_anhidrotic_dry_skin": 10, "altered_mental_state": 10, "rapid_bounding_pulse": 8, "delirium_coma": 9},
        "required": ["core_hyperthermia_above_40c", "altered_mental_state"],
        "treatment": "Immediate conductive immersion in ice water, evaporative misting with fans, and aggressive fluid resuscitation.",
        "precaution": "Critical medical emergency; mortality exceeds 50% if cooling is delayed beyond 30 minutes."
    },
    "Heat Exhaustion": {
        "category": "Emergency", "severity": "Moderate", "emergency": False,
        "description": "Water-electrolyte depletion syndrome caused by heavy exertion in high ambient heat and humidity.",
        "symptoms": {"profuse_sweating": 10, "dizziness_lightheadedness": 9, "pale_cool_clammy_skin": 9, "nausea": 7, "muscle_heat_cramps": 8, "headache": 7},
        "required": ["profuse_sweating", "pale_cool_clammy_skin"],
        "treatment": "Move to a cool shade/air-conditioned environment, elevate feet, loosen tight clothing, and sip chilled electrolyte water.",
        "precaution": "If the patient stops sweating or becomes confused, they have progressed to fatal heat stroke."
    },
    "Dehydration": {
        "category": "Emergency", "severity": "Moderate", "emergency": False,
        "description": "Negative water balance accompanied by electrolyte shifts impairing normal cardiovascular and metabolic function.",
        "symptoms": {"intense_thirst": 10, "dry_mucous_membranes": 9, "dark_concentrated_urine": 9, "sunken_eyes": 8, "skin_turgor_tenting": 8, "dizziness": 8},
        "required": ["intense_thirst", "dark_concentrated_urine"],
        "treatment": "Oral rehydration solution (WHO-ORS), small frequent fluid sips, or IV normal saline for severe deficits.",
        "precaution": "Check urine color chart; output should be pale straw color."
    },
    "Anaphylaxis": {
        "category": "Emergency", "severity": "Emergency", "emergency": True,
        "description": "Severe, life-threatening generalized systemic hypersensitivity reaction with airway compromise and hypotension.",
        "symptoms": {"stridor_laryngeal_edema": 10, "angioedema_lip_swelling": 10, "hypotensive_shock": 10, "diffuse_urticaria": 9, "wheezing": 9},
        "required": ["stridor_laryngeal_edema", "angioedema_lip_swelling"],
        "treatment": "Immediate intramuscular adrenaline/epinephrine (0.3–0.5mg of 1:1000) into lateral thigh, high-flow oxygen, IV fluids.",
        "precaution": "Never delay epinephrine. Call emergency ambulance immediately; monitor for biphasic reactions."
    },
    "Sepsis": {
        "category": "Emergency", "severity": "Emergency", "emergency": True,
        "description": "Life-threatening organ dysfunction caused by a dysregulated systemic host response to an underlying infection.",
        "symptoms": {"hypotension_systolic_under_90": 10, "tachypnea_respiratory_rate_over_22": 10, "altered_mental_state": 10, "mottled_clammy_skin": 9, "extreme_shivering": 8},
        "required": ["hypotension_systolic_under_90", "tachypnea_respiratory_rate_over_22"],
        "treatment": "The 'Sepsis Six': high-flow oxygen, blood cultures, broad-spectrum IV antibiotics, IV fluid bolus, lactate measure, urine output monitoring.",
        "precaution": "Every hour of delayed antibiotic administration in septic shock increases mortality by approximately 7.6%."
    },
    "Systemic Lupus Erythematosus": {
        "category": "Musculoskeletal", "severity": "Serious", "emergency": False,
        "description": "Multisystem autoimmune connective tissue disease driven by antinuclear antibody (ANA) immune complex deposition.",
        "symptoms": {"malar_butterfly_rash": 10, "photosensitivity": 9, "symmetric_polyarthritis": 9, "oral_ulcers": 8, "fatigue": 8, "proteinuria": 8},
        "required": ["malar_butterfly_rash", "photosensitivity"],
        "treatment": "Hydroxychloroquine for all patients, systemic corticosteroids, mycophenolate or cyclophosphamide for nephritis.",
        "precaution": "Avoid direct ultraviolet sunlight; routine urinalysis required to detect silent lupus nephritis."
    }
}

# ---------------------------------------------------------------------------
# EXTENDED CONTRADICTIONS & RED-FLAG WARNING TRIGGERS
# ---------------------------------------------------------------------------
INITIAL_CONTRADICTIONS = [
    ("fever", "no_fever"),
    ("high_fever", "no_fever"),
    ("diarrhea", "constipation"),
    ("weight_loss", "weight_gain"),
    ("unexplained_weight_loss", "weight_gain"),
    ("bradycardia", "tachycardia"),
    ("hypotension", "hypertension")
]

INITIAL_WARNINGS = {
    "shortness_of_breath", "difficulty_breathing", "chest_pain",
    "crushing_chest_pain", "sudden_shortness_of_breath", "confusion",
    "fainting", "coughing_blood", "hemoptysis", "black_stool",
    "severe_headache", "neck_stiffness", "facial_droop",
    "one_sided_weakness", "stridor_laryngeal_edema",
    "angioedema_lip_swelling", "core_hyperthermia_above_40c",
    "hydrophobia", "rice_water_diarrhea"
}


# ---------------------------------------------------------------------------
# DATABASE INITIALIZATION AND SEEDING
# ---------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS diseases (
            name TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            severity TEXT NOT NULL,
            emergency INTEGER NOT NULL DEFAULT 0,
            description TEXT NOT NULL,
            treatment TEXT NOT NULL,
            precaution TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS symptoms (
            id TEXT PRIMARY KEY,
            note TEXT DEFAULT 'Standard clinical observation fact.',
            warning_flag INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS disease_symptoms (
            disease_name TEXT NOT NULL,
            symptom_id TEXT NOT NULL,
            weight INTEGER NOT NULL,
            is_required INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (disease_name, symptom_id),
            FOREIGN KEY (disease_name) REFERENCES diseases(name) ON DELETE CASCADE,
            FOREIGN KEY (symptom_id) REFERENCES symptoms(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS contradictions (
            symptom_a TEXT NOT NULL,
            symptom_b TEXT NOT NULL,
            PRIMARY KEY (symptom_a, symptom_b)
        );
        CREATE TABLE IF NOT EXISTS evaluation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            present_facts TEXT NOT NULL,
            absent_facts TEXT NOT NULL,
            top_disease TEXT NOT NULL,
            top_score REAL NOT NULL,
            candidate_count INTEGER NOT NULL
        );
    """)

    # Seed the complete dataset using INSERT OR REPLACE
    all_symptoms = set()
    for d_name, d_val in INITIAL_KB.items():
        cur.execute(
            "INSERT OR REPLACE INTO diseases VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                d_name, d_val["category"], d_val["severity"],
                1 if d_val["emergency"] else 0,
                d_val["description"], d_val["treatment"], d_val["precaution"]
            )
        )
        for s_id, weight in d_val["symptoms"].items():
            all_symptoms.add(s_id)
            is_req = 1 if s_id in d_val["required"] else 0
            cur.execute(
                "INSERT OR REPLACE INTO disease_symptoms VALUES (?, ?, ?, ?)",
                (d_name, s_id, int(weight), is_req)
            )

    for s_id in sorted(all_symptoms):
        warn = 1 if s_id in INITIAL_WARNINGS else 0
        note = "Urgent triage safety indicator." if warn else "Reported clinical observation fact."
        cur.execute("INSERT OR IGNORE INTO symptoms VALUES (?, ?, ?)", (s_id, note, warn))

    for a, b in INITIAL_CONTRADICTIONS:
        cur.execute("INSERT OR IGNORE INTO contradictions VALUES (?, ?)", (a, b))

    conn.commit()
    conn.close()


def fetch_full_state():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    kb = {}
    cur.execute("SELECT * FROM diseases ORDER BY name ASC")
    for row in cur.fetchall():
        kb[row["name"]] = {
            "category": row["category"],
            "severity": row["severity"],
            "emergency": bool(row["emergency"]),
            "description": row["description"],
            "treatment": row["treatment"],
            "precaution": row["precaution"],
            "symptoms": {},
            "required": []
        }

    cur.execute("SELECT * FROM disease_symptoms")
    for row in cur.fetchall():
        d_name = row["disease_name"]
        if d_name in kb:
            kb[d_name]["symptoms"][row["symptom_id"]] = row["weight"]
            if row["is_required"]:
                kb[d_name]["required"].append(row["symptom_id"])

    symptoms_meta = {}
    warning_facts = []
    cur.execute("SELECT * FROM symptoms ORDER BY id ASC")
    for row in cur.fetchall():
        symptoms_meta[row["id"]] = {
            "note": row["note"],
            "warning": bool(row["warning_flag"])
        }
        if row["warning_flag"]:
            warning_facts.append(row["id"])

    contradictions = []
    cur.execute("SELECT symptom_a, symptom_b FROM contradictions")
    for row in cur.fetchall():
        contradictions.append([row["symptom_a"], row["symptom_b"]])

    logs = []
    cur.execute("SELECT * FROM evaluation_logs ORDER BY id DESC LIMIT 25")
    for row in cur.fetchall():
        logs.append({
            "id": row["id"],
            "timestamp": row["timestamp"],
            "present_facts": json.loads(row["present_facts"]),
            "absent_facts": json.loads(row["absent_facts"]),
            "top_disease": row["top_disease"],
            "top_score": row["top_score"],
            "candidate_count": row["candidate_count"]
        })

    conn.close()
    return {
        "kb": kb,
        "symptoms_meta": symptoms_meta,
        "warning_facts": warning_facts,
        "contradictions": contradictions,
        "logs": logs
    }


# ---------------------------------------------------------------------------
# HTTP REST API & STATIC HANDLER
# ---------------------------------------------------------------------------
class MedixAIRequestHandler(SimpleHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            self._send_json(200, fetch_full_state())
            return
        if parsed.path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON payload."})
            return

        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()

        try:
            if parsed.path == "/api/symptoms":
                s_id = str(data.get("id", "")).strip().lower().replace(" ", "_")
                note = str(data.get("note", "Reported clinical observation fact.")).strip()
                warn = 1 if data.get("warning") else 0
                if not s_id:
                    self._send_json(400, {"error": "Symptom identifier is required."})
                    return
                cur.execute(
                    "INSERT OR REPLACE INTO symptoms (id, note, warning_flag) VALUES (?, ?, ?)",
                    (s_id, note, warn)
                )
                conn.commit()
                self._send_json(201, fetch_full_state())

            elif parsed.path == "/api/diseases":
                name = str(data.get("name", "")).strip()
                category = str(data.get("category", "")).strip()
                severity = str(data.get("severity", "Moderate")).strip()
                emergency = 1 if data.get("emergency") else 0
                description = str(data.get("description", "")).strip()
                treatment = str(data.get("treatment", "")).strip()
                precaution = str(data.get("precaution", "")).strip()
                symptoms_dict = data.get("symptoms", {})
                required_list = data.get("required", [])

                if not name or not category or not description or not symptoms_dict or not required_list:
                    self._send_json(400, {"error": "All required disease fields and premises must be provided."})
                    return

                cur.execute(
                    "INSERT OR REPLACE INTO diseases VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (name, category, severity, emergency, description, treatment, precaution)
                )
                cur.execute("DELETE FROM disease_symptoms WHERE disease_name = ?", (name,))
                for s_id, weight in symptoms_dict.items():
                    s_clean = str(s_id).strip().lower().replace(" ", "_")
                    w_val = max(1, min(10, int(weight)))
                    is_req = 1 if s_clean in required_list else 0
                    cur.execute(
                        "INSERT OR IGNORE INTO symptoms (id, note, warning_flag) VALUES (?, ?, 0)",
                        (s_clean, "Reported clinical observation fact.")
                    )
                    cur.execute(
                        "INSERT INTO disease_symptoms VALUES (?, ?, ?, ?)",
                        (name, s_clean, w_val, is_req)
                    )
                conn.commit()
                self._send_json(201, fetch_full_state())

            elif parsed.path == "/api/contradictions":
                a = str(data.get("symptom_a", "")).strip().lower().replace(" ", "_")
                b = str(data.get("symptom_b", "")).strip().lower().replace(" ", "_")
                if not a or not b or a == b:
                    self._send_json(400, {"error": "Two distinct symptoms are required."})
                    return
                cur.execute("INSERT OR IGNORE INTO contradictions VALUES (?, ?)", (a, b))
                conn.commit()
                self._send_json(201, fetch_full_state())

            elif parsed.path == "/api/logs":
                present = data.get("present_facts", [])
                absent = data.get("absent_facts", [])
                top_disease = str(data.get("top_disease", "None"))
                top_score = float(data.get("top_score", 0.0))
                candidate_count = int(data.get("candidate_count", 0))
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cur.execute(
                    "INSERT INTO evaluation_logs (timestamp, present_facts, absent_facts, top_disease, top_score, candidate_count) VALUES (?, ?, ?, ?, ?, ?)",
                    (ts, json.dumps(present), json.dumps(absent), top_disease, top_score, candidate_count)
                )
                conn.commit()
                self._send_json(201, fetch_full_state())

            else:
                self._send_json(404, {"error": "Endpoint not found."})
        finally:
            conn.close()

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/logs":
            conn = sqlite3.connect(DB_FILE)
            conn.execute("DELETE FROM evaluation_logs")
            conn.commit()
            conn.close()
            self._send_json(200, fetch_full_state())
        else:
            self._send_json(404, {"error": "Endpoint not found."})


if __name__ == "__main__":
    init_db()
    server = HTTPServer(("0.0.0.0", PORT), MedixAIRequestHandler)
    print(f"MEDIXAI Full-Stack Server running at http://localhost:{PORT}")
    print(f"Connected to embedded SQLite database: {os.path.abspath(DB_FILE)}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        server.server_close()