def get_api_data(env):
    config = env["ir.config_parameter"].sudo()
    token = config.get_param("forwardbot_gitlab.token")
    url = config.get_param("forwardbot_gitlab.base_url")

    return url, token
