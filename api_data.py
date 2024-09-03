from flask import Flask, jsonify, request

import llm_guard as lg
from llm_guard import scan_output, scan_prompt
from llm_guard.input_scanners import Anonymize, PromptInjection, TokenLimit, Toxicity
from llm_guard.output_scanners import Deanonymize, NoRefusal, Relevance, Sensitive
from llm_guard.input_scanners.toxicity import MatchType
from llm_guard.vault import Vault

import urllib.request
import json

app = Flask(__name__)

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
    
    print("promtp", prompt)
    
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400
    
    # check toxicity
    
    scanner = Toxicity(threshold=0.5, match_type=MatchType.SENTENCE)

    sanitized_prompt1, is_valid1, risk_score1 = scanner.scan(prompt)
    
    response_text = llm_inference(prompt).strip()
    
    # vault = Vault()
    # input_scanners = [Anonymize(vault), Toxicity(), TokenLimit(), PromptInjection()]
    # output_scanners = [Deanonymize(vault), NoRefusal(), Relevance(), Sensitive()]
    
    # sanitized_prompt, results_valid, results_score = scan_prompt(input_scanners, prompt)
    # if any(results_valid.values()) is False:
    #     print(f"Prompt {prompt} is not valid, scores: {results_score}")
    #     exit(1)

    # print(f"Prompt: {sanitized_prompt}")


    # response_text = llm_inference(prompt).strip()


    # sanitized_response_text, results_valid, results_score = scan_output(
    #     output_scanners, sanitized_prompt, response_text
    # )
    # if any(results_valid.values()) is False:
    #     print(f"Output {response_text} is not valid, scores: {results_score}")
    #     exit(1)

    # print(f"Output: {sanitized_response_text}\n")
    
    
    response = [{"metric":"toxicity", "value": risk_score1 * 100, "sanitized_prompt": sanitized_prompt1, "alert": not is_valid1, "response" : "responseText"}, {"metric":"sentiment", "value":"20", "sanitized_prompt": "All not cool", "alert": "false", "response": "responseText"}]
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(debug=True)
    
