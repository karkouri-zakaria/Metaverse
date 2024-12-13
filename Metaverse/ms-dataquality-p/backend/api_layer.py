from flask import Flask, request, jsonify
from flask_cors import CORS
from backend.dataquality import DataQualityService
from backend.dataconnect import DataconnectBackend
import os
from dotenv import load_dotenv
import logging



#load_dotenv()
env_file = '.env'
load_dotenv(env_file, override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


# Initialize services
db_name = os.getenv('DB_NAME')
dqs = DataQualityService(db_name)
dcb = DataconnectBackend(db_name)

@app.route('/api/datasets/<user_id>', methods=['GET'])
def get_datasets(user_id):
    try:
        datasets = dcb.get_all_datasets(user_id)
        logger.info(f"datasets are: {datasets}")
        return jsonify([
            {
                'id': dataset[0],
                'name': dataset[3],  # Assuming file_name is at index 3
                'bucket': dataset[2],  # Assuming bucket_name is at index 2
                'type': dataset[6],  # Assuming file_type is at index 6
            }
            for dataset in datasets
        ]), 200
    except Exception as e:
        return jsonify({'error during ......': str(e)}), 500

@app.route('/api/generate-rules', methods=['POST'])
def generate_rules():
    data = request.json
    dataset_id = data.get('datasetId')
    
    if not dataset_id:
        return jsonify({'error': 'Dataset ID is required'}), 400

    try:
        result = dqs.process_selected_dataset(dataset_id)
        if result:
            #dataframe, metadata, rules_df = result
            
            # Convert rules_df to a list of dictionaries
            #rules = rules_df.to_dict('records')
            
            # Process rules to match the expected format
            #logger.info(f"result:\n {result}")
            processed_rules = [
                {
                    'title': rule['Rule'],
                    'incidents': 'No Applicable',  # You may want to calculate this
                    'dataset': result['metadata']['file_name'],
                    'health': 'No Applicable'  # You may want to calculate this
                    #'sql_query': rule['SQL Query']
                }
                for rule in result['rules']
            ]
            
            return jsonify(processed_rules), 200
        else:
            return jsonify({'error': 'Failed to process dataset'}), 400
    except Exception as e:
        #logger.info(f"result:\n {result}")
        print({result})
        return jsonify({'error in this stage': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)