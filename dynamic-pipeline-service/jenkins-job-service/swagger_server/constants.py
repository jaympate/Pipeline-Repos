from custom_framework.log_util import logger

PROJECT_RELEASE = '1.56'

ENV_NAME = 'APP_ENV'
MAIL_FROM = "noreply-dynamic-pipeline-{}@company.com"
JENKINS_MAIL_FROM = "noreply-jenkins-{}@company.com"
VAULT_NAME = 'VAULT_TOKEN'
NON_DEV_ENVIRONMENTS = ['qa', 'uat', 'master']
FOLLOW_HIERARCHY = "enable"
ARTIFACTS_VALIDATION = 'enable'
DEPLOY_JOB_EXTENTION = '_deploy'
FREESTYLE_PROJECT = 'freestyleproject'
WORKFLOW_JOB = 'workflowjob'
WORKFLOWMULTIBRANCH_PROJECT = "workflowmultibranchproject"
HEADER_CID = 'CID'
HEADER_REPO_URL = 'Repo url'
DEFAULT_MAIL_FROM = "noreply-dynamic-pipeline@company.com"
JIRA_URL = "Jira url"
JIRA_ADDITIONAL_ASSIGNEE = "Additional Assignee"
APPROVAL_MSG = "This job requires action from approvers"
JOB_NAME = "Job name"
ISSUE_TYPE = "Action Item"
JIRA_FIELD_CHECK = "status"
WORKFLO_OLD_STATUS = "QA Review"
WORKFLO_NEW_STATUS = "Resolved"
APPROVAL_STATUS = "Approval"
PIPELINE_PATH = "{template_version}/pipeline"
JENKINS_FILE = 'Jenkinsfile'
PIPELINE_EXT = "groovy"
ENV = "env"
ENV_TYPE = "env_type"
PROD_TYPE_ENV = "prod"
NON_DEV = "non-dev"
NON_DEV_BOOLEAN_TRUE = "true"
NON_DEV_BOOLEAN_FALSE = "false"
DEV = "dev"
KEY_PIPELINE_MANAGED = "pipeline_managed"
KEY_JENKINS_METADATA = "jenkins_metadata"
KEY_PIPELINE_MAPPER = "pipeline_mapper"
KEY_MULTIBRANCH_SCM = "multibranch_scm"
KEY_PIPELINE_SCM = "pipeline_scm"
KEY_PIPELINE_CUSTOM = "pipeline_custom"
SRIPTFILE_ERROR_MSG = "The script file is not presented in the git path - "
JENKINS_FILE_ERROR_MSG = "There is no Jenkinsfile in the application repo, Please verify-"
ARGUMENTS = "arguments"
DOTNET = "dotnet"
DOCKER = "docker"
ADB2C = "adb2c"
KUBERNETES ="kubernetes"
companySTUDIO = "companystudio"

