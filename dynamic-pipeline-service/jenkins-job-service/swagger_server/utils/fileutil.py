################################################# MAINTAINER DIO-OffShore@company.com ####################################
# OBJECTIVE
#     Builds a Jenkins template with the provided parameters and job requirements
#
# NAME
#     fileutil.py
#
# FUNCTIONS
#     get_configure_new_file(self, yaml_data, environment, primary_server, credential_id=None, job_type=None)
#
#     jenkins_configuration(jenkins_info, yaml_data, corelation_id, job_type, credential_id,builder,app_type)
#
#     get_pipeline_data_list(yaml_data)
#
#     set_parameters_pipelineinfo(pipe_line_tool_data_list,jenkins_parameters)
#
#     data_convert_tfs_format(yaml_data, key_append, tf_data_vars)
#
#     get_job_templates(raw_url)
#
#      get_multibranch_pipeline_configuration(yaml_data,repo_name,organization,jenkins_parameters,credential_id,templates_repo,templates_branch,template_version)
#
#     set_environment_variables(env_variables)
#
#     set_github_jenkinswebhook_url(jenkins_url,repo_host,organization)
#
#     set_cron_expression(poll_interval)
#
#     get_pipeline_data(yaml_data, pipe_line_key,log)
#
#     create_issue_in_jira(jira_url, jira_user, jira_token, project_key, job_name, issue_type,epic_id=None)
#
#     jenkins_configuration(jenkins_info, yaml_data, corelation_id)
#
#     get_pipelinescm_scriptfile(jenkins_info, pipeline_path, script_file)
#
#     update_apim_parameters(apim_details, yaml_data)
#
################################################# MAINTAINER DIO-OffShore@company.com ####################################


import datetime
import os
import re
import time
import base64
import xml.etree.ElementTree as ET

import jenkins
import pytz
import requests
import yaml
from dateparser import parse
from dateutil.parser import parse
from flask import current_app as app
from flask import render_template_string
from custom_framework.notification_engine import notification_engine_util
from custom_framework.util import mail
from custom_framework.vault import vault
from jira import JIRA
from pymodm import connect
from swagger_server import constants
from swagger_server.models.jira_approval_model import JiraMetadata
from tzlocal import get_localzone
from urllib3.exceptions import MaxRetryError, NewConnectionError

notification_util = notification_engine_util.NotificationEngineUtil()
flo_env = os.environ.get('APP_ENV', None)
flo_name = constants.FLO_NAME
current_file_name = os.path.basename(__file__)

df_store_vkey = ""
vault_url = ""
vault_path = ""


