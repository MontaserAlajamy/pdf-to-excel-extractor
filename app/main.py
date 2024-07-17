from flask import Flask, request, render_template, send_file
import os
import tabula
import pandas as pd
from werkzeug.utils import secure_filename
import requests
from io import StringIO

app = Flask(__name__)

UPLOAD_FOLDER = '/app/uploads'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clean_table(df):
    df.dropna(how='all', inplace=True)
    df.dropna(how='all', axis=1, inplace=True)
    return df.reset_index(drop=True)

def refine_with_groq(df, api_key):
    headers = {"Authorization": f"Bearer {api_key}"}
    prompt = f"Clean and format the following table data:\n\n{df.to_csv(index=False)}"
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json={
                "model": "mixtral-8x7b-32768",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5,
                "max_tokens": 1000
            }
        )
        if response.status_code == 200:
            refined_csv = response.json()['choices'][0]['message']['content'].strip()
            return pd.read_csv(StringIO(refined_csv))
        else:
            return df
    except Exception:
        return df

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('index.html', message='No file part')
        file = request.files['file']
        if file.filename == '':
            return render_template('index.html', message='No selected file')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            output_format = request.form.get('output_format', 'xlsx')
            llm_choice = request.form.get('llm_choice', 'No Refinement')
            api_key = request.form.get('api_key', '')
            
            tables = tabula.read_pdf(filepath, pages='all', multiple_tables=True)
            refined_tables = []
            for table in tables:
                cleaned_table = clean_table(table)
                if llm_choice == "Groq API" and api_key:
                    refined_table = refine_with_groq(cleaned_table, api_key)
                else:
                    refined_table = cleaned_table
                refined_tables.append(refined_table)
            
            output_filename = f"extracted_tables.{output_format}"
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
            
            if output_format == 'xlsx':
                with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                    for i, table in enumerate(refined_tables):
                        table.to_excel(writer, sheet_name=f'Table_{i+1}', index=False)
            else:
                if len(refined_tables) == 1:
                    refined_tables[0].to_csv(output_path, index=False)
                else:
                    for i, table in enumerate(refined_tables):
                        table.to_csv(f"{output_path[:-4]}_Table_{i+1}.csv", index=False)
            
            return send_file(output_path, as_attachment=True)
        
    return render_template('index.html')

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True, host='0.0.0.0')