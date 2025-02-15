import wordninja
import tldextract
import os
from bs4 import BeautifulSoup, Comment

WORD_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'improved_crypto_words.txt.gz')
keyword_in_url = { # Update as needed!
                
            }

domain_whitelist = { # Update as needed!
    
}

lm_ninja = None
if(lm_ninja is None):
    lm_ninja = wordninja.LanguageModel(WORD_MODEL_DIR)

def match_domain_name_with_keywords(domain_name):
    for domain_kw in domain_whitelist:
        if(domain_name.endswith(domain_kw)):
            return False
    extracted = tldextract.extract(domain_name)
    domain_without_tld = extracted.domain
    if extracted.subdomain:
        domain_without_tld = extracted.subdomain + '.' + domain_without_tld
    domain_name_splits = set(lm_ninja.split(domain_without_tld))
    for url_keyword in keyword_in_url:
        if url_keyword in domain_name_splits: return True
    return False