class FileUtil(object):
    """
           function to builds the jenkins template and returns

           Arguments:
                yaml_data :
                   type: dict
                   purpose: contains info related app and artifacts
                environment:
                       type:str
                       purpose: Application Envirment

               primary_server:
                       type:object
                       purpose: jenkins connection object

               credential_id:
                        type: key
                       purpose: key to establish connection to git repo

           """

    def get_configure_new_file(self, yaml_data, environment, primary_server, builder_info, credential_id=None,
                               job_type=None,artifact_url=None,source_code=None,sonarqube_url=None):
        jira_url = None
        new_jira_id = None
        deploy_time = None
        corelation_id = yaml_data.get("cid")
        database_url = app.config.get('database_url')
        log = app.config.get('log')
        try:
            global df_store_vkey, vault_url, vault_path
            df_store_vkey = app.config.get('df_store_vkey')
            vault_url = app.config.get('vault_url')
            vault_path = app.config.get('vault_path')
            artifact_repository = app.config.get('artifact_repository')
            pipe_line_tool_data_list = get_pipeline_data_list(yaml_data, log)
            log.info('pipe_line_tool_data_list :' + str(pipe_line_tool_data_list))
            branch = yaml_data.get('branch')
            version = yaml_data.get('app').get('version')
            app_code = yaml_data.get('app').get('code')
            app_name = yaml_data.get('app').get('name')
            app_type = yaml_data.get('app_type')
            repo_name = yaml_data.get('repo_name')
            repo_host = yaml_data.get('repo_host')
            compare_url = yaml_data.get('compare_url')
            organization = yaml_data.get('organization')
            # Bitbucket integration to fetch the Project name and scm repo url
            repo_type = yaml_data.get('repo_type')
            release = yaml_data.get('release')
            env_var_data = yaml_data.get('env_vars')
            mail_users_list = yaml_data.get('notification_users')
            commited_user_mail = yaml_data.get("committed_user_mail")

            if mail_users_list:
                mail_users_list = ','.join(mail_users_list)
                mail_users_list = mail_users_list + ',' + commited_user_mail
            else:
                mail_users_list = commited_user_mail

            if not yaml_data.get('artifacts'):
                msg = constants.ARTIFACTS_MISSING_ERROR
                return None, msg, None, deploy_time, None

            artifact_name = list(yaml_data.get('artifacts').keys())[0]
            artifact_path = yaml_data.get('artifacts').get(artifact_name) + '/' + artifact_name
            artifact_path_only = yaml_data.get('artifacts').get(artifact_name)
            artifact_ext = artifact_name.rsplit('.', 1)[-1]
            artifact_no_ext = artifact_name.rsplit('.', 1)[0]

            non_dev_environments = yaml_data.get('non-dev-environments')
            if non_dev_environments is None:
                non_dev_environments_list = constants.NON_DEV_ENVIRONMENTS
            else:
                non_dev_environments_list = non_dev_environments.get('env_list', None)
                if non_dev_environments_list is None:
                    non_dev_environments_list = constants.NON_DEV_ENVIRONMENTS

            #             if environment in non_dev_environments_list:
            #                 release = constants.DEPLOY_KEY

            classifier, build_name, build_command = [None] * 3
            if not yaml_data.get('build_tool') and environment not in non_dev_environments_list:
                msg = constants.BUILD_SECTION_MISSING_ERROR
                return None, msg, None, deploy_time, None

            if yaml_data.get('build_tool'):
                classifier = yaml_data.get('build_tool').get('arguments')
                build_name = yaml_data.get('build_tool').get('name')
                build_command = yaml_data.get('build_tool').get('command')

            if pipe_line_tool_data_list is None:
                msg = "pipeline data not presented"
                return None, msg, None, deploy_time, None
            jenkins_info = pipe_line_tool_data_list.get('jenkins')
            if jenkins_info is None:
                msg = "jenkins details not presented in pipeline info"
                return None, msg, None, deploy_time, None
            templates_repo = jenkins_info.get('template_repo')
            if classifier is None:
                classifier = constants.RELEASE
            nexus_app_repo = yaml_data.get('nexus_app_repo')
            nexus_app_release_repo = yaml_data.get('nexus_app_release_repo')
            templates_branch = jenkins_info.get('branch')
            template_version = jenkins_info.get('version')
            yaml_data_arr = []
            key_append_value = ''
            data_convert_tfs_format(yaml_data, key_append_value, yaml_data_arr)
            yaml_data_string = "%s" % (';'.join(yaml_data_arr))
            log.debug("data_convert_tfs_format : " + str(yaml_data_string))
            yaml_data_formatted = yaml_data_string

            jenkins_parameters = {'yaml_data': str(yaml_data), 'repo_host': repo_host, 'repo_name': repo_name,
                                  'branch': branch,
                                  'environment': environment, 'version': version,
                                  'app_code': app_code, 'app_name': app_name, 'app_type': app_type,
                                  'organization': organization, 'artifact_name': artifact_name,
                                  'artifact_path': artifact_path,
                                  'artifact_path_only': artifact_path_only, 'artifact_ext': artifact_ext,
                                  'artifact_no_ext': artifact_no_ext,
                                  'artifact_repository': artifact_repository, 'release': release,
                                  'build_name': build_name,
                                  'build_command': build_command, 'classifier': classifier,
                                  'mail_users_list': mail_users_list,
                                  'repo_type': repo_type,
                                  'nexus_app_repo': nexus_app_repo,
                                  'nexus_app_release_repo': nexus_app_release_repo,
                                  'yaml_data_formatted': yaml_data_formatted,
                                  'cid': corelation_id
                                  }

            # <----- DDO-2870 Support for repo_alias jenkins parameter
            if yaml_data.get('repo_alias'):
                jenkins_parameters.update({'repo_alias': yaml_data.get('repo_alias')})
            # DDO-2870 END   ----->
            if yaml_data.get('infra') and (yaml_data.get('infra', {}).get('cloud_provider') == constants.ONPREM_KEY):
                log.info("This is for onprem deployment adding the onprem details to jenkins parameters")
                deploy_artifacts = yaml_data.get('infra').get('deploy_artifacts')
                if deploy_artifacts:
                    jenkins_parameters.update(deploy_artifacts)

            if env_var_data is not None:
                formated_env_data = set_environment_variables(env_var_data)
                jenkins_parameters.update({'env_vars': formated_env_data})
                log.event(corelation_id, "environment variables creation completed")
            set_parameters_pipelineinfo(pipe_line_tool_data_list, jenkins_parameters)
            nexus_app_release_repo = yaml_data.get('nexus_app_release_repo')
            if nexus_app_release_repo:
                jenkins_parameters.update({'nexus_app_release_repo': nexus_app_release_repo})
            code_scanner = yaml_data.get('code_scanner')
            if code_scanner:
                sonar_params = code_scanner.get('sonar_params')
                if sonar_params:
                    jenkins_parameters.update(sonar_params)
                appscan_params = code_scanner.get('appscan_params')
                if appscan_params:
                    jenkins_parameters.update(appscan_params)
            jenkins_extra_params = yaml_data.get('jenkins_extra_params')
            if jenkins_extra_params is not None and isinstance(jenkins_extra_params, dict):
                jenkins_parameters.update(jenkins_extra_params)
            build_extra_params = yaml_data.get('build_extra_params')
            if build_extra_params is not None and isinstance(build_extra_params, dict):
                jenkins_parameters.update(build_extra_params)

            # <--- DDO-2831
            # setting readyApi flag to job
            post_deploy = yaml_data.get('post-deploy')
            if post_deploy is not None and isinstance(post_deploy, dict):
                post_deploy_data = dict_key_format(post_deploy, 'post-deploy',{})
                jenkins_parameters.update(post_deploy_data)
            # END DDO-2831 --->

            # setting schema version to job
            schema_version = yaml_data.get('schema_version')
            if schema_version:
                jenkins_parameters.update({'schema_version': schema_version})

            # setting env vars as jenkins parameter
            if "env" in yaml_data:
                env_var_values = set_environment_variables(yaml_data['env'])
                if env_var_values:
                    jenkins_parameters.update({"env_vars": env_var_values.replace(',', ';')})

            # setting azure tags as jenkins parameter
            if "azure" in yaml_data and "tags" in yaml_data['azure'] and (yaml_data['azure']['tags']):
                azure_tags_values = set_environment_variables(yaml_data['azure']['tags'])
                jenkins_parameters.update({"azure_tags": azure_tags_values.replace(',', ';')})

            # jenkins template agent mapping
            deploy_type = yaml_data.get("deploy_type", None)
            if environment != constants.MULTI_KEY and deploy_type is None:
                msg = "deploy type is empty in division yaml"
                return None, msg, new_jira_id, deploy_time, None

            jira_field_check, workflow_new_status, jira_jql, workflo_old_status, script_repo_url, jenkins_agent = [
                                                                                                                      None] * 6

            # <----- DDO-2978 adding support for slave variable and this will be revoked once all the
            # changes to support agent were in place
            agent = yaml_data.get('agent', None) if yaml_data.get('agent', None) else yaml_data.get('slave', None)
            if agent:
                jenkins_agent = yaml_data.get('jenkins_metadata', {}).get('agent_mapper', {})[agent]
            #  END of DDO-2978 ----->
            # setting swap_api_url as jenkins parameter
            swap_api_details = yaml_data.get(constants.CALLBACK_KEY)
            if swap_api_details:
                jenkins_parameters.update(swap_api_details)
            if organization and deploy_type:
                agent_key = organization + "_" + deploy_type
                if not jenkins_agent:
                    jenkins_agent = yaml_data.get('jenkins_metadata', {}).get('agent_mapper', {}).get(agent_key, None)

            if environment == constants.MULTI_KEY:
                jenkins_parameters.update({'job_type': environment})
                config_deploy_file, error_msg, new_jira_id, deploy_time = get_multibranch_pipeline_configuration(
                    yaml_data, repo_name, organization, jenkins_parameters,
                    credential_id, templates_repo, templates_branch, template_version, log, agent)
                return config_deploy_file, error_msg, new_jira_id, deploy_time, None

            if yaml_data.get('build_tool'):
                builder = yaml_data.get('build_tool').get('name')

            app_type = yaml_data.get('app_type')

            try:
                jenkins_conf_info = jenkins_configuration(jenkins_info, yaml_data, corelation_id, log)
            except Exception as e:
                log.error(e, corelation_id)
                return None, str(e), None, deploy_time, None
            template_file = jenkins_conf_info.get('template_file')
            jenkins_template = jenkins_conf_info.get('jenkins_template')
            jenkins_folder_template = jenkins_conf_info.get('folder_template')
            if yaml_data.get('jenkins_metadata', {}) and yaml_data.get('jenkins_metadata', {}).get('agent_mapper', {}):
                if not agent and jenkins_agent is None:
                    jenkins_agent = yaml_data.get('jenkins_metadata', {}).get('agent_mapper', {}).get(deploy_type, None)

            if jenkins_agent is None:
                msg = "jenkins_agent is not mapped with deploy type"
                return None, msg, new_jira_id, deploy_time, jenkins_folder_template

            log.event(corelation_id, "Before set job parameters")
            if yaml_data.get('cloud_info') and isinstance(yaml_data.get('cloud_info'), dict):
                jenkins_parameters.update(yaml_data.get('cloud_info'))

            # APIM Integration
            apim_details = yaml_data.get('apim')
            if apim_details and isinstance(apim_details, dict):
                # update apim_paramters as jenkins params
                update_apim_parameters(apim_details, yaml_data)

                jenkins_parameters.update(yaml_data.get('apim'))
            # APIM Integration ends here

            log.event(corelation_id, "after job parameteres set")
            log.event(corelation_id, "Yaml data creation completed")
            jenkins_from_mail = constants.JENKINS_MAIL_FROM.format(os.getenv(constants.ENV_NAME))
            poll_interval = yaml_data.get('poll_interval')

            jira_info = pipe_line_tool_data_list.get('jira')
            if jira_info is not None and len(jira_info) != 0:
                jira_url = jira_info.get('url')
                jira_user = jira_info.get('user')
                vault_obj = vault.Vault(vault_url, os.environ[constants.VAULT_NAME])
                try:
                    jira_token_vkey = jira_info.get('vkey')
                    jira_token = vault_obj.get(vault_path, jira_token_vkey)
                except (vault.AuthError, vault.VaultSealed, vault.VaultForbidden) as e:
                    log.error(e, corelation_id)
                    raise Exception("Error Getting secret from Vault ") from e
                jira_id = yaml_data.get('jira_issue_id')
            else:
                jira_user, jira_token, jira_id = [None] * 3
            notifications = yaml_data.get('notifications')
            jenkins_notification_url = None
            if notifications:
                jenkins_notification_url = notifications.get('jenkins')
            build_additional_notification = yaml_data.get('build_additional_notification')
            if build_additional_notification is not None:
                jenkins_parameters.update({'build_additional_notification': build_additional_notification})
                if jenkins_notification_url:
                    build_additional_notification = [build_additional_notification, jenkins_notification_url]
                else:
                    build_additional_notification = [build_additional_notification]
            else:
                if jenkins_notification_url:
                    build_additional_notification = [jenkins_notification_url]
                else:
                    build_additional_notification = None

            jenkins_parameters.update({'jenkins_from_mail': jenkins_from_mail, 'tf_vars_data': yaml_data_formatted})

            log.event(corelation_id, "after jenkins params")
            source_env = yaml_data.get('source_env')

            log.info("commited_user_mail : " + str(commited_user_mail))
            env_type = None
            if environment in non_dev_environments_list:
                env_type = constants.NON_DEV
                dev_env = False
                group_support_check = yaml_data.get('group')
                if group_support_check == True:
                    new_jira_id = yaml_data.get('master_jira_id')
                    jenkins_parameters.update({'group': "true"})
                    jenkins_parameters.update({'parent_cid': yaml_data.get('parent_cid')})
                    master_jira_info = yaml_data.get('master_jira_info')
                    jenkins_parameters.update({'jira_field_check': master_jira_info.get('jira_field_check')})
                    workflo_old_status = master_jira_info.get('workflow_old_status')
                    jenkins_parameters.update({'workflo_old_status': workflo_old_status})
                    workflow_new_status = master_jira_info.get('workflow_new_status')
                    jenkins_parameters.update({'workflow_new_status': workflow_new_status})
                    log.info("This job supports for group deployment, no need to create new jira id for approval")
                else:
                    # In Future will not support for this feature for default approvers and root level approvers
                    approval_mail_list = non_dev_environments.get('approvers', None)
                    if approval_mail_list is None:
                        approval_mail_list = yaml_data.get('approvers')
                        if approval_mail_list is None:
                            approval_mail_list = commited_user_mail.split(',')

                    '''
                    If environment is non dev then will match the current environment to prod_environments regular expression.
                    If environment not available then will send email to support team
                    If environment matches to prod environment, then will proceed to check the given approvers are matched to
                    global approvers white list
                    Get the matched approvers list and proceed to create Jira id for approval and add to these allowed approvers.
                    If white_list_approvers are not present will send email to support team as well as app team.
                    If approvers are not matched to white list approvers then will send email to app team as well as support team.
                    '''
                    df_store_approvers_url = raw_url_formation(app.config.get('df_store_approvers_url'))
                    response_content = get_file_content(df_store_approvers_url)
                    if response_content is None:
                        mail_from = app.config.get('MAIL_FROM')
                        mail_support = app.config.get('MAIL_SUPPORT')
                        subject = 'missed approvers white list data'
                        status = mail.STATUS.CRITICAL
                        data = {'cid': corelation_id,
                                'df_store_approvers_url': df_store_approvers_url}
                        msg_not_file = "approvers.yml file is not found in dynamic-pipeline-store repo, please check whether the file exist in repo"
                        message = msg_not_file + "/Authorization failed from dynamic-pipeline to connect to github, please check whether credentials are provided correctly"
                        mail.send(mail_from, mail_support, '', subject, status, data, message)
                        return None, message, new_jira_id, deploy_time, jenkins_folder_template
                    try:
                        global_approvers_data = yaml.safe_load(response_content)
                    except Exception as e:
                        message = "Approvers file parsing failed - " + str(e)
                        return None, message, new_jira_id, deploy_time, jenkins_folder_template
                    # Getting the prod_environments regular expression data from flo.yml
                    prod_environment_regx = global_approvers_data.get('prod_environments')
                    # Checking prod_environment_regx data present
                    if prod_environment_regx:
                        # matching to current environment to given regx of prod env data
                        prod_env_match = re.match(prod_environment_regx, environment)
                        if prod_env_match:
                            env_type = constants.PROD_TYPE_ENV
                            if approval_mail_list is None:
                                approval_mail_list = []
                            # If env matched to prod env then getting the white list approvers data from yaml_data present in flo.yml
                            approvers_white_list_data = global_approvers_data.get('white_list_approvers')
                            log.info("Filtering whitelisting of approvers")
                            if approvers_white_list_data:
                                # if data will present then calling the approvers_filter_process() to get the matched approvers.
                                if approval_mail_list and isinstance(approval_mail_list, list):
                                    approval_mail_list = list(map(lambda x: x.lower(), approval_mail_list))
                                common_approvers, allowed_approvers, msg = approvers_filter_process(
                                    approvers_white_list_data, organization, repo_name,
                                    approval_mail_list)
                                # <----- DDO-2644 WILDCARD support
                                if common_approvers is not None:
                                    common_approvers = list(
                                        filter((constants.WILD_CARD_APPROVER).__ne__, common_approvers))
                                if allowed_approvers is not None:
                                    allowed_approvers = list(
                                        filter((constants.WILD_CARD_APPROVER).__ne__, allowed_approvers))
                                    # DDO-2644 END ---->
                                # Returned white list approvers are passing to approval mail list, if it none returned the process and send email to app team
                                if common_approvers:
                                    remining_white_list_approvers = list(
                                        set(approval_mail_list) - set(common_approvers))
                                    if remining_white_list_approvers:
                                        approval_mail_list = common_approvers
                                        msg_remine = "Remaining approvers are not part of allowed approvers " + str(
                                            remining_white_list_approvers)
                                        msg = "The final approvers after filtering are " + str(
                                            approval_mail_list) + "<br>" + msg_remine
                                        notification_util.insert_message(corelation_id, database_url, msg,
                                                                         mail.STATUS.INFO,
                                                                         flo_name)
                                    else:
                                        approval_mail_list = common_approvers
                                        msg = "The final approvers after filtering are " + str(approval_mail_list)
                                        notification_util.insert_message(corelation_id, database_url, msg,
                                                                         mail.STATUS.INFO,
                                                                         flo_name)
                                elif allowed_approvers:
                                    approval_mail_list = allowed_approvers
                                    msg = "The final approvers after filtering are"
                                    msg_glb = msg + "<br>The global approvers are " + str(allowed_approvers)
                                    notification_util.insert_message(corelation_id, database_url, msg_glb,
                                                                     mail.STATUS.INFO,
                                                                     flo_name)
                                else:
                                    msg = "approvers data was not provided please verify your division yaml or" \
                                          " global approval yaml"
                                    return None, msg, new_jira_id, deploy_time, jenkins_folder_template
                            else:
                                # If approvel white list data is not present, sending email to support team as well as app team
                                mail_from = app.config.get('MAIL_FROM')
                                mail_support = app.config.get('MAIL_SUPPORT')
                                subject = 'missed approvers white list data'
                                status = mail.STATUS.CRITICAL
                                data = {'cid': corelation_id,
                                        'df_store_approvers_url': df_store_approvers_url}
                                message = "white_list_approvers data is not available in approvers.yml"
                                mail.send(mail_from, mail_support, '', subject, status, data, message)
                                msg = "Global approvers are not available"
                                return None, msg, new_jira_id, deploy_time, jenkins_folder_template
                        else:
                            if approval_mail_list is None:
                                msg = "The Jira Approvers List is empty can't process this job"
                                notification_util.insert_message(corelation_id, database_url, msg, mail.STATUS.ERROR,
                                                                 flo_name)
                                return None, "The Approvers list is empty for this non-dev job", None, None, None
                    else:
                        # If prod_environments regx is not present, sending email to support team as well as app team
                        mail_from = app.config.get('MAIL_FROM')
                        mail_support = app.config.get('MAIL_SUPPORT')
                        subject = 'missed prod_environment data'
                        status = mail.STATUS.CRITICAL
                        data = {'cid': corelation_id,
                                'df_store_approvers_url': df_store_approvers_url}
                        message = "prod_environment regx data is not available in approvers.yml"
                        mail.send(mail_from, mail_support, '', subject, status, data, message)
                        msg = "Missed global prod_environment data"
                        return None, msg, new_jira_id, deploy_time, jenkins_folder_template
                    project_key, issue_type, jira_field_check, workflo_old_status, workflow_new_status, epic_id, label_list = [
                                                                                                                                  None] * 7
                    jenkins_parameters.update({constants.ENV: constants.DEV})
                    if yaml_data.get('jira', {}):
                        project_key = yaml_data.get('jira', {}).get('project_key')
                        if project_key is None:
                            msg = "project key is not available in organization defaults"
                            return None, msg, new_jira_id, deploy_time, jenkins_folder_template
                        issue_type = yaml_data.get('jira', {}).get('issue_type')
                        if issue_type is None:
                            issue_type = constants.ISSUE_TYPE
                        jira_field_check = yaml_data.get('jira', {}).get('jira_field_check')
                        if jira_field_check is None:
                            jira_field_check = constants.JIRA_FIELD_CHECK
                        jenkins_parameters.update({'jira_field_check': jira_field_check})
                        log.event(corelation_id, "jira field check creation completed")
                        workflo_old_status = yaml_data.get('jira', {}).get('workflo_old_status')
                        if workflo_old_status is None:
                            workflo_old_status = constants.WORKFLO_OLD_STATUS
                        jenkins_parameters.update({'workflo_old_status': workflo_old_status})
                        log.event(corelation_id, "workflo old status creation completed")
                        workflow_new_status = yaml_data.get('jira', {}).get('workflow_new_status')
                        if workflow_new_status is None:
                            workflow_new_status = constants.WORKFLO_NEW_STATUS
                        jenkins_parameters.update({'workflow_new_status': workflow_new_status})
                        log.event(corelation_id, "workflo new status creation completed")
                        epic_id = yaml_data.get('jira', {}).get('epic_id')
                        label_list = yaml_data.get('jira', {}).get('label_list')
                    jenkins_job_name = str(app_code + '_' + environment)

                    log.event(corelation_id, "creating the new jira issue")
                    if not yaml_data.get(constants.SCHEDULE_TIME):
                        new_jira_id, error_msg = create_issue_in_jira(jira_url, jira_user, jira_token, project_key,
                                                                      jenkins_job_name, issue_type, approval_mail_list,
                                                                      corelation_id, log, compare_url, epic_id,
                                                                      label_list,artifact_url,source_code,sonarqube_url)

                    else:
                        try:
                            exp_time = yaml_data.get('deploy_time')
                            exp_est_time = parse(exp_time)
                            zone = constants.EST_TIMEZONE
                            current_local_time = datetime.datetime.now(get_localzone())
                            current_est_time = current_local_time.astimezone(pytz.timezone(zone))
                            if exp_est_time.replace(tzinfo=None) > current_est_time.replace(tzinfo=None):
                                if primary_server is None:
                                    msg = "Server connection Failed"
                                    log.status(corelation_id, mail.STATUS.ERROR, msg)
                                    return msg, 500, None, None, None
                                queue_list = primary_server.get_queue_info()
                                for queues in queue_list:
                                    name = queues.get('task').get('name')
                                    if name == jenkins_job_name:
                                        id = queues.get('id')
                                        log.info(
                                            "details of existing build in queue" + str(id) + "," + str(
                                                jenkins_job_name))
                                        primary_server.cancel_queue(id)

                                new_jira_id, error_msg = create_issue_in_jira(jira_url, jira_user, jira_token,
                                                                              project_key,
                                                                              jenkins_job_name, issue_type,
                                                                              approval_mail_list, corelation_id, log,
                                                                              compare_url, epic_id, label_list,artifact_url,source_code,sonarqube_url)

                            else:
                                msg = "Expected schedule time is passed from current time "
                                log.status(corelation_id, mail.STATUS.ERROR, msg)
                                return None, msg, None, deploy_time, jenkins_folder_template
                        except Exception as e:
                            log.error(e, corelation_id)
                            msg = "Expected date format is 'DD MM YYYY HOURES:MINUTES ZONE' " \
                                  "For ex: 11 Dec 2018 15:30 EST  and supports only EST time zone " + '<br>' + str(e)
                            log.status(corelation_id, mail.STATUS.ERROR, msg)
                            return None, msg, None, deploy_time, jenkins_folder_template

                    if new_jira_id is None:
                        return None, error_msg, new_jira_id, None, None
                    else:

                        job_name = organization + '/' + jenkins_job_name

                        if yaml_data.get(constants.SCHEDULE_TIME):
                            deploy_time = yaml_data.get(constants.SCHEDULE_TIME)
                            insert_jira_details(log, yaml_data, new_jira_id, workflo_old_status, workflow_new_status,
                                                job_name,
                                                corelation_id, deploy_time)
                        else:
                            insert_jira_details(log, yaml_data, new_jira_id, workflo_old_status, workflow_new_status,
                                                job_name,
                                                corelation_id, )
                    jenkins_parameters.update({'jira_id': new_jira_id})
                    jira_jql = "id=" + str(new_jira_id)
                    log.event(corelation_id, "successfully created the new jira issue : " + str(new_jira_id))

                    # Checking deploy_time exist, if exist then will go to schedule build else will go normal approval flo

                    deploy_time = yaml_data.get(constants.SCHEDULE_TIME)
                    # if deploy_time is None:
                    #     jira_exist = True
                    # else:
                    #     jira_exist = False
                    if deploy_time:
                        jenkins_parameters.update({
                            "deploy_time": deploy_time})  # setting this parameter to validate schedule approval in pipelie script
                build_number = yaml_data.get('build_number')
                jenkins_parameters.update({'jira_id': new_jira_id})
                jenkins_parameters.update({'BUILD_NUMBER': str(build_number)})
            else:
                build_number = 1
                dev_env = True
                env_type = constants.DEV
                jenkins_parameters.update({constants.NON_DEV: constants.NON_DEV_BOOLEAN_FALSE})
                source_env = environment
            jenkins_parameters.update({constants.ENV_TYPE: env_type})
            # <----- DDO-2978
            jenkins_parameters.update(
                {'source_env': source_env, 'agent_label': jenkins_agent, 'slave_label': jenkins_agent})

            # END OF DDO-2978 ----->

            if jenkins_template is None:
                log.event(corelation_id,
                          "jenkins template option is not provided in the application yaml" + app_name + ".yml")
                msg = "jenkins template option is not provided in the application yaml" + app_name + ".yml"
                return None, msg, new_jira_id, deploy_time, jenkins_folder_template
            script_repo_url = templates_repo
            script_branch = templates_branch
            pipeline_mapper = yaml_data.get(constants.KEY_JENKINS_METADATA).get(constants.KEY_PIPELINE_MAPPER)
            pipeline_path = constants.PIPELINE_PATH.format(**{'template_version': template_version})
            if jenkins_template.lower() == constants.KEY_PIPELINE_MANAGED:
                if pipeline_mapper is not None:
                    log.event(corelation_id, "pipeline mapper is available in flo.yml")
                    script_file = pipeline_mapper.get(app_code)
                    if script_file is None:
                        log.event(corelation_id,
                                  "app_code mapping file is not available in pipeline_mapper, getting default pipelinescript - " + app_type + "_" + deploy_type + "." + constants.PIPELINE_EXT)
                        raw_url = get_raw_url(templates_repo, templates_branch, pipeline_path,
                                              app_type + "_" + deploy_type + "." + constants.PIPELINE_EXT)
                        response = get_job_templates(raw_url)
                        if response is None:
                            msg = constants.SRIPTFILE_ERROR_MSG + str(raw_url)
                            return None, msg, new_jira_id, deploy_time, jenkins_folder_template
                        script_path = pipeline_path + "/" + app_type + "_" + deploy_type + "." + constants.PIPELINE_EXT
                    else:
                        log.event(corelation_id, "This is pipeline_managed and pipelinescript is -" + script_file)
                        raw_url = get_raw_url(templates_repo, templates_branch, pipeline_path,
                                              script_file)
                        response = get_job_templates(raw_url)
                        if response is None:
                            msg = constants.SRIPTFILE_ERROR_MSG + str(raw_url)
                            return None, msg, new_jira_id, deploy_time, jenkins_folder_template
                        script_path = pipeline_path + "/" + script_file
                else:
                    log.event(corelation_id,
                              "pipeline_mapper is not available, getting default pipelinescript - " + app_type + "_" + deploy_type + "." + constants.PIPELINE_EXT)
                    raw_url = get_raw_url(templates_repo, templates_branch, pipeline_path,
                                          app_type + "_" + deploy_type + "." + constants.PIPELINE_EXT)
                    response = get_job_templates(raw_url)
                    if response is None:
                        msg = constants.SRIPTFILE_ERROR_MSG + str(raw_url)
                        return None, msg, new_jira_id, deploy_time, jenkins_folder_template
                    script_path = pipeline_path + "/" + app_type + "_" + deploy_type + "." + constants.PIPELINE_EXT

            elif jenkins_template.lower() == constants.KEY_PIPELINE_SCM:
                log.event(corelation_id, "This is pipeline_scm and pipeline script is Jenkinsfile")
                if pipeline_mapper is not None:
                    log.event(corelation_id, "pipeline mapper is available in flo.yml")
                    script_file = pipeline_mapper.get(app_code)
                    if script_file is None:
                        file_name = app_code + "." + constants.PIPELINE_EXT
                        log.event(corelation_id,
                                  "app_code mapping file is not available in pipeline_mapper, getting default pipeline script  ")
                        script_repo_url, script_path, script_branch = get_pipelinescm_scriptfile(jenkins_info,
                                                                                                 pipeline_path,
                                                                                                 file_name, yaml_data)
                        if script_repo_url is None:
                            msg = script_path
                            return None, msg, new_jira_id, deploy_time, jenkins_folder_template

                    else:
                        script_repo_url, script_path, script_branch = get_pipelinescm_scriptfile(jenkins_info,
                                                                                                 pipeline_path,
                                                                                                 script_file, yaml_data)
                        if script_repo_url is None:
                            msg = script_path
                            return None, msg, new_jira_id, deploy_time, jenkins_folder_template
                else:
                    file_name = app_code + "." + constants.PIPELINE_EXT
                    log.event(corelation_id,
                              "pipeline_mapper is not available, getting default pipelinescript")
                    script_repo_url, script_path, script_branch = get_pipelinescm_scriptfile(jenkins_info,
                                                                                             pipeline_path,
                                                                                             file_name, yaml_data)
                    if script_repo_url is None:
                        msg = script_path
                        return None, msg, new_jira_id, deploy_time, jenkins_folder_template
            # <----- DDO-3080 adding support for pipeline custom
            elif jenkins_template.lower() == constants.KEY_PIPELINE_CUSTOM:
                log.event(corelation_id, "This is pipeline_custom and pipeline script is from custom repo ")
                repo_alias = yaml_data.get('repo_alias')
                file_name = repo_alias + "_" + organization + "_" + app_code
                if pipeline_mapper is not None:
                    log.event(corelation_id, "pipeline mapper is available in flo.yml")

                    script_file = pipeline_mapper.get(file_name)

                    if script_file is None:
                        file_name = file_name + "." + constants.PIPELINE_EXT
                        log.event(corelation_id,
                                  "%s mapping file is not available in pipeline_mapper, getting default pipeline script" % file_name)
                        script_repo_url, script_path, script_branch = get_pipelinecustom_scriptfile(jenkins_info,
                                                                                                    file_name, log)
                        if script_repo_url is None:
                            msg = script_path
                            return None, msg, new_jira_id, deploy_time, jenkins_folder_template

                    else:
                        log.info("Jenkins template file is provided in flo.yml in pipeline_mapper")
                        log.info("verifying in custom repo for jenkins file with %s name" % file_name)
                        script_repo_url, script_path, script_branch = get_pipelinecustom_scriptfile(jenkins_info,
                                                                                                    script_file, log)
                        if script_repo_url is None:
                            msg = script_path
                            return None, msg, new_jira_id, deploy_time, jenkins_folder_template
                else:
                    file_name = file_name + "." + constants.PIPELINE_EXT
                    log.event(corelation_id,
                              "pipeline_mapper is not available, getting default pipelinescript "
                              "from custom repo with %s name" % file_name)
                    script_repo_url, script_path, script_branch = get_pipelinecustom_scriptfile(jenkins_info,
                                                                                                file_name, log)
                    if script_repo_url is None:
                        msg = script_path
                        return None, msg, new_jira_id, deploy_time, jenkins_folder_template
            # END of DDO-3080 ----->
            else:
                log.event(corelation_id, "This is for custom pipeline")
                job_template = yaml_data.get('job_template')
                if not job_template:
                    msg = constants.JOB_TEMPLATE_KEY_MISSING_ERROR
                    return None, msg, new_jira_id, deploy_time, jenkins_folder_template

                script_file = jenkins_template.lower() + "." + constants.PIPELINE_EXT

                # reading custom xml file to get the script path from file.
                log.event(corelation_id, str(job_template))
                raw_url = get_raw_url(templates_repo, templates_branch, template_version, job_template)
                log.event(corelation_id, str(raw_url))

                formated_config = get_job_templates(raw_url)
                log.event(corelation_id, "Build config format checking completed")
                if formated_config is None:
                    msg = str(job_template) + " - template is getting failed"
                    raise Exception(msg)

                scriptpath_element = re.findall('<scriptPath>(.*)</scriptPath>', formated_config)

                if not scriptpath_element:
                    msg = constants.SCRIPTPATH_MISSING_ERROR
                    return None, msg, new_jira_id, None, jenkins_folder_template

                script_filename = ''.join(scriptpath_element).split('/')[-1]
                if not script_filename == script_file:
                    msg = constants.SCRIPTFILENAME_MISMATCH
                    return None, msg, new_jira_id, deploy_time, jenkins_folder_template

                raw_url = get_raw_url(templates_repo, templates_branch, pipeline_path, script_file)
                response = get_job_templates(raw_url)
                if response is None:
                    msg = constants.SRIPTFILE_ERROR_MSG + str(raw_url)
                    return None, msg, new_jira_id, deploy_time, jenkins_folder_template
                script_path = pipeline_path + "/" + script_file

            log.event(corelation_id, "after build schedule interval set")
            # By default setting poll scm as daily for schedule builds so added condition
            poll_intervl_param, poll_time, webhook_enable = 0, 0, False

            if environment not in non_dev_environments_list:
                jenkins_url = builder_info.get('url')
                if poll_interval is not None and (
                        poll_interval.lower() == constants.DISABLED or poll_interval.lower() == constants.DISABLE):
                    poll_interval = constants.DISABLE
                if (
                        poll_interval is not None and poll_interval.lower() != constants.INSTANT and
                        poll_interval.lower() != constants.DISABLE and re.search('\d', poll_interval)):
                    poll_time = int(re.findall('\d+', poll_interval)[0])
                # we will not set a webhook or poll time if poll_interval is None or disable or poll_time is Zero.
                if poll_interval is None or poll_interval == constants.DISABLE or (
                        poll_time == constants.ZERO and re.search('\d', poll_interval)):
                    webhook_enable = False
                    dev_env = False
                # we will configure webhook insteadof poll scm if user uses less than 60 minutes or 1 hour or instant
                elif poll_interval is not None and ((poll_interval.lower().__contains__(
                        constants.MINUTES) and poll_time <= constants.POLL_TIME) or (poll_interval.lower().__contains__(
                    constants.HOUR) and poll_time == constants.POLL_TIME_IN_HOUR) or poll_interval.lower() == constants.INSTANT):
                    log.event(corelation_id, "Webhook will configure insteadof poll scm")
                    status_code = set_github_jenkinswebhook_url(jenkins_url, repo_host, organization)
                    webhook_enable = True
                    if status_code == 201:
                        log.event(corelation_id,
                                  "successfully created the jenkins web hook in " + repo_name + " repository")
                    elif status_code == 422:
                        log.event(corelation_id,
                                  "Already configured the jenkins web hook in " + repo_name + " repository")
                    else:
                        log.event(corelation_id,
                                  "failed to  created the jenkins web hook in " + repo_name + " repository")
                        webhook_enable = False
                else:
                    log.event(corelation_id, "Jenkins poll scm configuration")
                    poll_intervl_param = set_cron_expression(poll_interval)
                    dev_env = True
            log.debug('jenkins_parameters : ' + str(jenkins_parameters))
            log.info("script_path : " + script_path)
            jira_exist = False
            # <----- DDO-2978
            if ("override_slave_label" in jenkins_parameters) or jenkins_parameters.get("override_slave_label"):
                jenkins_parameters.update({"override_agent_label": jenkins_parameters.get("override_slave_label")})
                msg = constants.AGENT_NAME_WARNING

                # <----- DDO-3095 disabling waring notification
                log.status(corelation_id, mail.STATUS.WARNING, msg)
                # notification_util.insert_message(corelation_id, database_url, msg, mail.STATUS.WARNING, flo_name,
                #                                  )
                # END OF DDO-3095 ----->
            # <----- DDO-3452
            if ("ansible_slave_label" in jenkins_parameters) or jenkins_parameters.get("ansible_slave_label"):
                jenkins_parameters.update({"ansible_agent_label": jenkins_parameters.get("ansible_slave_label")})
                msg = constants.AGENT_NAME_WARNING
                log.info(msg)
            # END OF DDO-3452 ----->
            template_file = render_template_string(template_file, jenkins_parameters=jenkins_parameters,
                                                   build_additional_notification=build_additional_notification,
                                                   poll_intervl_param=poll_intervl_param,
                                                   jira_field_check=jira_field_check, jira_exist=jira_exist,
                                                   workflow_new_status=workflow_new_status,
                                                   workflo_old_status=workflo_old_status,
                                                   script_repo_url=script_repo_url,
                                                   script_branch=script_branch,
                                                   credential_id=credential_id, pipeline_script_path=script_path,
                                                   dev_env=dev_env, jira_token=jira_token,
                                                   jira_jql=jira_jql, slave_properties=jenkins_agent,
                                                   webhook_enable=webhook_enable,
                                                   )
            return template_file, None, new_jira_id, deploy_time, jenkins_folder_template
        except Exception as e:
            log.error(e, corelation_id)
            msg = constants.JOB_CONFIG_FAIL_ERROR.format(str(current_file_name), '<br>', str(e), '<br>')
            return None, msg, None, None, None


