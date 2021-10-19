from pymongo.write_concern import WriteConcern
from pymodm import  MongoModel, fields


class GroupDeployData(MongoModel):
    parent_cid = fields.CharField()
    jira_id = fields.CharField()
    cid = fields.CharField()
    job_name = fields.CharField(required=True, primary_key=True)
    repo_url = fields.CharField()
    branch = fields.CharField()
    class Meta:
        write_concern = WriteConcern(j=True)
