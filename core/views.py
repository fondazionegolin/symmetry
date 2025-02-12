from django.shortcuts import render
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
import json
import os
import time
from datetime import datetime
import openai
from django.conf import settings
from dotenv import load_dotenv
import base64
from openai import OpenAI
load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def index(request):
    return render(request, 'core/index.html')

@csrf_exempt
def serve_json(request, filename):
    try:
        print(f"Serving JSON file: {filename}")
        json_dir = os.path.join(settings.BASE_DIR, 'json')
        json_path = os.path.join(json_dir, filename)
        print(f"Full path: {json_path}")
        
        if not os.path.exists(json_path):
            print(f"File not found at: {json_path}")
            print(f"JSON directory is: {json_dir}")
            print(f"Directory contents: {os.listdir(json_dir) if os.path.exists(json_dir) else 'directory not found'}")
            return JsonResponse({'error': 'File not found'}, status=404)
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Successfully loaded JSON data: {data}")
            return JsonResponse(data)
            
    except Exception as e:
        print(f"Error serving JSON: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

def get_questions():
    return [
        "Con chi ho il piacere di parlare?",
        "Hai piacere che ti scatti una foto per personalizzare ulteriormente l'esperienza?",
        "Ok, adesso che siamo in confidenza, mi vuoi parlare di un tuo ricordo d'infanzia? Descrivilo minuziosamente...",
        "E c'è qualche avvenimento recente che vorresti raccontarmi?",
        "Hai avuto una vita ricca finora. Non avere paura del tempo! Adesso prova a immaginarti in vecchiaia, immagina una scena che ti veda protagonista."
    ]

def determine_gender(name):
    # Lista di desinenze comuni per nomi maschili e femminili in italiano
    male_endings = ['o', 'e', 'i', 'n', 'k', 'r', 'd', 't']
    female_endings = ['a', 'e']
    
    name = name.lower().strip()
    
    # Eccezioni comuni
    male_exceptions = ['andrea', 'luca', 'mattia', 'elia', 'noah', 'tobia']
    female_exceptions = ['alice', 'beatrice', 'nicole']
    
    if name in male_exceptions:
        return 'male'
    if name in female_exceptions:
        return 'female'
    
    # Controllo desinenza
    if name[-1] in male_endings and name[-1] not in female_endings:
        return 'male'
    if name[-1] in female_endings and name not in male_exceptions:
        return 'female'
    
    # Default a maschile se non riusciamo a determinare
    return 'male'

def generate_scene_prompts(answers):
    try:
        print("Generating scene prompts for answers:", answers)
        
        prompts = []
        scenes = [
            {"description": answers[2], "età": "infanzia", "live_clip": "nature"},
            {"description": answers[3], "età": "presente", "live_clip": "urban"},
            {"description": answers[4], "età": "futuro", "live_clip": "scifi"}
        ]
        
        for scene in scenes:
            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": """
                        Sei un esperto nella creazione di prompt per Stable Diffusion. 
                        Genera un prompt dettagliato in inglese per creare un'immagine digitale artistica.
                        Il prompt deve:
                        1. Descrivere una scena vivida e dettagliata
                        2. Includere dettagli su stile artistico, illuminazione e atmosfera
                        3. Mantenere un tono poetico e suggestivo
                        4. Essere lungo circa 2-3 frasi
                        """},
                        {"role": "user", "content": f"Genera un prompt per questa scena: {scene['description']}"}
                    ],
                    temperature=0.7
                )
                
                prompt = response.choices[0].message.content.strip()
                print(f"Generated prompt for {scene['età']}: {prompt}")
                
                prompts.append({
                    "prompt": prompt,
                    "live_clip": scene["live_clip"],
                    "età": scene["età"]
                })
                
            except Exception as e:
                print(f"Error generating prompt for scene {scene['età']}: {str(e)}")
                # Fallback prompt in caso di errore
                prompts.append({
                    "prompt": f"Create a digital painting of a person experiencing this moment: {scene['description']}",
                    "live_clip": scene["live_clip"],
                    "età": scene["età"]
                })
        
        print("Generated all prompts successfully:", prompts)
        return prompts
        
    except Exception as e:
        print("Error in generate_scene_prompts:", str(e))
        raise

def get_user_code():
    # Mappa dei mesi in lettere
    month_map = {
        1: 'A', 2: 'B', 3: 'C', 4: 'D', 5: 'E', 6: 'F',
        7: 'G', 8: 'H', 9: 'I', 10: 'J', 11: 'K', 12: 'L'
    }
    
    now = datetime.now()
    month_letter = month_map[now.month]
    day_str = f"{now.day:02d}"  # Giorno in formato 01, 02, ecc.
    
    # Leggo il contatore corrente
    counter_file = os.path.join('json', 'user_counter.txt')
    try:
        if os.path.exists(counter_file):
            with open(counter_file, 'r') as f:
                counter = int(f.read().strip())
        else:
            counter = 0
    except:
        counter = 0
    
    # Incremento il contatore
    counter += 1
    
    # Salvo il nuovo valore
    os.makedirs('json', exist_ok=True)
    with open(counter_file, 'w') as f:
        f.write(str(counter))
    
    # Converto il contatore in formato alfanumerico (A1-Z9)
    tens = (counter - 1) // 10  # 0-9 per A-J
    units = counter % 10  # 0-9
    
    # Converto le decine in lettere (A-J)
    tens_letter = chr(65 + tens) if tens < 26 else 'Z'
    
    # Il codice finale sarà: [mese][giorno][decine][unità]
    # Esempio: B12A1 per 12 febbraio, primo utente
    user_code = f"{month_letter}{day_str}{tens_letter}{units}"
    
    return user_code

@csrf_exempt
def get_user_code_endpoint(request):
    if request.method == 'GET':
        user_code = get_user_code()
        return JsonResponse({'user_code': user_code})
    return JsonResponse({'error': 'Metodo non consentito'}, status=405)

@csrf_exempt
def save_photo(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            image_data = data.get('image').split(',')[1]
            image_bytes = base64.b64decode(image_data)
            
            # Create filename with timestamp
            filename = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = os.path.join(settings.MEDIA_ROOT, filename)
            
            # Save the image
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            return JsonResponse({'success': True, 'filename': filename})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def process_answers(request):
    if request.method == 'POST':
        try:
            print("\n=== Processing new request ===")
            print("POST data:", request.POST)
            print("FILES:", request.FILES)
            
            # Ottieni le risposte dal FormData
            answers_str = request.POST.get('answers')
            print("Raw answers string:", answers_str)
            
            if not answers_str:
                return JsonResponse({'error': 'Nessuna risposta ricevuta'})
            
            try:
                answers = json.loads(answers_str)
                print("Parsed answers:", answers)
            except json.JSONDecodeError as e:
                print("JSON decode error:", str(e))
                return JsonResponse({'error': 'Errore nel parsing delle risposte'})
            
            # Ottieni il codice utente
            user_code = request.POST.get('user_code')
            print("User code:", user_code)
            
            if not user_code:
                return JsonResponse({'error': 'Codice utente mancante'})
            
            if not isinstance(answers, list):
                return JsonResponse({'error': 'Le risposte devono essere una lista'})
            
            if len(answers) != 5:
                print(f"Invalid number of answers: {len(answers)}")
                return JsonResponse({'error': f'Numero di risposte non valido: ricevute {len(answers)}, attese 5'})
            
            # Gestione della foto
            if 'photo' in request.FILES:
                photo = request.FILES['photo']
                print("Processing photo:", photo.name)
                try:
                    # Assicurati che la directory media esista
                    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
                    # Salva la foto con il codice utente nel nome
                    photo_path = os.path.join(settings.MEDIA_ROOT, f"{user_code}_photo.jpg")
                    with open(photo_path, 'wb+') as destination:
                        for chunk in photo.chunks():
                            destination.write(chunk)
                    print("Photo saved successfully at:", photo_path)
                except Exception as e:
                    print("Error saving photo:", str(e))
                    return JsonResponse({'error': f'Errore nel salvare la foto: {str(e)}'})
            
            try:
                # Genera i prompt per le scene
                scene_prompts = generate_scene_prompts(answers)
                print("Scene prompts generated successfully")
            except Exception as e:
                print("Error generating scene prompts:", str(e))
                return JsonResponse({'error': f'Errore nella generazione dei prompt: {str(e)}'})
            
            # Crea il dizionario con i dati
            try:
                output_data = {
                    'name': answers[0],
                    'user_code': user_code,
                    'photo_consent': answers[1].lower() in ['sì', 'si', 'yes', 'ok', 'certo'],
                    'memories': {
                        'childhood': scene_prompts[0],
                        'recent': scene_prompts[1],
                        'future': scene_prompts[2]
                    }
                }
                print("Output data created successfully")
            except Exception as e:
                print("Error creating output data:", str(e))
                return JsonResponse({'error': f'Errore nella creazione dei dati: {str(e)}'})
            
            try:
                # Assicurati che la directory json esista
                json_dir = os.path.join(settings.BASE_DIR, 'json')
                os.makedirs(json_dir, exist_ok=True)
                
                # Usa solo il codice utente come nome file
                json_filename = f"{user_code}.json"
                json_path = os.path.join(json_dir, json_filename)
                
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=4)
                
                print("JSON saved successfully:", json_path)
                print("=== Request processed successfully ===\n")
                
                return JsonResponse({
                    'message': 'Dati salvati con successo',
                    'json_file': json_filename
                })
            except Exception as e:
                print("Error saving JSON:", str(e))
                return JsonResponse({'error': f'Errore nel salvare il file JSON: {str(e)}'})
            
        except Exception as e:
            import traceback
            print("\n=== Error in process_answers ===")
            print("Error:", str(e))
            print("Traceback:", traceback.format_exc())
            print("=== End error report ===\n")
            return JsonResponse({'error': f'Errore durante l\'elaborazione: {str(e)}'})
            
    return JsonResponse({'error': 'Metodo non consentito'}, status=405)