def create_jenkins_folder(jenkins_con, jenkins_job_name, organization, jenkins_folder_template):
    """
     Method to check for folder existence in jenkins if the folder does not exist creates a new folder
    """
    folder_list = [organization]
    sub_folders = jenkins_job_name.split('/')
    folder_formation = ''
    if jenkins_folder_template is None:
        msg = "Jenkins folder template does not exist, Please contact DevOps_Support@company.com"
        raise Exception(msg)
    if len(sub_folders) > 1:
        folder_list.extend(sub_folders[:-1])
    for folder in folder_list:
        folder_formation = folder_formation + folder
        try:
            jenkins_folder_exist_check = jenkins_con.job_exists(folder_formation)
        except Exception:
            msg = "Jenkins Server Connection failed, while checking job existence"
            raise Exception(msg)
        if jenkins_folder_exist_check:
            folder_formation = folder_formation + '/'
        else:
            rendered = render_template_string(jenkins_folder_template)
            jenkins_con.create_job(folder_formation, rendered)
            folder_formation = folder_formation + '/'
    return folder_formation


def jenkins_job_creation(jenkins_con, organization, jenkins_job_name, jenkins_config_file, log, cid):
    try:
        job_request_deploy = jenkins_con.create_job(organization + '/' + jenkins_job_name,
                                                    jenkins_config_file)
        log.debug(str(job_request_deploy))
    except Exception as e:
        msg = "Jenkins Job creation failed - " + organization + '/' + jenkins_job_name
        log.status(cid, mail.STATUS.ERROR, str(jenkins_job_name) + " job creation failed ")
        log.error(msg + str(e), cid)
        raise Exception(msg)


