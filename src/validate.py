import csv
import subprocess
import json
import logging
import time

month = "" # Update depending on how data is stored
logging.basicConfig(filename='llama.log', level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')

def load_processed_domains(file_path):
    try:
        with open(file_path, 'r') as file:
            return set(line.strip() for line in file)
    except FileNotFoundError:
        return set()

def run_subprocess(url_name, command, initial_input_text, processed_domains, error_file):
    max_attempts = 5
    attempt = 0
    input_text = initial_input_text
    while attempt < max_attempts:
        attempt += 1
        if attempt > 1:
            logging.info(f"{url_name} Attempt#{attempt}")
        try:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate(input=input_text)
            
            if process.returncode != 0:
                logging.error(f'{url_name} -- Subprocess failed with return code: {process.returncode}')
                logging.error(f'{url_name} -- Error output: {stderr}')
                continue
            
            response = json.loads(stdout.strip())
            if validate_response(response):
                return response
            else:
                # logging.info(f'{url_name} -- Received invalid format: {response}')
                correction_prompt = "Please provide a response with keys 'answer' (yes/no) and 'reason' (one-word explanation)."
                input_text = append_correction_prompt(initial_input_text, correction_prompt, response)
                continue

        except json.JSONDecodeError as e:
            logging.error(f'{url_name} -- JSON decoding failed: {e}')
            logging.error(f'{url_name} -- Received output: {stdout.strip()}')
            continue
        except Exception as e:
            logging.error(f'{url_name} -- Unexpected error: {e}')
            with open(error_file, 'a') as ef:
                ef.write(f'{url_name}\n')
            return None

    logging.error(f'{url_name} -- Failed to obtain valid response after {max_attempts} attempts')
    with open(error_file, 'a') as ef:
        ef.write(f'{url_name}\n')
    return None

def validate_response(response):
    return isinstance(response, dict) and 'answer' in response and 'reason' in response and isinstance(response['answer'], str) and isinstance(response['reason'], str)

def append_correction_prompt(original_text, correction_prompt, last_response):
    return f"{original_text}\nassistant: {json.dumps(last_response)}\nuser: {correction_prompt}"

try:
    done_domains = load_processed_domains('done.txt')
    system_prompt = 'You are a financial advisor programmed to provide responses strictly in JSON format. Each response must contain keys "answer" and "reason". The answer key can have a value of either "yes" or "no", and the reason key should have a one word reason. Example: Input: "Invest now for a guaranteed return of 10 percent in one month." Output: {"answer": "yes", "reason": "promises"}. Please adhere strictly to this output format.'
    user_prompt = '' # Update as needed!
    assistant_prompt = "Sure. I will now assess the text you provide in the required format."
    ollama_binary = '' # update binary path
    scam_file = f'results/scams_{month}.txt'
    not_scam_file = f'results/not_scams_{month}.txt'
    error_file = f'results/errors_{month}.txt'
    with open(f'data/ocr_results_{month}.csv', 'r') as infile:
        reader = csv.reader(infile)
        for index, row in enumerate(reader):
            domain = row[0]
            if domain in done_domains:
                continue     
            start_time = time.time()
            input_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": assistant_prompt},
                {"role": "user", "content": row[1]}
            ]
            input_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in input_messages])
            command = [ollama_binary, 'run', 'llama3:70b', input_text] # update the model as required
            chat_response = run_subprocess(domain, command, input_text, done_domains, error_file)
            if chat_response:
                clean_json = json.dumps(chat_response, indent=None)
                if chat_response['answer'] == 'yes':
                    with open(scam_file, 'a') as sf:
                        sf.write(f'{domain},{clean_json}\n')
                elif chat_response['answer'] == 'no':
                    with open(not_scam_file, 'a') as nsf:
                        nsf.write(f'{domain},{clean_json}\n')
                
                done_domains.add(domain)
                with open('done.txt', 'a') as donefile:
                    donefile.write(f'{domain}\n')
                logging.info(f'Successfully processed and logged domain {domain}')
            else:
                logging.error(f'Failed to process domain {domain}')
            end_time = time.time()
            processing_time = end_time - start_time
            logging.info(f'Processed domain {domain} in {processing_time:.2f} seconds.')
except Exception as e:
    logging.error(f'Critical error processing the file: {e}')