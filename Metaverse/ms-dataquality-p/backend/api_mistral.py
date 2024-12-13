import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



# Fonction pour générer des règles de qualité des données et leurs scripts SQL pour une colonne donnée
def generate_quality_rules_with_sql(api_key, column_name):
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": "mistral-small-latest",
        "messages": [
            {
                "role": "user",
                "content": f"Generate data quality rule names for the following column: {column_name}. For each rule, also provide the SQL script to check the rule. Format: 'Rule: RuleName | SQL Query: <sql_script>'"
            }
        ],
        "temperature": 0.7,
        "top_p": 1,
        "max_tokens": 1024,  
        "stream": False,
        "safe_prompt": False,
        "random_seed": 1337
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # Raise an exception for bad status codes
        response_data = response.json()
        content = response_data.get("choices", [])[0].get("message", {}).get("content", "")
        logger.info(f"API response for {column_name}: {content[:150]}...")  # Print first 100 characters of response
        return content
    except Exception as e:
        logger.info(f"Error generating rules for {column_name}: {str(e)}")
        return ""