"""
function to return jenkins template
"""


def jenkins_configuration(jenkins_info, yaml_data, corelation_id, log):
    log.info("jenkins_info:" + str(jenkins_info))
    if len(jenkins_info) != 0:
        templates_repo = jenkins_info.get('template_repo')
        templates_branch = jenkins_info.get('branch')
        template_version = jenkins_info.get('version')
        folder_template = yaml_data.get('jenkins_metadata').get('template_mapper').get('folder_template')
        jenkins_template_file = None

    else:
        msg = "Jenkins details not presented in pipeline info data"
        raise Exception(msg)
    jenkins_template = yaml_data.get('jenkins_template', None)
    if jenkins_template is not None:
        jenkins_template_file = yaml_data.get('jenkins_metadata').get('template_mapper').get(jenkins_template)
    if jenkins_template not in [constants.KEY_PIPELINE_SCM, constants.KEY_PIPELINE_MANAGED,
                                constants.KEY_MULTIBRANCH_SCM, constants.KEY_PIPELINE_CUSTOM]:
        jenkins_template_file = yaml_data.get('job_template')
    if jenkins_template_file is None or templates_repo is None or templates_branch is None or template_version is None:
        if jenkins_template not in [constants.KEY_PIPELINE_SCM, constants.KEY_PIPELINE_MANAGED,
                                    constants.KEY_MULTIBRANCH_SCM, constants.KEY_PIPELINE_CUSTOM]:
            msg = constants.JOB_TEMPLATE_KEY_MISSING_ERROR
        else:
            msg = "template details are empty in pipeline data"
        raise Exception(msg)

    log.event(corelation_id, str(jenkins_template_file))
    raw_url = get_raw_url(templates_repo, templates_branch, template_version, jenkins_template_file)
    log.event(corelation_id, str(raw_url))

    formated_config = get_job_templates(raw_url)
    log.event(corelation_id, "Build config format checking completed")
    if formated_config is None:
        msg = str(jenkins_template_file) + " - template is getting failed"
        raise Exception(msg)

    if folder_template:
        raw_url = get_raw_url(templates_repo, templates_branch, template_version, folder_template)
        formatted_folder_config = get_job_templates(raw_url)

    log.event(corelation_id, "Before setting properties")
    log.event(corelation_id, str(formated_config))

    return {'template_file': formated_config, 'jenkins_template': jenkins_template,
            'folder_template': formatted_folder_config}


# <----- DDO-3080 adding support for pipeline custom
def get_pipelinecustom_scriptfile(jenkins_info, script_file, log):
    custom_templates_repo = jenkins_info.get("template_scm_repo")
    custom_templates_branch = jenkins_info.get("scm_branch")
    custom_pipeline_path = jenkins_info.get('version')
    script_repo_url, script_path, script_branch = [None] * 3
    if custom_templates_repo is not None:
        custom_script_file = script_file
        if custom_templates_branch is None:
            msg = "Custom templates branch is not provided in pipeline_info, please verify and update the configuration "
            log.error(msg)
            return None, msg, None
        else:
            raw_url = get_raw_url(custom_templates_repo, custom_templates_branch, custom_pipeline_path,
                                  custom_script_file)
        response = get_job_templates(raw_url)
        script_path = custom_pipeline_path + "/" + custom_script_file
        if response is not None:
            script_repo_url = custom_templates_repo
            script_branch = custom_templates_branch
        else:
            log.error("pipeline script is not available in custom repo %s" % raw_url)
            msg = constants.SRIPTFILE_ERROR_MSG + str(raw_url)
            return None, msg, None
    return script_repo_url, script_path, script_branch


# END of DDO-3080 ----->

def get_pipelinescm_scriptfile(jenkins_info, pipeline_path, script_file, yaml_data):
    templates_repo = jenkins_info.get('template_repo')
    templates_branch = jenkins_info.get('branch')
    scm_templates_repo = jenkins_info.get("template_scm_repo")
    script_repo_url = templates_repo
    jenkinsfile = constants.JENKINS_FILE
    script_branch = templates_branch
    scm_templates_branch = jenkins_info.get("scm_branch")
    scm_pipeline_path = jenkins_info.get('version')
    if scm_templates_repo is not None:
        scm_script_file = script_file
        if scm_templates_branch is None:
            scm_templates_branch = templates_branch
            raw_url = get_raw_url(scm_templates_repo, templates_branch, scm_pipeline_path, scm_script_file)
        else:
            raw_url = get_raw_url(scm_templates_repo, scm_templates_branch, scm_pipeline_path, scm_script_file)
        response = get_job_templates(raw_url)
        script_path = scm_pipeline_path + "/" + scm_script_file
        if response is None:
            script_file = constants.KEY_PIPELINE_SCM + "." + constants.PIPELINE_EXT
            raw_url = get_raw_url(templates_repo, templates_branch, pipeline_path, script_file)
            response = get_job_templates(raw_url)
            script_path = pipeline_path + "/" + script_file
        else:
            script_repo_url = scm_templates_repo
            script_branch = scm_templates_branch
    else:
        script_file = constants.KEY_PIPELINE_SCM + "." + constants.PIPELINE_EXT
        raw_url = get_raw_url(templates_repo, templates_branch, pipeline_path, script_file)
        response = get_job_templates(raw_url)
        script_path = pipeline_path + "/" + script_file
    # <----- DDO-2534 Jenkinsfile validation big fix
    if script_file == constants.KEY_PIPELINE_SCM + "." + constants.PIPELINE_EXT and (
            yaml_data.get('repo_host') and yaml_data.get('branch')):
        jenkinsfile_raw_url = get_raw_url(yaml_data.get('repo_host'), yaml_data.get('branch'), '',
                                          jenkinsfile)
        jenkinsfile_response = get_job_templates(jenkinsfile_raw_url)
        if jenkinsfile_response is None:
            msg = constants.JENKINS_FILE_ERROR_MSG + str(jenkinsfile_raw_url)
            return None, msg, None
    # DDO-2534 END ----->
    if response is None:
        msg = constants.SRIPTFILE_ERROR_MSG + str(raw_url)
        return None, msg, None
    return script_repo_url, script_path, script_branch