NEXUS_API_URL = 'https://{nexus_url}/service/rest/v1/search?repository={nexus_repo}&name={organization}/{artifact_no_ext}/{version}.{build_number}/{artifact_no_ext}-{version}.{build_number}'
DOCKER_ARTIFACT_REPOSITORY= "Digital-Devops-Docker"
DOCKER_NEXUS_API_URL_KUBERNETES = 'https://{nexus_url}/service/rest/v1/search?repository={nexus_repo}&name={app_name}&version={version}.{build_number}'
DOCKER_NEXUS_API_URL = 'https://{nexus_url}/service/rest/v1/search?repository={nexus_repo}&name={app_name}-{source_env}&version={version}.{build_number}'
ANGULAR = "angular"
RELEASE = "Release"
JENKINS_WEBHOOK_EXT = "github-webhook/"
MULTI_KEY = 'multi'
MULTI_DEFAULT_JENKINS_TEMPLATE = 'multibranch_scm'
MULTI_SUFFIX = '_multi'
SCHEDULE_TIME = 'deploy_time'
FRMT = '%d %b %Y %I:%M %p %Z'
SENTRY_URL_NA = 'http://aa329c7c9c4c45618d9d1e8b4c0841a9:b971e9b66f9f443d8ba206b675301b4f@sentry.company.com/9'
SENTRY_URL_APAC = 'https://d9ec29c1c3fe460a8dae73fb109b947e:38828160bc3c48c0b378af561d2311ef@apac-sentry.company.com/8'
APAC_REGION = 'apac'
SCHEMA_FILE = "swagger_server/schema/Configuration_schema.yml"
MSG_YAML_ERROR = "Unable to read the file content file have bad yaml content {yaml_file}"
SUB_YAML_ERROR = "Yaml File Access Error"
DEFAULT_MAIL_SUPPORT = "dynamic-pipeline_Dev@company.com"
DEFAULT_MAIL_TO = "DevOps_Support@company.com"
DEFAULT_MAIL_CC = "dynamic-pipeline_Dev@company.com"
HEADER_FLO_NAME = "flo"
SUB_CONF_VALID_SCHEMA_ERROR = "Missing Configuration Schema File"
MSG_CONF_VALID_SCHEMA_ERROR = "Schema validation file is missing, Please ensure that Configuration_schema.yml is present under schema folder"
SUB_CONF_ERROR = "Config Error"
MSG_CONF_ERROR = "Error loading the configuration from {config_file},make sure that data provided in the file is valid "
SUB_JIRAUSER_NOTFOUND = "JIRA User not Found"
MSG_JIRAUSER_NOTFOUND = "Unable to get user details of %s from JIRA , please verify user profile or user details provided "
MSG_NO_ADDITIONAL_ASSIGNEE = "None of the below approval users have access to JIRA, please verify User data : "
MSG_SENTRY_ERROR = "Error while configuring sentry, "
MSG_NO_VENV = VAULT_NAME + " environment variable is not set.Unable to proceed"
SUB_NO_VENV = VAULT_NAME + ' not set'
MSG_JIRALABEL_FORMAT_NOT_SUPPORT = "Unable to process given label data format in jira details, it support by either list or comma separated string"
VAULT_SECRET_FETCH_ERROR = "Error Getting secret from Vault "
FLO_NAME = 'Job-config-flo'
log_location = '/var/log/dynamic-pipeline/job_config_flo.log'
CONFIG_FILE = "swagger_server/conf/{flo_env}/jenkinsConfigJob_configuration.yml"
DEFAULT_LOG_FILE = "/var/log/dynamic-pipeline/job_config_flo.log"
DEFAULT_LOG_LEVEL = logger.INFO
MSG_RECEIVED = "received request"
# bitbucket constants
BITBUCKET_REPO_TYPE = 'bitbucket'

PIPELINE_INFRA_KEY = 'infra'
ONPREM_KEY = 'onprem'
MASTER_BRANCH = 'master'


REPO_URL = "Repo URL"
APP_ENV_KEY = "APP_ENV"
REPO_BRANCH = "Repo Branch"

ARTIFACTS_MISSING_ERROR = 'Artifacts is not available in application yaml'
JOB_TEMPLATE_KEY_MISSING_ERROR = 'Job template name is not available in Division Yaml, make sure to add the custom xml file name under job_template key'
SCRIPTPATH_MISSING_ERROR = 'Script Path is not available in the custom xml, which has been kept under pipeline path, make sure it should matches the groovy file name'
SCRIPTFILENAME_MISMATCH = 'The script file which is been available in xml file is not matched with the groovy file, makesure it should match with the jenkins_template name and to be placed under pipeline path.'

BUILD_SECTION_MISSING_ERROR = 'Build Tool is mandatory for lower environments(which requires build), make sure to give build_tool section in application yaml'

JOB_CONFIG_FAIL_ERROR = "Unexpected Error from Job-Config - {} {} {} {} Reach out to DevOps_Support@company.com for further details"
EST_TIMEZONE = 'US/Eastern'
INSTANT = 'instant'
MINUTES = 'minute'
HOUR = 'hour'
POLL_TIME = 60
POLL_TIME_IN_HOUR = 1

DISABLE = 'disable'
DISABLED = 'disabled'
ZERO = 0

ENV_MASTER = 'master'
ENV_PREPROD = 'preprod'
ENV_PRE_PROD = 'pre-prod'
ENV_UAT = 'uat'
ENV_DEV = 'dev'
ENV_SIT = 'sit'
ENV_TEST = 'test'

