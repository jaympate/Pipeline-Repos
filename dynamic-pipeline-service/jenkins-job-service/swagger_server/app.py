#!/usr/bin/env python3

import os
import sys
import uuid

import connexion
import yaml
from cerberus import Validator
from custom_framework import flo
from custom_framework.log_util import logger
from custom_framework.notification_engine import notification_engine_util
from custom_framework.util import mail
from custom_framework.vault import vault

from swagger_server import constants
from swagger_server import encoder
from swagger_server import exception_error_code

notification_util = notification_engine_util.NotificationEngineUtil()
options = {"swagger_ui": False}
app = connexion.App(__name__, specification_dir='./swagger/', options=options)
app.app.json_encoder = encoder.JSONEncoder
app.add_api('swagger.yaml', arguments={'title': 'Job-Config-Flo'})
flo_env = os.environ.get(constants.ENV_NAME)
#<--- Begin DPE-11889
df_store_url = os.environ.get(constants.DF_STORE_URL)
#END DPE-11889-->

if flo_env is None or len(flo_env.strip()) == 0:
    print(constants.ENV_NAME + " env variable not set cannot start server")
    sys.exit()


class VaultObjectError(Exception):
    pass


@app.app.before_first_request
def load_configuration():
    # generate UUID for unique identification
    cid = str(uuid.uuid4().hex)
    app.app.config['log'] = logger.Logger(constants.FLO_NAME)
    log = app.app.config['log']
    log.basic_config(constants.DEFAULT_LOG_LEVEL, constants.DEFAULT_LOG_FILE, constants.FLO_NAME)
    log.event(cid, "configured the logging with default configuration")
    log.info("log level:" + str(log.logger.level), cid)
    log.status(cid, flo.STATUS.RECEIVED, constants.MSG_RECEIVED)
    #<--- Begin DPE-11889
    app.app.config['df_store_approvers_url'] = constants.DF_STORE_APPROVERS_URL.format(**{'df_store_url': df_store_url,'flo_env': flo_env})
    #END DPE-11889-->
    if flo_env == constants.MASTER_BRANCH:
        mail_from = constants.DEFAULT_MAIL_FROM
    elif flo_env == constants.APAC_REGION:
        mail_from = constants.MAIL_FROM.format(flo_env)
    else:
        mail_from = constants.MAIL_FROM.format(flo_env)
    mail_to = constants.DEFAULT_MAIL_TO
    mail_cc = constants.DEFAULT_MAIL_CC
    if os.environ.get(constants.VAULT_NAME, None) is None:
        message = constants.MSG_NO_VENV
        log.critical(message, cid)
        log.status(cid, flo.STATUS.ERROR, message)
        mail.send(mail_from, mail_to, mail_cc, constants.SUB_NO_VENV, mail.STATUS.CRITICAL, data={},
                  message=message)
        sys.exit()
    log.event(cid, "flo_env:" + flo_env)
    log.info("loading configuration", cid)

    configfile = constants.CONFIG_FILE.format(**{'flo_env': flo_env})
    schema_file = constants.SCHEMA_FILE
    try:
        with open(configfile, 'r') as stream:
            configuration_data = yaml.safe_load(stream)
    except Exception as e:
        message = exception_error_code.BAD_YAML_ERROR + ": " + constants.MSG_YAML_ERROR.format(
            **{'yaml_file': configfile})
        log.error(message + str(e), cid)
        log.status(cid, flo.STATUS.ERROR, message)
        mail.send(mail_from, mail_to, mail_cc, constants.SUB_YAML_ERROR, mail.STATUS.CRITICAL, data={},
                  message=message)
        sys.exit()
    # get the schema file where rules for app configuration where defined
    try:
        with open(schema_file, 'r') as stream:
            schema = yaml.safe_load(stream)
    except Exception as e:
        message = exception_error_code.NO_SCHEMA_FILE + ": " + constants.MSG_CONF_VALID_SCHEMA_ERROR
        log.error(message + str(e), cid)
        log.status(cid, flo.STATUS.ERROR, message)
        mail.send(mail_from, mail_to, mail_cc, constants.SUB_CONF_VALID_SCHEMA_ERROR, mail.STATUS.CRITICAL, data={},
                  message=message)
        sys.exit()
    # validating the configuration file
    validator = Validator(schema)
    # check if Configuration validation is successful
    if not validator.validate(configuration_data, schema):
        message = exception_error_code.CONF_ERROR + " : " + constants.MSG_CONF_ERROR.format(
            **{'config_file': configfile}) + " : " + str(validator.errors)
        log.error(message, cid)
        log.status(cid, flo.STATUS.ERROR, message + str(validator.errors))
        mail.send(mail_from, mail_to, mail_cc, constants.SUB_CONF_ERROR, mail.STATUS.CRITICAL, data={},
                  message=message)
        sys.exit()

    # loading app configuration to app context
    for conf in configuration_data.keys():
        for key, value in configuration_data.get(conf).items():
            if conf == 'MAIL':
                if key != 'MAIL_FROM':
                    app.app.config[key] = ','.join(value)
                    continue
            app.app.config[key] = value

    log.event(cid, "successfully loaded the configuration ")

    vault_obj = vault.Vault(app.app.config['vault_url'], os.environ[constants.VAULT_NAME])
    app.app.config['vault_obj'] = vault_obj
    # <----- DDO-3032 getting db connection string from vault
    try:
        vault_path = app.app.config['vault_path']
        db_uri = vault_obj.get(vault_path, app.app.config.get('database_url'))
        app.app.config['database_url'] = db_uri
    except (vault.AuthError, vault.VaultSealed, vault.VaultForbidden) as e:
        log.error(e, cid)
        raise VaultObjectError(constants.VAULT_SECRET_FETCH_ERROR) from e
    except Exception as e:
        log.error(e, cid)
        raise VaultObjectError(constants.VAULT_SECRET_FETCH_ERROR) from e
    # END of DDO-3032 ----->