# function to get the pipeline data from yaml_dat dict

def get_pipeline_data_list(yaml_data, log):
    try:
        pipeline_data = yaml_data.get('pipeline')
        pipe_line_tool_data_list = {}
        if isinstance(pipeline_data, list):
            pipeline_enabled_data = [item for item in pipeline_data if item['status'] == 'enabled']
            for component in pipeline_enabled_data:
                data = get_pipeline_data(yaml_data, component.get('type'), log)
                name = component.get('name')
                if data:
                    pipe_line_tool_data_list[name] = data
        elif isinstance(pipeline_data, dict):
            for tool_type in pipeline_data:
                for tool_name, data in pipeline_data.get(tool_type).items():
                    data = get_pipeline_data(yaml_data, tool_type, log, tool_name)
                    if data:
                        pipe_line_tool_data_list[tool_name] = data
        return pipe_line_tool_data_list
    except Exception as e:
        log.error(e)
        return None


def refine(templates):
    template_update = {}
    for key, value in templates.items():
        if 'repo' not in key:
            template_update.update({key.replace('template_', ''): value})
        else:
            template_update.update({key: value})
    return template_update


"""
function to update jenkins parameters
"""


def set_parameters_pipelineinfo(pipe_line_tool_data_list, jenkins_parameters):
    for component in pipe_line_tool_data_list:
        # if component != 'jenkins':
        for property in pipe_line_tool_data_list.get(component):
            if property != 'name':
                if component != 'sonarqube':
                    jenkins_parameters.update(
                        {component + "_" + property: pipe_line_tool_data_list.get(component).get(property)})
                else:
                    jenkins_parameters.update({property: pipe_line_tool_data_list.get(component).get(property)})


"""
function which take yaml_data and from TFS supported data
"""


def data_convert_tfs_format(yaml_data, key_append, tf_data_vars):
    if isinstance(yaml_data, dict):
        for key, value in yaml_data.items():
            if isinstance(value, dict):
                if key_append == '':
                    key_append = key_append + key
                else:
                    key_append = key_append + '_' + key
                data_convert_tfs_format(value, key_append, tf_data_vars)
                key_append = ''
            elif isinstance(value, list):
                for i in range(len(value)):
                    if key_append == '':
                        key_append = key_append + key
                    else:
                        key_append = key_append + '_' + key
                    data_convert_tfs_format(value[i], key_append, tf_data_vars)
                    key_append = ''
            else:
                if key_append == '':
                    tf_data_vars.append(key + '=' + '"{}"'.format(str(value)))
                else:
                    tf_data_vars.append(key_append + '_' + str(key) + '=' + '"{}"'.format(str(value)))
    else:
        tf_data_vars.append(key_append + '=' + '"{}"'.format(str(yaml_data)))
    return tf_data_vars


"""
function which take the raw_url and return the file content
"""


def get_job_templates(raw_url):
    # <--- DPE-12199
    split_url = [row for row in raw_url.split('/') if row]
    org = split_url[3]
    repo_name = split_url[4]
    branch = split_url[5]
    file_name = '/'.join(split_url[6:])
    content_url = 'https://git-server.company.com/api/v3/repos/{}/{}/contents/{}?ref={}'.format(org, repo_name, file_name, branch)

    vault_obj = vault.Vault(vault_url, os.environ[constants.VAULT_NAME])
    token = vault_obj.get(vault_path, df_store_vkey)
    file_content_request = requests.get(content_url, auth=('', token))
    status_code = file_content_request.status_code

    if status_code == 200:
        content = file_content_request.json()
        if content.get('type') == 'file':
            encoded_file = content.get('content')
            ascii_encoded_file = encoded_file.encode('ascii')
            b64_decoded_file = base64.b64decode(ascii_encoded_file)
            file_content = b64_decoded_file.decode('utf-8')
            return file_content
        else:
            return None
        # DPE-12199 --->
    else:
        return None


def get_file_content(raw_url):
    # <--- DPE-12199
    split_url = [row for row in raw_url.split('/') if row]
    org = split_url[3]
    repo_name = split_url[4]
    branch = split_url[5]
    file_name = '/'.join(split_url[6:])
    content_url = 'https://git-server.company.com/api/v3/repos/{}/{}/contents/{}?ref={}'.format(org, repo_name, file_name, branch)

    vault_obj = vault.Vault(vault_url, os.environ[constants.VAULT_NAME])
    token = vault_obj.get(vault_path, df_store_vkey)
    file_content_request = requests.get(content_url, auth=('', token))
    status_code = file_content_request.status_code

    if status_code == 200:
        content = file_content_request.json()
        if content.get('type') == 'file':
            encoded_file = content.get('content')
            ascii_encoded_file = encoded_file.encode('ascii')
            b64_decoded_file = base64.b64decode(ascii_encoded_file)
            file_content = b64_decoded_file.decode('utf-8')
            return file_content
        else:
            return None
        # DPE-12199 --->
    else:
        return None


"""
function to form a raw url to get the file content from github
"""


def get_raw_url(clone_url, branch, folder, template_file):
    if clone_url and branch:
        if clone_url.endswith('.git'):
            clone_url = clone_url[:-4]
        total_file_url = clone_url + '/' + branch + '/' + folder + '/' + template_file
        regexpression = r"(http[s]?:\/\/[^\/]+)"
        matches = re.search(regexpression, total_file_url)
        if matches:
            baseurl = matches.group(1)
            path = total_file_url.split(baseurl)[1]
            raw_url = baseurl + '/raw' + path
            return raw_url

    return None


"""
function to create a new JIRA issue
"""


def create_issue_in_jira(jira_url, jira_user, jira_token, project_key, job_name,
                         issue_type, approval_mail_list, corelation_id, log,
                         compare_url, epic_id=None, label_list=None,artifact_url=None,source_code=None,sonarqube_url=None):
    try:
        jira = JIRA(server=jira_url, basic_auth=(jira_user, jira_token),options={'verify':False})
        user_login_name_list = []
        inactive_user_list = []
        for user_mail in approval_mail_list:
            user_data = jira.search_users(user_mail)
            if len(user_data) == 1:
                user_login_name = user_data[0].name
                user_login_name_list.append({'name': user_login_name})
            else:
                inactive_user_list.append(user_mail)
        if len(inactive_user_list) != 0:
            inactive_user_details = ",".join(inactive_user_list)
            msg = constants.MSG_JIRAUSER_NOTFOUND % str(inactive_user_details)
            log.info("unable to get user details :" + str(inactive_user_details))
            database_url = app.config.get('database_url')
            notification_util.insert_message(corelation_id, database_url, msg, mail.STATUS.WARNING, flo_name)

        if not user_login_name_list:
            return None, constants.MSG_NO_ADDITIONAL_ASSIGNEE + str(approval_mail_list)

        if label_list is not None:
            if isinstance(label_list, str):
                label_list = label_list.split(',')
            elif not isinstance(label_list, list):
                label_list = None
                msg = constants.MSG_JIRALABEL_FORMAT_NOT_SUPPORT
                log.info(msg)
                database_url = app.config.get('database_url')
                notification_util.insert_message(corelation_id, database_url, msg, mail.STATUS.WARNING, flo_name)
        else:
            log.info("Jira label data is not provided")
        jira_id_list_label_mapped = []
        if label_list is not None and len(label_list) != 0:
            jql_query = ''
            for label in label_list:
                jql_query = jql_query + 'labels = ' + str(label) + ' AND '
            if jql_query != '':
                jql_query = jql_query + "project = " + project_key
                jira_id_list_label_mapped = jira.search_issues(jql_query)

        description = 'Approval purpose -- Commits Reference : %s' % compare_url
        if source_code:
            description = description + "\t" + "Source Code: " + source_code
        if artifact_url:
            description = description + "\t" + "Artifact URL: " + artifact_url
        if sonarqube_url:
            description = description + "\t" + "SonarQube Report: " + sonarqube_url
        args = {"project": project_key, "summary": 'New approval request for :' + job_name,
                "description": description,
                "labels": label_list,
                "issuetype": {'name': issue_type},
                "assignee": {"name": ""}}
        # Identify the id of Additional Assignee JIRA field
        allfields = jira.fields()
        name_map = {field['name']: field['id'] for field in allfields}
        custom_field_id = name_map.get(constants.JIRA_ADDITIONAL_ASSIGNEE)
        args[custom_field_id] = user_login_name_list
        new_issue = jira.create_issue(**args)

        label_list_mapped_jira_id_list = []
        if len(jira_id_list_label_mapped) != 0:
            for jira_id in jira_id_list_label_mapped:
                issue = jira.issue(jira_id)
                label_list_mapped_jira_id_list.append(issue)
            for outward_issue in label_list_mapped_jira_id_list:
                jira.create_issue_link('relates', new_issue, outward_issue)
        else:
            log.info("Jira label data is empty")

        if epic_id is None:
            return new_issue.key, None
        else:
            jira.add_issues_to_epic(epic_id, [new_issue.key])
            return new_issue.key, None

    except (NewConnectionError, ConnectionRefusedError, MaxRetryError, ConnectionError, Exception) as e:
        log.error(e)
        return None, e


"""
function to return the data in  yaml data that matches with provided key
"""


def get_pipeline_data(yaml_data, pipe_line_key, log, pipeline_tool=None):
    pipeline_tool_data_formated = {}
    pipe_line_data = None
    status = 'disabled'
    try:
        pipeline = yaml_data.get('pipeline')
        if isinstance(pipeline, list):
            pipe_line_data = next((item for item in pipeline if item["type"] == pipe_line_key))
        elif isinstance(pipeline, dict):
            pipe_line_data = pipeline.get(pipe_line_key)
    except StopIteration as e:
        log.error(e)
    except Exception as e:
        log.error(e)
    if pipe_line_data is not None and isinstance(pipeline, list):
        status = pipe_line_data.get('status')
        name = pipe_line_data.get('name')
        template = pipe_line_data.get('template')
        pipeline_tool_data = pipe_line_data
    elif pipe_line_data is not None and isinstance(pipeline, dict):
        data = {}

        if pipeline_tool:
            data = pipe_line_data.get(pipeline_tool)
            if 'status' in data and data.get('status').lower() == 'enabled':
                status = data.get('status')
        else:
            for pipeline_tool, data in pipe_line_data.items():
                if 'status' in data and data.get('status').lower() == 'enabled':
                    status = data.get('status')
                    break

        name = pipeline_tool
        template = pipe_line_data.get(pipeline_tool).get('template')
        pipeline_tool_data = data
    else:
        return {}
    if status.lower() == 'enabled':
        pipeline_tool_data_formated.update({'name': name})
        pipeline_info_data = yaml_data.get(template)
        if pipeline_info_data and pipeline_tool_data and name in pipeline_info_data.keys():
            if constants.PIPELINE_INFRA_KEY in pipeline_tool_data.keys() and constants.PIPELINE_INFRA_KEY in pipeline_info_data.get(
                    name).keys():
                pipeline_tool_data_formated.update(pipeline_info_data.get(name).get(constants.PIPELINE_INFRA_KEY).get(
                    pipeline_tool_data.get(constants.PIPELINE_INFRA_KEY)))
            elif name in pipeline_info_data.keys() and constants.PIPELINE_INFRA_KEY in pipeline_info_data.get(
                    name).keys():
                pipeline_tool_data_formated.update(
                    pipeline_info_data.get(name).get(constants.PIPELINE_INFRA_KEY).get('NA'))
            if 'template' in pipeline_info_data.get(name).keys():
                templates = {}
                for element, values in pipeline_info_data.get(name).items():
                    if element == constants.PIPELINE_INFRA_KEY:
                        continue
                    for key, value in values.items():
                        templates.update({str(element) + '_' + str(key): value})
                if 'template_version' in pipeline_tool_data.keys():
                    templates.update({'template_version': pipeline_tool_data.get('template_version')})
                else:
                    templates.update({'template_version': 'v1'})
                pipeline_tool_data_formated.update(refine(templates))
        return pipeline_tool_data_formated
    else:
        return {}