APIM_APP_ENV_PROD = 'prod'
APIM_APP_ENV_PREPROD = 'pprod'
APIM_APP_ENV_UAT = 'uat'
APIM_APP_ENV_SIT = 'sit'
APIM_APP_ENV_TEST = 'test'

DEPLOY_TIME_KEY = 'Schedule Deploy Time'
NON_SLOT_DEPLOY = 2
IS_A_SLOT_DEPLOY = 0

SLOT_DEPLOY_SCHEMA = 1.3
CALLBACK_KEY = 'callback_info'

JENKINS_ERROR = "Exception while trying to connect to Jenkins - "
JENKINS_JOB_CONFIG_SUCCESS = 'Successfully updated release as swap'
JOB_URL_NA_ERROR = 'Job url is not available, hence returned without any updation'
JENKINS_USER_NA_ERROR = 'Jenkins User is not available'
JENKINS_VKEY_NA_ERROR = 'Jenkins Vkey is not available'
XML_CONFIG_ERROR = 'Failed while getting Config XML data'
JIRA_NOT_APPROVED_ERROR = 'Jira is not approved, hence updated ecosystem as 1 and returned'
SCHEDULE_ERROR_MSG = "Slot Deployment is completed, but unable to do SWAP. Because expected schedule time is passed, by the time of jira approval"
ECOSYSTEM_READY_VALUE = 2
CONFIGURING_ECOSYSTEM = 1
NON_SLOT_DEPLOY = 3
IS_A_SLOT_DEPLOY = 0

SUCCESS_KEY = 'SUCCESS'
FAILED_KEY = 'FAILED'
SLOT_DEPLOYMENT_FAIL_MSG = 'Slot Deployment is failed, hence unable to do SWAP.'

SWAP_SCHEDULE_TRIGGER = 'Jenkins Job has been configured for SWAP Deployment and it will trigger at %s'
SWAP_JIRA_TRIGGER = 'Jenkins Job has been triggered for SWAP Deployment, as Jira is approved.'
SWAP_BEFORE_JIRA_APPROVAL = 'Jenkins Job has been configured for SWAP Deployment, job will trigger once Jira is approved'
SWAP_BEFORE_JIRA_APPROVAL_SCHEDULETIME = 'Jenkins Job has been configured for SWAP Deployment. Job will trigger at %s , if Jira is approved'

JIRA_APPROVED_VALUE = 1
JIRA_DECLINED_VALUE = 2
JIRA_NOT_APPROVED_FLAG = 0
ECOSYSTEM_VALUE_WHEN_SLOTDEPLOYMENT_FAILED = 4

DEPLOY_KEY = 'deploy'

WILD_CARD_APPROVER = '*'
JOB_CONFIGURE_MESSAGE = "Successfully configured jenkins job"

AGENT_NAME_WARNING = " We have started removing offensive terminology within the project,'slave' term was " \
                     "deprecated and replaced by the 'agent' term. Please update your yaml files and Jenkinsfiles accordingly "

#<--- Begin DPE-11889
DF_STORE_URL = 'DF_STORE_URL'
DF_STORE_APPROVERS_URL = "{df_store_url}/{flo_env}/v1/approvers.yml"
#END DPE-11889-->

#<--- Begin DPE-12851
ARTIFACT_URL_WITH_CLASSIFIER = 'https://{nexus_url}/repository/{artifact_repository}/{organization}/{artifact_no_ext}/{version}.{build_number}/{artifact_no_ext}-{version}.{build_number}-{classifier_name}.{environment}.{artifact_ext}'
ARTIFACT_URL_WITHOUT_CLASSIFIER = 'https://{nexus_url}/repository/{artifact_repository}/{organization}/{artifact_no_ext}/{version}.{build_number}/{artifact_no_ext}-{version}.{build_number}.{environment}.{artifact_ext}'
APIAPPS = "apiapps"
ARTIFACT_API_URL = "artifact_api_url"
MSBUILD = 'msbuild'
#END DPE-12851-->
APP_METADATA_API_URL='app_metadata_url'

DOCKER_KUBERNETES_IMAGE = '{docker_url}/dynamic-pipeline/{artifact_no_ext}:{version}.{build_number}'
GENERIC_KUBERNETES_IMAGE = '{docker_repository}/{artifact_no_ext}-{source_env}:{version}.{build_number}'