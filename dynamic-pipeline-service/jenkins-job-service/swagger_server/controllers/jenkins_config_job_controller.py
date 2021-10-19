################################################# MAINTAINER dynamic-pipeline_Dev@company.com ####################################
# OBJECTIVE
#     Job Config flo takes the yaml data and configures the jenkins job template and creates a jenkins job
#
# NAME
#     jenkins_config_job_controller.py
#
# FUNCTIONS
#      invoke_job_config(body)
#      invoke_slotswap(body)
#
################################################# MAINTAINER dynamic-pipeline_Dev@company.com ####################################
import os
import uuid
import requests
import connexion
import yaml
from flask import current_app as app
from custom_framework import flo
from custom_framework.notification_engine import notification_engine_util
from custom_framework.util import mail
from healthcheck import HealthCheck, EnvironmentDump

from swagger_server import constants
from swagger_server.models.group_deploy_model import GroupDeployData
from swagger_server.utils.fileutil import FileUtil
from swagger_server.utils.fileutil import connect_to_db
from swagger_server.utils.fileutil import get_pipeline_data, swap_deployment_processing,get_artifact_data
from swagger_server.utils.fileutil import set_github_jenkinswebhook_url
from swagger_server.utils.jenkinsConfigJobwutil import jenkinsConfigJobwUtil
from swagger_server.utils.fileutil import create_jenkins_folder,jenkins_job_creation

notification_util = notification_engine_util.NotificationEngineUtil()
jenkins_flo = jenkinsConfigJobwUtil()
fileutil = FileUtil()

current_file_name = os.path.basename(__file__)