"""
function to formate the poll interval time as jenkins recommended form
"""


def set_cron_expression(poll_interval):
    if poll_interval is None:
        param = '@daily'
        return param
    poll_interval = poll_interval.lower()
    if poll_interval == "daily" or poll_interval == "monthly" or poll_interval == "weekly" or poll_interval == "yearly" or poll_interval == "annually" or poll_interval == "midnight":
        param = '@' + poll_interval

    elif poll_interval.__contains__("minutes"):
        sch = int(re.findall('\d+', poll_interval)[0])
        if sch != 1:
            if sch <= 60:
                param = "H/%d * * * *" % sch
            else:
                sch = round(sch / 60)
                param = "H 0-23/%d * * *" % sch
        else:
            param = "@daily"

    elif poll_interval.__contains__("hours"):
        sch = int(re.findall('\d+', poll_interval)[0])
        param = "H 0-23/%d * * *" % sch

    elif poll_interval.__contains__("day"):
        sch = int(re.findall('\d+', poll_interval)[0])
        if sch:
            param = "H %d * * *" % sch
        else:
            param = "H 1 * * *"

    else:
        param = '@daily'
    return param


"""
function to get the jenkins templete when flo_multi.yml is modified
"""


def get_multibranch_pipeline_configuration(yaml_data, repo_name, organization, jenkins_parameters, credential_id,
                                           templates_repo, templates_branch, template_version, log, agent):
    exclude_branches_list = yaml_data.get('exclude_branches')
    include_branches_list = yaml_data.get('include_branches')
    exclude_branch_prs_list = yaml_data.get('exclude_branch_PRs')
    discover_strategy = yaml_data.get('discover_strategy')
    corelation_id = yaml_data.get("cid")
    script_id = yaml_data.get("multibranch_script_id")
    sandbox_enable = yaml_data.get("sandbox_enable")
    script_id_enable, sandbox_value = False, False
    # <----- DDO-2684 adding restrictions to sandbox_enable to be boolean
    if script_id is not None and script_id and isinstance(script_id, str):
        script_id_enable = True
    if sandbox_enable is not None and (isinstance(sandbox_enable, bool) and sandbox_enable):
        sandbox_value = True
    # END DDO-2684 ----->
    jenkins_agent = None
    build_name = yaml_data.get('build_tool').get('name')
    is_exclude_branch = True
    if exclude_branches_list is not None:
        exclude_branches_with_space = " ".join(exclude_branches_list)
    else:
        exclude_branches_with_space = ''
    if include_branches_list is not None:
        include_branches_with_space = " ".join(include_branches_list)
    else:
        include_branches_with_space = '*'
    is_exclude_branch_pr, pr_exclude_branches_with_space, pr_include_branches_with_space = get_branch_source_filter_configuration(
        exclude_branch_prs_list)
    if is_exclude_branch_pr:
        exclusive = exclude_branch_prs_list.get('exclusive')
        if exclusive:
            is_exclude_branch = False
    branch_strategy, origin_pullrequest_strategy, fork_pullrequest_strategy = 1, 1, 1
    if discover_strategy is not None:
        branch_strategy = discover_strategy.get('branches', 1)
        origin_pullrequest_strategy = discover_strategy.get('origin_pullrequests', 1)
        fork_pullrequest_strategy = discover_strategy.get('fork_pullrequests', 1)

    if yaml_data.get('jenkins_metadata', {}) != {} and yaml_data.get('jenkins_metadata', {}).get('agent_mapper',
                                                                                                 {}) != {}:
        agent_key = organization + "_" + build_name
        jenkins_agent = yaml_data.get('jenkins_metadata', {}).get('agent_mapper', {}).get(agent_key, None)
        if not agent and jenkins_agent is None:
            jenkins_agent = yaml_data.get('jenkins_metadata', {}).get('agent_mapper', {}).get(build_name, None)
    # <----- DDO-2978
    jenkins_parameters.update({'agent_label': jenkins_agent, 'slave_label': jenkins_agent})

    # END OF DDO-2978 ----->
    jenkins_template = yaml_data.get('jenkins_template')
    template = yaml_data.get('jenkins_metadata').get('template_mapper').get(jenkins_template)
    raw_url = get_raw_url(templates_repo, templates_branch, template_version, template)
    formated_config = get_job_templates(raw_url)
    log.event(corelation_id, "Build config format checking completed")
    if formated_config is None:
        msg = str(template) + " - template is getting failed"
        return None, msg, None, None
    # <----- DDO-2978
    database_url = app.config.get('database_url')
    if ("override_slave_label" in jenkins_parameters) or jenkins_parameters.get("override_slave_label"):
        jenkins_parameters.update({"override_agent_label": jenkins_parameters.get("override_slave_label")})
        msg = constants.AGENT_NAME_WARNING
        # <----- DDO-3095 disabling waring notification
        log.status(corelation_id, mail.STATUS.WARNING, msg)
        # notification_util.insert_message(corelation_id, database_url, msg, mail.STATUS.WARNING, flo_name,
        #                                  )
        # END OF DDO-3095 ----->
    # END OF DDO-2978 ----->
    # <----- DDO-3452
    if ("ansible_slave_label" in jenkins_parameters) or jenkins_parameters.get("ansible_slave_label"):
        jenkins_parameters.update({"ansible_agent_label": jenkins_parameters.get("ansible_slave_label")})
        msg = constants.AGENT_NAME_WARNING
        log.info(msg)
    # END OF DDO-3452 ----->
    template_file = render_template_string(formated_config, exclude_branches_with_space=exclude_branches_with_space,
                                           repo_name=repo_name,
                                           is_exclude_branch=is_exclude_branch,
                                           is_exclude_branch_pr=is_exclude_branch_pr,
                                           pr_exclude_branches_with_space=pr_exclude_branches_with_space,
                                           pr_include_branches_with_space=pr_include_branches_with_space,
                                           organization=organization, credential_id=credential_id,
                                           jenkins_parameters=jenkins_parameters,
                                           include_branches_with_space=include_branches_with_space,
                                           branch_strategy=branch_strategy,
                                           fork_pullrequest_strategy=fork_pullrequest_strategy,
                                           origin_pullrequest_strategy=origin_pullrequest_strategy,
                                           script_id_enable=script_id_enable, sandbox_value=sandbox_value,
                                           script_id=script_id
                                           )
    return template_file, None, None, None


def get_branch_source_filter_configuration(exclude_branch_prs_list):
    """
    This function is to support "Filter by name including PRs destined for this branch (with wildcards)" option for
    multi pipeline job
    Args:
        exclude_branch_prs_list: exclude branch prs list from application yaml

    Returns:
        is_exclude_branch_pr: boolean flag
        pr_exclude_branches_with_space: exclude list with space
        pr_include_branches_with_space: Include list with space

    """
    is_exclude_branch_pr = False
    if exclude_branch_prs_list:
        is_exclude_branch_pr = True
        exclude_branches = exclude_branch_prs_list.get('exclude_branches')
        include_branches = exclude_branch_prs_list.get('include_branches')
        if exclude_branches:
            pr_exclude_branches_with_space = " ".join(exclude_branches)
        else:
            pr_exclude_branches_with_space = ''
        if include_branches:
            pr_include_branches_with_space = " ".join(include_branches)
        else:
            pr_include_branches_with_space = '*'

        return is_exclude_branch_pr, pr_exclude_branches_with_space, pr_include_branches_with_space
    return is_exclude_branch_pr, None, None


"""
Function to set webhook in git to trigger the jenkins build when any changes were made in the repo
"""


def set_github_jenkinswebhook_url(jenkins_url, repo_host, organization):
    data = {
        "name": "web",
        "active": True,
        "events": ["*"],
        "config": {
            "url": jenkins_url + constants.JENKINS_WEBHOOK_EXT,
            "content_type": "json"
        }
    }
    hook_api_url = repo_host.replace(organization, 'api/v3/repos/' + organization).replace('.git', '/hooks')
    vault_obj = vault.Vault(vault_url, os.environ[constants.VAULT_NAME])
    token = vault_obj.get(vault_path, df_store_vkey)
    responce = requests.post(hook_api_url, json=data, auth=('', token))
    status = responce.status_code
    return status


"""
function to format the environmental variables as required
"""


def set_environment_variables(env_variables=None, encrypt_variables=None):
    env_data = []
    if env_variables:
        for env_vars_key, env_vars_value in env_variables.items():
            if isinstance(env_variables[env_vars_key], dict):

                connection_data = env_variables[env_vars_key]
                for connection_key, connection_value in connection_data.items():

                    if isinstance(connection_data[connection_key], dict):
                        db_data = connection_data[connection_key]
                        for db_key, db_value in db_data.items():
                            if isinstance(db_data[db_key], dict):
                                type_data = db_data[db_key]
                                for type_key, type_value in type_data.items():
                                    env_data.append(
                                        env_vars_key + '_' + connection_key + '_' + db_key + '_' + type_key + '=' + type_value)
                            else:
                                env_data.append(env_vars_key + '_' + connection_key + '_' + db_key + '=' + db_value)
                    elif env_vars_key == 'vars':
                        env_data.append(connection_key + '=' + connection_value)
                    else:
                        env_data.append(env_vars_key + '_' + connection_key + '=' + connection_value)
            else:
                if env_vars_key is not None and env_vars_value is not None:
                    env_data.append(env_vars_key + '=' + env_vars_value)

        env_var_data = ",".join(env_data)
        return env_var_data


# updating apim_paramters as jenkins params
def update_apim_parameters(apim_details, yaml_data):
    if apim_details.get('apim_endpoint'):
        branch = yaml_data.get('branch').lower()
        if apim_details.get('apim_endpoint_context'):
            apim_app_env = apim_details.get('apim_endpoint_context')
        elif constants.ENV_MASTER in branch:
            apim_app_env = constants.APIM_APP_ENV_PROD
        elif constants.ENV_PREPROD in branch or constants.ENV_PRE_PROD in branch:
            apim_app_env = constants.APIM_APP_ENV_PREPROD
        elif constants.ENV_UAT in branch:
            apim_app_env = constants.APIM_APP_ENV_UAT
        elif constants.ENV_DEV in branch or constants.ENV_SIT in branch:
            apim_app_env = constants.APIM_APP_ENV_SIT
        elif constants.ENV_TEST in branch:
            apim_app_env = constants.APIM_APP_ENV_TEST
        else:
            apim_app_env = 'None'

        endpoint_url = apim_details['apim_endpoint']
        apim_region = 'None'
        if yaml_data.get('cloud_info'):
            if yaml_data['cloud_info'].get('hostingfarmDomain'):
                apim_region = yaml_data['cloud_info'].get('webappName')
            if not apim_region:
                apim_region = yaml_data['cloud_info'].get('apiapp_name')

        if apim_region and apim_app_env:
            apim_region = apim_region[:2]
            endpoint_url += apim_region + '/' + apim_app_env

            yaml_data['apim']['apim_endpoint'] = endpoint_url


