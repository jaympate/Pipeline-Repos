import sentry_sdk,sys,os
from swagger_server import constants
flo_env = os.environ.get(constants.ENV_NAME)
if flo_env is None or len(flo_env.strip()) == 0:
    print(constants.ENV_NAME + " env variable not set cannot start server")
    sys.exit()


try:
    if flo_env == constants.APAC_REGION:
        sentry_sdk.init(constants.SENTRY_URL_APAC, environment=flo_env, release=constants.PROJECT_RELEASE)
    else:
        sentry_sdk.init(constants.SENTRY_URL_NA, environment=flo_env, release=constants.PROJECT_RELEASE)
except Exception as e:
    print(constants.MSG_SENTRY_ERROR + str(e))