def invoke_job_config(body):  # noqa: E501
    continous_builder = app.config.get('continous_builder')
    artifact_repo = app.config.get('artifact_repo')
    issue_tracker = app.config.get('issue_tracker')
    mail_from = app.config.get('MAIL_FROM')
    flo_name = constants.FLO_NAME

    log = app.config.get('log')
    log.info("log: " + str(log))
    database_url = app.config.get('database_url')
    if connexion.request.is_json:
        builder_info = None
        yaml_data = connexion.request.get_json()
        log.info("yaml_data: " + str(yaml_data))
        corelation_id = yaml_data.get('cid')
        artifact_url =  None
        source_code = None
        sonarqube_url = None
        try:
            app_repo = yaml_data.get('repo_name')
            organization = yaml_data.get('organization')
            repo_host = yaml_data.get('repo_host')
            branch = yaml_data.get('branch')

            # DDO-2941
            if yaml_data.get('app_type') == constants.DOCKER and yaml_data.get('deploy_type') == constants.KUBERNETES:
                nexus_api_url = constants.DOCKER_NEXUS_API_URL_KUBERNETES
                artifact_repository = constants.DOCKER_ARTIFACT_REPOSITORY
            # DDO-2940
            elif (yaml_data.get('deploy_type') == constants.KUBERNETES) and (yaml_data.get('app_type') == constants.ANGULAR or yaml_data.get('app_type') == constants.companySTUDIO):
                nexus_api_url = constants.DOCKER_NEXUS_API_URL
                artifact_repository = constants.DOCKER_ARTIFACT_REPOSITORY
            else:
                # DDO-2937, DDO-2939 raw repo
                # Artifact validation support Angular_linux, Angular_static, php_linuxwepapps
                nexus_api_url = constants.NEXUS_API_URL
                artifact_repository = app.config.get('artifact_repository')

            log.status(corelation_id, flo.STATUS.RECEIVED, "received request from execute-flo")
            log.event(corelation_id, "received content type is application/json")
            log.status(corelation_id, flo.STATUS.IN_PROCESS, "started processing :" + str(app_repo))
            commited_user_mail = yaml_data.get("committed_user_mail")
            if yaml_data.get('pipeline'):
                builder_info = get_pipeline_data(yaml_data, continous_builder, log)
            else:
                msg = "Pipeline data was missing, Could you please verify" \
                      " whether pipeline data was included in the yaml file"
                log.status(corelation_id, mail.STATUS.ERROR, msg)
                log.critical(msg)
                return send_alerts(log, msg, corelation_id, mail.STATUS.ERROR, mail.STATUS.CRITICAL)

            name = None
            if len(builder_info) != 0:
                name = builder_info.get('name')
                log.event(corelation_id,
                          "successfully fetched the continuous_builder tool data from pipeline configuration")
            else:
                msg = "Continuous builder tool data is not available in pipeline configuration"
                log.status(corelation_id, mail.STATUS.ERROR, msg)
                log.critical(msg)
                return send_alerts(log, msg, corelation_id, mail.STATUS.ERROR, mail.STATUS.CRITICAL)

            if name == 'jenkins':
                log.event(corelation_id, "connecting to the jenkins server")
                log.info('builder_info : ' + str(builder_info))
                log.info('yaml_data : ' + str(yaml_data))
                primary_server, msg = jenkins_flo.jenkins_server_connection(builder_info)
                if primary_server is None:
                    log.status(corelation_id, mail.STATUS.ERROR, msg)
                    return send_alerts(log, msg, corelation_id, mail.STATUS.ERROR, mail.STATUS.CRITICAL)
                try:
                    primary_server.job_exists(organization)
                except Exception as e:
                    log.error(e, corelation_id)
                    msg = "Jenkins Server connection Failed from dynamic-pipeline"
                    log.status(corelation_id, mail.STATUS.ERROR, msg)
                    return send_alerts(log, msg, corelation_id, mail.STATUS.ERROR, mail.STATUS.CRITICAL)
                log.event(corelation_id, "jenkins server connection success")
                repo_name = yaml_data.get('repo_name')
                appcode = yaml_data.get('app').get('code')
                repo_host = yaml_data.get('repo_host')
                # Bitbucket integration to fetch the Project name and scm repo url
                repo_type = yaml_data.get('repo_type')
                if constants.BITBUCKET_REPO_TYPE in repo_type:
                    bb_repo_url = repo_host.split('/')
                    organization = bb_repo_url[-1]
                    # Setting the repo_url to scm url of bitbucket
                    repo_host_url = repo_host.split('/')
                    repo_host_bb = repo_host_url[0:3]
                    repo_host_bb.append('scm')
                    repo_host_bb.append(repo_host_url[4])
                    repo_host_bb.append(repo_host_url[6])
                    repo_host = ''
                    for url in repo_host_bb:
                        repo_host = repo_host + '/' + url
                    repo_host = repo_host[1:] + '.git'
                    yaml_data['repo_host'] = repo_host

                environment = yaml_data.get('environment')
                if environment == constants.MULTI_KEY:
                    yaml_data['jenkins_template'] = constants.MULTI_DEFAULT_JENKINS_TEMPLATE
                jenkins_template = yaml_data.get('jenkins_template', None)
                log.info('jenkins_template : ' + str(jenkins_template))
                user_jenkins_template = None
                if jenkins_template is None:
                    msg = "Jenkins template type is not provided in division yaml file,jenkins_template need to be pipeline_scm or pipeline_managed"
                    log.status(corelation_id, mail.STATUS.ERROR, " jenkins template type is not provided ")
                    log.error(msg)
                    return send_alerts(log, msg, corelation_id, mail.STATUS.ERROR, mail.STATUS.ERROR)

                jenkins_metadata = yaml_data.get('jenkins_metadata', None)
                if jenkins_metadata is not None:
                    template_mapper = jenkins_metadata.get('template_mapper', None)
                    if template_mapper is not None:
                        user_jenkins_template = template_mapper.get(jenkins_template)
                        log.info('user_jenkins_template first inside : ' + str(user_jenkins_template))
                        if user_jenkins_template is None and jenkins_template.lower() in [constants.KEY_PIPELINE_SCM,
                                                                                          constants.KEY_PIPELINE_MANAGED,
                                                                                          constants.KEY_MULTIBRANCH_SCM]:
                            msg = "in flo.yml jenkins_template configuration xml file is not available"
                            log.critical(msg)
                            log.status(corelation_id, mail.STATUS.ERROR, msg)
                            return send_alerts(log, msg, corelation_id, mail.STATUS.ERROR, mail.STATUS.CRITICAL)
                    else:
                        msg = "In flo.yml jenkins_template mapper is not available - " + (jenkins_template)
                        log.critical(msg)
                        log.status(corelation_id, mail.STATUS.ERROR, msg)
                        return send_alerts(log, msg, corelation_id, mail.STATUS.ERROR, mail.STATUS.CRITICAL)
                else:
                    msg = "In flo.yml jenkins_metadata is not available"
                    log.critical(msg)
                    log.status(corelation_id, mail.STATUS.ERROR, msg)
                    return send_alerts(log, msg, corelation_id, mail.STATUS.ERROR, mail.STATUS.CRITICAL)
                non_dev_environments = yaml_data.get('non-dev-environments')
                if non_dev_environments is None:
                    non_dev_environments_list = constants.NON_DEV_ENVIRONMENTS
                else:
                    non_dev_environments_list = non_dev_environments.get('env_list', None)
                    if non_dev_environments_list is None:
                        non_dev_environments_list = constants.NON_DEV_ENVIRONMENTS
                log.debug("checking the environment in non dev environments ")
                jenkins_job_name = appcode + '_' + environment
                credential_id = app.config.get('git_global_user')
                # DDO-2621
                # <----- DDO-3006 updating jenkins job url

                jenkins_url =  builder_info['url'] + "job/" + organization + "/job/" + jenkins_job_name.replace('/','/job/')
                mail_meta_content = {"Jenkin Url":  jenkins_url
                                     }

                # END of DDO-3006 ----->
                if environment in non_dev_environments_list:
                    # If it is a non dev environment check if user have provided source_env and build_number
                    # build_number represents the artifact number that need to be downloaded
                    # source_env this is to check whether the artifact exist in that environment
                    log.event(corelation_id, "Validating the follow up hierarchy")
                    # Todo check the artifacts enabled in pipeline scm job also
                    # DDO-2621

                    mail_meta_content['Artifact version'] = str(yaml_data['app']['version']) + "." + str(
                        yaml_data['build_number'])

                    nexus_app_repo = artifact_repository
                    if yaml_data.get('nexus_app_repo') is not None:
                        nexus_app_repo = yaml_data['nexus_app_repo']
                    version = yaml_data.get('app').get('version')
                    build_number = yaml_data.get("build_number")
                    source_env = yaml_data.get("source_env")
                    if build_number is None or source_env is None:
                        msg = "build number or source_env is not presented in application yml"
                        log.status(corelation_id, mail.STATUS.ERROR, msg)
                        log.error(msg)
                        return send_alerts(log, msg, corelation_id, mail.STATUS.ERROR, mail.STATUS.ERROR)
                    artifact_nexus_info = get_pipeline_data(yaml_data, artifact_repo, log)
                    if len(artifact_nexus_info) == 0:
                        msg = "nexus builder tool data is not available in pipeline configuration"
                        log.status(corelation_id, mail.STATUS.ERROR, msg)
                        log.critical(msg)
                        return send_alerts(log, msg, corelation_id, mail.STATUS.ERROR, mail.STATUS.CRITICAL)
                    nexus_url = artifact_nexus_info.get('url')
                    mfy_repo = artifact_nexus_info.get('mfy_repo')
                    log.event(corelation_id, "checking the artifacts present in nexus")
                    nexus_reponce, error_msg = jenkins_flo.artifacts_check_in_nexus(yaml_data, nexus_url,
                                                                                    nexus_app_repo, nexus_api_url,
                                                                                    mfy_repo)
                    if nexus_reponce is None:
                        msg = "Artifacts checking failed for this version : " + str(
                            version) + " and build number : " + str(build_number) + " : " + str(error_msg)
                        log.status(corelation_id, mail.STATUS.ERROR,
                                   str(jenkins_job_name) + " artifacts checking in nexus")
                        log.error(msg)
                        return send_alerts(log, msg, corelation_id, mail.STATUS.ERROR, mail.STATUS.ERROR)
                    log.event(corelation_id, "artifacts are available in nexus")
                    if jenkins_template.lower() == constants.KEY_PIPELINE_MANAGED :
                        source_code,artifact_url,sonarqube_url = get_artifact_data(yaml_data,nexus_url,nexus_app_repo,log)
                        if source_code and artifact_url:
                            mail_meta_content['Source Code'] = source_code
                            mail_meta_content['Artifact URL'] = artifact_url
                        if sonarqube_url:
                            mail_meta_content['SonarQube Report'] = sonarqube_url
                else:
                    log.event(corelation_id, "This is development job no need to check followup hierarchy")
                jenkins_config_file, error_msg, new_jira_id, deploy_time, folder_template = fileutil.get_configure_new_file(
                    yaml_data,
                    environment,
                    primary_server,
                    builder_info,
                    credential_id,
                    'deploy',artifact_url,source_code,sonarqube_url)
                log.debug('jenkins_config_file : ' + str(jenkins_config_file))
                if jenkins_config_file is None:
                    if str(error_msg).__contains__('JiraError'):
                        msg = 'Error while creating JIRA for approval ' + '<br>' + str(error_msg)
                    else:
                        msg = "Jenkins Job configuration failed - " + '<br>' + str(error_msg)
                    log.status(corelation_id, mail.STATUS.ERROR, str(jenkins_job_name) + " job updated ")
                    log.error(msg)
                    return send_alerts(log, msg, corelation_id, mail.STATUS.ERROR, mail.STATUS.ERROR)
                log.info("Job name is :" + str(jenkins_job_name))
                log.info("checking if the job exists in jenkins")
                try:
                    jenkins_job_exist_check = primary_server.job_exists(organization + '/' + jenkins_job_name)
                except Exception as e:
                    log.error(e, corelation_id)
                    msg = "Jenkins Server Connection failed"
                    return send_alerts(log, msg, corelation_id, mail.STATUS.ERROR, mail.STATUS.ERROR)
                if not jenkins_job_exist_check:
                    log.event(corelation_id, jenkins_job_name + " job does not exist in jenkins, creating new job")
                    try:
                        jenkins_job_creation(primary_server, organization, jenkins_job_name, jenkins_config_file, log,
                                             corelation_id)

                    except Exception as e:
                        log.info(str(e), corelation_id)
                        try:
                            create_jenkins_folder(primary_server, jenkins_job_name, organization, folder_template)
                            jenkins_job_creation(primary_server, organization, jenkins_job_name, jenkins_config_file,
                                                 log,
                                                 corelation_id)
                        except Exception as e:
                            log.error(str(e), corelation_id)
                            # DDO-2621
                            return send_alerts(log, str(e), corelation_id, mail.STATUS.ERROR,
                                           mail.STATUS.ERROR, mail_meta_content)
                    log.event(corelation_id, "successfully created Jenkins job :" + str(jenkins_job_name))
                else:
                    log.event(corelation_id, jenkins_job_name + " job exist in jenkins, updating job")
                    try:
                        deploy_job_type_info = primary_server.get_job_info(organization + '/' + jenkins_job_name)
                    except Exception as e:
                        log.error(e, corelation_id)
                        msg = "Jenkins Server Connection failed"
                        return send_alerts(log, msg, corelation_id, mail.STATUS.ERROR, mail.STATUS.CRITICAL)
                    deploy_job_type = deploy_job_type_info.get('_class').split('.')[-1]
                    if deploy_job_type.lower() == constants.WORKFLOW_JOB or deploy_job_type.lower() == constants.WORKFLOWMULTIBRANCH_PROJECT:
                        log.event(corelation_id,
                                  jenkins_job_name + " - exist job is " + deploy_job_type + " updation is possible")
                        try:
                            job_request_deploy = primary_server.reconfig_job(organization + '/' + jenkins_job_name,
                                                                             jenkins_config_file)
                            log.debug(str(job_request_deploy))

                        except Exception as e:
                            msg = "Jenkins Job updation failed - " + organization + '/' + jenkins_job_name
                            log.status(corelation_id, mail.STATUS.ERROR, str(jenkins_job_name) + " job updated ")
                            log.error(msg + str(e), corelation_id)
                            # DDO-2621
                            return send_alerts(log, msg, corelation_id, mail.STATUS.ERROR,
                                               mail.STATUS.ERROR, mail_meta_content)
                        log.event(corelation_id, "successfully updated Jenkins job :" + str(jenkins_job_name))

                    else:
                        msg = jenkins_job_name + " - job is a " + deploy_job_type + \
                              " type configured job, so freestyle to pipeline updation is not possible "
                        log.status(corelation_id, mail.STATUS.ERROR, str(jenkins_job_name) + " job updated ")
                        log.error(msg)
                        # DDO-2621
                        return send_alerts(log, msg, corelation_id, mail.STATUS.ERROR, mail.STATUS.ERROR,
                                           mail_meta_content
                                           )

                group_support_check = yaml_data.get('group')
                if group_support_check == True:
                    parent_cid = yaml_data.get('parent_cid')
                    is_dev_job = yaml_data.get('is_dev_job')
                    job_full_name = organization + '/' + jenkins_job_name
                    repo_url = repo_host
                    if repo_host.endswith('.git'):
                        repo_url = repo_url[:-4]
                    try:
                        connect_to_db(corelation_id)
                        if not is_dev_job:
                            insert_groupdeploydata = GroupDeployData(parent_cid=parent_cid, jira_id=new_jira_id,
                                                                     cid=corelation_id, job_name=job_full_name,
                                                                     repo_url=repo_url, branch=branch).save()
                        else:
                            insert_groupdeploydata = GroupDeployData(parent_cid=parent_cid,
                                                                     cid=corelation_id, job_name=job_full_name,
                                                                     repo_url=repo_url, branch=branch).save()
                        log.debug(insert_groupdeploydata)
                    except Exception as e:
                        return send_alerts(log, e, corelation_id, mail.STATUS.ERROR, mail.STATUS.ERROR)
                    return job_full_name, 200
                if new_jira_id is not None:
                    if mail_from is None:
                        log.info("configured mail_from is none using default", corelation_id)
                        mail_from = constants.DEFAULT_MAIL_FROM
                    repo_url = yaml_data.get('repo_host')
                    if repo_url.endswith('.git'):
                        repo_url = repo_url[:-4]

                    # approvers_list = non_dev_environments.get('approvers', None)
                    # if approvers_list is None:
                    #     msg = "The Jira Approvers List is empty can't process this job"
                    #     notification_util.insert_message(corelation_id, database_url, msg, mail.STATUS.INFO,
                    #                                          flo_name)
                    #     return 'Success', HTTPStatus.OK
                    # approvers_mails_to = ",".join(approvers_list)

                    build_notification_users = yaml_data.get('notification_users')
                    if build_notification_users is None:
                        build_notification_users = []
                    mail_cc_list = [commited_user_mail] + build_notification_users
                    mail_cc = ",".join(mail_cc_list)
                    if mail_cc is None:
                        mail_cc = constants.DEFAULT_MAIL_CC
                    jira_info = get_pipeline_data(yaml_data, issue_tracker, log)
                    jira_url = jira_info.get('url')
                    jira_id_url = str(jira_url) + "/browse/" + str(new_jira_id)
                    workflo_old_status = yaml_data.get('jira', {}).get('workflo_old_status')
                    if workflo_old_status is None:
                        workflo_old_status = constants.WORKFLO_OLD_STATUS
                    workflow_new_status = yaml_data.get('jira', {}).get('workflow_new_status')
                    if workflow_new_status is None:
                        workflow_new_status = constants.WORKFLO_NEW_STATUS
                    message = constants.APPROVAL_MSG
                    extra_params = {constants.JOB_NAME: jenkins_job_name, constants.JIRA_URL: jira_id_url,
                                    constants.APPROVAL_STATUS: workflo_old_status + " to " + workflow_new_status}
                    if deploy_time:
                        extra_params[constants.DEPLOY_TIME_KEY] = deploy_time
                    notification_util.insert_message(corelation_id, database_url, message, mail.STATUS.INFO, flo_name,
                                                     extra_params=extra_params)

                log.status(corelation_id, mail.STATUS.SUCCESS, "dynamic-pipeline-service completed")
                if environment == 'multi':
                    jenkins_url = builder_info.get('url')
                    status_code = set_github_jenkinswebhook_url(jenkins_url, repo_host, organization)
                    if status_code == 201:
                        log.event(corelation_id,
                                  "successfully created the jenkins web hook in " + repo_name + " repository")
                    elif status_code == 422:
                        log.event(corelation_id,
                                  "Already configured the jenkins web hook in " + repo_name + " repository")
                    else:
                        log.event(corelation_id,
                                  "failed to  created the jenkins web hook in " + repo_name + " repository")
                message = constants.JOB_CONFIGURE_MESSAGE
                notification_util.insert_message(corelation_id, database_url, message, mail.STATUS.INFO, flo_name,
                                                 extra_params=mail_meta_content)

                return "dynamic-pipeline-service completed successfully ", 200

        except Exception as e:
            log.error(e, corelation_id)
            msg = constants.JOB_CONFIG_FAIL_ERROR.format(str(current_file_name), '<br>', str(e), '<br>')
            send_alerts(log, msg, corelation_id, mail.STATUS.ERROR, mail.STATUS.CRITICAL)
            return msg, 500
    else:
        corelation_id = str(uuid.uuid4().hex)
        mail_from = app.config.get('MAIL_FROM')
        mail_to = constants.DEFAULT_MAIL_TO
        msg = "Media type is not supported 415"
        flo_name = constants.FLO_NAME
        log.status(corelation_id, mail.STATUS.ERROR, msg)
        log.critical(msg)
        notification_util.insert_message(corelation_id, database_url, msg, mail.STATUS.ERROR, flo_name)
        notification_util.send_notifications(corelation_id, notification_from=mail_from, notification_to=mail_to)
        return msg, 415


