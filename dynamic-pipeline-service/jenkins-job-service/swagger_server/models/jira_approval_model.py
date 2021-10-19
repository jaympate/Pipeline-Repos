from pymongo.write_concern import WriteConcern
from pymodm import  MongoModel, fields


class JiraMetadata(MongoModel):
    jira_id = fields.CharField(required=True, primary_key=True)
    cid = fields.CharField()
    job_name = fields.CharField()
    commit_id = fields.CharField()
    workflow_status = fields.CharField()
    new_workflow_status = fields.CharField()
    approved = fields.IntegerField()
    deploy_time = fields.CharField()
    jira_approve_time = fields.CharField()
    ecosystem_ready = fields.IntegerField()
    deploy_type = fields.CharField()

    class Meta:
        write_concern = WriteConcern(j=True)
