import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from pydantic import BaseModel
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.checker import DataQualityChecker
from backend.gitlab_utils import GitLabUtils
from backend.database import Database
from backend.dataquality import DataQualityService

# Load environment variables
env_file = '.env'
if not load_dotenv(env_file, override=True):
    raise RuntimeError("Failed to load environment variables from .env file.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS for all routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
try:
    db = Database()
    dqs = DataQualityService()
    gl_utils = GitLabUtils()
    checker = DataQualityChecker()
except Exception as e:
    logger.error("Failed to initialize services: %s", str(e))
    raise

# Define Pydantic models
class Dataset(BaseModel):
    id: str
    name: str

class QualityRule(BaseModel):
    column: str
    rule_name: str
    query: str

class QualityCheckCreate(BaseModel):
    type: str
    name: str
    description: str
    rule: QualityRule
    dataset: Dataset

@app.post("/api/data-quality/dataset/generate-checks")
async def generate_quality_rules(dataset: Dataset):
    try:
        result = dqs.process_selected_dataset(dataset.model_dump())
        if result:
            df = result["dataframe"]
            metadata = result["metadata"]
            rules = result["rules"]
            return {"dataframe": df, "metadata": metadata, "rules": rules}
        else:
            raise HTTPException(status_code=500, detail="Failed to generate quality rules.")
    except Exception as e:
        logger.error("Error generating quality rules: %s", str(e))
        raise HTTPException(status_code=500, detail="Error in processing dataset quality rules.")

@app.post("/api/data-quality/dataset/apply-check")
async def apply_quality_check(quality_check: QualityCheckCreate):
    try:
        check_result = checker.generate_and_save_quality_report(quality_check.dataset.model_dump(), quality_check.rule)
        return check_result
    except Exception as e:
        logger.error("Error applying quality check: %s", str(e))
        raise HTTPException(status_code=500, detail="Error applying quality check.")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=1002)