def send_alerts(log, msg, corelation_id, error, status, extra_params=None):
    database_url = app.config.get('database_url')
    flo_name = constants.FLO_NAME
    notification_util.insert_message(corelation_id, database_url, msg, status, flo_name, extra_params)
    return msg, 500


# Slot Swap Integration
def invoke_slot_swap(body):
    log = app.config.get('log')
    log.info("Invoke Slot Swap is initiated")
    database_url = app.config.get('database_url')
    if connexion.request.is_json:
        response_data = connexion.request.get_json()
        log.info("response_data: " + str(response_data))

        # call slotswap_utils
        message, status = swap_deployment_processing(response_data)
        log.info(message)
        return message, status
    else:
        corelation_id = str(uuid.uuid4().hex)
        mail_from = app.config.get('MAIL_FROM')
        mail_to = constants.DEFAULT_MAIL_TO
        msg = "Media type is not supported 415"
        flo_name = constants.FLO_NAME
        log.status(corelation_id, mail.STATUS.ERROR, msg)
        log.critical(msg)
        notification_util.insert_message(corelation_id, database_url, msg, mail.STATUS.ERROR, flo_name)
        notification_util.send_notifications(corelation_id, notification_from=mail_from, notification_to=mail_to)
        return msg, 415


def application_data():
    return True, {"maintainer": "dynamic-pipeline",
                  "Service Name": "dynamic-pipeline-service",
                  "Support": "DevOps_Support@company.com",
                  "git_repo": "https://git-server.company.com/Digital-DevOps/dynamic-pipeline-service"}


def environment_check():
    flo_env = os.environ.get(constants.ENV_NAME)
    vault_env = os.environ.get(constants.VAULT_NAME)
    if flo_env is None or len(flo_env.strip()) == 0:
        print(constants.ENV_NAME + " env variable not set server not healthy ")
        return False, 500
    if vault_env is None or len(vault_env.strip()) == 0:
        print(constants.VAULT_NAME + " env variable not set  server not healthy")
        return False, 500
    return True, 200


def healthcheck():
    health = HealthCheck()
    health.add_check(application_data)
    health.add_check(environment_check)
    health_status = health.run()
    return yaml.safe_load(health_status[0])


def getenvironment():
    envcheck = EnvironmentDump()
    envcheck.add_section("application data", application_data)
    env_status = envcheck.run()
    return yaml.safe_load(env_status[0])
