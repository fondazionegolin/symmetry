from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import os
import base64
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def index(request):
    return render(request, 'core/index.html')

@csrf_exempt
def save_photo(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            image_data = data.get('image').split(',')[1]
            image_bytes = base64.b64decode(image_data)
            
            # Create filename with timestamp
            filename = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = os.path.join('media', 'photos', filename)
            
            # Save the image
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            return JsonResponse({'success': True, 'filename': filename})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def detect_gender(text):
    # Lista di parole chiave per il genere
    male_indicators = ['sono un ragazzo', 'sono un uomo', 'sono maschio', 'mi chiamo ', 'io sono ']
    female_indicators = ['sono una ragazza', 'sono una donna', 'sono femmina', 'mi chiamo ', 'io sono ']
    
    # Nomi maschili e femminili più comuni in Italia
    male_names = ['alessandro', 'andrea', 'antonio', 'giuseppe', 'giovanni', 'mario', 'luigi', 'roberto', 'stefano', 'paolo', 'francesco', 'marco', 'luca', 'bruno', 'angelo', 'carlo', 'franco', 'domenico', 'giorgio', 'piero']
    female_names = ['maria', 'anna', 'giuseppina', 'rosa', 'angela', 'giovanna', 'teresa', 'lucia', 'carmela', 'anna maria', 'antonia', 'carla', 'elena', 'rita', 'paola', 'francesca', 'laura', 'luisa', 'sara', 'valentina']
    
    text = text.lower()
    
    # Cerca indicatori espliciti
    for indicator in male_indicators:
        if indicator in text:
            after_indicator = text[text.find(indicator) + len(indicator):].strip().split()[0]
            if after_indicator in male_names:
                return 'male'
            
    for indicator in female_indicators:
        if indicator in text:
            after_indicator = text[text.find(indicator) + len(indicator):].strip().split()[0]
            if after_indicator in female_names:
                return 'female'
    
    # Cerca nomi nel testo
    words = text.split()
    for word in words:
        if word in male_names:
            return 'male'
        if word in female_names:
            return 'female'
    
    return None

@csrf_exempt
def process_answers(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        answers = data.get('answers', [])
        
        # Debug print
        print("Received answers:", answers)
        
        # Detect gender from first answer
        gender = detect_gender(answers[0]) if answers else None
        gender_prefix = "una donna" if gender == "female" else "un uomo" if gender == "male" else "una persona"
        
        # Create a conversation with the user's answers
        conversation = f"""
        Persona:
        {answers[0]}
        
        Ricordo d'infanzia:
        {answers[2] if len(answers) > 2 else ""}
        
        Evento fondamentale:
        {answers[3] if len(answers) > 3 else ""}
        
        Visione del futuro:
        {answers[4] if len(answers) > 4 else ""}
        """
        
        # Debug print
        print("Conversation for GPT:", conversation)
        
        # Generate prompts using OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": f"""You are an expert in creating Stable Diffusion prompts. Generate three artistic prompts based on the user's life story.
                The user is {gender_prefix}, keep this in mind when generating the prompts.
                Format each prompt with these Stable Diffusion best practices:
                - Start with the main subject ({gender_prefix}) and its key characteristics
                - Add artistic style (e.g., 'vintage photograph', 'oil painting', 'cinematic')
                - Include lighting and atmosphere details
                - Add camera perspective if relevant
                - Include artist references or art movements if appropriate
                - End with quality boosters like 'highly detailed', 'masterpiece', 'vintage film grain'
                
                Return EXACTLY 3 prompts in this format:
                (childhood) prompt text here
                (adult) prompt text here
                (elderly) prompt text here
                
                Each prompt must be on its own line with the age marker in parentheses.
                Make sure each prompt is complete and descriptive."""},
                {"role": "user", "content": conversation}
            ]
        )
        
        # Parse the response to extract three prompts
        response_text = response.choices[0].message.content.strip()
        prompt_lines = [line.strip() for line in response_text.split('\n') if line.strip()]
        
        print("GPT Response:", response_text)
        print("Parsed lines:", prompt_lines)
        
        prompts = {
            "childhood": next((line.replace('(childhood)', '').strip() for line in prompt_lines if '(childhood)' in line), ''),
            "adult": next((line.replace('(adult)', '').strip() for line in prompt_lines if '(adult)' in line), ''),
            "elderly": next((line.replace('(elderly)', '').strip() for line in prompt_lines if '(elderly)' in line), '')
        }

        # Print prompts for debugging
        print("Final prompts:")
        for age, prompt in prompts.items():
            print(f"{age}: {prompt}")

        # Generate images using DALL-E
        images = {}
        for age, prompt in prompts.items():
            if prompt:  # Only generate if we have a prompt
                try:
                    print(f"Generating {age} image with prompt: {prompt}")
                    response = client.images.generate(
                        model="dall-e-3",
                        prompt=f"A photorealistic {prompt}. The image should be highly detailed and cinematic.",
                        size="1024x1024",
                        quality="standard",
                        n=1
                    )
                    images[age] = response.data[0].url
                    print(f"Successfully generated {age} image")
                except Exception as e:
                    images[age] = None
                    print(f"Error generating {age} image: {str(e)}")
            else:
                images[age] = None
                print(f"No prompt available for {age}")
        
        result = {
            "prompts": prompts,
            "images": images
        }
        print("Sending response:", result)
        return JsonResponse(result)
    return JsonResponse({'error': 'Invalid request method'})