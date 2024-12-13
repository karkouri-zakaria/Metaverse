from asyncio.log import logger
import os
import gitlab
import asyncio
import logging
from dotenv import load_dotenv

env_file = '.env'
load_dotenv(env_file, override=True)

class GitLabUtils:
    def __init__(self):
        self.gl = gitlab.Gitlab(
            os.getenv('GITLAB_URL'),
            private_token=os.getenv('PRIVATE_TOKEN')
        )
        self.project_id = os.getenv('PROJECT_ID')
        self.pipeline_branch = os.getenv('PIPELINE_BRANCH')

    async def trigger_pipeline(self, variables, is_delete=False):
        project = await asyncio.to_thread(self.gl.projects.get, self.project_id)
        
        if is_delete:
            variables.append({'key': 'DELETE_RESOURCES', 'value': 'true'})

        try:
            pipeline = await asyncio.to_thread(project.pipelines.create, {
                'ref': self.pipeline_branch,
                'variables': variables
            })
            #print(pipeline)
            #status_message = "Delete pipeline triggered. Manual approval required." if is_delete else "Pipeline triggered successfully."
            return pipeline
            #status_message = "Delete pipeline triggered. Manual approval required." if is_delete else "Pipeline triggered successfully."
            #return pipeline #, status_message
        except gitlab.exceptions.GitlabCreateError as err:
            logger.error(f"GitLab error occurred: {err}")
            return None

    async def check_pipeline_status(self, pipeline_id):
        try:
            project = await asyncio.to_thread(self.gl.projects.get, self.project_id)
            pipeline = await asyncio.to_thread(project.pipelines.get, pipeline_id)
            return pipeline.status
        except gitlab.exceptions.GitlabGetError as err:
            logger.error(f"Failed to retrieve pipeline status: {err}")
            return "failed"

    async def get_last_stage_jobs(self, pipeline_id):
        project = await asyncio.to_thread(self.gl.projects.get, self.project_id)
        pipeline = await asyncio.to_thread(project.pipelines.get, pipeline_id)
        stages = await asyncio.to_thread(pipeline.stages.list)
        last_stage = stages[-1]
        jobs = await asyncio.to_thread(last_stage.jobs.list)
        return jobs

    async def approve_delete_job(self, pipeline_id):
        project = await asyncio.to_thread(self.gl.projects.get, self.project_id)
        pipeline = await asyncio.to_thread(project.pipelines.get, pipeline_id)

        delete_job = None
        for job in await asyncio.to_thread(pipeline.jobs.list):
            if job.name == 'delete' and job.status == 'manual':
                delete_job = job
                break

        if delete_job:
            try:
                await asyncio.to_thread(delete_job.play)
                return "Delete job approved and started."
            except gitlab.exceptions.GitlabError as err:
                return f"Error approving delete job: {err}"
        else:
            return "Delete job not found or not in manual state."

    
""" import os
import gitlab
from dotenv import load_dotenv

 # Load environment variables from .env file
load_dotenv()

class GitLabUtils:
    def __init__(self):
        self.trigger_gl = gitlab.Gitlab(
            os.getenv('GITLAB_URL'),
            private_token=os.getenv('TRIGGER_PRIVATE_TOKEN')
        )
        #self.delete_gl = gitlab.Gitlab(
        #    os.getenv('GITLAB_URL'),
        #    private_token=os.getenv('DELETE_PRIVATE_TOKEN')
        #)
        self.project_id = os.getenv('PROJECT_ID')
        self.trigger_branch = os.getenv('TRIGGER_BRANCH')
        self.delete_branch = os.getenv('DELETE_BRANCH')

    def trigger_pipeline(self, variables):
        project = self.trigger_gl.projects.get(self.project_id)
        pipeline = project.pipelines.create({'ref': self.trigger_branch, 'variables': variables})
        return pipeline

    def check_pipeline_status(self, pipeline_id):
        project = self.trigger_gl.projects.get(self.project_id)
        pipeline = project.pipelines.get(pipeline_id)
        return pipeline.status

    def get_last_stage_jobs(self, pipeline_id):
        project = self.trigger_gl.projects.get(self.project_id)
        pipeline = project.pipelines.get(pipeline_id)
        stages = pipeline.stages.list()
        last_stage = stages[-1]
        jobs = last_stage.jobs.list()
        return jobs

    def delete_trigger_gitlab_pipeline(self, user_id, instance_id, instance_type):
        project = self.trigger_gl.projects.get(self.project_id)
        try:
            pipeline = project.pipelines.create({
                'ref': self.delete_branch,
                'variables': [
                    {'key': 'USER_ID', 'value': user_id},
                    {'key': 'INSTANCE_ID', 'value': instance_id},
                    {'key': 'INSTANCE_TYPE', 'value': instance_type}
                ]
            })
            return pipeline.id, pipeline.status
        except gitlab.exceptions.GitlabCreateError as err:
            return f"GitLab error occurred: {err}" """