def insert_jira_details(log, yaml_data, jira_id, to_status, from_status, job_name, corelation_id, deploy_time="none"):
    database_url = app.config.get('database_url')
    try:
        connect(database_url)
    except ConnectionError as e:
        log.error(e, corelation_id)
        msg = "Unable to connect mongodb url - " + str(e)
        log.status(corelation_id, mail.STATUS.ERROR, "Unable to connect mongodb url")
        log.critical(msg)
        return None
    except Exception as e:
        log.error(e, corelation_id)
        msg = "Unable to connect mongodb url - " + str(e)
        log.status(corelation_id, mail.STATUS.ERROR, "Unable to connect mongodb url")
        log.critical(msg)
        return None
    ecosystem_ready = constants.NON_SLOT_DEPLOY
    if float(yaml_data.get('schema_version')) == constants.SLOT_DEPLOY_SCHEMA:
        if yaml_data.get("cloud_info") and yaml_data.get("cloud_info").get('slotEnable') and \
                yaml_data.get("cloud_info").get('slotEnable') == 'true':
            if yaml_data.get('release') == 'deploy':
                ecosystem_ready = constants.IS_A_SLOT_DEPLOY
    commit_id = yaml_data.get('commit_id')
    if commit_id is None:
        commit_id = 'none'
    insert_data = JiraMetadata(jira_id=jira_id, cid=corelation_id, job_name=job_name, commit_id=commit_id,
                               workflow_status=to_status,
                               new_workflow_status=from_status, approved=constants.JIRA_NOT_APPROVED_FLAG,
                               deploy_time=deploy_time, jira_approve_time='none',
                               ecosystem_ready=ecosystem_ready, deploy_type='normal').save()
    return insert_data


def connect_to_db(corelation_id):
    log = app.config.get('log')
    database_url = app.config.get('database_url')
    log.info("connecting to " + database_url + " DB")
    try:
        connect(database_url)
    except ConnectionError as e:
        log.error(e, corelation_id)
        msg = "Unable to connect mongodb url - " + str(e)
        log.status(corelation_id, mail.STATUS.ERROR, "Unable to connect mongodb url")
        log.critical(msg)
        raise Exception(msg)
    except Exception as e:
        log.error(e, corelation_id)
        msg = "Unable to connect mongodb url - " + str(e)
        log.status(corelation_id, mail.STATUS.ERROR, "Unable to connect mongodb url")
        log.critical(msg)
        raise Exception(msg)


def get_jira_detailsfromdb(log, corelation_id, jira_id):
    try:
        connect_to_db(corelation_id)
    except ConnectionError as e:
        log.error(e, corelation_id)
        msg = "Unable to connect mongodb url - " + str(e)
        log.status(corelation_id, mail.STATUS.ERROR, "Unable to connect mongodb url")
        log.critical(msg)
        return None
    except Exception as e:
        log.error(e, corelation_id)
        msg = "Unable to connect mongodb url - " + str(e)
        log.status(corelation_id, mail.STATUS.ERROR, "Unable to connect mongodb url")
        log.critical(msg)
        return None
    data_dict = {'_id': jira_id}
    data = JiraMetadata.objects.raw(data_dict)
    data_list = list(data)
    if len(data_list) != 0:
        return data_list[-1]
    else:
        return None


def update_ecosystem_status(log, corelation_id, jira_id, flag):
    try:
        connect_to_db(corelation_id)
    except ConnectionError as e:
        log.error(e, corelation_id)
        msg = "Unable to connect mongodb url - " + str(e)
        log.status(corelation_id, mail.STATUS.ERROR, "Unable to connect mongodb url")
        log.critical(msg)
        return None
    except Exception as e:
        log.error(e, corelation_id)
        msg = "Unable to connect mongodb url - " + str(e)
        log.status(corelation_id, mail.STATUS.ERROR, "Unable to connect mongodb url")
        log.critical(msg)
        return None

    data_dict = {'_id': jira_id}
    log.info("updating DB with ecosystem_ready flag to %s " % flag, corelation_id)
    data = JiraMetadata.objects.raw(data_dict).update({"$set": {'ecosystem_ready': flag}}, upsert=True)
    return data


def swap_deployment_processing(response_data):
    log = app.config.get('log')
    log.info('Slot Deployment process started')
    try:
        exp_time, jira_id, yaml_data, mail_users_list, app_code, primary_server, job_url, api_status = jenkins_job_update(
            response_data)
        if api_status == constants.SUCCESS_KEY:
            # check and trigger jenkins job
            message, status = validate_trigger_jenkins_job(job_url, exp_time, jira_id, yaml_data, mail_users_list,
                                                           app_code, primary_server)
        else:
            message = constants.SLOT_DEPLOYMENT_FAIL_MSG
            log.error(message)
            status = 500
        return message, status
    except Exception as e:
        msg = 'Exception while re-configuring the jenkins Job and triggering %s' % str(e)
        return msg, 500


def jenkins_job_update(response_data):
    log = app.config.get('log')
    log.info('Updating Jenkins Job with release as swap')
    try:
        job_url = response_data.get('job_url')
        if not job_url:
            message = constants.JOB_URL_NA_ERROR
            raise Exception(message)

        jenkins_user = response_data.get('jenkins_user')
        if not jenkins_user:
            message = constants.JENKINS_USER_NA_ERROR
            raise Exception(message)

        jenkins_vkey = response_data.get('jenkins_vkey')
        if not jenkins_vkey:
            message = constants.JENKINS_VKEY_NA_ERROR
            raise Exception(message)

        vault_path = app.config.get('vault_path')
        vault_url = app.config.get('vault_url')

        vault_obj = vault.Vault(vault_url, os.environ[constants.VAULT_NAME])
        jenkins_token = vault_obj.get(vault_path, jenkins_vkey)
        jenkins_job_split=job_url.strip('/').split('/job/')
        jenkins_url = jenkins_job_split[0]
        organization=jenkins_job_split[1]
        jenkins_job_name="/".join(jenkins_job_split[2:])

        # get config.xml of jenkins job
        configxml_url = job_url + '/config.xml'
        configxml_response = requests.get(configxml_url, auth=(jenkins_user, jenkins_token))
        if configxml_response.status_code != 200:
            message = constants.XML_CONFIG_ERROR
            raise Exception(message)

        exp_time, jira_id, yaml_data, mail_users_list, app_code = [False] * 5

        # Get Proper XML Output
        xmlstring = configxml_response.text
        config = ET.ElementTree(ET.fromstring(xmlstring))
        root = config.getroot()
        jenkins_parameters = root.findall('properties')[0].find('hudson.model.ParametersDefinitionProperty').find(
            'parameterDefinitions').getchildren()
        for index, params in enumerate(jenkins_parameters):
            if params.find('name').text == 'release':
                config.getroot().findall('properties')[0].find('hudson.model.ParametersDefinitionProperty').find(
                    'parameterDefinitions').getchildren()[index].find('defaultValue').text = 'swap'

            if params.find('name').text == 'deploy_time':
                exp_time = params.find('defaultValue').text

            if params.find('name').text == 'jira_id':
                jira_id = params.find('defaultValue').text

            if params.find('name').text == 'yaml_data':
                yaml_data = params.find('defaultValue').text

            if params.find('name').text == 'mail_users_list':
                mail_users_list = params.find('defaultValue').text

            if params.find('name').text == 'app_code':
                app_code = params.find('defaultValue').text
        # yaml_data is retrieved from a jenkins parameter and which is of string type and when we use
        # eval function of python will evaluate the expression in string format , will convert the string to dict
        cid = yaml.safe_load(yaml_data).get('cid')

        if jira_id:
            jiradetails = get_jira_detailsfromdb(log, cid, jira_id)
            eco_flag = jiradetails.ecosystem_ready
            if eco_flag < constants.CONFIGURING_ECOSYSTEM:
                update_ecosystem_status(log, cid, jira_id, constants.CONFIGURING_ECOSYSTEM)
            else:
                log.error("Received multiple request for swap deploy ")
                return exp_time, jira_id, yaml_data, mail_users_list, app_code, None, job_url, constants.FAILED_KEY
        job_status = response_data.get('job_status')
        if job_status.lower() != constants.SUCCESS_KEY.lower():
            # update ecosystem in DB
            update_ecosystem_status(log, cid, jira_id, constants.ECOSYSTEM_VALUE_WHEN_SLOTDEPLOYMENT_FAILED)
            # Sending mail
            msg = constants.SLOT_DEPLOYMENT_FAIL_MSG
            send_alerts(log, msg, constants.FLO_NAME, cid, mail.STATUS.ERROR, mail_users_list, None, job_url,
                        jira_id, app_code)
            return exp_time, jira_id, yaml_data, mail_users_list, app_code, None, job_url, constants.FAILED_KEY

        configdata = ET.tostring(config.getroot(), encoding='utf8', method='xml').decode()

        try:
            primary_server = jenkins.Jenkins(jenkins_url, username=jenkins_user, password=jenkins_token)
        except Exception as e:
            message = constants.JENKINS_ERROR + '<br>' + str(e)
            raise Exception(message)

        # Jenkins job updation
        try:
            job_request_deploy = primary_server.reconfig_job(organization + '/' + jenkins_job_name,
                                                             configdata)
            log.debug(str(job_request_deploy))

        except Exception as e:
            message = "Jenkins Job updation failed - " + organization + '/' + jenkins_job_name
            raise Exception(message)
    except Exception as e:
        message = 'Exception while re-configuring the jenkins Job %s' % str(e)
        raise Exception(message)

    log.info(constants.JENKINS_JOB_CONFIG_SUCCESS)
    return exp_time, jira_id, yaml_data, mail_users_list, app_code, primary_server, job_url, constants.SUCCESS_KEY


def validate_trigger_jenkins_job(job_url, exp_time, jira_id, yaml_data, mail_users_list, app_code, primary_server):
    log = app.config.get('log')
    log.info('Validating and Trigger Jenkins job process has started')
    try:
        jenkins_job_split = job_url.strip('/').split('/job/')
        jenkins_url = jenkins_job_split[0]
        organization = jenkins_job_split[1]
        jenkins_job_name = "/".join(jenkins_job_split[2:])
        cid = yaml.safe_load(yaml_data).get('cid')
        approved_time, approved_datetime, jiradetails, approved, time_delay, trigger_job = [None] * 6

        # Get JiraDetails from DB
        if jira_id:
            jiradetails = get_jira_detailsfromdb(log, cid, jira_id)

        # Checking whether to trigger Job or not
        if exp_time:  # NonDev Job
            exp_est_time = parse(exp_time)
            zone = constants.EST_TIMEZONE
            if jiradetails:
                approved_time = jiradetails.jira_approve_time
            # Convert approved_time to readable dateformat
            if approved_time and approved_time != 'none':
                jira_trigger_time = int(str(approved_time)[:10])
                jira_time = str(time.ctime(jira_trigger_time))
                approved_datetime = parse(jira_time)
            else:
                msg = constants.JIRA_NOT_APPROVED_ERROR
                log.info(msg)
                # update ecosystem status as 1
                update_ecosystem_status(log, cid, jira_id, constants.ECOSYSTEM_READY_VALUE)

                msg = constants.SWAP_BEFORE_JIRA_APPROVAL_SCHEDULETIME % exp_time
                send_alerts(log, msg, constants.FLO_NAME, cid, mail.STATUS.SUCCESS, mail_users_list, None, job_url,
                            jira_id, app_code)

                return msg, 200

            approved_est_time = approved_datetime.astimezone(pytz.timezone(zone))
            if exp_est_time.replace(tzinfo=None) > approved_est_time.replace(tzinfo=None):
                log.info('deploy time is less than current time, hence triggering the job')

                current_local_time = datetime.datetime.now(get_localzone())
                current_est_time = current_local_time.astimezone(pytz.timezone(zone))
                time_diff = (exp_est_time.replace(tzinfo=None) - current_est_time.replace(tzinfo=None))
                time_diff_in_sec = time_diff.days * 24 * 60 * 60 + time_diff.seconds
                time_delay = str(time_diff_in_sec) + "sec"
                log.info("time delay for schedule build: " + str(time_delay))

                trigger_job = True
            else:
                # Send mail saying job will not trigger
                msg = constants.SCHEDULE_ERROR_MSG
                send_alerts(log, msg, constants.FLO_NAME, cid, mail.STATUS.ERROR, mail_users_list, None, job_url,
                            jira_id, app_code)
                return msg, 500
        elif jira_id:  # NonDev Job
            if jiradetails:
                approved = jiradetails.approved
            if approved == constants.JIRA_APPROVED_VALUE:
                log.info('Jira is approved, hence triggering the job')
                trigger_job = True

        if trigger_job:
            # update ecosystem status as 1
            update_ecosystem_status(log, cid, jira_id, constants.ECOSYSTEM_READY_VALUE)
            # Call Trigger Job
            jenkins_param_dict = {'key': 'value'}
            if time_delay:
                jenkins_param_dict = {'delay': time_delay}
            try:
                job_request = primary_server.build_job(organization + '/' + jenkins_job_name, jenkins_param_dict)
                log.info('Job has been triggered -- %s - %s' % (organization, jenkins_job_name))
                log.debug(str(job_request))
            except Exception as e:
                msg = "Jenkins Job execution failed - " + organization + '/' + jenkins_job_name
                return msg, 500
            # send notification users saying, job has been triggered
            if time_delay:
                msg = constants.SWAP_SCHEDULE_TRIGGER % exp_time
            else:
                msg = constants.SWAP_JIRA_TRIGGER
            send_alerts(log, msg, constants.FLO_NAME, cid, mail.STATUS.SUCCESS, mail_users_list, None, job_url,
                        jira_id, app_code)
        else:
            # send notification to users, as release has been updated as swap
            if approved != constants.JIRA_DECLINED_VALUE:
                if exp_time:
                    msg = constants.SWAP_BEFORE_JIRA_APPROVAL_SCHEDULETIME % exp_time
                else:
                    msg = constants.SWAP_BEFORE_JIRA_APPROVAL
                send_alerts(log, msg, constants.FLO_NAME, cid, mail.STATUS.SUCCESS, mail_users_list, None, job_url,
                            jira_id, app_code)
    except Exception as e:
        message = 'Exception while validating and triggering jenkins job %s' % str(e)
        raise Exception(message)

    # Do not update ecosystem value, as Jira is declined
    if approved != constants.JIRA_DECLINED_VALUE:
        update_ecosystem_status(log, cid, jira_id, constants.ECOSYSTEM_READY_VALUE)

    return "Success", 200


