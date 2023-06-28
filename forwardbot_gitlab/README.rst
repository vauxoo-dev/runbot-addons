#################
forwardbot_gitlab
#################
This is an implementation for a Gitlab bot that automatically creates forward ports for merge
requests that have been successfully merged on previous versions.

*****
Flow
*****
The bot listens for events through `webhooks <https://docs.gitlab.com/ee/user/project/integrations/webhooks.html>`_ and
sends them to a queue to be processed. As of now, the only events that are handled are those related to merge requests.
