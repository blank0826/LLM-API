from flask import Flask, jsonify, request
from flask_cors import CORS
from llm_guard import scan_output, scan_prompt
from llm_guard.input_scanners import Anonymize, PromptInjection, InvisibleText, Toxicity, BanTopics, Secrets
from llm_guard.output_scanners import Deanonymize, NoRefusal, Relevance, Sensitive, Bias  
from llm_guard.input_scanners.toxicity import MatchType
from llm_guard.vault import Vault

import urllib.request
import json

app = Flask(__name__)
CORS(app, support_credentials=True)

url = 'https://Phi-3-mini-4k-instruct-csocq-serverless.eastus2.inference.ai.azure.com/v1/chat/completions'
api_key = 'oUAoPlQg7egFHKUCIdXG12L8aNOqllGO'

def llm_inference(input_prompt):
    data =  {
    "messages": [
        {
        "role": "user",
        "content": input_prompt
        }
    ],
    "max_tokens": 1024,
    "temperature": 0.7,
    "top_p": 1
    }
    body = str.encode(json.dumps(data))
    if not api_key:
        raise Exception("A key should be provided to invoke the endpoint")
    headers = {'Content-Type':'application/json', 'Authorization':('Bearer '+ api_key)}
    req = urllib.request.Request(url, body, headers)
    try:
        response = urllib.request.urlopen(req)
        result = response.read().decode('utf-8')
        return result
    except urllib.error.HTTPError as error:
        print("The request failed with status code: " + str(error.code))
        print(error.info())
        print(error.read().decode("utf8", 'ignore'))

@app.route('/api/data', methods=['GET'])
def check_prompt(): 
    prompt = request.args.get('prompt')
    print("prompt", prompt)
    
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400
    
    banTopics = ["violence", "threat", "illegal", "hacking", "drugs", "forgery", "self harm", "adult content", "explicit material", "unsafe practices", 
                     "dangerous stunts", "conspiracy"]
    
    scanner =  BanTopics(topics=banTopics, threshold=0.1)
    output_model = scanner._classifier(prompt, banTopics, multi_label=False)
    label_score = dict(zip(output_model["labels"], output_model["scores"]))  
    topic_scores_list = [{'name': name, 'value': value} for name, value in label_score.items()]
    sanitized_prompt, valid_ban_topics, result_score_ban_topics = scanner.scan(prompt)
    
    vault = Vault()
    input_scanners = [Anonymize(vault), InvisibleText(), PromptInjection(), Secrets(redact_mode="partial")]
    output_scanners = [Deanonymize(vault), NoRefusal(), Relevance(), Sensitive(), Bias()]

    sanitized_prompt, results_valid_prompt, results_score_prompt = scan_prompt(input_scanners, prompt)

    response_text = llm_inference(prompt).strip()

    sanitized_response_text = scan_output(
        output_scanners, sanitized_prompt, response_text
    )
    
    response = [{"metric":"Secrets", "value": float(results_score_prompt['Secrets']) * 100, "sanitized_prompt": sanitized_prompt, "alert": results_valid_prompt['Secrets'], "response": sanitized_response_text},{"metric": "Anonymize", "value": float(results_score_prompt['Anonymize']) * 100, "sanitized_prompt": sanitized_prompt, "alert": results_valid_prompt['Anonymize'], "response" : sanitized_response_text},{"metric":"Invisible Text", "value":  float(results_score_prompt['InvisibleText']) * 100, "sanitized_prompt": sanitized_prompt, "alert": results_valid_prompt['InvisibleText'], "response" : sanitized_response_text}, {"metric":"Prompt Injection", "value": float(results_score_prompt['PromptInjection']) * 100, "sanitized_prompt": sanitized_prompt, "alert": results_valid_prompt['PromptInjection'], "response": sanitized_response_text},{"metric":"Ban Topics", "value": float(result_score_ban_topics) * 100, "sanitized_prompt": sanitized_prompt, "alert": valid_ban_topics, "response": sanitized_response_text, "sub_metrics": topic_scores_list}]
    
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
    