def send_alerts(log, msg, flo_name, corelation_id, status, mail_to=None, success_msg=None, job_url=None, jira_id=None,
                job_name=None):
    mail_from = app.config.get('MAIL_FROM')
    log.status(corelation_id, status, msg)
    subject = "Approval Workflow Processing"
    if job_name:
        job_name = job_name.split('/')[-1]
        subject = subject + " : " + job_name
    mail_cc = app.config.get('MAIL_CC')
    mail_data = {'cid': corelation_id, 'flo_name': flo_name}
    if jira_id:
        mail_data.update({'jira_id': jira_id})
    if not mail_to:
        mail_to = constants.DEFAULT_MAIL_TO

    if status.name.lower() == 'error':
        mail_status = mail.STATUS.ERROR
    else:
        mail_data.update({'job_url': job_url})
        mail_status = mail.STATUS.SUCCESS

    mail.send(mail_from, mail_to, mail_cc, subject, mail_status, data=mail_data,
              message=msg)


def approvers_filter_process(approvers_white_list_data, organization, repo_name, approval_mail_list):
    """
    This method will return the approvers mail list matched with white label list from flo.yml
    :param approvers_white_list_data: white_list_approvers from flo.yml or collated yaml data
    :param organization: application repo organization from collated yaml data
    :param repo_name: application repository name
    :param approval_mail_list: approvers data from collated yaml data
    :return: white_label_list
    """
    final_white_list_approvers = []
    # <----- DDO-3071 adding support to case sensitive comparision
    if approval_mail_list and isinstance(approval_mail_list, list):
        approval_mail_list = list(map(lambda x: x.lower(), approval_mail_list))
    # END DDO-3071
    global_list = approvers_white_list_data.get('global_list')
    if global_list:
        final_white_list_approvers.extend(global_list)
    org_level_data = approvers_white_list_data.get('org_level_list')
    if org_level_data:
        org_data = org_level_data.get(organization)
        if org_data:
            org_global_list = org_data.get('global_list')
            if org_global_list:
                final_white_list_approvers.extend(org_global_list)
            repo_level_list = org_data.get(repo_name)
            if repo_level_list:
                final_white_list_approvers.extend(repo_level_list)
    if final_white_list_approvers:
        # Compare and getting the matched approvers list to white list approvers
        # < ----- DDO-2644 WILDCARD support
        # <----- DDO-3071 adding support to case sensitive comparision
        if isinstance(final_white_list_approvers, list):
            final_white_list_approvers = list(map(lambda x: x.lower(), final_white_list_approvers))
        # END DDO-3071
        if constants.WILD_CARD_APPROVER in final_white_list_approvers:
            return approval_mail_list, list(set(final_white_list_approvers)), None
        # DDO-2644 END
        approvers_white_list = [approvers_list for approvers_list in approval_mail_list if
                                approvers_list in final_white_list_approvers]
        if approvers_white_list:
            return list(set(approvers_white_list)), list(set(final_white_list_approvers)), None
        else:
            if approval_mail_list:
                msg = "The provided approvers are not part of allowed approvers - " + str(approval_mail_list)
                return None, list(set(final_white_list_approvers)), msg
            else:
                msg = "Approvers are not available in approvers details in division file"
                return None, list(set(final_white_list_approvers)), msg
    else:
        # If global approvers white list data is empty, sending email to support team as well as app team
        mail_from = app.config.get('MAIL_FROM')
        mail_support = app.config.get('MAIL_SUPPORT')
        df_store_flo_url = app.config.get('df_store_flo_url')
        subject = 'approvers white list data is empty'
        status = mail.STATUS.CRITICAL
        data = {'df_store_flo_url': df_store_flo_url}
        message = "allowed approvers details not present in approvers.yml"
        mail.send(mail_from, mail_support, '', subject, status, data, message)
        msg = "Global approvers are not available"
        return None, None, msg


# <--- DDO-2831
# This function will return the key_key_key:value of nested dictionary
# Example:
# input : dict_data = {'post-deploy': {'test': {'enable': True, 'tool': 'readyapi'}}}
# input : key_append = 'post-deploy'
# Output : {'post-deploy_test_enable': True, 'post-deploy_test_tool': 'readyapi'}
def dict_key_format(dict_data, key_append, jenkins_data_dict):
    if isinstance(dict_data, dict):
        for key, value in dict_data.items():
            if isinstance(value, dict):
                if key_append == '' or key_append is None:
                    key_append = key_append + key
                else:
                    key_append = key_append + '_' + key
                dict_key_format(value, key_append, jenkins_data_dict)
                key_append = ''
            else:
                if key_append == '' or key_append is None:
                    jenkins_data_dict.update({key: value})
                else:
                    key = key_append + '_' + str(key)
                    jenkins_data_dict.update({key: value})
    else:
        jenkins_data_dict.update({key_append: dict_data})
    return jenkins_data_dict
# END DDO-2831 --->


def raw_url_formation(input_url):
    regexpresion = r"(http[s]?:\/\/[^\/]+)"
    matches = re.search(regexpresion, input_url)
    if matches:
        baseurl = matches.group(1)
        path = input_url.split(baseurl)[1]
        raw_url = baseurl + '/raw' + path
    else:
        raw_url = None
    return raw_url

def get_artifact_data(yaml_data,nexus_url,nexus_app_repo,log):
    try:
        artifact_name = list(yaml_data.get('artifacts').keys())[0]
        artifact_ext = artifact_name.rsplit('.', 1)[-1]
        artifact_no_ext = artifact_name.rsplit('.', 1)[0]
        organization = yaml_data.get('organization')
        source_env = yaml_data.get('source_env')
        version = str(yaml_data.get('app').get('version'))
        environment = yaml_data.get('environment')
        build_number = str(yaml_data.get('build_number'))
        app_type = yaml_data.get('app_type')
        deploy_type = yaml_data.get('deploy_type')
        if app_type == constants.DOCKER or deploy_type == constants.KUBERNETES or app_type == constants.companySTUDIO:
            if app_type == constants.DOCKER and deploy_type == constants.KUBERNETES and yaml_data.get('jenkins_extra_params') and (yaml_data.get('jenkins_extra_params', {}).get('docker_url')):
                docker_url = yaml_data.get('jenkins_extra_params', {}).get('docker_url')
                artifact_url =  constants.DOCKER_KUBERNETES_IMAGE.format(**{'docker_url':str(docker_url),'artifact_no_ext':artifact_no_ext,'version':version,'build_number':build_number})
            elif deploy_type == constants.KUBERNETES and yaml_data.get('jenkins_extra_params') and (yaml_data.get('jenkins_extra_params', {}).get('docker_repository')):
                docker_repository = yaml_data.get('jenkins_extra_params', {}).get('docker_repository')
                artifact_url =  constants.GENERIC_KUBERNETES_IMAGE.format(**{'docker_repository':str(docker_repository),'artifact_no_ext':artifact_no_ext,'version':version,'build_number':build_number,'source_env':source_env})
            else:
                return None,None,None
        else:
            if app_type == constants.DOTNET or app_type == constants.ADB2C or app_type == constants.MSBUILD:
                arguments = yaml_data.get('build_tool', {}).get(constants.ARGUMENTS, None)
                if arguments is not None:
                    classifier_name = arguments
                else:
                    classifier_name = constants.RELEASE
                artifact_url =  constants.ARTIFACT_URL_WITH_CLASSIFIER.format(**{'nexus_url':str(nexus_url),'artifact_repository':nexus_app_repo,'organization':organization, 'artifact_no_ext':artifact_no_ext,'version':version,'build_number':build_number,'environment':source_env,'classifier_name':classifier_name,'artifact_ext':artifact_ext})
            else:
                artifact_url = constants.ARTIFACT_URL_WITHOUT_CLASSIFIER.format(**{'nexus_url':str(nexus_url),'artifact_repository':nexus_app_repo,'organization':organization, 'artifact_no_ext':artifact_no_ext,'version':version,'build_number':build_number,'environment':source_env,'artifact_ext':artifact_ext})
        if yaml_data.get('repo_host').endswith('.git'):
            """
            Added new logic for retriving the app meta data from new app metadata endpoint api url
            Based on artifact url filter we are getting the metadata
            If this has not exist then we are proceedning to gat data in older way
            """
            app_metadata_url = yaml_data.get(constants.CALLBACK_KEY).get(constants.APP_METADATA_API_URL)
            if app_metadata_url:
                db_filter_data = {"buildartifacts":artifact_url}
                app_metadata_response = requests.get(app_metadata_url,json=db_filter_data)
                app_metadata_statuscode = app_metadata_response.status_code
                if app_metadata_statuscode == 200 :
                    app_metadata = app_metadata_response.json()
                    if app_metadata:
                        commit_id = app_metadata[0].get('commitID')
                        sonarqube_url = app_metadata[0].get('sonarURL')
                        if commit_id:
                            source_code = yaml_data.get('repo_host')[:-4]+'/tree/'+ commit_id
                            return source_code,artifact_url,sonarqube_url
            artifact_api_url = yaml_data.get(constants.CALLBACK_KEY).get(constants.ARTIFACT_API_URL,{})
            artifact_query_url = artifact_api_url + "?artifact_url=" + artifact_url
            artifact_data = requests.get(artifact_query_url)
            status_code = artifact_data.status_code
            if status_code == 200:
                artificat_content = artifact_data.json()
                if artificat_content.get("commit_id"):
                    source_code = yaml_data.get('repo_host')[:-4]+'/tree/'+ artificat_content.get("commit_id")
                    return source_code,artifact_url,None
                else:
                    log.info("Artifact details not persisted in DB")
        return None,None,None
    except Exception as e:
        log.info("Exception in getting Artifact details from DB :"+ str(e))
    return None,None,None
