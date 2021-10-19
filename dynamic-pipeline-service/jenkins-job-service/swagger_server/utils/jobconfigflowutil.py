################################################# MAINTAINER dynamic-pipeline_Dev@company.com ####################################
# OBJECTIVE
#     Establish connection to Jenkins , check the existence of artifact in nexus
#
# NAME
#     jenkinsConfigJobwutil.py
#
# FUNCTIONS
#     jenkins_server_connection(commited_user_mail,app_repo, builder_info)
#
#     artifacts_check_in_nexus(self,yaml_data,nexus_url,artifact_repository)
################################################# MAINTAINER dynamic-pipeline_Dev@company.com ####################################


import os
import jenkins
import requests
import yaml
from swagger_server.utils.fileutil import FileUtil
from custom_framework.log_util import logger
from custom_framework.util import mail
from swagger_server import constants
from custom_framework.vault import vault
from flask import current_app as app
from custom_framework.notification_engine import notification_engine_util
notification_util = notification_engine_util.NotificationEngineUtil()

flo_name = constants.FLO_NAME

class jenkinsConfigJobwUtil(logger.Logger):
    def __init__(self):
        super(jenkinsConfigJobwUtil, self).__init__(flo_name)
        self.fileutil = FileUtil()

    """
    function to establish connection to jenkins

    Arguments:
         commited_user_mail :
            type: str
            purpose: contains mail id who committed the flo_{env}.yml
         app_repo:
                type:str
                purpose: contains application repo name

        jenkins_info:
                type:dict
                purpose: contains jenkins info

    """

    def jenkins_server_connection(self,jenkins_info):
        self.info("Establishing jenkins connection")
        vault_url = app.config.get('vault_url')
        vault_path = app.config.get('vault_path')
        try:
            jenkins_token_vkey = jenkins_info.get('vkey')
            if jenkins_token_vkey is None:
                msg = "In pipeline_info.yml jenkins vault key value is not available"
                self.error(msg)
                return None,msg
            jenkins_url = jenkins_info.get('url')
            jenkins_user = jenkins_info.get('user')
            vault_obj = vault.Vault(vault_url, os.environ[constants.VAULT_NAME])
            token = vault_obj.get(vault_path, jenkins_token_vkey)

        except NameError as e:
            msg = "Failed to getting Jenkins token from vault - "+str(e)
            self.error(msg)
            return None,msg
        except Exception as e:
            msg = "Failed to getting Jenkins token from vault - "+str(e)
            self.error(msg)
            return None,msg

        if jenkins_user and jenkins_url and token is not None:
            try:
                primary_server = jenkins.Jenkins(jenkins_url, username=jenkins_user, password=token)
                return primary_server,None
            except ConnectionRefusedError as e:
                msg = "Jenkins connection failed from dynamic-pipeline "
                self.error(msg+str(e))
                return None,msg
            except ConnectionError as e:
                msg = "Jenkins connection failed from dynamic-pipeline "
                self.error(msg+str(e))
                return None,msg
            except Exception as e:
                msg = "Jenkins connection failed from dynamic-pipeline "
                self.error(msg+str(e))
                return None,msg
        else:
            msg = "In pipeline_info.yml please verify jenkins user or jenkins token or jenkins url is available"
            self.error(msg)
            return None,msg

    """
       function to check if the artifact exist in nexus

       Arguments:
            yaml_data :
               type: dict
               purpose: contains info related app and artifacts
            nexus_url:
                   type:str
                   purpose: contains nexus url

           artifact_repository:
                   type:str
                   purpose: contains artifact repository name

       """

    def artifacts_check_in_nexus(self, yaml_data, nexus_url, nexus_app_repo, nexus_api_url, mfy_repo = None):
        log = app.config.get('log')

        artifact_name = list(yaml_data.get('artifacts').keys())[0]
        artifact_ext = artifact_name.rsplit('.', 1)[-1]
        artifact_no_ext = artifact_name.rsplit('.', 1)[0]
        organization = yaml_data.get('organization')
        source_env = yaml_data.get('source_env')
        version = str(yaml_data.get('app').get('version'))
        environment = yaml_data.get('environment')
        build_number = str(yaml_data.get('build_number'))
        non_dev_env = yaml_data.get('non-dev-environments')
        jenkins_template = yaml_data.get('jenkins_template')
        if non_dev_env is None:
            follow_hierarchy = constants.FOLLOW_HIERARCHY
            non_dev_env_list = constants.NON_DEV_ENVIRONMENTS
            artifacts_validation = constants.ARTIFACTS_VALIDATION
        else:
            follow_hierarchy = non_dev_env.get('follow_hierarchy', None)
            non_dev_env_list = non_dev_env.get('env_list', None)
            artifacts_validation = non_dev_env.get('artifacts_validation', None)
            if follow_hierarchy is None:
                follow_hierarchy = constants.FOLLOW_HIERARCHY
            if non_dev_env_list is None:
                non_dev_env_list = constants.NON_DEV_ENVIRONMENTS
            if artifacts_validation is None:
                artifacts_validation = constants.ARTIFACTS_VALIDATION
        if jenkins_template == constants.KEY_PIPELINE_MANAGED:
            status,msg = self.artifact_validation_in_nexus(yaml_data, nexus_url, nexus_app_repo, nexus_api_url)
            if status == 'fail':
               return None,msg
            elif status == 'success':
               artifacts_validation = 'disable'
            else:
               log.info("This is not dotnet apiaps , proceeding for normal process")
        try:
            if artifacts_validation == 'enable':
                app_type = None
                deploy_type = None
                if yaml_data.get('app_type') is not None:
                    app_type = yaml_data.get('app_type').lower()
                else:
                    return None, "app_type is not defined"

                if yaml_data.get('deploy_type') is not None:
                    deploy_type = yaml_data.get('deploy_type').lower()
                else:
                    return None, "deploy_type is not defined"

                if app_type == constants.DOCKER:
                    # DDO-2941
                    if deploy_type == constants.KUBERNETES:
                        # As the docker kubernetes based application has a different path in nexus
                        app_name = "dynamic-pipeline/" + yaml_data.get('app', {}).get('name', None)
                        url_name = nexus_api_url.format(
                            **{'nexus_url': str(nexus_url), 'nexus_repo': nexus_app_repo,
                               'app_name': app_name,
                               'version': version, 'build_number': build_number})
                # DDO-2940
                elif (deploy_type == constants.KUBERNETES) and (app_type == constants.ANGULAR or app_type == constants.companySTUDIO):
                    url_name = nexus_api_url.format(
                        **{'nexus_url': str(nexus_url), 'nexus_repo': nexus_app_repo, 'organization': organization,
                           'app_name': yaml_data.get('app', {}).get('name', None), 'source_env': source_env,
                           'artifact_no_ext': artifact_no_ext, 'version': version, 'build_number': build_number})
                else:
                    # DDO-2937, DDO-2939, DDO-3021 raw repo
                    # Artifact validation support Angular_linux, Angular_static, php_linuxwepapps, modular_functions
                    url_name = nexus_api_url.format(**{'nexus_url':str(nexus_url),'nexus_repo':nexus_app_repo,
                                                       'organization':organization, 'artifact_no_ext':artifact_no_ext,
                                                       'version':version,'build_number':build_number})

                    arguments = yaml_data.get('build_tool', {}).get(constants.ARGUMENTS, None)

                    if app_type == constants.DOTNET or app_type == constants.ADB2C:
                        if arguments is not None:
                            url_name = url_name + "-" + arguments + "." + source_env + "." + artifact_ext
                        else:
                            url_name = url_name + "-" + constants.RELEASE + "." + source_env + "." + artifact_ext
                    else:
                        url_name = url_name + "." + source_env + "." + artifact_ext
                try:
                    log.info("Artifact validation started for: " + str(url_name))
                    nexus_responce = requests.get(url_name)
                    nexus_responce_json = nexus_responce.json()
                    artifact_items = nexus_responce_json.get('items')
                    if len(artifact_items) == 0:
                        return None, "artifacts are not available for this path - " + str(url_name)
                except (ConnectionRefusedError, ConnectionError, Exception) as e:
                    self.error(e)
                    return None, "Unable to connect to Nexus for Artifact validation"

            if follow_hierarchy == 'enable':
                current_env_index = non_dev_env_list.index(environment)
                if current_env_index > 0:
                    follow_prev_env = non_dev_env_list[current_env_index - 1]
                else:
                    follow_prev_env = source_env

                data_url = "https://" + str(
                    nexus_url) + "/repository/" + mfy_repo + "/" + follow_prev_env + "/" + organization + "/" + artifact_no_ext + "/" + version + "." + build_number + "/" + artifact_no_ext + "-" + version + "." + build_number + "." + "MFY"

                log.info("Previous promotional deployment validation started for: " + str(data_url))
                try:
                    data_responce = requests.get(data_url)
                except (ConnectionRefusedError, ConnectionError ,Exception) as e:
                    self.error(e)
                    return None, "Unable to connect to Nexus for previous promotional deployment validation"

                if data_responce.status_code == 200:
                    artifact_meta_data = yaml.load(data_responce.text)
                    status = artifact_meta_data.get('status')
                    if status.lower() == 'success':
                        return "SUCCESS", None
                    else:
                        return None, "previous promotional deployment failure - " + str(follow_prev_env)
                else:
                    return None, "previous promotional deployment meta data file not presented - " + str(
                        follow_prev_env)
            else:
                return "SUCCESS", None
        except (ConnectionRefusedError, ConnectionError, Exception) as e:
            self.error(e)
            return None, e

    def artifact_validation_in_nexus(self, yaml_data, nexus_url, nexus_app_repo, nexus_api_url):
        '''
        This function is used to validate the artifact exist in nexus for dotnet apiapps type of apps
        param: yaml_data
        param: nexus_url
        param: nexus_app_repo
        param: nexus_api_url
        '''
        log = app.config.get('log')
        artifact_name = list(yaml_data.get('artifacts').keys())[0]
        artifact_ext = artifact_name.rsplit('.', 1)[-1]
        artifact_no_ext = artifact_name.rsplit('.', 1)[0]
        organization = yaml_data.get('organization')
        source_env = yaml_data.get('source_env')
        version = str(yaml_data.get('app').get('version'))
        build_number = str(yaml_data.get('build_number'))
        app_type = None
        deploy_type = None
        status = 'ignore' # success|fail|ignore
        if yaml_data.get('app_type') is not None:
            app_type = yaml_data.get('app_type').lower()
        else:
            status = 'fail'
            return status, "app_type is not defined"

        if yaml_data.get('deploy_type') is not None:
            deploy_type = yaml_data.get('deploy_type').lower()
        else:
            status = 'fail'
            return status, "deploy_type is not defined"

        if app_type == constants.DOTNET and deploy_type == constants.APIAPPS:
            url_name = nexus_api_url.format(**{'nexus_url':str(nexus_url),'nexus_repo':nexus_app_repo,
                                            'organization':organization, 'artifact_no_ext':artifact_no_ext,
                                            'version':version,'build_number':build_number})

            arguments = yaml_data.get('build_tool', {}).get(constants.ARGUMENTS, None)
            if arguments is not None:
                url_name = url_name + "-" + arguments + "." + source_env + "." + artifact_ext
            else:
                url_name = url_name + "-" + constants.RELEASE + "." + source_env + "." + artifact_ext
        else:
            return status,None
        try:
            log.info("Artifact validation started for: " + str(url_name))
            nexus_responce = requests.get(url_name)
            nexus_responce_json = nexus_responce.json()
            artifact_items = nexus_responce_json.get('items')
            if len(artifact_items) == 0:
                return 'fail', "artifacts are not available for this path - " + str(url_name)
            else:
                return 'success',None
        except (ConnectionRefusedError, ConnectionError, Exception) as e:
            self.error(e)
            return 'fail', "Unable to connect to Nexus for Artifact validation"


